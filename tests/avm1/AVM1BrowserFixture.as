import flash.external.ExternalInterface;

/** Compiled production browser/panel; mock transport/provider data only. */
class AVM1BrowserFixture
{
    private static var checks:Array;
    private static var panel:Object;
    private static var nativeState:String;
    private static var nativePending:String;
    private static var nativeFails:Boolean;
    private static var lastFallback:String;

    public static function sendEvent(name:String, arg:Object, num:Number):Void
    {
        if (name == "OPENMCM_browserStateChanged") lastFallback = String(arg);
        AVM1InteractionProbe.record("modEvent", {name:name, arg:arg, num:num});
    }

    private static function mockNative():Object
    {
        return {
            GetProfileStateChunkCount:function():Number {
                return Math.ceil(AVM1BrowserFixture.nativeState.length / 1024);
            },
            GetProfileStateChunk:function(index:Number):String {
                return AVM1BrowserFixture.nativeState.substr(index * 1024, 1024);
            },
            BeginProfileStateUpdate:function():Boolean {
                AVM1BrowserFixture.nativePending = "";
                return true;
            },
            AppendProfileStateChunk:function(chunk:String):Boolean {
                AVM1BrowserFixture.nativePending += chunk;
                return true;
            },
            CommitProfileStateUpdate:function():Boolean {
                if (AVM1BrowserFixture.nativeFails) return false;
                AVM1BrowserFixture.nativeState = AVM1BrowserFixture.nativePending;
                return true;
            }
        };
    }

    private static function check(name:String, passed:Boolean):Void
    {
        checks.push({name:name, passed:passed});
    }

    public static function snapshot():Object
    {
        var names:Array = [];
        for (var i:Number = 0; i < panel._modNames.length; i++)
            names.push({name:panel._modNames[i].modName, text:panel._modNames[i].text,
                id:panel._modNames[i].modIndex});
        return {names:names, mode:panel._sideMode, state:panel._state,
            dialog:panel._dialog.kind, action:panel._dialog.browserAction,
            input:panel._inputField.text, selected:panel._selectedModRegistryIndex,
            browserVisible:panel._chrome.browserControls._visible,
            data:panel._browser.buildState()};
    }

    public static function main(root:MovieClip):Void
    {
        checks = [];
        AVM1InteractionProbe.prepare(root);
        lastFallback = "";
        _global.skse.SendModEvent = sendEvent;
        var fader:MovieClip = root.createEmptyMovieClip("ConfigPanelFader", 1);
        panel = fader.createEmptyMovieClip("configPanel", 1);
        MCMCompatPanel.install(MovieClip(panel), {});
        var p:Object = panel;
        var b:Object = p._browser;
        p.startPage();
        p.endPage();
        check("Untouched early close cannot publish default preferences", lastFallback == "" && !b.locallyChanged);
        p.startPage();
        p.loadBrowserState("OPENMCMB1|0|0|0|0|0|0|0|0|0|0|F|Zulu");
        check("Preference reply after early close is still accepted", b.preference("Zulu", false).favorite == true);
        p.loadBrowserState("OPENMCMB1|0|0|0|0|0|0|0|0|0|0");
        p.setModNames("Zulu", "", "Alpha", "XPMSE");
        check("Sparse registry IDs preserved after browser sort", p._modNames[0].modIndex == 2 && p._modNames[2].modIndex == 0);
        check("Browser controls are visible in mod list", p._chrome.browserControls._visible);
        b.selected(p._modNames[1]);
        b.action("favorite");
        b.action("favorites");
        check("Favorite filter retains XPMSE's raw ID", p._modNames.length == 1 && p._modNames[0].modIndex == 3);
        b.action("hide");
        check("Hide removes favorite from visible tabs", p._modNames.length == 0);
        b.action("hidden");
        check("Hidden tab recovers same menu", p._modNames.length == 1 && p._modNames[0].modName == "XPMSE");
        b.action("hide");
        b.action("all");
        b.accept("rename", "XPMSE", "Custom styles");
        b.accept("search", "", "xPmSe");
        check("Case insensitive raw-name search survives alias", p._modNames.length == 1 && p._modNames[0].text == "Custom styles");
        b.action("clear");
        b.accept("priority", "Zulu", "1");
        check("Pinned priority leads alphabetical sorting", p._modNames[0].modName == "Zulu");
        var state:String = b.buildState();
        check("New OpenMCM header with favorite record", state.indexOf("OPENMCMB1|") == 0 && state.indexOf("|F|XPMSE") >= 0);
        check("Malformed import is transactional", !b.loadState(state + "|N|Incomplete") && b.buildState() == state);
        b.action("search");
        check("Search uses existing input dialog", p._dialog.kind == "input" && p._dialog.browserAction == "search" && p._textInputOwned);
        p._inputField.text = "missing";
        p._acceptDialog();
        check("Search acceptance restores READY without provider unlock", p._dialog == null && p._state == 0 && p._modNames.length == 0 && !p._textInputOwned);
        b.action("clear");
        p._openBrowserTools();
        check("Browser actions reuse keyboard/controller menu list", p._dialog.kind == "menu" && p._dialog.browserAction == "tools" && p._menuDialogList.entryList.length == 10);
        p._cancelDialog();
        check("Browser menu cancellation restores READY", p._dialog == null && p._state == 0);
        p._selectMod(p._modNames[0]);
        check("Opening filtered menu dispatches raw registry identity", p._selectedModRegistryIndex == 0 && p._sideMode == "pages");
        check("Browser controls are hidden on provider pages", !p._chrome.browserControls._visible);
        p.unlock(false);
        p._goBack();
        check("Back restores browser controls", p._sideMode == "mods" && p._chrome.browserControls._visible);
        nativeState = "OPENMCMB1|0|0|0|0|9|0|0|0|0|0|N|XPMSE|Old";
        nativeFails = true;
        _global.skse.plugins = {OpenMCMBrowser:mockNative()};
        p._browser = b = new MCMCompatBrowser(p);
        b.save();
        check("Global scroll is not overwritten before names arrive", b.scrolls[0] == 9 && nativeState.split("|")[5] == "9");
        p.loadBrowserState("");
        p.setModNames("Zulu", "", "Alpha", "XPMSE");
        b.accept("rename", "XPMSE", "Recovered styles");
        var recovery:String = lastFallback;
        check("Failed shared commit marks only local fallback", recovery.substr(recovery.length - 4) == "|L|1" && nativeState.indexOf("Recovered") < 0);
        p._browser = b = new MCMCompatBrowser(p);
        p.loadBrowserState(recovery);
        p.setModNames("Zulu", "", "Alpha", "XPMSE");
        check("New movie recovers local edit over stale valid shared profile", b.preference("XPMSE", false).alias == "Recovered styles" && b.recoveryPending);
        nativeFails = false;
        b.save();
        check("Unchanged retry commits and clears local marker", !b.recoveryPending && lastFallback.indexOf("|L|1") < 0 && nativeState.indexOf("Recovered") >= 0 && nativeState.indexOf("|L|1") < 0);
        delete _global.skse.plugins;
        // Leave a clean list for external native-mouse and text-entry checks.
        b.loadState("OPENMCMB1|0|0|0|0|0|0|0|0|0|0");
        b.accept("search", "", "");
        p.setModNames("Zulu", "", "Alpha", "XPMSE");
        ExternalInterface.addCallback("browserSnapshot", AVM1BrowserFixture, snapshot);
        ExternalInterface.call("recordAVM1", "browserChecks", {checks:checks});
        ExternalInterface.call("recordAVM1", "ready", snapshot());
    }
}
