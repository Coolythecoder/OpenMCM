import flash.external.ExternalInterface;

/** Runs the real OpenMCM class; only SKSE transport and diagnostic observers are stubbed. */
class AVM1MouseFixture
{
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
        _root.fixturePanel.setMouseDiagnostics(false);
        var result:Object = probeSnapshot();
        record("probeStopped", result);
        return result;
    }

    public static function record(kind:String, data:Object):Void
    {
        trace(kind + ": " + data);
        ExternalInterface.call("recordAVM1", kind, data);
    }

    public static function main(root:MovieClip):Void
    {
        Stage.scaleMode = "noScale";
        Stage.align = "TL";
        _global["skse"] = {
            SendModEvent:function(name:String, arg:Object, num:Number):Void {
                AVM1MouseFixture.record("modEvent", {name:name, arg:arg, num:num});
            }
        };
        var fader:MovieClip = root.createEmptyMovieClip("ConfigPanelFader", 1);
        var panel:Object = fader.createEmptyMovieClip("configPanel", 1);
        MCMCompatPanel.install(MovieClip(panel), {});
        panel.startPage();
        panel.setModNames("OpenMCM", "XPMSE");
        root["fixturePanel"] = panel;
        if (_root.fixtureDiagnostics == "true") {
            panel.setMouseDiagnostics(true);
            _root.fixtureProbe = panel._mouseProbe;
            record("probeInstalled", probeSnapshot());
        }
        ExternalInterface.addCallback("stopDiagnostics", AVM1MouseFixture,
            AVM1MouseFixture.stopDiagnostics);
        ExternalInterface.addCallback("probeSnapshot", AVM1MouseFixture,
            AVM1MouseFixture.probeSnapshot);
        for (var i:Number = 0; i < 2; i++) {
            var row:Object = panel._sideRows["row" + i];
            row["originalPress"] = row.onPress;
            row["originalOver"] = row.onRollOver;
            row.onPress = function():Void {
                AVM1MouseFixture.record("rowPress", {path:String(this), index:this._entryIndex});
                this.originalPress.apply(this, arguments);
            };
            row.onRollOver = function():Void {
                AVM1MouseFixture.record("rowOver", {path:String(this), index:this._entryIndex});
                this.originalOver.apply(this, arguments);
            };
            AVM1MouseFixture.record("row", {index:i, path:String(row),
                triggerPath:String(row.triggerArea),
                bounds:row.triggerArea.getBounds(root),
                hiddenHitAreaAssigned:row.hitArea != undefined});
        }
        var observer:Object = {
            onMouseDown:function():Void {
                var p:Object = _root.fixturePanel;
                AVM1MouseFixture.record("mouseDown", {x:_root._xmouse, y:_root._ymouse,
                    state:p._state, side:p._sideIndex, focus:Selection.getFocus()});
            },
            onMouseUp:function():Void {
                var p:Object = _root.fixturePanel;
                AVM1MouseFixture.record("mouseUp", {x:_root._xmouse, y:_root._ymouse,
                    state:p._state, side:p._sideIndex, mode:p._sideMode});
            }
        };
        Mouse.addListener(observer);
        AVM1MouseFixture.record("ready", {focusEnabled:panel.focusEnabled, path:String(panel)});
    }
}
