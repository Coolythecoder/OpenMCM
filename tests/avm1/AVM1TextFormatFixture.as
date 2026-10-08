import flash.external.ExternalInterface;

/** Native TextField-format diagnostic; no TextField methods are substituted. */
class AVM1TextFormatFixture
{
    private static var timer:Number;
    private static var rows:Array;
    private static var util:Object;

    public static function formatData(format:TextFormat):Object
    {
        var keys:Array = ["font", "size", "color", "bold", "italic", "underline",
            "align", "letterSpacing", "kerning", "leading", "leftMargin", "rightMargin"];
        var result:Object = {};
        for (var i:Number = 0; i < keys.length; i++) {
            var value:Object = format[keys[i]];
            result[keys[i]] = value === undefined ? "<undefined>" : value === null ? "<null>" : value;
        }
        return result;
    }

    public static function snapshot(field:TextField):Object
    {
        var runs:Array = [];
        for (var i:Number = 0; i < field.text.length; i++)
            runs.push({character:field.text.charAt(i), format:formatData(field.getTextFormat(i, i + 1))});
        return {text:field.text, htmlText:field.htmlText, baseline:formatData(field.getNewTextFormat()),
            aggregate:formatData(field.getTextFormat()), runs:runs, alpha:field._alpha,
            embedFonts:field.embedFonts, textColor:field.textColor};
    }

    public static function experiment(parent:MovieClip, name:String, definition:Object, mode:String,
        y:Number, embedded:Boolean):Void
    {
        var input:Object = definition.value;
        var font:String = definition.font == undefined ? "$EverywhereFont" : definition.font;
        var align:String = definition.align == undefined ? "left" : definition.align;
        var field:TextField = util.makeText(parent, name, parent.getNextHighestDepth(),
            10, y, 1150, 30, 20, 0xFFFFFF, false, align, font, 1.1, true);
        // Snapshot styles independently of the standalone runtime's absent game font library.
        field.embedFonts = embedded;
        var baseline:TextFormat = field.getNewTextFormat();
        if (definition.italic != undefined) baseline.italic = definition.italic;
        if (definition.underline != undefined) baseline.underline = definition.underline;
        field.setNewTextFormat(baseline);
        field.setTextFormat(baseline);
        field.multiline = definition.multiline == true;
        var result:Object = {name:name, caseId:definition.id, input:util.safeString(input),
            inputType:typeof(input), mode:mode, embedded:embedded, before:snapshot(field),
            expectedText:mode == "plain" ? util.safeString(input) : definition.text,
            expectedOverrides:mode == "plain" ? [] : definition.overrides};
        if (definition.nativeControl == true) {
            var control:TextField = util.makeText(parent, name + "Control", parent.getNextHighestDepth(),
                10, y, 1150, 30, 20, 0xFFFFFF, false, align, font, 1.1, true);
            control.embedFonts = embedded;
            control.multiline = field.multiline;
            control.setNewTextFormat(baseline);
            control.setTextFormat(baseline);
            control.html = true;
            control.htmlText = util.safeString(input);
            result.nativeControl = snapshot(control);
        }
        if (mode == "production" || mode == "semantic") {
            util.applyHtmlText(field, input);
        } else if (mode == "plain") {
            util.applyText(field, input);
        } else {
            field.html = true;
            if (mode == "openParagraph" || mode == "innerOpenParagraph" || mode == "fontOnly") {
                var content:String = util.safeString(input);
                if (baseline.underline == true) content = "<u>" + content + "</u>";
                if (baseline.italic == true) content = "<i>" + content + "</i>";
                if (baseline.bold == true) content = "<b>" + content + "</b>";
                var fontTag:String = '<font face="' + baseline.font + '" size="' + baseline.size +
                    '" color="' + util.hexColor(Number(baseline.color)) + '">';
                var paragraphTag:String = '<p align="' + baseline.align + '">';
                var opening:String = mode == "fontOnly" ? fontTag :
                    mode == "openParagraph" ? paragraphTag + fontTag : fontTag + paragraphTag;
                field.htmlText = '<textformat leading="' + baseline.leading + '">' +
                    opening + content + '</font></textformat>';
            } else if (mode == "wrapper") {
                field.htmlText = '<font face="$EverywhereFont" size="20" color="#FFFFFF">' + input + '</font>';
            } else {
                field.htmlText = util.safeString(input);
            }
            result.afterHtml = snapshot(field);
            field.setNewTextFormat(baseline);
            var typography:TextFormat;
            if (mode == "parsed" || mode == "openParagraph" || mode == "innerOpenParagraph" || mode == "fontOnly")
                typography = field.getTextFormat();
            else typography = new TextFormat();
            result.patchBefore = formatData(typography);
            typography.letterSpacing = baseline.letterSpacing;
            typography.kerning = baseline.kerning;
            result.patchAfter = formatData(typography);
            field.setTextFormat(typography);
        }
        result.after = snapshot(field);
        rows.push(result);
    }

    public static function pooled(parent:MovieClip, embedded:Boolean):Void
    {
        var fieldName:String = "pooled" + embedded;
        var field:TextField = util.makeText(parent, fieldName, parent.getNextHighestDepth(),
            600, 680, 600, 35, 20, 0xFFFFFF, false, "left", "$EverywhereFont", 1.1, true);
        field.embedFonts = embedded;
        var result:Object = {name:fieldName, mode:"pooled", embedded:embedded, before:snapshot(field),
            expectedText:"General", expectedOverrides:[], stages:[]};
        util.applyHtmlText(field, "Initial plain");
        result.stages.push({name:"plain", expectedText:"Initial plain", expectedOverrides:[], after:snapshot(field)});
        util.applyHtmlText(field, '<font color="#E86BA5" size="26">Pink</font> White');
        result.stages.push({name:"html", expectedText:"Pink White",
            expectedOverrides:[{start:0, end:4, color:0xE86BA5, size:26}], after:snapshot(field)});
        var reused:TextField = util.makeText(parent, fieldName, parent.getNextHighestDepth(),
            600, 680, 600, 35, 20, 0xFFFFFF, false, "left", "$EverywhereFont", 1.1, true);
        reused.embedFonts = embedded;
        util.applyHtmlText(reused, "General");
        result.sameField = field === reused;
        result.after = snapshot(reused);
        rows.push(result);
    }

    public static function role(parent:MovieClip, name:String, font:String, size:Number,
        alignment:String, kerning:Boolean, leading:Number, embedded:Boolean):Void
    {
        var field:TextField = util.makeText(parent, name + embedded, parent.getNextHighestDepth(),
            10, 680, 580, 35, size, 0xFFFFFF, true, alignment, font, 0.8, kerning);
        field.embedFonts = embedded;
        var baseline:TextFormat = field.getNewTextFormat();
        baseline.leading = leading;
        field.setNewTextFormat(baseline);
        field.setTextFormat(baseline);
        var result:Object = {name:name + embedded, mode:"role", embedded:embedded,
            input:'<font color="#E86BA5">Pink</font> White', before:snapshot(field),
            expectedText:"Pink White", expectedOverrides:[{start:0, end:4, color:0xE86BA5}]};
        util.applyHtmlText(field, result.input);
        result.after = snapshot(field);
        rows.push(result);
    }

    public static function initialize():Void
    {
        clearInterval(timer);
        util = _global["MCMCompatUtil"];
        var candidateMode:String = String(ExternalInterface.call("textFormatCandidate"));
        var candidateOnly:Boolean = candidateMode == "openParagraph" ||
            candidateMode == "innerOpenParagraph" || candidateMode == "fontOnly";
        var layer:MovieClip = _root.createEmptyMovieClip("textFormatFixture", _root.getNextHighestDepth());
        layer.beginFill(0x333333); layer.moveTo(0, 0); layer.lineTo(1280, 0);
        layer.lineTo(1280, 720); layer.lineTo(0, 720); layer.endFill();
        rows = [];
        var modes:Array = ["plain", "production", "sparse", "parsed", "wrapper"];
        var cases:Array = [
            {id:"plain", value:"General", text:"General", overrides:[]},
            {id:"color", value:'<font color="#E86BA5">Pink</font> White', text:"Pink White",
                overrides:[{start:0, end:4, color:0xE86BA5}]},
            {id:"blackSize", value:'<font color="#000000">Black</font> <font size="28">Big</font> Normal',
                text:"Black Big Normal", overrides:[{start:0, end:5, color:0}, {start:6, end:9, size:28}]},
            {id:"font", value:'<font face="$EverywhereMediumFont">Medium</font> Normal', text:"Medium Normal",
                overrides:[{start:0, end:6, font:"$EverywhereMediumFont"}]}
        ];
        // Production-only cases test semantics that the diagnostic wrappers do
        // not claim to implement. Expected strings are explicit, never produced
        // by stripping tags or by replacing TextField's actual HTML parser.
        var semantics:Array = [
            {id:"entities", value:'A &amp; B &lt; C &gt; D &quot;Q&quot; &#65; &#x42;',
                text:'A & B < C > D "Q" A B', overrides:[]},
            {id:"entityInColor", value:'<font color="#E86BA5">A &amp; B</font> C',
                text:"A & B C", overrides:[{start:0, end:5, color:0xE86BA5}]},
            {id:"nestedColors", value:'<font color="#E86BA5">P<font color="#00FF00"><b>G</b></font>P</font>W',
                text:"PGPW", overrides:[{start:0, end:3, color:0xE86BA5},
                    {start:1, end:2, color:0x00FF00, bold:true}]},
            {id:"nestedStyles", value:'A<b>B<i>C</i></b><u>D</u>E', text:"ABCDE",
                overrides:[{start:1, end:3, bold:true}, {start:2, end:3, italic:true},
                    {start:3, end:4, underline:true}]},
            {id:"rightBoldValue", value:'<font color="#E86BA5">Pink</font> White', text:"Pink White",
                font:"$EverywhereBoldFont", align:"right", overrides:[{start:0, end:4, color:0xE86BA5}]},
            {id:"baselineStyles", value:'A<font color="#E86BA5">B</font>C', text:"ABC", italic:true,
                underline:true, overrides:[{start:1, end:2, color:0xE86BA5}]},
            {id:"paragraphs", value:'<p>One</p><p>Two</p>', text:"One\rTwo\r", multiline:true,
                nativeControl:true, overrides:[]},
            {id:"paragraphAlign", value:'<p align="center">Center</p><p align="right">Right</p>',
                text:"Center\rRight\r", multiline:true, nativeControl:true,
                overrides:[{start:0, end:7, align:"center"}, {start:7, end:13, align:"right"}]},
            {id:"lineBreak", value:"One<br>Two", text:"One\rTwo", multiline:true,
                nativeControl:true, overrides:[]},
            {id:"multilineInline", value:'<font color="#E86BA5">Pink</font> White', text:"Pink White",
                multiline:true, nativeControl:true, overrides:[{start:0, end:4, color:0xE86BA5}]},
            {id:"trailingAfterParagraph", value:'<p>One</p>Two', text:"One\rTwo", multiline:true,
                nativeControl:true, overrides:[]},
            {id:"empty", value:"", text:"", overrides:[]},
            {id:"null", value:null, text:"", overrides:[]},
            {id:"undefined", value:undefined, text:"", overrides:[]},
            {id:"number", value:42, text:"42", overrides:[]},
            {id:"boolean", value:true, text:"true", overrides:[]}
        ];
        var y:Number = 5;
        for (var embedded:Number = 0; embedded < 2; embedded++) {
            if (candidateOnly) {
                for (var s:Number = 0; s < semantics.length; s++)
                    experiment(layer, candidateMode + embedded + "_" + semantics[s].id,
                        semantics[s], candidateMode, 5 + s * 32, embedded == 1);
                continue;
            }
            y = 5;
            for (var i:Number = 0; i < modes.length; i++) {
                for (var j:Number = 0; j < cases.length; j++) {
                    experiment(layer, "case" + embedded + "_" + i + "_" + j,
                        cases[j], modes[i], y, embedded == 1);
                    y += 32;
                }
            }
            pooled(layer, embedded == 1);
            role(layer, "header", "$EverywhereMediumFont", 22, "left", true, 0, embedded == 1);
            role(layer, "label", "$EverywhereFont", 22, "left", false, 2, embedded == 1);
            role(layer, "value", "$EverywhereBoldFont", 20, "right", false, 2, embedded == 1);
            for (var k:Number = 0; k < semantics.length; k++)
                experiment(layer, "semantic" + embedded + "_" + semantics[k].id,
                    semantics[k], "semantic", 5 + k * 32, embedded == 1);
        }
        ExternalInterface.call("recordAVM1", "textFormatResults", {
            host:_root.QuestJournalFader != undefined,
            candidate:candidateOnly ? candidateMode : "",
            constructor:formatData(new TextFormat()), rows:rows});
        ExternalInterface.call("recordAVM1", "ready", {});
    }

    public static function start(root:MovieClip):Void
    {
        Stage.scaleMode = "noScale";
        Stage.align = "TL";
        timer = setInterval(AVM1TextFormatFixture.initialize, 1200);
    }
}
