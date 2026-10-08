import flash.external.ExternalInterface;

/** Injected only into a diagnostic COPY of the final Journal SWF. */
class AVM1HostFixture
{
    private static var initializeTimer:Number;

    public static function boundarySnapshot():Object
    {
        var fader:Object = _root.QuestJournalFader;
        var panel:Object = _root.ConfigPanelFader.configPanel;
        return {phase:_root.fixtureBoundaryPhase, presses:_root.fixtureBoundaryPresses,
            journalVisible:fader._visible, journalAlpha:fader._alpha,
            journalHitTestDisable:fader.hitTestDisable, panelVisible:panel._visible,
            ownershipPresent:panel._journalInputState != undefined,
            savedVisible:panel._journalInputState.visible,
            savedHitTestDisable:panel._journalInputState.hitTestDisable};
    }

    public static function boundaryStep(action:String):Object
    {
        var journal:Object = _root.QuestJournalFader.Menu_mc;
        _root.fixtureBoundaryPhase = action;
        if (action == "open" || action == "repeatOpen") {
            journal.ConfigPanelOpen();
            _root.ConfigPanelFader.configPanel.setModNames("OpenMCM", "XPMSE");
        } else if (action == "close") {
            journal.ConfigPanelClose();
        } else if (action == "endPage") {
            _root.ConfigPanelFader.configPanel.endPage();
        } else if (action == "unload") {
            // Let AVM1 dispatch the real onUnload event; do not call it manually.
            _root.ConfigPanelFader.configPanel.removeMovieClip();
        }
        var result:Object = boundarySnapshot();
        record("boundaryState", result);
        return result;
    }

    public static function installBoundaryCanary():Void
    {
        var fader:MovieClip = _root.QuestJournalFader;
        // Reproduce a faded alpha-zero Journal rather than an absent Journal.
        fader._visible = true;
        fader._alpha = 0;
        var canary:MovieClip = fader.createEmptyMovieClip("fixtureBackgroundCanary",
            fader.getNextHighestDepth());
        var point:Object = {x:506, y:288};
        fader.globalToLocal(point);
        canary.beginFill(0xFF0000, 0);
        canary.moveTo(point.x - 20, point.y - 20);
        canary.lineTo(point.x + 20, point.y - 20);
        canary.lineTo(point.x + 20, point.y + 20);
        canary.lineTo(point.x - 20, point.y + 20);
        canary.lineTo(point.x - 20, point.y - 20);
        canary.endFill();
        _root.fixtureBoundaryPresses = 0;
        _root.fixtureBoundaryPhase = "beforeOpen";
        // This new canary is the only fixture handler. No production handler is replaced.
        canary.onPress = function():Void {
            _root.fixtureBoundaryPresses++;
            AVM1HostFixture.record("backgroundPress", AVM1HostFixture.boundarySnapshot());
        };
        ExternalInterface.addCallback("boundaryStep", AVM1HostFixture,
            AVM1HostFixture.boundaryStep);
        ExternalInterface.addCallback("boundarySnapshot", AVM1HostFixture,
            AVM1HostFixture.boundarySnapshot);
        record("boundaryState", boundarySnapshot());
    }

    public static function probeSnapshot():Object
    {
        var p:Object = _root.fixtureProbe;
        var listeners:Object = Mouse;
        var matches:Number = 0;
        if (listeners._listeners != undefined) {
            for (var i:Number = 0; i < listeners._listeners.length; i++)
                if (listeners._listeners[i] == p) matches++;
        }
        return {present:p != null, stopped:p._stopped, listening:p._listening,
            overlayPresent:p._overlay != undefined, downs:p._downs,
            overlayText:p._output.text, textHeight:p._output.textHeight,
            fieldHeight:p._output._height, textWidth:p._output.textWidth,
            fieldWidth:p._output._width,
            listenerReferences:listeners._listeners == undefined ? -1 : matches};
    }

    public static function stopDiagnostics():Object
    {
        _root.ConfigPanelFader.configPanel.setMouseDiagnostics(false);
        var result:Object = probeSnapshot();
        record("probeStopped", result);
        return result;
    }

    public static function record(kind:String, data:Object):Void
    {
        trace("HOST_DIAGNOSTIC " + kind + ": " + data);
        ExternalInterface.call("recordAVM1", kind, data);
    }

    public static function snapshot(kind:String):Void
    {
        var p:Object = _root.ConfigPanelFader.configPanel;
        var picker:Object = Mouse;
        var target:Object = picker.getTopMostEntity == undefined ? null : picker.getTopMostEntity();
        record(kind, {x:_root._xmouse, y:_root._ymouse, state:p._state,
            side:p._sideIndex, mode:p._sideMode, focus:Selection.getFocus(),
            topmost:target == null ? "unavailable in this runtime" : String(target),
            journalDepth:_root.QuestJournalFader.getDepth(),
            panelDepth:_root.ConfigPanelFader.getDepth(),
            journalAlpha:_root.QuestJournalFader._alpha,
            journalVisible:_root.QuestJournalFader._visible,
            panelVisible:p._visible});
    }

    public static function initializeHost():Void
    {
        clearInterval(initializeTimer);
        var journal:Object = _root.QuestJournalFader.Menu_mc;
        record("hostBeforeInit", {path:String(journal), initType:typeof(journal.InitExtensions),
            openType:typeof(journal.ConfigPanelOpen)});
        _root.InitExtensions();
        journal.SetPlatform(0, false);
        journal.RestoreSavedSettings(2, false);
        if (_root.fixtureBoundary == "true") {
            installBoundaryCanary();
            snapshot("ready");
            return;
        }
        journal.ConfigPanelOpen();
        var panel:Object = _root.ConfigPanelFader.configPanel;
        if (_root.fixtureFlow == "true") {
            AVM1InteractionProbe.attach(panel, true);
            return;
        }
        panel.setModNames("OpenMCM", "XPMSE");
        if (_root.fixtureDiagnostics == "true") {
            panel.setMouseDiagnostics(true);
            _root.fixtureProbe = panel._mouseProbe;
            record("probeInstalled", probeSnapshot());
        }
        ExternalInterface.addCallback("stopDiagnostics", AVM1HostFixture,
            AVM1HostFixture.stopDiagnostics);
        ExternalInterface.addCallback("probeSnapshot", AVM1HostFixture,
            AVM1HostFixture.probeSnapshot);
        for (var i:Number = 0; i < 2; i++) {
            var row:Object = panel._sideRows["row" + i];
            record("row", {index:i, path:String(row), triggerPath:String(row.triggerArea),
                bounds:row.triggerArea.getBounds(_root), pressType:typeof(row.onPress),
                hiddenHitAreaAssigned:row.hitArea != undefined});
        }
        snapshot("ready");
    }

    public static function main(root:MovieClip):Void
    {
        record("hostMain", {path:String(root)});
        Stage.scaleMode = "noScale";
        Stage.align = "TL";
        _global["skse"] = {
            SendModEvent:function(name:String, arg:Object, num:Number):Void {
                AVM1HostFixture.record("modEvent", {name:name, arg:arg, num:num});
            }
        };
        if (_root.fixtureFlow == "true") AVM1InteractionProbe.prepare(root);
        // These Scaleform-only multi-controller queries have no Ruffle implementation.
        // Do not replace mouse picking, selection set/get, or any mouse handler.
        var selection:Object = Selection;
        if (selection.getControllerFocusGroup == undefined)
            selection.getControllerFocusGroup = function(index:Number):Number { return 0; };
        if (selection.getControllerMaskByFocusGroup == undefined)
            selection.getControllerMaskByFocusGroup = function(index:Number):Number { return 1; };
        var capabilities:Object = System.capabilities;
        if (capabilities.numControllers == undefined)
            capabilities.numControllers = 1;
        Mouse.addListener({
            onMouseDown:function():Void { AVM1HostFixture.snapshot("mouseDown"); },
            onMouseUp:function():Void { AVM1HostFixture.snapshot("mouseUp"); }
        });
        initializeTimer = setInterval(AVM1HostFixture.initializeHost, 1000);
    }
}
