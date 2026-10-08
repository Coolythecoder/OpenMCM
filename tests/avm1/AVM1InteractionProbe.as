import flash.external.ExternalInterface;

/** Real production panel/list classes; fixture calls simulate only provider data. */
class AVM1InteractionProbe
{
    private static var nextToken:Number = 1;

    public static function record(kind:String, data:Object):Void
    {
        ExternalInterface.call("recordAVM1", kind, data);
    }

    private static function token(target:Object):Number
    {
        if (target == undefined) return -1;
        if (target.__fixtureToken == undefined) target.__fixtureToken = nextToken++;
        return target.__fixtureToken;
    }

    private static function describeList(list:Object):Object
    {
        if (list == undefined) return null;
        var rows:Array = [];
        for (var slot:Number = 0; slot < 32; slot++) {
            var row:Object = list["row" + slot];
            if (row == undefined) continue;
            rows.push({slot:slot, token:token(row), index:row._entryIndex,
                visible:row._visible, enabled:row.isEnabled,
                hitAreaAssigned:row.hitArea != undefined,
                triggerVisible:row.triggerArea._visible,
                triggerAlpha:row.triggerArea._alpha,
                triggerBounds:row.triggerArea.getBounds(_root),
                bounds:row.getBounds(_root)});
        }
        var selected:Object = list.entryList[list.selectedIndex];
        return {path:String(list), token:token(list), visible:list._visible,
            selectedIndex:list.selectedIndex, scrollPosition:list.scrollPosition,
            disableInput:list.disableInput, disableSelection:list.disableSelection,
            selectedRegistryIndex:selected.modIndex, selectedPageIndex:selected.pageIndex,
            selectedText:selected.text, entryCount:list.entryList.length, rows:rows};
    }

    public static function snapshot():Object
    {
        var p:Object = _root.fixturePanel;
        return {state:p._state, mode:p._sideMode, active:p._active,
            focus:Selection.getFocus(), dialogKind:p._dialog.kind,
            dialogValue:p._dialog.value, dialogSelection:p._dialog.selectionIndex,
            dialogActive:p._dialog.activeIndex, dialogScroll:p._dialog.scroll,
            dialogColor:p._dialog.color,
            activePage:p._activePageIndex, selectedMod:p._selectedModRegistryIndex,
            modList:describeList(p._modList), pageList:describeList(p._pageList),
            optionsList:describeList(p._optionsList), menuList:describeList(p._menuDialogList)};
    }

    public static function control(name:String):Object
    {
        var p:Object = _root.fixturePanel;
        var target:Object = p._modalLayer[name];
        if (name.substr(0, 7) == "menuRow" && p._menuDialogList != undefined)
            target = p._menuDialogList.getRendererForIndex(Number(name.substr(7)));
        if (name == "pageBack") target = p._pageList.titleBack;
        if (target == undefined) return null;
        return {token:token(target), path:String(target), bounds:target.getBounds(_root)};
    }

    private static function options():Void
    {
        var p:Object = _root.fixturePanel;
        // Sparse option IDs and the normal SkyUI bit-packed type/flag ABI.
        p.setOptionFlagsBuffer(3, 0, 4, 5, 2 | (1 << 8), 1, 2 | (2 << 8), 8, 6, 0);
        p.setOptionTextBuffer("Toggle", "", "Slider", "Menu", "Disabled", "Heading", "Hidden", "Input", "Color", "");
        p.setOptionStrValueBuffer("", "", "{0}", "A", "value", "", "", "start", "", "");
        p.setOptionNumValueBuffer(0, 0, 20, 0, 0, 0, 0, 0, 0x990033, 0);
        p.flushOptionBuffers(10);
    }

    /** Provider responses only: never dispatches a mouse/keyboard handler. */
    public static function respond(action:String):Object
    {
        var p:Object = _root.fixturePanel;
        if (action == "pages") {
            p.setPageNames("General", "None", "Styles");
            options();
            p.unlock(false);
        } else if (action == "options") {
            options();
            p.unlock(false);
        } else if (action == "unlock") {
            p.unlock(false);
        } else if (action == "slider") {
            p.setSliderDialogParams(20, 25, 0, 100, 5);
        } else if (action == "menu") {
            p.setMenuDialogOptions("A", "B", "C", "D", "E", "F", "G");
            p.setMenuDialogParams(0, 1);
        } else if (action == "input") {
            p.setInputDialogParams("start");
        } else if (action == "color") {
            p.setColorDialogParams(0x990033, 0xFFFFFF);
        } else if (action == "manyOptions") {
            var flags:Array = [], texts:Array = [], values:Array = [], numbers:Array = [];
            for (var k:Number = 0; k < 52; k++) {
                flags.push(2); texts.push("Option " + k); values.push("Value " + k); numbers.push(k);
            }
            p.setOptionFlagsBuffer.apply(p, flags);
            p.setOptionTextBuffer.apply(p, texts);
            p.setOptionStrValueBuffer.apply(p, values);
            p.setOptionNumValueBuffer.apply(p, numbers);
            p.flushOptionBuffers(52);
            p.unlock(false);
        } else if (action == "manyMods") {
            p.endPage();
            p.startPage();
            var names:Array = [];
            for (var i:Number = 0; i < 26; i++)
                names.push("MCM " + (i < 10 ? "0" : "") + i);
            p.setModNames.apply(p, names);
        } else if (action == "refreshMods") {
            p.setModNames("Zulu", "", "Alpha", "XPMSE");
        } else if (action == "close") {
            p.endPage();
        } else if (action == "reopen") {
            p.startPage();
            p.setModNames("Zulu", "", "Alpha", "XPMSE");
        }
        var result:Object = snapshot();
        record("response", {action:action, state:result});
        return result;
    }

    private static function observeList(list:Object):Void
    {
        for (var i:Number = 0; i < 3; i++) {
            var callback:String = ["onRowEvent", "onSelectionChange", "onItemPress"][i];
            var original:Function = list[callback];
            list["__fixtureOriginal_" + callback] = original;
        }
        list.onRowEvent = function(event:Object):Void {
            AVM1InteractionProbe.record("rowEvent", {type:event.type, kind:event.kind,
                index:event.index, registry:event.entry.modIndex, text:event.entry.text,
                x:_root._xmouse, y:_root._ymouse, focus:Selection.getFocus()});
            var original:Function = event.list.__fixtureOriginal_onRowEvent;
            if (original != undefined) original.call(this, event);
        };
        list.onSelectionChange = function(event:Object):Void {
            AVM1InteractionProbe.record("selectionChange", {kind:event.kind,
                index:event.index, registry:event.entry.modIndex, text:event.entry.text});
            var original:Function = event.list.__fixtureOriginal_onSelectionChange;
            if (original != undefined) original.call(this, event);
            AVM1InteractionProbe.record("afterSelection", {
                index:event.index, kind:event.kind, focus:Selection.getFocus(),
                listVisible:event.list._visible, rowVisible:event.clip._visible,
                rowBounds:event.clip.getBounds(_root)});
        };
        list.onItemPress = function(event:Object):Void {
            AVM1InteractionProbe.record("itemPress", {kind:event.kind,
                index:event.index, registry:event.entry.modIndex, page:event.entry.pageIndex,
                text:event.entry.text, token:event.clip.__fixtureToken});
            var original:Function = event.list.__fixtureOriginal_onItemPress;
            if (original != undefined) original.call(this, event);
        };
    }

    public static function prepare(root:MovieClip):Void
    {
        Stage.scaleMode = "noScale";
        Stage.align = "TL";
        // The standalone movie lacks the Journal's authored FocusHandler.
        // Reproduce its declared Scaleform focus flags, without replacing
        // Selection.setFocus or synthesizing any input callbacks.
        _global["gfxExtensions"] = 1;
        var selection:Object = Selection;
        selection.alwaysEnableArrowKeys = true;
        selection.disableFocusKeys = true;
        selection.disableFocusAutoRelease = true;
        selection.disableFocusRolloverEvent = true;
        root._focusrect = false;
        _global["MCM_COMPAT_RAW_KEYS"] = true;
        _global["skse"] = {
            SendModEvent:function(name:String, arg:Object, num:Number):Void {
                AVM1InteractionProbe.record("modEvent", {name:name, arg:arg, num:num});
            },
            AllowTextInput:function(enabled:Boolean):Void {
                AVM1InteractionProbe.record("textInput", {enabled:enabled});
            }
        };
    }

    public static function attach(p:Object, alreadyStarted:Boolean):Void
    {
        _root["fixturePanel"] = p;
        if (!alreadyStarted) p.startPage();
        p.setModNames("Zulu", "", "Alpha", "XPMSE");
        observeList(p._modList);
        observeList(p._pageList);
        observeList(p._optionsList);
        ExternalInterface.addCallback("flowSnapshot", AVM1InteractionProbe, snapshot);
        ExternalInterface.addCallback("flowRespond", AVM1InteractionProbe, respond);
        ExternalInterface.addCallback("flowControl", AVM1InteractionProbe, control);
        record("ready", snapshot());
    }
}
