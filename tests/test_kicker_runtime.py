"""Source contracts and a timing model for the opt-in Kicker adapter.

These tests do not execute Papyrus or substitute for Skyrim save/load testing.
The model checks bounded scheduling, stale callbacks, and menu deferral; source
contracts connect those expectations to the shipped adapter entry points.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "src" / "compat" / "jaxonz-kicker"


def body(source: str, name: str) -> str:
    found = re.search(
        rf"(?ims)^\s*(?:Bool\s+)?(?:Event|Function)\s+{name}\([^\n]*\)\s*\n(.*?)^\s*End(?:Event|Function)\b",
        source,
    )
    if not found:
        raise AssertionError(f"missing Papyrus body: {name}")
    return found.group(1)


@dataclass
class KickerModel:
    """Event-level specification; deliberately not an in-game runtime claim."""

    pending: bool = False
    waiting: bool = False
    ready: bool = False
    start: float = 0.0
    resume_time: float = 0.0
    ready_delay: int = 10
    maximum_delay: int = 30
    scheduled: float | None = None
    schedule_count: int = 0
    generation: int = 0
    in_flight: bool = False
    failed_attempts: int = 0
    retry_not_before: float = 0.0
    retry_delay: float = 2.0
    open_menus: set[str] = field(default_factory=set)
    manager_exists: bool = True
    manager_acknowledges: bool = True
    defer_manager_reply: bool = False
    attempts: list[float] = field(default_factory=list)
    manager_calls: list[int] = field(default_factory=list)
    notifications: int = 0
    registrations: int = 0
    menu_registrations: set[str] = field(default_factory=set)
    menu_probe_hook: Callable[[KickerModel, float], None] | None = None

    def load(self, now: float) -> None:
        self.generation += 1
        self.pending = False
        self.in_flight = False
        self.failed_attempts = 0
        self.retry_not_before = 0.0
        self.retry_delay = 2.0
        self.scheduled = None
        self.registrations += 1
        self.menu_registrations = {"Journal Menu", "RaceSex Menu"}
        self.ready = False
        self.waiting = False
        self.resume_time = 0.0
        if not 1 <= self.ready_delay <= 30:
            self.ready_delay = 10
        if not self.ready_delay <= self.maximum_delay <= 30:
            self.maximum_delay = 30
        self.start = now
        self.pending = True
        self.schedule_at(now + self.ready_delay)

    def schedule_at(self, deadline: float) -> None:
        if not self.pending or self.waiting or self.scheduled == deadline:
            return
        self.scheduled = deadline
        self.schedule_count += 1

    def manager_ready(self, now: float) -> None:
        self.ready = True
        if self.pending and not self.waiting and now - self.start >= self.ready_delay:
            self.evaluate(now)

    def update(self, now: float) -> None:
        if self.scheduled is not None and now >= self.scheduled:
            self.scheduled = None
        self.evaluate(now)

    def evaluate(self, now: float) -> None:
        if not self.pending or self.waiting or self.in_flight:
            return
        deadline = max(self.resume_time, self.retry_not_before)
        if now < deadline:
            self.schedule_at(deadline)
            return
        elapsed = max(0.0, now - self.start)
        if elapsed >= self.maximum_delay or (self.ready and elapsed >= self.ready_delay):
            self.try_refresh(now)
        else:
            delay = self.ready_delay if elapsed < self.ready_delay else self.maximum_delay
            self.schedule_at(self.start + delay)

    def close_menu(self, name: str, now: float = 0.0) -> None:
        self.open_menus.discard(name)
        if self.pending and self.waiting and name in self.menu_registrations:
            if not self.open_menus & {"Journal Menu", "RaceSex Menu"}:
                self.waiting = False
                self.resume_time = now + 1.0
                self.schedule_at(max(self.resume_time, self.retry_not_before))

    def try_refresh(self, now: float) -> None:
        if not self.pending or self.in_flight:
            return
        generation = self.generation
        self.in_flight = True
        self.scheduled = None
        self.waiting = True
        blocked = self.probe_menus(now)
        if generation != self.generation:
            return
        if not self.waiting:
            self.in_flight = False
            self.evaluate(now)
            return
        if blocked:
            self.in_flight = False
            return
        self.waiting = False
        self.attempts.append(now)
        if self.manager_exists:
            self.manager_calls.append(generation)
            if self.defer_manager_reply:
                return
        self.complete_attempt(generation, self.manager_exists and self.manager_acknowledges, now)

    def complete_attempt(self, generation: int, acknowledged: bool, now: float) -> None:
        if generation != self.generation:
            return
        if acknowledged:
            self.finish()
            self.notifications += 1
            return
        self.waiting = True
        blocked = self.probe_menus(now)
        if generation != self.generation:
            return
        self.failed_attempts += 1
        if self.failed_attempts >= 6:
            self.finish()
            return
        self.retry_not_before = now + self.retry_delay
        self.retry_delay = min(8.0, 2.0 * self.retry_delay)
        if blocked and self.waiting:
            self.in_flight = False
        else:
            self.waiting = False
            self.in_flight = False
            self.schedule_at(max(self.retry_not_before, self.resume_time))

    def probe_menus(self, now: float) -> bool:
        blocked = bool(self.open_menus & {"Journal Menu", "RaceSex Menu"})
        hook, self.menu_probe_hook = self.menu_probe_hook, None
        if hook is not None:
            hook(self, now)
        return blocked

    def finish(self) -> None:
        self.pending = False
        self.in_flight = False
        self.waiting = False
        self.scheduled = None
        self.menu_registrations.clear()


def checker_model(*, exact_kicker: bool, manager: bool, skyui: bool,
                  required: int = 1, warn: int = 1) -> tuple[bool, str | None]:
    """Return result and warning kind, preserving even upstream's zero quirk."""
    if not skyui and exact_kicker and manager:
        return bool(required), "manager" if warn == 2 else None
    message = None
    if warn == 0:
        pass
    elif skyui and warn == 2:
        message = "installed"
    elif not skyui and required == 1:
        message = "optional"
    elif not skyui:  # Original property-to-itself comparison is always true.
        message = "required"
    return skyui and bool(required), message


class KickerSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.alias = (ADAPTER / "JaxonzMCMKicker.psc").read_text(encoding="utf-8")
        cls.checker = (ADAPTER / "JaxonzSKSEVersionCheckScript.psc").read_text(encoding="utf-8")

    def test_alias_preserves_original_fields_and_entry_points(self) -> None:
        for declaration in ("Bool bMCMready", "Int iWaitSeconds", "Int iMCMregdelay = 10", "Int iMaxWait = 30"):
            self.assertIn(declaration, self.alias)
        self.assertIn("extends ReferenceAlias", self.alias)
        self.assertIn("BeginLoadCycle()", body(self.alias, "OnInit"))
        self.assertIn("BeginLoadCycle()", body(self.alias, "OnPlayerLoadGame"))
        body(self.alias, "OnConfigManagerReady")
        body(self.alias, "OnUpdate")

    def test_each_load_rearms_registrations_and_discards_old_cycle(self) -> None:
        load = body(self.alias, "BeginLoadCycle")
        self.assertIn('RegisterForModEvent("SKICP_configManagerReady", "OnConfigManagerReady")', load)
        self.assertLess(load.index("UnregisterForUpdate()"), load.index("ScheduleUpdateAt("))
        self.assertIn("_cycleGeneration += 1", load)
        self.assertIn("_attemptInFlight = False", load)
        self.assertIn("_failedAttempts = 0", load)
        self.assertIn("_retryNotBefore = 0.0", load)
        self.assertIn("bMCMready = False", load)
        self.assertIn("iWaitSeconds = 0", load)
        self.assertIn("_waitingForMenuClose = False", load)
        self.assertIn("_loadStartTime = Utility.GetCurrentRealTime()", load)
        for menu in ("Journal Menu", "RaceSex Menu"):
            self.assertIn(f'RegisterForMenu("{menu}")', load)

    def test_timing_is_bounded_and_does_not_count_callback_duplicates(self) -> None:
        evaluate = body(self.alias, "EvaluateRefresh")
        self.assertIn("Float now = Utility.GetCurrentRealTime()", evaluate)
        self.assertIn("Float elapsed = now - _loadStartTime", evaluate)
        self.assertIn("elapsed >= iMaxWait", evaluate)
        self.assertIn("bMCMready && elapsed >= iMCMregdelay", evaluate)
        self.assertNotIn("iWaitSeconds +=", self.alias)
        self.assertNotIn("RegisterForUpdate(", self.alias)
        self.assertNotIn("Utility.Wait", self.alias)
        self.assertIn("iMaxWait > 30", body(self.alias, "BeginLoadCycle"))

    def test_refresh_defers_with_no_timer_until_relevant_menu_close(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        guard = attempt[attempt.index('; Arm before the native query'):attempt.index("SKI_ConfigManager manager")]
        self.assertIn('UI.IsMenuOpen("RaceSex Menu")', guard)
        self.assertIn("_waitingForMenuClose = True", guard)
        self.assertNotIn("UnregisterForUpdate()", guard)
        self.assertLess(attempt.index("UnregisterForUpdate()"), attempt.index("_waitingForMenuClose = True"))
        self.assertIn("Return", guard)
        self.assertNotIn("RegisterForSingleUpdate", guard)
        close = body(self.alias, "OnMenuClose")
        self.assertIn("_refreshPending && _waitingForMenuClose", close)
        self.assertNotIn("TryRefresh()", close)
        self.assertIn('Float resumeTime = Utility.GetCurrentRealTime() + 1.0', close)
        self.assertIn('_menuResumeTime = resumeTime', close)
        self.assertIn("If _retryNotBefore > deadline", close)
        self.assertIn("ScheduleUpdateAt(deadline)", close)
        self.assertIn("Float nextAttemptTime = _menuResumeTime", body(self.alias, "EvaluateRefresh"))

    def test_refresh_requires_actual_manager_acknowledgement_not_stage_acceptance(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        self.assertIn('SKI_ConfigManager manager = Quest.GetQuest("SKI_ConfigManagerInstance") as SKI_ConfigManager', attempt)
        self.assertLess(attempt.index("If manager != None"), attempt.index("manager.OpenMCM_TryForceReset()"))
        self.assertIn("resetAcknowledged = manager.OpenMCM_TryForceReset()", attempt)
        self.assertRegex(attempt, r"If resetAcknowledged\s+FinishLoadCycle\(\)\s+Debug.Notification\(")
        self.assertNotIn("_refreshPending = False", attempt)
        for forbidden in (".SetStage(", ".ForceReset(", "SendModEvent(", "OpenMCM_ConfigBase", "GoToState("):
            self.assertNotIn(forbidden, self.alias)

    def test_failed_calls_have_bounded_backoff_and_no_false_success(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        self.assertIn("_failedAttempts += 1", attempt)
        self.assertIn("If _failedAttempts >= 6", attempt)
        self.assertIn("_retryNotBefore = retryStartTime + _retryDelay", attempt)
        self.assertIn("_retryDelay *= 2.0", attempt)
        self.assertIn("If _retryDelay > 8.0", attempt)
        self.assertIn("Float deadline = _retryNotBefore", attempt)
        self.assertIn("ScheduleUpdateAt(deadline)", attempt)
        evaluate = body(self.alias, "EvaluateRefresh")
        self.assertIn("If _retryNotBefore > nextAttemptTime", evaluate)
        self.assertLess(evaluate.index("If now < nextAttemptTime"), evaluate.index("TryRefresh()"))
        self.assertIn("_scheduledUpdateTime == deadline", body(self.alias, "ScheduleUpdateAt"))

    def test_in_flight_and_generation_guards_protect_new_load(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        self.assertIn("If !_refreshPending || _attemptInFlight", attempt)
        self.assertLess(attempt.index("_attemptInFlight = True"), attempt.index("Quest.GetQuest"))
        completion = attempt[attempt.index("resetAcknowledged = manager.OpenMCM_TryForceReset()") :]
        self.assertLess(completion.index("If generation != _cycleGeneration"), completion.index("_attemptInFlight = False"))
        self.assertLess(completion.index("If generation != _cycleGeneration"), completion.index("_failedAttempts += 1"))
        self.assertIn("_attemptInFlight", body(self.alias, "EvaluateRefresh"))

    def test_retry_gate_stays_held_until_deadline_and_generation_are_checked(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        failure = attempt[attempt.index("Float retryStartTime = Utility.GetCurrentRealTime()") :]
        query = failure[failure.index('Bool menuOpen = UI.IsMenuOpen("Journal Menu")'):]
        self.assertLess(query.index("If generation != _cycleGeneration"), query.index("_failedAttempts += 1"))
        self.assertLess(failure.index("_retryNotBefore = retryStartTime + _retryDelay"), failure.index("_attemptInFlight = False"))
        finish = body(self.alias, "FinishLoadCycle")
        self.assertLess(finish.index("_refreshPending = False"), finish.index("_attemptInFlight = False"))

    def test_menu_close_is_armed_before_query_and_observed_close_keeps_grace(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        self.assertLess(attempt.index("_waitingForMenuClose = True"), attempt.index('Bool menuBlocked = UI.IsMenuOpen'))
        self.assertLess(attempt.index("If !_waitingForMenuClose"), attempt.index("If menuBlocked"))
        self.assertIn("EvaluateRefresh()", attempt)
        failure = attempt[attempt.index("Float retryStartTime") :]
        self.assertLess(failure.index("_waitingForMenuClose = True"), failure.index('Bool menuOpen = UI.IsMenuOpen'))
        self.assertIn("If menuOpen && _waitingForMenuClose", failure)
        self.assertIn("If _menuResumeTime > deadline", failure)

    def test_menu_wait_cleanup_cannot_cancel_a_concurrently_scheduled_close_grace(self) -> None:
        attempt = body(self.alias, "TryRefresh")
        initial_wait = attempt[attempt.index("If menuBlocked") : attempt.index("SKI_ConfigManager manager")]
        retry_wait = attempt[attempt.index("If menuOpen && _waitingForMenuClose") :]
        for branch in (initial_wait, retry_wait):
            self.assertNotIn("UnregisterForUpdate()", branch)
            self.assertNotIn("_scheduledUpdateTime = 0.0", branch)
        self.assertEqual(attempt.count("UnregisterForUpdate()"), 1)

    def test_checker_keeps_saved_fields_properties_and_functions(self) -> None:
        for declaration in (
            'String Property strModName Auto',
            'String Property sSKSEVersionRequired = "2.0.17" Auto',
            'Int Property iMinVersionRelease = 46 Auto',
            'Int Property iWarnUser = 1 Auto',
            'Int Property iSkyUIRequired = 1 Auto',
            'String Property sUserWarningMessage Auto',
            'Int iWarnNever = 0', 'Int iWarnOnFail = 1', 'Int iWarnAlways = 2',
            'Int iSkyUINotRequired = 0', 'Int iSkyUINotOptional = 1', 'Int iSkyUIRequired = 2',
        ):
            self.assertIn(declaration, self.checker)
        init = body(self.checker, "OnInit")
        self.assertIn("CheckSKSEVersion(iWarnUser)", init)
        self.assertIn("CheckSkyUIVersion(iWarnUser)", init)

    def test_manager_exception_requires_exact_quest_and_absent_full_skyui(self) -> None:
        check = body(self.checker, "CheckSkyUIVersion")
        self.assertIn('Bool bSkyUIInstalled = Quest.GetQuest("SKI_MainInstance")', check)
        self.assertIn('If !bSkyUIInstalled && Self == Game.GetFormFromFile(0x000D62, "JaxonzMCMKicker.esp")', check)
        self.assertIn('Quest mcmManager = Quest.GetQuest("SKI_ConfigManagerInstance")', check)
        self.assertIn("If mcmManager != None", check)
        self.assertNotIn('strModName ==', check)
        self.assertIn("Return Self.iSkyUIRequired as Bool", check)

    def test_other_checker_branches_keep_upstream_warning_and_return_semantics(self) -> None:
        check = body(self.checker, "CheckSkyUIVersion")
        self.assertIn("Self.iSkyUIRequired == Self.iSkyUIRequired", check)
        self.assertIn("If iWarnUserFlag == iWarnNever", check)
        self.assertIn("ElseIf bSkyUIInstalled && (iWarnUserFlag == iWarnAlways)", check)
        self.assertIn("Some features may not be availalble.", check)
        self.assertIn("will not run correctly without it. Please install SkyUI.", check)
        self.assertIn("Return bSkyUIInstalled && Self.iSkyUIRequired", check)

    def test_skse_gate_is_independent_of_manager_exception(self) -> None:
        check = body(self.checker, "CheckSKSEVersion")
        for function in ("GetVersionRelease", "GetVersion", "GetVersionMinor", "GetVersionBeta"):
            self.assertIn(f"SKSE.{function}()", check)
        self.assertIn("SKSE.GetVersionRelease() < iMinVersionRelease", check)
        self.assertIn("Return bGoodEnough", check)
        self.assertNotIn("GetFormFromFile", check)
        self.assertNotIn("GetQuest", check)

    def test_adapted_sources_credit_upstream_and_do_not_claim_mit(self) -> None:
        for source in (self.alias, self.checker):
            self.assertIn("Jaxonz", source)
            self.assertIn("insaneplumber", source)
            self.assertIn("https://www.nexusmods.com/skyrimspecialedition/mods/36801", source)
            self.assertIn("noncommercial use", source)
            self.assertIn("not relicensed under MIT", source)


class KickerTimingModelTests(unittest.TestCase):
    def test_ready_manager_refreshes_after_ten_seconds_once(self) -> None:
        runtime = KickerModel()
        runtime.load(100)
        runtime.manager_ready(102)
        runtime.update(109.9)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 110)
        runtime.update(110)
        runtime.update(130)
        runtime.manager_ready(135)
        self.assertEqual(runtime.attempts, [110])
        self.assertEqual(runtime.notifications, 1)
        self.assertIsNone(runtime.scheduled)

    def test_missing_readiness_uses_single_thirty_second_fallback(self) -> None:
        runtime = KickerModel()
        runtime.load(0)
        runtime.update(10)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 30)
        runtime.update(30)
        runtime.update(31)
        self.assertEqual(runtime.attempts, [30])
        self.assertIsNone(runtime.scheduled)

    def test_late_readiness_does_not_have_to_wait_until_timeout(self) -> None:
        runtime = KickerModel()
        runtime.load(0)
        runtime.update(10)
        runtime.manager_ready(19)
        self.assertEqual(runtime.attempts, [19])

    def test_pending_saved_cycle_and_queued_callbacks_are_rearmed(self) -> None:
        runtime = KickerModel(pending=True, waiting=True, ready=True, start=-100, scheduled=1)
        runtime.load(50)
        self.assertFalse(runtime.ready)
        self.assertFalse(runtime.waiting)
        for _ in range(20):
            runtime.update(51)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 60)
        runtime.manager_ready(52)
        runtime.update(60)
        self.assertEqual(runtime.attempts, [60])

    def test_both_menus_must_close_and_unrelated_close_does_not_resume(self) -> None:
        runtime = KickerModel(open_menus={"Journal Menu", "RaceSex Menu"})
        runtime.load(0)
        runtime.manager_ready(5)
        runtime.update(10)
        self.assertTrue(runtime.waiting)
        self.assertIsNone(runtime.scheduled)
        runtime.close_menu("InventoryMenu")
        runtime.close_menu("Journal Menu")
        for now in (30, 60, 100):
            runtime.update(now)
            runtime.manager_ready(now)
        self.assertEqual(runtime.attempts, [])
        runtime.close_menu("RaceSex Menu", 100)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 101)
        runtime.manager_ready(100.5)
        runtime.update(100.5)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 101)
        runtime.update(101)
        runtime.close_menu("Journal Menu", 102)
        self.assertEqual(runtime.attempts, [101])
        self.assertEqual(runtime.menu_registrations, set())

    def test_reopened_menu_during_close_delay_defers_again_without_polling(self) -> None:
        runtime = KickerModel(open_menus={"Journal Menu"})
        runtime.load(0)
        runtime.update(30)
        runtime.close_menu("Journal Menu", 31)
        runtime.open_menus.add("RaceSex Menu")
        runtime.update(32)
        self.assertTrue(runtime.waiting)
        self.assertIsNone(runtime.scheduled)
        self.assertEqual(runtime.attempts, [])
        runtime.close_menu("RaceSex Menu", 40)
        runtime.update(41)
        self.assertEqual(runtime.attempts, [41])

    def test_load_while_previously_waiting_starts_new_delay(self) -> None:
        runtime = KickerModel(open_menus={"Journal Menu"})
        runtime.load(0)
        runtime.update(30)
        runtime.load(100)
        runtime.close_menu("Journal Menu")
        self.assertEqual(runtime.attempts, [])
        runtime.update(110)
        self.assertEqual(runtime.attempts, [])
        runtime.update(130)
        self.assertEqual(runtime.attempts, [130])
        self.assertEqual(runtime.registrations, 2)

    def test_missing_manager_or_busy_manager_exhausts_bounded_retries_without_success(self) -> None:
        for exists, succeeds in ((False, True), (True, False)):
            with self.subTest(exists=exists, succeeds=succeeds):
                runtime = KickerModel(manager_exists=exists, manager_acknowledges=succeeds)
                runtime.load(0)
                for now in (30, 32, 36, 44, 52, 60):
                    runtime.update(now)
                runtime.update(100)
                self.assertEqual(runtime.attempts, [30, 32, 36, 44, 52, 60])
                self.assertEqual(runtime.manager_calls, [1] * 6 if exists else [])
                self.assertEqual(runtime.notifications, 0)
                self.assertFalse(runtime.pending)
                self.assertIsNone(runtime.scheduled)
                self.assertEqual(runtime.menu_registrations, set())

    def test_next_load_permits_one_new_attempt(self) -> None:
        runtime = KickerModel()
        for now in (0, 100, 200):
            runtime.load(now)
            runtime.update(now + 30)
            runtime.update(now + 35)
        self.assertEqual(runtime.attempts, [30, 130, 230])
        self.assertEqual(runtime.registrations, 3)

    def test_invalid_saved_timing_values_are_bounded(self) -> None:
        for early, maximum in ((0, 0), (-10, -20), (999, 999), (10, 2)):
            with self.subTest(early=early, maximum=maximum):
                runtime = KickerModel(ready_delay=early, maximum_delay=maximum)
                runtime.load(0)
                runtime.update(30)
                self.assertEqual(runtime.attempts, [30])

    def test_busy_false_keeps_pending_until_later_actual_acknowledgement(self) -> None:
        runtime = KickerModel(manager_acknowledges=False)
        runtime.load(0)
        runtime.update(30)
        self.assertTrue(runtime.pending)
        self.assertEqual(runtime.notifications, 0)
        self.assertEqual(runtime.failed_attempts, 1)
        self.assertEqual(runtime.scheduled, 32)
        runtime.manager_acknowledges = True
        runtime.update(32)
        self.assertFalse(runtime.pending)
        self.assertEqual(runtime.notifications, 1)
        self.assertEqual(runtime.attempts, [30, 32])

    def test_readiness_and_stale_updates_cannot_bypass_backoff_or_duplicate_timers(self) -> None:
        runtime = KickerModel(manager_acknowledges=False)
        runtime.load(0)
        runtime.update(30)
        schedules = runtime.schedule_count
        for _ in range(100):
            runtime.manager_ready(30.5)
            runtime.update(31)
        self.assertEqual(runtime.attempts, [30])
        self.assertEqual(runtime.schedule_count, schedules)
        self.assertEqual(runtime.scheduled, 32)
        runtime.update(32)
        self.assertEqual(runtime.attempts, [30, 32])
        self.assertEqual(runtime.scheduled, 36)

    def test_in_flight_duplicate_callbacks_do_not_start_another_request(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        for _ in range(20):
            runtime.manager_ready(31)
            runtime.update(31)
        self.assertEqual(runtime.attempts, [30])
        self.assertTrue(runtime.pending)
        self.assertEqual(runtime.notifications, 0)
        runtime.complete_attempt(1, True, 32)
        self.assertFalse(runtime.pending)
        self.assertEqual(runtime.notifications, 1)

    def test_old_load_completion_cannot_consume_new_cycle_or_clear_its_inflight_guard(self) -> None:
        for stale_ack in (False, True):
            with self.subTest(stale_ack=stale_ack):
                runtime = KickerModel(defer_manager_reply=True)
                runtime.load(0)
                runtime.update(30)
                runtime.load(100)
                runtime.update(130)
                runtime.complete_attempt(1, stale_ack, 131)
                self.assertTrue(runtime.pending)
                self.assertTrue(runtime.in_flight)
                self.assertEqual(runtime.failed_attempts, 0)
                self.assertEqual(runtime.notifications, 0)
                runtime.complete_attempt(2, False, 132)
                self.assertFalse(runtime.in_flight)
                self.assertEqual(runtime.failed_attempts, 1)
                self.assertEqual(runtime.scheduled, 134)

    def test_open_menu_during_false_reply_defers_without_polling_or_spending_retry_budget(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        runtime.open_menus.add("Journal Menu")
        runtime.complete_attempt(1, False, 31)
        self.assertTrue(runtime.waiting)
        self.assertIsNone(runtime.scheduled)
        for now in (32, 40, 100):
            runtime.manager_ready(now)
            runtime.update(now)
        self.assertEqual(runtime.attempts, [30])
        self.assertEqual(runtime.failed_attempts, 1)
        runtime.close_menu("Journal Menu", 100)
        runtime.update(100.5)
        self.assertEqual(runtime.attempts, [30])
        runtime.update(101)
        self.assertEqual(runtime.attempts, [30, 101])

    def test_menu_close_grace_cannot_shorten_retry_backoff(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        runtime.open_menus.add("RaceSex Menu")
        runtime.complete_attempt(1, False, 31)
        runtime.close_menu("RaceSex Menu", 31.1)
        self.assertEqual(runtime.scheduled, 33)
        runtime.update(32.1)
        self.assertEqual(runtime.attempts, [30])
        runtime.update(33)
        self.assertEqual(runtime.attempts, [30, 33])

    def test_menu_closing_during_initial_probe_does_not_lose_close_event(self) -> None:
        runtime = KickerModel(open_menus={"Journal Menu"})
        runtime.load(0)
        runtime.menu_probe_hook = lambda model, now: model.close_menu("Journal Menu", now)
        runtime.update(30)
        self.assertFalse(runtime.waiting)
        self.assertEqual(runtime.attempts, [])
        self.assertEqual(runtime.scheduled, 31)
        runtime.update(31)
        self.assertEqual(runtime.attempts, [31])
        self.assertEqual(runtime.notifications, 1)

    def test_menu_closing_during_failed_reply_probe_preserves_backoff(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        runtime.open_menus.add("RaceSex Menu")
        runtime.menu_probe_hook = lambda model, now: model.close_menu("RaceSex Menu", now)
        runtime.complete_attempt(1, False, 31)
        self.assertFalse(runtime.waiting)
        self.assertEqual(runtime.scheduled, 33)
        runtime.update(32)
        self.assertEqual(runtime.attempts, [30])
        runtime.update(33)
        self.assertEqual(runtime.attempts, [30, 33])

    def test_readiness_during_failed_reply_probe_does_not_reenter_before_deadline(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        runtime.menu_probe_hook = lambda model, now: (model.manager_ready(now), model.update(now))
        runtime.complete_attempt(1, False, 31)
        self.assertEqual(runtime.attempts, [30])
        self.assertEqual(runtime.scheduled, 33)
        self.assertEqual(runtime.failed_attempts, 1)

    def test_load_during_failed_reply_probe_does_not_mutate_new_cycle(self) -> None:
        runtime = KickerModel(defer_manager_reply=True)
        runtime.load(0)
        runtime.update(30)
        runtime.menu_probe_hook = lambda model, now: model.load(100)
        runtime.complete_attempt(1, False, 31)
        self.assertEqual(runtime.generation, 2)
        self.assertEqual(runtime.failed_attempts, 0)
        self.assertFalse(runtime.in_flight)
        self.assertEqual(runtime.scheduled, 110)
        self.assertEqual(runtime.notifications, 0)


class KickerCheckerModelTests(unittest.TestCase):
    def test_exact_kicker_accepts_standalone_manager(self) -> None:
        self.assertEqual(checker_model(exact_kicker=True, manager=True, skyui=False), (True, None))
        self.assertEqual(checker_model(exact_kicker=True, manager=True, skyui=False, warn=2), (True, "manager"))

    def test_other_jaxonz_quest_does_not_gain_manager_exception(self) -> None:
        self.assertEqual(checker_model(exact_kicker=False, manager=True, skyui=False), (False, "optional"))
        self.assertEqual(checker_model(exact_kicker=False, manager=True, skyui=False, required=2), (False, "required"))

    def test_full_skyui_keeps_original_branch_for_kicker_and_other_quests(self) -> None:
        for exact in (False, True):
            self.assertEqual(checker_model(exact_kicker=exact, manager=True, skyui=True, warn=2), (True, "installed"))

    def test_missing_manager_still_warns_and_never_warn_and_zero_property_are_preserved(self) -> None:
        self.assertEqual(checker_model(exact_kicker=True, manager=False, skyui=False), (False, "optional"))
        self.assertEqual(checker_model(exact_kicker=True, manager=False, skyui=False, warn=0), (False, None))
        self.assertEqual(checker_model(exact_kicker=False, manager=True, skyui=True, required=0, warn=2), (False, "installed"))
        self.assertEqual(checker_model(exact_kicker=False, manager=True, skyui=False, required=0), (False, "required"))


if __name__ == "__main__":
    unittest.main()
