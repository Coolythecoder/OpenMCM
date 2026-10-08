/**
 * Small, dependency-free helpers shared by the MCM compatibility panel.
 *
 * This file deliberately does not import gfx.*, skyui.*, or any authored
 * library symbol.  Everything used here is part of AVM1/Scaleform itself or
 * is feature-detected from SKSE at runtime.
 */
class MCMCompatUtil
{
	private static var _translator:TextField;
	private static var _keyNames:Object;
	private static var _fallbackTranslations:Object;

	public function MCMCompatUtil()
	{
	}

	public static function safeString(value:Object):String
	{
		if (value == undefined || value == null)
			return "";
		return String(value);
	}

	/** Translate a Bethesda $TOKEN without depending on SkyUI's Translator. */
	public static function translate(value:Object):String
	{
		var text:String = safeString(value);
		if (text == "" || text.charAt(0) != "$")
			return text;

		if (_translator == undefined) {
			_translator = _root.createTextField("_mcmCompatTranslator",
				_root.getNextHighestDepth(), 0, 0, 1, 1);
			_translator._visible = false;
		}

		_translator.text = text;
		var translated:String = _translator.text;
		if (translated == text || translated == "") {
			if (_fallbackTranslations == undefined)
				buildFallbackTranslations();
			var fallback:Object = _fallbackTranslations[text.toLowerCase()];
			if (fallback != undefined)
				return String(fallback);
		}
		return translated;
	}

	private static function buildFallbackTranslations():Void
	{
		_fallbackTranslations = {};
		_fallbackTranslations["$mod configuration"] = "Mod Configuration";
		_fallbackTranslations["$options"] = "Options";
		_fallbackTranslations["$pages"] = "Pages";
		_fallbackTranslations["$message"] = "Message";
		_fallbackTranslations["$accept"] = "Accept";
		_fallbackTranslations["$cancel"] = "Cancel";
		_fallbackTranslations["$default"] = "Default";
		_fallbackTranslations["$done"] = "Done";
		_fallbackTranslations["$exit"] = "Exit";
		_fallbackTranslations["$toggle"] = "Toggle";
		_fallbackTranslations["$select"] = "Select";
		_fallbackTranslations["$back"] = "Back";
		_fallbackTranslations["$open slider"] = "Open Slider";
		_fallbackTranslations["$open menu"] = "Open Menu";
		_fallbackTranslations["$pick color"] = "Pick Color";
		_fallbackTranslations["$input text"] = "Input Text";
		_fallbackTranslations["$remap"] = "Remap";
		_fallbackTranslations["$unmap"] = "Unmap";
		_fallbackTranslations["$press a button to map to this action."] =
			"Press a button to map to this action.";
		_fallbackTranslations["$unbound"] = "Unbound";
	}

	/**
	 * Translate nested tokens in the form "$Sentence {$Nested token}".
	 * This mirrors the public behaviour used by classic SkyUI MCMs.
	 */
	public static function translateNested(value:Object):String
	{
		var text:String = safeString(value);
		if (text == "" || text.indexOf("{") == -1)
			return translate(text);

		var substitutions:Array = [];
		var offset:Number = 0;
		while (true) {
			var start:Number = text.indexOf("{", offset);
			var end:Number = text.indexOf("}", start + 1);
			if (start == -1 || end == -1 || start >= end)
				break;

			substitutions.push(translate(text.slice(start + 1, end)));
			text = text.slice(0, start + 1) + text.slice(end);
			offset = start + 2;
		}

		text = translate(text);
		var pieces:Array = text.split("{}");
		var result:String = "";
		var i:Number;
		for (i = 0; i < substitutions.length; i++)
			result += safeString(pieces[i]) + substitutions[i];
		if (i < pieces.length)
			result += pieces[i];
		return result;
	}

	public static function unescapeText(value:Object):String
	{
		var text:String = safeString(value);
		text = text.split("\\n").join("\n");
		text = text.split("\\t").join("\t");
		return text;
	}

	public static function formatSlider(formatValue:Object, value:Number):String
	{
		var format:String = translate(formatValue);
		if (format == "")
			return String(Math.round(value * 100) / 100);

		var start:Number = format.indexOf("{");
		var end:Number = format.indexOf("}", start + 1);
		if (start == -1 || end == -1)
			return format;

		var decimals:Number = Number(format.slice(start + 1, end));
		if (isNaN(decimals) || decimals < 0)
			decimals = 0;
		if (decimals > 8)
			decimals = 8;

		var multiplier:Number = Math.pow(10, decimals);
		var rendered:String = String(Math.round(value * multiplier) / multiplier);
		if (decimals > 0) {
			if (rendered.indexOf(".") == -1)
				rendered += ".";
			var fractional:Number = rendered.length - rendered.indexOf(".") - 1;
			while (fractional < decimals) {
				rendered += "0";
				fractional++;
			}
		}

		return format.slice(0, start) + rendered + format.slice(end + 1);
	}

	public static function hexColor(value:Number):String
	{
		var rgb:Number = value & 0xFFFFFF;
		var text:String = rgb.toString(16).toUpperCase();
		while (text.length < 6)
			text = "0" + text;
		return "#" + text;
	}

	public static function keyName(code:Number):String
	{
		if (code == -1 || code == 282)
			return translate("$Unbound");

		if (_keyNames == undefined)
			buildKeyNames();
		var result:Object = _keyNames[String(code)];
		if (result != undefined)
			return String(result);

		if (code >= 256)
			return "PAD " + code;
		return "KEY " + code;
	}

	private static function buildKeyNames():Void
	{
		_keyNames = {};
		_keyNames["1"] = "ESC";
		_keyNames["2"] = "1";
		_keyNames["3"] = "2";
		_keyNames["4"] = "3";
		_keyNames["5"] = "4";
		_keyNames["6"] = "5";
		_keyNames["7"] = "6";
		_keyNames["8"] = "7";
		_keyNames["9"] = "8";
		_keyNames["10"] = "9";
		_keyNames["11"] = "0";
		_keyNames["12"] = "-";
		_keyNames["13"] = "=";
		_keyNames["14"] = "BACKSPACE";
		_keyNames["15"] = "TAB";
		_keyNames["16"] = "Q";
		_keyNames["17"] = "W";
		_keyNames["18"] = "E";
		_keyNames["19"] = "R";
		_keyNames["20"] = "T";
		_keyNames["21"] = "Y";
		_keyNames["22"] = "U";
		_keyNames["23"] = "I";
		_keyNames["24"] = "O";
		_keyNames["25"] = "P";
		_keyNames["28"] = "ENTER";
		_keyNames["29"] = "LCTRL";
		_keyNames["30"] = "A";
		_keyNames["31"] = "S";
		_keyNames["32"] = "D";
		_keyNames["33"] = "F";
		_keyNames["34"] = "G";
		_keyNames["35"] = "H";
		_keyNames["36"] = "J";
		_keyNames["37"] = "K";
		_keyNames["38"] = "L";
		_keyNames["42"] = "LSHIFT";
		_keyNames["44"] = "Z";
		_keyNames["45"] = "X";
		_keyNames["46"] = "C";
		_keyNames["47"] = "V";
		_keyNames["48"] = "B";
		_keyNames["49"] = "N";
		_keyNames["50"] = "M";
		_keyNames["54"] = "RSHIFT";
		_keyNames["56"] = "LALT";
		_keyNames["57"] = "SPACE";
		_keyNames["58"] = "CAPS LOCK";
		_keyNames["59"] = "F1";
		_keyNames["60"] = "F2";
		_keyNames["61"] = "F3";
		_keyNames["62"] = "F4";
		_keyNames["63"] = "F5";
		_keyNames["64"] = "F6";
		_keyNames["65"] = "F7";
		_keyNames["66"] = "F8";
		_keyNames["67"] = "F9";
		_keyNames["68"] = "F10";
		_keyNames["87"] = "F11";
		_keyNames["88"] = "F12";
		_keyNames["157"] = "RCTRL";
		_keyNames["181"] = "NUM /";
		_keyNames["184"] = "RALT";
		_keyNames["199"] = "HOME";
		_keyNames["200"] = "UP";
		_keyNames["201"] = "PAGE UP";
		_keyNames["203"] = "LEFT";
		_keyNames["205"] = "RIGHT";
		_keyNames["207"] = "END";
		_keyNames["208"] = "DOWN";
		_keyNames["209"] = "PAGE DOWN";
		_keyNames["210"] = "INSERT";
		_keyNames["211"] = "DELETE";
		_keyNames["256"] = "MOUSE 1";
		_keyNames["257"] = "MOUSE 2";
		_keyNames["258"] = "MOUSE 3";
		_keyNames["259"] = "MOUSE 4";
		_keyNames["260"] = "MOUSE 5";
		_keyNames["264"] = "WHEEL UP";
		_keyNames["265"] = "WHEEL DOWN";
		_keyNames["266"] = "DPAD UP";
		_keyNames["267"] = "DPAD DOWN";
		_keyNames["268"] = "DPAD LEFT";
		_keyNames["269"] = "DPAD RIGHT";
		_keyNames["270"] = "START";
		_keyNames["271"] = "BACK";
		_keyNames["272"] = "L STICK";
		_keyNames["273"] = "R STICK";
		_keyNames["274"] = "LB";
		_keyNames["275"] = "RB";
		_keyNames["276"] = "A";
		_keyNames["277"] = "B";
		_keyNames["278"] = "X";
		_keyNames["279"] = "Y";
		_keyNames["280"] = "LT";
		_keyNames["281"] = "RT";
	}

	public static function sendModEvent(name:String, stringArg:Object, numberArg:Number):Boolean
	{
		var bridge:Object = _global["skse"];
		if (bridge == undefined)
			bridge = _root["skse"];
		if (bridge == undefined || bridge.SendModEvent == undefined) {
			trace("MCMCompat: missing SKSE bridge for " + name);
			return false;
		}

		bridge.SendModEvent(name,
			(stringArg == undefined ? null : stringArg),
			(isNaN(numberArg) ? 0 : numberArg));
		return true;
	}

	public static function allowTextInput(enabled:Boolean):Boolean
	{
		var bridge:Object = _global["skse"];
		if (bridge == undefined)
			bridge = _root["skse"];
		if (bridge == undefined || bridge.AllowTextInput == undefined)
			return false;
		bridge.AllowTextInput(enabled);
		return true;
	}

	public static function startRemapMode(receiver:Object):Boolean
	{
		var bridge:Object = _global["skse"];
		if (bridge == undefined)
			bridge = _root["skse"];
		if (bridge == undefined || bridge.StartRemapMode == undefined)
			return false;
		bridge.StartRemapMode(receiver);
		return true;
	}

	public static function drawRect(clip:MovieClip, x:Number, y:Number,
		width:Number, height:Number, color:Number, alpha:Number,
		lineColor:Number, lineAlpha:Number):Void
	{
		clip.lineStyle(1, lineColor, lineAlpha);
		clip.beginFill(color, alpha);
		clip.moveTo(x, y);
		clip.lineTo(x + width, y);
		clip.lineTo(x + width, y + height);
		clip.lineTo(x, y + height);
		clip.lineTo(x, y);
		clip.endFill();
	}

	public static function drawHorizontalGradientRect(clip:MovieClip, x:Number,
		y:Number, width:Number, height:Number, color:Number,
		leftAlpha:Number, rightAlpha:Number):Void
	{
		// Flash's linear-gradient coordinate system is supplied by a Matrix. The
		// code-drawn gradient matches the classic list selection fade without
		// importing an authored SkyUI asset.
		var matrix:Object = new flash.geom.Matrix();
		matrix.createGradientBox(width, height, 0, x, y);
		clip.beginGradientFill("linear", [color, color],
			[leftAlpha, rightAlpha], [0, 255], matrix);
		clip.moveTo(x, y);
		clip.lineTo(x + width, y);
		clip.lineTo(x + width, y + height);
		clip.lineTo(x, y + height);
		clip.lineTo(x, y);
		clip.endFill();
	}

	public static function drawRadialGradientRect(clip:MovieClip, x:Number,
		y:Number, width:Number, height:Number, color:Number,
		centerAlpha:Number, edgeAlpha:Number, edgeRatio:Number):Void
	{
		var matrix:Object = new flash.geom.Matrix();
		matrix.createGradientBox(width, height, 0, x, y);
		var ratio:Number = isNaN(edgeRatio) ? 255 : edgeRatio;
		clip.beginGradientFill("radial", [color, color],
			[centerAlpha, edgeAlpha], [0, ratio], matrix);
		clip.moveTo(x, y);
		clip.lineTo(x + width, y);
		clip.lineTo(x + width, y + height);
		clip.lineTo(x, y + height);
		clip.lineTo(x, y);
		clip.endFill();
	}

	public static function drawCenteredGradientRect(clip:MovieClip, x:Number,
		y:Number, width:Number, height:Number, color:Number,
		edgeAlpha:Number, centerAlpha:Number):Void
	{
		var matrix:Object = new flash.geom.Matrix();
		matrix.createGradientBox(width, height, 0, x, y);
		clip.beginGradientFill("linear", [color, color, color],
			[edgeAlpha, centerAlpha, edgeAlpha], [0, 130, 255], matrix);
		clip.moveTo(x, y);
		clip.lineTo(x + width, y);
		clip.lineTo(x + width, y + height);
		clip.lineTo(x, y + height);
		clip.lineTo(x, y);
		clip.endFill();
	}

	public static function drawLine(clip:MovieClip, x1:Number, y1:Number,
		x2:Number, y2:Number, color:Number, alpha:Number, thickness:Number):Void
	{
		clip.lineStyle(thickness, color, alpha);
		clip.moveTo(x1, y1);
		clip.lineTo(x2, y2);
	}

	public static function drawPolygon(clip:MovieClip, points:Array,
		color:Number, alpha:Number, lineColor:Number, lineAlpha:Number,
		thickness:Number):Void
	{
		if (points == undefined || points.length < 3)
			return;
		clip.lineStyle(thickness, lineColor, lineAlpha);
		clip.beginFill(color, alpha);
		clip.moveTo(Number(points[0].x), Number(points[0].y));
		for (var i:Number = 1; i < points.length; i++)
			clip.lineTo(Number(points[i].x), Number(points[i].y));
		clip.lineTo(Number(points[0].x), Number(points[0].y));
		clip.endFill();
	}

	public static function drawDiamond(clip:MovieClip, centerX:Number,
		centerY:Number, radiusX:Number, radiusY:Number, color:Number,
		alpha:Number, lineColor:Number, lineAlpha:Number):Void
	{
		drawPolygon(clip, [
			{x:centerX, y:centerY - radiusY},
			{x:centerX + radiusX, y:centerY},
			{x:centerX, y:centerY + radiusY},
			{x:centerX - radiusX, y:centerY}
		], color, alpha, lineColor, lineAlpha, 1);
	}

	public static function drawCircle(clip:MovieClip, centerX:Number,
		centerY:Number, radius:Number, color:Number, alpha:Number,
		lineColor:Number, lineAlpha:Number, thickness:Number):Void
	{
		var control:Number = radius * 0.55228475;
		clip.lineStyle(thickness, lineColor, lineAlpha);
		clip.beginFill(color, alpha);
		clip.moveTo(centerX + radius, centerY);
		clip.curveTo(centerX + radius, centerY + control,
			centerX + control, centerY + radius);
		clip.curveTo(centerX - control, centerY + radius,
			centerX - radius, centerY);
		clip.curveTo(centerX - radius, centerY - control,
			centerX - control, centerY - radius);
		clip.curveTo(centerX + control, centerY - radius,
			centerX + radius, centerY);
		clip.endFill();
	}

	public static function makeText(parent:MovieClip, name:String, depth:Number,
		x:Number, y:Number, width:Number, height:Number, size:Number,
		color:Number, bold:Boolean, alignment:String, fontName:String,
		letterSpacing:Number, kerning:Boolean):TextField
	{
		// Pooled list renderers keep their TextFields alive across data/scroll updates.
		if (parent[name] == undefined)
			parent.createTextField(name, depth, x, y, width, height);
		var field:TextField = parent[name];
		field.autoSize = false;
		field._x = x;
		field._y = y;
		field._width = width;
		field._height = height;
		field._visible = true;
		field.selectable = false;
		field.mouseWheelEnabled = false;
		// quest_journal imports these aliases from the game's localized
		// gfxfontlib.swf. Using outlines keeps the MCM visually consistent at
		// every supported UI scale without shipping a language-specific font.
		field.embedFonts = true;
		field.multiline = false;
		field.wordWrap = false;
		field.autoSize = false;
		var alias:String = safeString(fontName);
		if (alias == "")
			alias = bold ? "$EverywhereMediumFont" : "$EverywhereFont";
		// Imported font symbols are style-sensitive. Medium is not flagged as a
		// bold face; only the dedicated Bold alias may request bold outlines.
		var faceIsBold:Boolean = alias == "$EverywhereBoldFont";
		var format:TextFormat = new TextFormat(alias, size, color,
			faceIsBold, false, false, null, null, alignment);
		format.letterSpacing = isNaN(letterSpacing) ? 0.8 : letterSpacing;
		format.kerning = kerning == true;
		field.setNewTextFormat(format);
		field.setTextFormat(format);
		return field;
	}

	public static function applyText(field:TextField, value:Object):Void
	{
		field.html = false;
		field.text = safeString(value);
		field.setTextFormat(field.getNewTextFormat());
	}

	/** SkyUI option headers, labels and values accept HTML-formatted text. */
	public static function applyHtmlText(field:TextField, value:Object):Void
	{
		// Resolve leading translation tokens before adding markup; a wrapper
		// would otherwise hide the token from Skyrim's translator. Buffer/value
		// callers already resolve nested translations before reaching this helper.
		var text:String = translate(value);
		if (text.indexOf("<") == -1 && text.indexOf("&") == -1) {
			// No markup or entities: the plain path reapplies the known game font
			// explicitly, rather than relying on dynamic HTML document defaults.
			applyText(field, text);
			return;
		}
		var baseline:TextFormat = field.getNewTextFormat();
		var content:String = text;
		if (baseline.underline == true) content = "<u>" + content + "</u>";
		if (baseline.italic == true) content = "<i>" + content + "</i>";
		if (baseline.bold == true) content = "<b>" + content + "</b>";
		// SkyUI's authored fields carry explicit font/color/paragraph defaults
		// in their initial HTML as well as DefineEditText metadata. Dynamic fields
		// have no such authored defaults. Supply an outer inherited format for
		// every assignment; inner mod tags remain untouched and can override it.
		var leading:Number = Number(baseline.leading);
		if (isNaN(leading)) leading = 0;
		// Leave the generated paragraph end implicit: an explicit </p> adds a
		// trailing line break to multiline inline content in the AVM1 parser.
		// Provider-authored paragraph endings remain unchanged inside content.
		content = '<textformat leading="' + leading + '"><p align="' +
			escapeHtmlAttribute(baseline.align) + '"><font face="' +
			escapeHtmlAttribute(baseline.font) + '" size="' + baseline.size +
			'" color="' + hexColor(Number(baseline.color)) + '">' + content +
			'</font></textformat>';
		field.html = true;
		field.htmlText = content;
		// SkyUI's SetText reads the parsed format back before restoring spacing.
		// A fresh format is not a safe partial-update object in every runtime:
		// its defaults can replace the game's font/size/color. The parsed format
		// retains those attributes, with null for mixed HTML runs so their
		// individual colors/fonts/styles are not flattened by setTextFormat.
		var typography:TextFormat = field.getTextFormat();
		typography.letterSpacing = baseline.letterSpacing;
		typography.kerning = baseline.kerning;
		field.setTextFormat(typography);
		// Keep pooled fields' future defaults independent of the previous row's
		// HTML. Restore them only after the parsed current text is formatted.
		field.setNewTextFormat(baseline);
	}

	private static function escapeHtmlAttribute(value:Object):String
	{
		var text:String = safeString(value);
		text = text.split("&").join("&amp;");
		text = text.split('"').join("&quot;");
		text = text.split("<").join("&lt;");
		return text.split(">").join("&gt;");
	}

	/** Apply the exact black 45-degree text shadow used by SkyUI's MCM. */
	public static function applyDropShadow(field:TextField, distance:Number,
		blur:Number, strength:Number, quality:Number):Void
	{
		if (field == undefined || flash.filters.DropShadowFilter == undefined)
			return;
		field.filters = [new flash.filters.DropShadowFilter(distance, 45,
			0x000000, 1, blur, blur, strength, quality, false, false, false)];
	}

	public static function applyTextFit(field:TextField, value:Object,
		minimumSize:Number):Void
	{
		applyText(field, value);
		var format:TextFormat = field.getNewTextFormat();
		var originalSize:Number = Number(format.size);
		if (isNaN(originalSize))
			return;
		var size:Number = originalSize;
		var minimum:Number = isNaN(minimumSize) ? 12 : minimumSize;
		while (field.textWidth > field._width - 6 && size > minimum) {
			size--;
			format.size = size;
			field.setTextFormat(format);
		}
	}
}
