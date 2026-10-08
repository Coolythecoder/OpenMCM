/**
 * OpenMCM browser preferences and controls.
 *
 * Independently implemented using MCM Menu Redone 2.3.0's browser behaviour
 * and tab/sort/scroll + H/N/P preference model as a reference. No upstream
 * ActionScript bodies, registry, timeline artwork or SkyUI-derived panel are
 * copied here. OPENMCMB1 adds inline F records in an OpenMCM-only profile.
 */
class MCMCompatBrowser
{
	private var owner:Object;
	private var layer:MovieClip;
	private var entries:Array;
	private var preferences:Array;
	private var sorts:Array;
	private var scrolls:Array;
	private var bottoms:Array;
	private var tab:Number;
	private var query:String;
	private var targetName:String;
	private var nativeLoaded:Boolean;
	private var preferencesLoaded:Boolean;
	private var registryReceived:Boolean;
	private var recoveryPending:Boolean;
	private var locallyChanged:Boolean;
	private var lastSaved:String;
	private var storageStatus:String;

	public function MCMCompatBrowser(panel:Object)
	{
		owner = panel;
		layer = owner._chrome.createEmptyMovieClip("browserControls", 25);
		entries = [];
		preferences = [];
		sorts = [0, 0, 0];
		scrolls = [0, 0, 0];
		bottoms = [false, false, false];
		tab = 0;
		query = "";
		targetName = "";
		nativeLoaded = false;
		preferencesLoaded = false;
		registryReceived = false;
		recoveryPending = false;
		locallyChanged = false;
		lastSaved = "";
		storageStatus = "Saved with this character";
		loadNative();
	}

	private function bridge():Object
	{
		var skse:Object = _global.skse;
		if (skse == undefined) skse = _root.skse;
		if (skse == undefined || skse.plugins == undefined) return undefined;
		return skse.plugins.OpenMCMBrowser;
	}

	private function clamp(value:Object, minimum:Number, maximum:Number):Number
	{
		var number:Number = Math.floor(Number(value));
		return isNaN(number) ? minimum : Math.max(minimum, Math.min(maximum, number));
	}

	private function preference(name:String, create:Boolean):Object
	{
		// Arrays deliberately avoid special Object keys such as __proto__.
		for (var i:Number = 0; i < preferences.length; i++)
			if (preferences[i].name == name) return preferences[i];
		if (!create || name == "" || name.length > 1024 || preferences.length >= 1024)
			return undefined;
		var record:Object = {name:name, favorite:false, hidden:false, alias:"", priority:0};
		preferences.push(record);
		return record;
	}

	private function find(name:String):Object
	{
		for (var i:Number = 0; i < entries.length; i++)
			if (entries[i].modName == name) return entries[i];
		return undefined;
	}

	public function receive(list:Array):Array
	{
		entries = list;
		registryReceived = true;
		return filtered();
	}

	public function filtered():Array
	{
		var result:Array = [];
		var needle:String = query.toLowerCase();
		for (var i:Number = 0; i < entries.length; i++) {
			var source:Object = entries[i];
			var record:Object = preference(String(source.modName), false);
			var hidden:Boolean = record != undefined && record.hidden == true;
			var favorite:Boolean = record != undefined && record.favorite == true;
			if (tab == 2 ? !hidden : hidden || (tab == 1 && !favorite)) continue;
			var display:String = record != undefined && record.alias != "" ?
				String(record.alias) : String(source.text);
			// Search both the displayed alias and the author's original name.
			if (needle != "" && display.toLowerCase().indexOf(needle) < 0 &&
				String(source.text).toLowerCase().indexOf(needle) < 0 &&
				String(source.modName).toLowerCase().indexOf(needle) < 0) continue;
			result.push({modIndex:source.modIndex, modName:source.modName,
				text:display, enabled:true, favorite:favorite,
				priority:record != undefined && record.priority > 0 ? record.priority : 1000000,
				sortName:display.toLowerCase()});
		}
		var mode:Number = sorts[tab];
		result.sort(function(left:Object, right:Object):Number {
			if (left.priority != right.priority) return left.priority - right.priority;
			if (mode != 2 && left.sortName != right.sortName)
				return (left.sortName < right.sortName ? -1 : 1) * (mode == 1 ? -1 : 1);
			return Number(left.modIndex) - Number(right.modIndex);
		});
		return result;
	}

	public function selected(entry:Object):Void
	{
		if (entry != undefined) targetName = String(entry.modName);
		render();
	}

	public function captureScroll():Void
	{
		// Opening/closing before registration replies must not turn remembered
		// scroll positions into zeros from a temporary, empty list.
		if (!registryReceived || entries.length == 0 ||
			owner._sideMode != "mods" || query != "") return;
		var maximum:Number = Math.max(0, owner._modList.entryList.length - owner._modList.visibleCount);
		scrolls[tab] = clamp(owner._modList.scrollPosition, 0, maximum);
		bottoms[tab] = maximum > 0 && scrolls[tab] == maximum;
	}

	public function restoreScroll():Void
	{
		if (owner._sideMode != "mods") return;
		owner._modList.scrollPosition = query != "" ? 0 : (bottoms[tab] ?
			Math.max(0, owner._modList.entryList.length - owner._modList.visibleCount) : scrolls[tab]);
	}

	private function rebuild(resetScroll:Boolean):Void
	{
		if (owner._sideMode != "mods") return;
		owner._modNames = filtered();
		owner._modList.entryList = owner._modNames;
		owner._sideIndex = -1;
		for (var i:Number = 0; i < owner._modNames.length; i++) {
			if (owner._modNames[i].modName == targetName) {
				owner._sideIndex = i;
				break;
			}
		}
		if (owner._sideIndex < 0) {
			owner._sideIndex = owner._modNames.length > 0 ? 0 : -1;
			targetName = owner._sideIndex >= 0 ? String(owner._modNames[0].modName) : "";
		}
		if (resetScroll) owner._modList.scrollPosition = 0;
		else restoreScroll();
		owner._renderSide();
		owner._updateFooter();
	}

	public function buildState():String
	{
		var result:String = "OPENMCMB1|" + tab + "|" + sorts.join("|") + "|" +
			scrolls.join("|") + "|" + (bottoms[0] ? 1 : 0) + "|" +
			(bottoms[1] ? 1 : 0) + "|" + (bottoms[2] ? 1 : 0);
		for (var i:Number = 0; i < preferences.length; i++) {
			var record:Object = preferences[i];
			var name:String = escape(record.name);
			if (record.favorite) result += "|F|" + name;
			if (record.hidden) result += "|H|" + name;
			if (record.alias != "") result += "|N|" + name + "|" + escape(record.alias);
			if (record.priority > 0) result += "|P|" + name + "|" + record.priority;
		}
		return result;
	}

	public function loadState(serialized:String):Boolean
	{
		// Parse transactionally: never replace working preferences with a partial
		// or newer-format string. Missing installed menus retain their preferences.
		if (serialized == undefined || serialized.length > 32768) return false;
		var parts:Array = serialized.split("|");
		if (parts.length < 11 || parts[0] != "OPENMCMB1") return false;
		var parsed:Array = [];
		var parsedRecovery:Boolean = false;
		var index:Number = 11;
		while (index < parts.length) {
			var kind:String = parts[index++];
			if (kind == "L") {
				// A trailing local-only recovery marker is unambiguous and bounded.
				// It is never sent to the native shared-profile codec.
				if (parsedRecovery || index != parts.length - 1 || parts[index] != "1") return false;
				parsedRecovery = true;
				index++;
				continue;
			}
			if (kind != "F" && kind != "H" && kind != "N" && kind != "P") return false;
			if (index >= parts.length) return false;
			var name:String = unescape(parts[index++]);
			if (name == "" || name.length > 1024) return false;
			var record:Object = undefined;
			for (var p:Number = 0; p < parsed.length; p++)
				if (parsed[p].name == name) record = parsed[p];
			if (record == undefined) {
				if (parsed.length >= 1024) return false;
				record = {name:name, favorite:false, hidden:false, alias:"", priority:0};
				parsed.push(record);
			}
			if (kind == "F") record.favorite = true;
			else if (kind == "H") record.hidden = true;
			else {
				if (index >= parts.length) return false;
				var value:String = unescape(parts[index++]);
				if (kind == "N") {
					if (value.length > 60) return false;
					record.alias = value;
				} else record.priority = clamp(value, 0, 999);
			}
		}
		preferences = parsed;
		recoveryPending = parsedRecovery;
		tab = clamp(parts[1], 0, 2);
		for (var t:Number = 0; t < 3; t++) {
			sorts[t] = clamp(parts[2 + t], 0, 2);
			scrolls[t] = clamp(parts[5 + t], 0, 1000000);
			bottoms[t] = parts[8 + t] == "1";
		}
		return true;
	}

	private function hasRecoveryMarker(serialized:String):Boolean
	{
		return serialized != undefined && serialized.length >= 4 &&
			serialized.substr(serialized.length - 4) == "|L|1";
	}

	private function loadNative():Void
	{
		var native:Object = bridge();
		if (native == undefined || native.GetProfileStateChunkCount == undefined ||
			native.GetProfileStateChunk == undefined) return;
		var count:Number = Number(native.GetProfileStateChunkCount());
		if (isNaN(count) || count <= 0 || count > 32 || Math.floor(count) != count) return;
		var state:String = "";
		for (var i:Number = 0; i < count; i++) {
			var chunk:Object = native.GetProfileStateChunk(i);
			if (typeof(chunk) != "string" || chunk.length > 1024) return;
			state += chunk;
		}
		if (!hasRecoveryMarker(state) && loadState(state)) {
			nativeLoaded = true;
			lastSaved = buildState();
			storageStatus = "Global browser profile";
		}
	}

	public function loadSavedGame(serialized:String):Void
	{
		// Late replies never undo an explicit click. Normally shared preferences
		// beat an older save; a valid local recovery record is the exception after
		// a failed shared write, so reopening cannot silently discard that edit.
		if (serialized == undefined) return;
		// Manager acknowledgement is required even with a shared profile: its
		// reply may carry an unsaved local recovery that must be checked first.
		preferencesLoaded = true;
		if (locallyChanged) return;
		if (recoveryPending && !hasRecoveryMarker(serialized)) return;
		if (serialized == "" || (nativeLoaded && !hasRecoveryMarker(serialized))) {
			lastSaved = buildState();
			render();
			return;
		}
		if (!loadState(serialized)) {
			// Invalid saved input must not permanently lock the controls or cause
			// an untouched close to overwrite it with defaults.
			lastSaved = buildState();
			storageStatus = "Saved browser state invalid; current preferences retained";
			render();
			return;
		}
		lastSaved = buildState();
		if (recoveryPending) storageStatus = "Local recovery pending; shared save will retry";
		rebuild(false);
	}

	public function save():Void
	{
		// Native data alone is not authoritative before the manager has checked
		// for a local recovery. No controls can edit unknown preferences first.
		if (!preferencesLoaded || (!locallyChanged && !registryReceived && !recoveryPending)) return;
		captureScroll();
		var state:String = buildState();
		if (state == lastSaved && !recoveryPending) return;
		// Always reserve the four-character marker, including at the exact size
		// boundary, so a failed native write still fits the manager envelope.
		if (state.length + 4 > 32768) {
			storageStatus = "Preferences too large to save";
			return;
		}
		var native:Object = bridge();
		var saved:Boolean = false;
		if (native != undefined && native.BeginProfileStateUpdate != undefined &&
			native.AppendProfileStateChunk != undefined && native.CommitProfileStateUpdate != undefined) {
			saved = native.BeginProfileStateUpdate() == true;
			for (var offset:Number = 0; saved && offset < state.length; offset += 1024)
				saved = native.AppendProfileStateChunk(state.substr(offset, 1024)) == true;
			if (saved) saved = native.CommitProfileStateUpdate() == true;
			recoveryPending = !saved;
			storageStatus = saved ? "Global browser profile" : "Global save failed; character fallback retained";
			if (saved) nativeLoaded = true;
		} else if (recoveryPending) {
			storageStatus = "Local recovery pending; global storage unavailable";
		}
		// Publish only after the commit result is known. The marker survives
		// absent bridges/reloads and is removed only after a successful retry.
		MCMCompatUtil.sendModEvent("OPENMCM_browserStateChanged",
			state + (recoveryPending ? "|L|1" : ""), 0);
		locallyChanged = true;
		lastSaved = state;
	}

	public function action(actionName:String):Void
	{
		if (!preferencesLoaded || !owner._isVisibleAndActive() || owner._sideMode != "mods" ||
			owner._dialog != null || owner._state != 0) return;
		captureScroll();
		if (actionName == "all" || actionName == "favorites" || actionName == "hidden") {
			tab = actionName == "all" ? 0 : (actionName == "favorites" ? 1 : 2);
			query = "";
			rebuild(false);
		} else if (actionName == "sort") {
			sorts[tab] = (sorts[tab] + 1) % 3;
			rebuild(true);
		} else if (actionName == "clear") {
			query = "";
			rebuild(false);
		} else if (actionName == "search") {
			owner._openBrowserInput("search", "Search MCM names", query, "");
			return;
		} else if (actionName == "tools") {
			owner._openBrowserTools();
			return;
		} else {
			if (find(targetName) == undefined) return;
			var record:Object = preference(targetName, true);
			if (record == undefined) return;
			if (actionName == "favorite") record.favorite = !record.favorite;
			else if (actionName == "hide") record.hidden = !record.hidden;
			else if (actionName == "rename") {
				owner._openBrowserInput("rename", "Rename MCM (empty restores original)", record.alias, targetName);
				return;
			} else if (actionName == "priority") {
				owner._openBrowserInput("priority", "Priority 1-999 (0 = unpinned)", String(record.priority), targetName);
				return;
			} else return;
			rebuild(false);
		}
		if (actionName != "clear") locallyChanged = true;
		save();
		render();
	}

	public function accept(actionName:String, name:String, value:String):Void
	{
		if (!preferencesLoaded) return;
		if (actionName == "search") {
			query = value.substr(0, 60);
			rebuild(true);
			return;
		}
		if (find(name) == undefined) return;
		var record:Object = preference(name, true);
		if (record == undefined) return;
		if (actionName == "rename") record.alias = value.substr(0, 60);
		else if (actionName == "priority") record.priority = clamp(value, 0, 999);
		else return;
		locallyChanged = true;
		rebuild(false);
		save();
		render();
	}

	private function button(name:String, label:String, x:Number, y:Number,
		width:Number, index:Number, selected:Boolean, enabled:Boolean):Void
	{
		enabled = enabled && preferencesLoaded;
		// "clear" is a MovieClip method, so action names are never clip names.
		var clipName:String = "button_" + name;
		var clip:MovieClip = layer[clipName];
		if (clip == undefined) clip = layer.createEmptyMovieClip(clipName, index);
		clip.clear();
		clip._visible = true;
		clip._alpha = enabled ? 100 : 35;
		clip.enabled = enabled;
		clip.useHandCursor = false;
		MCMCompatUtil.drawRect(clip, x, y, width, 24, selected ? 0x666666 : 0x000000,
			selected ? 75 : 40, 0x999999, 45);
		var field:TextField = MCMCompatUtil.makeText(clip, "label", 1,
			x + 4, y + 2, width - 8, 21, 14, 0xFFFFFF, false, "center",
			"$EverywhereMediumFont", 0.8, true);
		MCMCompatUtil.applyTextFit(field, label, 10);
		clip._browser = this;
		clip._action = name;
		clip.onPress = function():Void { if (this.enabled) this._browser.action(this._action); };
	}

	public function render():Void
	{
		layer._visible = owner._sideMode == "mods" && owner._active;
		if (!layer._visible) return;
		layer._alpha = owner._contentDimmed ? 50 : 100;
		var selected:Object = find(targetName);
		var record:Object = preference(targetName, false);
		button("all", "All", 356, 110, 86, 1, tab == 0, true);
		button("favorites", "Favourites", 448, 110, 110, 2, tab == 1, true);
		button("hidden", "Hidden", 564, 110, 86, 3, tab == 2, true);
		button("sort", ["Sort: A-Z", "Sort: Z-A", "Sort: Registered"][sorts[tab]],
			656, 110, 143, 4, false, true);
		button("search", query == "" ? "Search..." : "Search: " + query,
			805, 110, 264, 5, query != "", true);
		button("clear", "Clear", 1075, 110, 91, 6, false, query != "");
		button("favorite", record != undefined && record.favorite ? "Unfavourite" : "Favourite",
			356, 142, 112, 7, false, selected != undefined);
		button("hide", record != undefined && record.hidden ? "Unhide" : "Hide",
			474, 142, 92, 8, false, selected != undefined);
		button("rename", "Rename", 572, 142, 102, 9, false, selected != undefined);
		button("priority", "Priority", 680, 142, 102, 10, false, selected != undefined);
		button("tools", "Browser actions", 788, 142, 148, 11, false, true);
		var caption:TextField = MCMCompatUtil.makeText(layer, "caption", 20,
			356, 174, 810, 23, 14, 0xCBCBCB, false, "left", "$EverywhereMediumFont", 0.8, true);
		var count:Number = owner._modNames.length;
		var detail:String = selected == undefined ? "Select or hover a menu to customise it" :
			"Selected: " + (record != undefined && record.alias != "" ? record.alias : selected.text);
		MCMCompatUtil.applyTextFit(caption, count + " / " + entries.length + " MCMs  |  " + detail, 10);
		var status:TextField = MCMCompatUtil.makeText(layer, "status", 21,
			356, 526, 810, 23, 12, 0xCBCBCB, false, "left", "$EverywhereMediumFont", 0.8, true);
		MCMCompatUtil.applyText(status, preferencesLoaded ?
			storageStatus + "  |  R / X: browser actions" : "Loading browser preferences...");
	}
}
