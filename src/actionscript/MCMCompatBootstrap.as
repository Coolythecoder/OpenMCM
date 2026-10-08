/**
 * Creates the exact display-list path used by SKI_ConfigBase and
 * SKI_ConfigManager: `_root.ConfigPanelFader.configPanel`.
 *
 * Call MCMCompatBootstrap.install(this) from Quest_Journal.InitExtensions.
 */
class MCMCompatBootstrap
{
	/** Names the vanilla Journal integration must expose or call. */
	public static var HOST_ABI:Array = [
		"ConfigPanelOpen", "ConfigPanelClose", "initExtensions",
		"setPlatform", "startPage", "endPage"
	];

	public function MCMCompatBootstrap()
	{
	}

	public static function install(journal:Object):MovieClip
	{
		var host:MovieClip = _root;
		var fader:MovieClip = host["ConfigPanelFader"];
		if (fader == undefined)
			fader = host.createEmptyMovieClip("ConfigPanelFader",
				host.getNextHighestDepth());

		var panel:MovieClip = fader["configPanel"];
		if (panel == undefined)
			panel = fader.createEmptyMovieClip("configPanel",
				fader.getNextHighestDepth());

		MCMCompatPanel.install(panel, journal);
		panel._x = 0;
		panel._y = 0;

		if (journal != undefined)
			journal.ConfigPanel = panel;
		installJournalFallbacks(journal, fader);
		installPlatformForwarder(journal);
		panel.initExtensions();
		// InitExtensions runs while the Journal itself is visible. Do not let the
		// newly-created display object cover it until ConfigPanelOpen is called.
		panel._visible = false;
		fader._visible = false;

		// Expose a small diagnostic record without changing the required ABI.
		_global["MCMCompat"] = {
			version:1,
			apiVersion:4,
			skyUI6Input:true,
			rootPath:"_root.ConfigPanelFader.configPanel",
			panel:panel
		};

		return panel;
	}

	/** Keep the dynamic MCM above the fading, still-interactive Journal. */
	public static function raisePanel():Void
	{
		var fader:MovieClip = _root["ConfigPanelFader"];
		var journalFader:MovieClip = _root["QuestJournalFader"];
		if (fader == undefined || journalFader == undefined)
			return;
		// SkyUI swaps authored timeline layers with a known initial order. Our
		// new dynamic layer already starts on top; an unconditional swap puts
		// it BEHIND the vanilla Journal, whose fadeOut only animates alpha.
		// Move only our layer if necessary, and never swap the Journal itself.
		if (fader.getDepth() <= journalFader.getDepth())
			fader.swapDepths(_root.getNextHighestDepth());
	}

	/**
	 * Vanilla Quest_Journal has no ConfigPanelOpen/Close functions. A patched
	 * journal can provide richer versions; these fallbacks are installed only
	 * when the host does not already define them.
	 */
	private static function installJournalFallbacks(journal:Object,
		fader:MovieClip):Void
	{
		if (journal == undefined)
			return;

		if (journal.DisableTabs == undefined) {
			journal.DisableTabs = function(disabled:Boolean):Void {
				this.QuestsTab.disabled = disabled;
				this.StatsTab.disabled = disabled;
				this.SystemTab.disabled = disabled;
			};
		}

		if (journal.ConfigPanelOpen == undefined) {
			journal.ConfigPanelOpen = function():Void {
				this.DisableTabs(true);
				if (this.SystemFader != undefined &&
					this.SystemFader.Page_mc != undefined &&
					this.SystemFader.Page_mc.endPage != undefined)
					this.SystemFader.Page_mc.endPage();
				if (this.DoHideMenu != undefined)
					this.DoHideMenu();
				_root.ConfigPanelFader._visible = true;
				MCMCompatBootstrap.raisePanel();
				var gfxPackage:Object = _global["gfx"];
				if (gfxPackage != undefined && gfxPackage.managers != undefined &&
					gfxPackage.managers.FocusHandler != undefined &&
					gfxPackage.managers.FocusHandler.instance != undefined)
					gfxPackage.managers.FocusHandler.instance.setFocus(this.ConfigPanel, 0);
				MCMCompatBootstrap.playSound("UIMenuOK");
				this.ConfigPanel.startPage();
			};
		}

		if (journal.ConfigPanelClose == undefined) {
			journal.ConfigPanelClose = function():Void {
				if (this.ConfigPanel != undefined) {
					MCMCompatBootstrap.playSound("UIMenuCancel");
					this.ConfigPanel.endPage();
				}
				_root.ConfigPanelFader._visible = false;
				var gfxPackage:Object = _global["gfx"];
				if (gfxPackage != undefined && gfxPackage.managers != undefined &&
					gfxPackage.managers.FocusHandler != undefined &&
					gfxPackage.managers.FocusHandler.instance != undefined)
					gfxPackage.managers.FocusHandler.instance.setFocus(this, 0);
				if (this.DoShowMenu != undefined)
					this.DoShowMenu();
				if (this.SystemFader != undefined &&
					this.SystemFader.Page_mc != undefined &&
					this.SystemFader.Page_mc.startPage != undefined)
					this.SystemFader.Page_mc.startPage();
				this.DisableTabs(false);
			};
		}

		// The Journal owns visibility after installation.
		fader._visible = false;
	}

	/** Play the same panel transition sounds as SkyUI's start/end methods. */
	public static function playSound(soundName:String):Void
	{
		var gfxPackage:Object = _global["gfx"];
		if (gfxPackage == undefined || gfxPackage.io == undefined ||
			gfxPackage.io.GameDelegate == undefined ||
			gfxPackage.io.GameDelegate.call == undefined)
			return;
		gfxPackage.io.GameDelegate.call("PlaySound", [soundName]);
	}

	/** Preserve vanilla SetPlatform and forward future platform changes. */
	private static function installPlatformForwarder(journal:Object):Void
	{
		if (journal == undefined || journal.SetPlatform == undefined ||
			journal._mcmCompatPlatformHooked == true)
			return;
		var previous:Function = journal.SetPlatform;
		journal.SetPlatform = function(platform:Number, ps3Switch:Boolean):Void {
			previous.apply(this, arguments);
			if (this.ConfigPanel != undefined &&
				this.ConfigPanel.setPlatform != undefined)
				this.ConfigPanel.setPlatform(platform, ps3Switch);
		};
		journal._mcmCompatPlatformHooked = true;
	}

	public static function uninstall():Void
	{
		var fader:MovieClip = _root["ConfigPanelFader"];
		if (fader == undefined)
			return;
		var panel:MovieClip = fader["configPanel"];
		if (panel != undefined && panel["_mcmCompatInstalled"] == true) {
			panel.onUnload();
			panel.removeMovieClip();
		}
		if (fader.getNextHighestDepth() <= 0)
			fader.removeMovieClip();
		delete _global["MCMCompat"];
	}
}
