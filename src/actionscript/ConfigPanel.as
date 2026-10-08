/**
 * Conventional class-name facade for build tools and compatibility scanners.
 * The real implementation is MCMCompatPanel and is installed on a dynamic
 * MovieClip so no exported ConfigPanel library symbol is required.
 */
class ConfigPanel
{
	public static var ROOT_PATH:String = "_root.ConfigPanelFader.configPanel";

	// Kept as explicit ABI data so a compiled SWF is easy to audit.
	public static var ABI_METHODS:Array = [
		"setModNames", "setPageNames", "setCustomContentParams",
		"loadCustomContent", "unloadCustomContent", "setTitleText",
		"setInfoText", "setOptionFlagsBuffer", "setOptionTextBuffer",
		"setOptionStrValueBuffer", "setOptionNumValueBuffer",
		"setSliderDialogParams", "setMenuDialogOptions",
		"setMenuDialogParams", "setColorDialogParams",
		"setInputDialogParams", "flushOptionBuffers", "invalidateOptionData",
		"setOptionFlags", "forcePageReset", "showMessageDialog",
		"initExtensions", "setPlatform", "startPage", "endPage", "unlock",
		"handleInput", "EndRemapMode"
	];

	public static var ABI_PROPERTIES:Array = [
		"selectedKeyCode", "optionCursorIndex", "optionCursor"
	];

	public static var ABI_EVENTS:Array = [
		"SKICP_modSelected", "SKICP_pageSelected",
		"SKICP_optionHighlighted", "SKICP_optionSelected",
		"SKICP_optionDefaulted", "SKICP_keymapChanged",
		"SKICP_sliderSelected", "SKICP_sliderAccepted",
		"SKICP_menuSelected", "SKICP_menuAccepted",
		"SKICP_colorSelected", "SKICP_colorAccepted",
		"SKICP_inputSelected", "SKICP_inputAccepted",
		"SKICP_dialogCanceled", "SKICP_messageDialogClosed"
	];

	public function ConfigPanel()
	{
	}

	public static function install(target:MovieClip, journal:Object):MovieClip
	{
		return MCMCompatPanel.install(target, journal);
	}
}
