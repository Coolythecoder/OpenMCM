Scriptname JaxonzMCMKicker extends ReferenceAlias

; OpenMCM compatibility adaptation of Jaxonz MCM Kicker by Jaxonz.
; SE port by insaneplumber: https://www.nexusmods.com/skyrimspecialedition/mods/36801
; Distributed under the upstream permission to modify with credit, for
; noncommercial use. This adapted script is not relicensed under MIT.
; Requires the original JaxonzMCMKicker.esp and its player alias.

; Keep all four upstream fields and their defaults for existing saves.
Bool bMCMready
Int iWaitSeconds
Int iMCMregdelay = 10
Int iMaxWait = 30

Bool _refreshPending = False
Bool _waitingForMenuClose = False
Float _loadStartTime = 0.0
Float _menuResumeTime = 0.0
Int _cycleGeneration = 0
Bool _attemptInFlight = False
Int _failedAttempts = 0
Float _retryNotBefore = 0.0
Float _retryDelay = 2.0
Float _scheduledUpdateTime = 0.0

Event OnInit()
	BeginLoadCycle()
EndEvent

Event OnPlayerLoadGame()
	BeginLoadCycle()
EndEvent

Function BeginLoadCycle()
	; Registrations and a pending update can survive in a save. Re-arm the
	; cycle on every load, including installation over the original script.
	_cycleGeneration += 1
	_refreshPending = False
	_attemptInFlight = False
	_failedAttempts = 0
	_retryNotBefore = 0.0
	_retryDelay = 2.0
	_scheduledUpdateTime = 0.0
	UnregisterForUpdate()
	UnregisterForMenu("Journal Menu")
	UnregisterForMenu("RaceSex Menu")
	RegisterForModEvent("SKICP_configManagerReady", "OnConfigManagerReady")
	RegisterForMenu("Journal Menu")
	RegisterForMenu("RaceSex Menu")
	bMCMready = False
	iWaitSeconds = 0
	_waitingForMenuClose = False
	_menuResumeTime = 0.0
	; Bound old saved timing fields while retaining the upstream 10/30s intent.
	If iMCMregdelay < 1 || iMCMregdelay > 30
		iMCMregdelay = 10
	EndIf
	If iMaxWait < iMCMregdelay || iMaxWait > 30
		iMaxWait = 30
	EndIf
	_loadStartTime = Utility.GetCurrentRealTime()
	_refreshPending = True
	ScheduleUpdateAt(_loadStartTime + (iMCMregdelay as Float))
EndFunction

Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	bMCMready = True
	If _refreshPending && !_waitingForMenuClose
		If Utility.GetCurrentRealTime() - _loadStartTime >= iMCMregdelay
			EvaluateRefresh()
		EndIf
	EndIf
EndEvent

Event OnUpdate()
	; Early callbacks left over from a save must not discard a new timer.
	If Utility.GetCurrentRealTime() >= _scheduledUpdateTime
		_scheduledUpdateTime = 0.0
	EndIf
	If _refreshPending && !_waitingForMenuClose
		EvaluateRefresh()
	EndIf
EndEvent

Function EvaluateRefresh()
	If !_refreshPending || _waitingForMenuClose || _attemptInFlight
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	Float nextAttemptTime = _menuResumeTime
	If _retryNotBefore > nextAttemptTime
		nextAttemptTime = _retryNotBefore
	EndIf
	If now < nextAttemptTime
		; Menu-close handlers on the manager must finish before its reset.
		; Readiness and stale update events also honor this one-shot delay.
		ScheduleUpdateAt(nextAttemptTime)
		Return
	EndIf
	Float elapsed = now - _loadStartTime
	; A queued update from the save must not advance the current load's timer.
	If elapsed < 0.0
		elapsed = 0.0
	EndIf
	iWaitSeconds = elapsed as Int
	If iWaitSeconds > iMaxWait
		iWaitSeconds = iMaxWait
	EndIf
	If elapsed >= iMaxWait || (bMCMready && elapsed >= iMCMregdelay)
		TryRefresh()
	Else
		Float deadline = _loadStartTime + (iMaxWait as Float)
		If elapsed < iMCMregdelay
			deadline = _loadStartTime + (iMCMregdelay as Float)
		EndIf
		; Absolute deadlines keep duplicate queued events from speeding up
		; the cycle or creating a persistent once-per-second update chain.
		ScheduleUpdateAt(deadline)
	EndIf
EndFunction

Event OnMenuClose(String menuName)
	If _refreshPending && _waitingForMenuClose
		If menuName == "Journal Menu" || menuName == "RaceSex Menu"
			Int generation = _cycleGeneration
			If !UI.IsMenuOpen("Journal Menu") && !UI.IsMenuOpen("RaceSex Menu")
				Float resumeTime = Utility.GetCurrentRealTime() + 1.0
				If generation != _cycleGeneration
					Return
				EndIf
				_waitingForMenuClose = False
				_menuResumeTime = resumeTime
				Float deadline = _menuResumeTime
				If _retryNotBefore > deadline
					deadline = _retryNotBefore
				EndIf
				ScheduleUpdateAt(deadline)
			EndIf
		EndIf
	EndIf
EndEvent

Function TryRefresh()
	If !_refreshPending || _attemptInFlight
		Return
	EndIf
	Int generation = _cycleGeneration
	_attemptInFlight = True
	; Cancel the previous timer before arming the close event. Never cancel
	; after a menu query: its close handler may already have armed the grace.
	_scheduledUpdateTime = 0.0
	UnregisterForUpdate()
	If generation != _cycleGeneration
		Return
	EndIf
	; Resetting the registry while an MCM page is live can invalidate its
	; option IDs. Character creation must finish before the refresh too.
	; Arm before the native query: a close event during that query must not
	; be lost and leave this cycle waiting for a menu that already closed.
	_waitingForMenuClose = True
	Bool menuBlocked = UI.IsMenuOpen("Journal Menu") || UI.IsMenuOpen("RaceSex Menu")
	If generation != _cycleGeneration
		Return
	EndIf
	If !_waitingForMenuClose
		; The close handler observed the transition while we queried menus.
		_attemptInFlight = False
		EvaluateRefresh()
		Return
	EndIf
	If menuBlocked
		_attemptInFlight = False
		Return
	EndIf
	_waitingForMenuClose = False
	SKI_ConfigManager manager = Quest.GetQuest("SKI_ConfigManagerInstance") as SKI_ConfigManager
	If generation != _cycleGeneration
		Return
	EndIf
	Bool resetAcknowledged = False
	If manager != None
		; This matching OpenMCM host returns true only after it actually resets
		; the registry. Quest stage acceptance and readiness events are not ack.
		resetAcknowledged = manager.OpenMCM_TryForceReset()
	EndIf
	; A pre-load stack can resume after a new cycle has started. It must not
	; clear the new in-flight guard, spend its retries, or report stale success.
	If generation != _cycleGeneration
		Return
	EndIf
	If resetAcknowledged
		FinishLoadCycle()
		Debug.Notification("Jaxonz MCM Kicker reset acknowledged... May take 1 minute for mod menus")
	Else
		; Keep the in-flight gate held across external clock/menu calls. A
		; readiness handler must not start a retry before its deadline exists.
		Float retryStartTime = Utility.GetCurrentRealTime()
		If generation != _cycleGeneration
			Return
		EndIf
		_waitingForMenuClose = True
		Bool menuOpen = UI.IsMenuOpen("Journal Menu") || UI.IsMenuOpen("RaceSex Menu")
		If generation != _cycleGeneration
			Return
		EndIf
		_failedAttempts += 1
		If _failedAttempts >= 6
			FinishLoadCycle()
			Debug.Trace("[Jaxonz MCM Kicker / OpenMCM] Reset not acknowledged after 6 attempts; stopping this load's refresh.", 1)
		Else
			_retryNotBefore = retryStartTime + _retryDelay
			_retryDelay *= 2.0
			If _retryDelay > 8.0
				_retryDelay = 8.0
			EndIf
			; Do not poll while a protected menu is open, including one opened
			; during the manager call. Closing it resumes this same retry budget.
			If menuOpen && _waitingForMenuClose
				_attemptInFlight = False
			Else
				_waitingForMenuClose = False
				_attemptInFlight = False
				Float deadline = _retryNotBefore
				If _menuResumeTime > deadline
					deadline = _menuResumeTime
				EndIf
				ScheduleUpdateAt(deadline)
			EndIf
		EndIf
	EndIf
EndFunction

Function ScheduleUpdateAt(Float deadline)
	If !_refreshPending || _waitingForMenuClose || _scheduledUpdateTime == deadline
		Return
	EndIf
	Int generation = _cycleGeneration
	Float remaining = deadline - Utility.GetCurrentRealTime()
	If generation != _cycleGeneration
		Return
	EndIf
	If remaining < 0.01
		remaining = 0.01
	EndIf
	UnregisterForUpdate()
	_scheduledUpdateTime = deadline
	RegisterForSingleUpdate(remaining)
EndFunction

Function FinishLoadCycle()
	_refreshPending = False
	_waitingForMenuClose = False
	_scheduledUpdateTime = 0.0
	_attemptInFlight = False
	UnregisterForUpdate()
	UnregisterForMenu("Journal Menu")
	UnregisterForMenu("RaceSex Menu")
EndFunction
