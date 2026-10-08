/** Original OpenMCM optional API extensions. No new input listeners or timers. */
class MCMCompatExtensions
{
	public static function requestPage(host:Object, provider:Number, page:Number,
		token:Number, destination:Number, name:String):Boolean
	{
		provider = Number(provider); page = Number(page); token = Number(token);
		destination = Number(destination);
		if (!host._openMCMApiEnabled || host._dialog != null || host._remapMode ||
			!host._openMCMMatchesPage(provider, page, token) ||
			isNaN(destination) || destination < 0 || Math.floor(destination) != destination)
			return false;
		// No redirects during OnPageReset or while a dialog is being populated.
		// DIALOG with no dialog is its accepted/cancelled callback awaiting unlock.
		// Panel constants are class-static, not properties on its MovieClip mixin.
		// Contract tests pin READY=0, WAIT_FOR_SELECT=6, WAIT_FOR_DEFAULT=7, DIALOG=8.
		if (host._state != 0 && host._state != 6 && host._state != 7 && host._state != 8)
			return false;
		var entry:Object = findPage(host, destination, name);
		if (entry == undefined) return false;
		host._openMCMNavigation = null;
		if (page == destination) return true;
		host._openMCMNavigation = {provider:provider, page:page, token:token,
			destination:destination, name:name};
		if (host._state == 0) drain(host);
		return true;
	}

	public static function findPage(host:Object, destination:Number, name:String):Object
	{
		if (name == undefined || name == "" || String(name).toLowerCase() == "none")
			return undefined;
		for (var i:Number = 0; i < host._pageNames.length; i++) {
			var entry:Object = host._pageNames[i];
			if (Number(entry.pageIndex) == destination && String(entry.pageName) == name &&
				entry.enabled != false) return entry;
		}
		return undefined;
	}

	public static function drain(host:Object):Boolean
	{
		var pending:Object = host._openMCMNavigation;
		if (pending == null || host._state != 0) return false;
		host._openMCMNavigation = null;
		if (!host._openMCMApiEnabled || host._dialog != null || host._remapMode ||
			!host._openMCMMatchesPage(pending.provider, pending.page, pending.token))
			return false;
		var entry:Object = findPage(host, pending.destination, pending.name);
		if (entry == undefined) return false;
		// Navigation wins over a requested reset of the page we are leaving.
		host._requestPageReset = false;
		for (var i:Number = 0; i < host._pageNames.length; i++)
			if (host._pageNames[i] == entry) host._sideIndex = i;
		host._focus = 0; // FOCUS_SIDE
		host._ensureSideVisible();
		host._selectPage(entry);
		host._syncListInput();
		host._focusActiveList();
		return true;
	}

	public static function setOptionsEnabled(host:Object, provider:Number, page:Number,
		token:Number, enabled:Number, ids:String):Boolean
	{
		provider = Number(provider); page = Number(page); token = Number(token);
		enabled = Number(enabled);
		if (!host._openMCMApiEnabled ||
			!host._openMCMMatchesPage(provider, page, token) || (enabled != 0 && enabled != 1) ||
			ids == undefined || ids.length == 0 || ids.length > 2048)
			return false;
		var parts:Array = ids.split(",");
		if (parts.length > 128) return false;
		var indexes:Array = [];
		for (var i:Number = 0; i < parts.length; i++) {
			if (parts[i] == "") return false;
			var id:Number = Number(parts[i]);
			var index:Number = host._openMCMOptionIndex(page, id);
			if (index < 0 || String(id) != parts[i]) return false;
			indexes.push(index);
		}
		for (var j:Number = 0; j < indexes.length; j++) {
			var entry:Object = host._optionEntries[indexes[j]];
			entry.flags = enabled == 1 ? (entry.flags & ~1) : (entry.flags | 1);
		}
		host._renderOptions();
		return true;
	}
}
