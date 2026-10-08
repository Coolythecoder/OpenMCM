import flash.external.ExternalInterface;

/** Real production panel/list/text implementation; API calls are the subject
 * under test. Provider buffers and page choices are supplied by this fixture.
 * This is not a mouse-dispatch or Skyrim/Scaleform verification fixture. */
class AVM1OpenMCMApiFixture
{
    private static var results:Array;

    private static function check(name:String, passed:Boolean):Void
    {
        results.push({name:name, passed:passed});
    }

    private static function publish(p:Object):Void
    {
        var flags:Array = [];
        var labels:Array = [];
        var values:Array = [];
        var numbers:Array = [];
        for (var i:Number = 0; i < 40; i++) {
            flags.push(i == 25 ? 3 : 2);
            labels.push("Option " + i);
            values.push("Old value");
            numbers.push(0);
        }
        p.setOptionFlagsBuffer.apply(p, flags);
        p.setOptionTextBuffer.apply(p, labels);
        p.setOptionStrValueBuffer.apply(p, values);
        p.setOptionNumValueBuffer.apply(p, numbers);
        p.flushOptionBuffers(40);
        p.unlock(false);
    }

    private static function extensions(p:Object):Void
    {
        var token:Number = p.openMCMPageToken;
        var fullID:Number = 3 * 256 + 24;
        var ids:String = String(fullID) + "," + String(fullID + 1);
        p._optionIndex = 24;
        p._optionScrollRow = 7;
        p._highlightIndex = 24;
        p._focus = 1;
        p._optionEntries[24].flags = 4;
        p._optionEntries[25].flags = 2;
        p._renderOptions();
        var renderer:Object = p._optionsList.getRendererForIndex(24);
        check("Conditional group accepts Papyrus string-array transport and retains other flags",
            p.openMCMSetOptionsEnabled("2","2",String(token),"0",ids) &&
            p._optionEntries[24].flags == 5 && p._optionEntries[25].flags == 3);
        check("Conditional group retains renderer and current navigation scope",
            renderer == p._optionsList.getRendererForIndex(24) &&
            renderer.isEnabled == false && p._optionIndex == 24 &&
            p._optionScrollRow == 7 && p._focus == 1 &&
            p._highlightIndex == 24 && p.openMCMPageToken == token);
        p._selectOption(24);
        check("Group-disabled option cannot activate its provider callback", p._state == 0);
        check("Invalid group member rejects the entire update without partial mutation",
            !p.openMCMSetOptionsEnabled(2,2,token,1,String(fullID) + ",9999") &&
            p._optionEntries[24].flags == 5 && p._optionEntries[25].flags == 3);
        check("Group rejects malformed canonical IDs and invalid enabled values",
            !p.openMCMSetOptionsEnabled(2,2,token,1,ids + ",") &&
            !p.openMCMSetOptionsEnabled(2,2,token,1,"0" + fullID) &&
            !p.openMCMSetOptionsEnabled(2,2,token,1,String(fullID) + ".0") &&
            !p.openMCMSetOptionsEnabled(2,2,token,2,ids) &&
            !p.openMCMSetOptionsEnabled(2,2,token,1,""));
        check("Group rejects wrong provider and raw page identities",
            !p.openMCMSetOptionsEnabled(3,2,token,1,ids) &&
            !p.openMCMSetOptionsEnabled(2,0,token,1,ids));
        check("Group rejects stale generations and page-local IDs",
            !p.openMCMSetOptionsEnabled(2,2,token - 1,1,ids) &&
            !p.openMCMSetOptionsEnabled(2,2,token,1,"24,25"));
        check("Enabling group clears only DISABLED while retaining HIDDEN and WITH_UNMAP",
            p.openMCMSetOptionsEnabled(2,2,token,1,ids) &&
            p._optionEntries[24].flags == 4 && p._optionEntries[25].flags == 2 &&
            p._optionsList.getRendererForIndex(24).isEnabled == true);
        check("Duplicate IDs are harmless and remain idempotent",
            p.openMCMSetOptionsEnabled(2,2,token,1,String(fullID) + "," + fullID) &&
            p._optionEntries[24].flags == 4);

        check("Page navigation rejects unknown, blank, filtered and mismatched destinations",
            !p.openMCMRequestPage(2,2,token,-1,"") &&
            !p.openMCMRequestPage(2,2,token,1,"None") &&
            !p.openMCMRequestPage(2,2,token,0,"Third") &&
            !p.openMCMRequestPage(2,2,token,0.5,"First") &&
            !p.openMCMRequestPage(2,2,token,4,"Missing"));
        check("Page navigation rejects wrong provider and stale generation",
            !p.openMCMRequestPage(3,2,token,0,"First") &&
            !p.openMCMRequestPage(2,2,token - 1,0,"First"));
        check("Requesting current page is a successful no-op",
            p.openMCMRequestPage(2,2,token,2,"Third") &&
            p._state == 0 && p.openMCMPageToken == token && p._openMCMNavigation == null);
        p._state = 1;
        check("Page navigation cannot redirect while OnPageReset is building",
            !p.openMCMRequestPage(2,2,token,0,"First") && p._openMCMNavigation == null);
        p._state = 2;
        check("Page navigation cannot redirect while a slider dialog is being populated",
            !p.openMCMRequestPage(2,2,token,0,"First") && p._openMCMNavigation == null);
        p._state = 6;
        p.showMessageDialog("Keep this dialog open", "OK", "Cancel");
        var dialog:Object = p._dialog;
        check("Page navigation cannot replace a visible message dialog",
            !p.openMCMRequestPage(2,2,token,0,"First") && p._dialog == dialog &&
            p.openMCMPageToken == token);
        p._cancelDialog();
        p.unlock(false);
        p._remapMode = true;
        check("Page navigation cannot interrupt key capture",
            !p.openMCMRequestPage(2,2,token,0,"First") && p._openMCMNavigation == null);
        p._remapMode = false;
        p._pageNames[0].enabled = false;
        check("Page navigation cannot enter a disabled published page",
            !p.openMCMRequestPage(2,2,token,0,"First"));
        p._pageNames[0].enabled = true;
        p._state = 6;
        p._requestPageReset = true;
        check("Callback navigation is queued without changing current page scope",
            p.openMCMRequestPage("2","2",String(token),"0","First") &&
            p._state == 6 && p.openMCMPageToken == token &&
            p._openMCMNavigation.destination == 0);
        p.unlock(false);
        check("Unlock drains navigation once and cancels an obsolete page reset",
            p._state == 1 && p._activePageIndex == 0 && p._sideIndex == 0 &&
            p._focus == 0 && p.openMCMPageToken == 0 &&
            p._openMCMNavigation == null && p._requestPageReset == false);
        publish(p);
        var firstToken:Number = p.openMCMPageToken;
        check("Navigated page gets a fresh token and its original option ID namespace",
            firstToken > token && p.openMCMPageIndex == 0 &&
            p.openMCMSetOptionsEnabled(2,0,firstToken,0,"280,281") &&
            !p.openMCMSetOptionsEnabled(2,0,firstToken,1,ids));
        check("Ready-state navigation follows the existing page-selection path immediately",
            p.openMCMRequestPage(2,0,firstToken,2,"Third") &&
            p._state == 1 && p._activePageIndex == 1 &&
            p._sideIndex == 1 && p.openMCMPageToken == 0);
        publish(p);
        token = p.openMCMPageToken;
        p._state = 7;
        check("Default callbacks may queue navigation until unlock",
            p.openMCMRequestPage(2,2,token,0,"First") && p._state == 7);
        check("Current-page request cancels an earlier queued redirect",
            p.openMCMRequestPage(2,2,token,2,"Third") && p._openMCMNavigation == null);
        p.unlock(false);
        check("Cancelled redirect does not rebuild or move the current page",
            p._state == 0 && p._activePageIndex == 1 && p.openMCMPageToken == token);
        p._state = 8;
        check("Completed dialog callback may queue navigation after its dialog closes",
            p.openMCMRequestPage(2,2,token,0,"First") && p._state == 8);
        p._pageNames[0].enabled = false;
        p.unlock(false);
        check("Queued destination is revalidated at unlock",
            p._state == 0 && p._activePageIndex == 1 &&
            p.openMCMPageToken == token && p._openMCMNavigation == null);
        p._pageNames[0].enabled = true;
        p._state = 6;
        p.openMCMRequestPage(2,2,token,0,"First");
        publish(p);
        check("A page rebuild invalidates a previously queued redirect",
            p._state == 0 && p._activePageIndex == 1 &&
            p.openMCMPageToken > token && p._openMCMNavigation == null);
        token = p.openMCMPageToken;
        p._state = 6;
        p.openMCMRequestPage(2,2,token,0,"First");
        p.setOpenMCMAPIEnabled(false);
        p.unlock(false);
        publish(p);
        var disabledToken:Number = p.openMCMPageToken;
        check("Opt-out cancels pending navigation and rejects both new extension endpoints",
            p._activePageIndex == 1 && p._openMCMNavigation == null &&
            !p.openMCMRequestPage(2,2,disabledToken,0,"First") &&
            !p.openMCMSetOptionsEnabled(2,2,disabledToken,0,ids));
        p.setOpenMCMAPIEnabled(true);
        publish(p);
        check("Re-enabling cannot resurrect old navigation or grouped update tokens",
            !p.openMCMRequestPage(2,2,token,0,"First") &&
            !p.openMCMSetOptionsEnabled(2,2,disabledToken,0,ids) &&
            p._activePageIndex == 1 && p._state == 0);
    }

    public static function main(root:MovieClip):Void
    {
        results = [];
        AVM1InteractionProbe.prepare(root);
        var fader:MovieClip = root.createEmptyMovieClip("ConfigPanelFader", 1);
        var p:Object = fader.createEmptyMovieClip("configPanel", 1);
        MCMCompatPanel.install(MovieClip(p), {});
        p.startPage();
        p.setModNames("Zulu", "", "Author");
        check("Real mixin starts with optional API disabled", p.openMCMApiVersion == 0 && p.openMCMApiEnabled == false);
        p.openMCMApiVersion = 99;
        p.openMCMApiEnabled = true;
        check("API availability getters cannot be assigned", p.openMCMApiVersion == 0 && p.openMCMApiEnabled == false);
        check("Mod list has no page scope", p.openMCMPageToken == 0 && p.openMCMProviderID == -1);
        p._selectMod(p._modNames[0]);
        publish(p);
        var opening:Number = p.openMCMPageToken;
        check("Opening blank page has raw index -1", opening > 0 && p.openMCMPageIndex == -1);
        check("Disabled API rejects live label updates", !p.openMCMSetOptionLabel(2,-1,opening,24,"Blocked") && p._optionEntries[24].text == "Option 24");
        check("Disabled API rejects live value updates", !p.openMCMSetOptionTextValue(2,-1,opening,24,"Blocked") && p._optionEntries[24].strValue == "Old value");
        check("Disabled API rejects optional help and page status", !p.openMCMSetInfoText(2,-1,opening,24,"Blocked") && !p.openMCMSetInfoText(2,-1,opening,-1,"Blocked"));
        p._highlightIndex = 24;
        check("Disabled API preserves explicit scoped legacy help", p.openMCMSetHighlightText(2,-1,opening,24,"Legacy help") && p._infoField.text == "Legacy help");
        check("Legacy bridge cannot bypass disabled page status", !p.openMCMSetHighlightText(2,-1,opening,-1,"Blocked") && p._infoField.text == "Legacy help");
        p._highlightIndex = 25;
        check("Disabled legacy bridge rejects stale highlight", !p.openMCMSetHighlightText(2,-1,opening,24,"Late help") && p._infoField.text == "Legacy help");
        p.setInfoText("Classic help");
        check("Classic SkyUI help endpoint remains available while off", p._infoField.text == "Classic help");
        p.setOpenMCMAPIEnabled(false);
        check("Idempotent disabled preference sync retains internal page scope", p.openMCMPageToken == opening);
        p.setOpenMCMAPIEnabled(true);
        check("Explicit opt-in advertises API and requires a fresh page", p.openMCMApiVersion == 1 && p.openMCMApiEnabled == true && p.openMCMPageToken == 0);
        check("Opt-in does not accept pre-toggle queued work", !p.openMCMSetOptionLabel(2,-1,opening,24,"Stale"));
        publish(p);
        check("Opt-in page flush publishes a fresh scope", p.openMCMPageToken > opening);
        opening = p.openMCMPageToken;
        p.setOpenMCMAPIEnabled(true);
        check("Idempotent enabled preference sync retains page scope", p.openMCMPageToken == opening);
        check("Blank page accepts unshifted option ID", p.openMCMSetOptionLabel(2,-1,opening,24,"Blank label"));
        p.setPageNames("First", "None", "Third");
        check("Initial page list publication preserves opening token", p.openMCMPageToken == opening);
        p._selectPage(p._pageNames[1]);
        check("Page selection invalidates before provider reply", p.openMCMPageToken == 0);
        publish(p);
        var token:Number = p.openMCMPageToken;
        var fullID:Number = 3 * 256 + 24;
        check("Filtered page retains raw identity", p.openMCMProviderID == 2 && p.openMCMPageIndex == 2);
        check("Page publication creates distinct token", token > opening);
        p._optionIndex = 24;
        p._optionScrollRow = 7;
        p._focus = 1;
        p._highlightIndex = 24;
        p._renderOptions();
        var row:Object = p._optionsList.getRendererForIndex(24);
        var label:Object = row.label;
        var value:Object = row.value;
        check("Colored label endpoint accepts string-array transport",
            p.openMCMSetOptionLabel("2","2",String(token),String(fullID),'<font color="#00FF00">Ready</font> plain'));
        check("Colored text value endpoint accepts TEXT row",
            p.openMCMSetOptionTextValue(2,2,token,fullID,'<font color="#FF8800">Done</font>'));
        check("Update retains renderer and text field identity",
            row == p._optionsList.getRendererForIndex(24) && row.label == label && row.value == value);
        check("Update retains selection scroll focus highlight and token",
            p._optionIndex == 24 && p._optionScrollRow == 7 && p._focus == 1 &&
            p._highlightIndex == 24 && p.openMCMPageToken == token);
        check("Native formatted label retains colors and plain baseline",
            label.text == "Ready plain" && label.getTextFormat(0,1).color == 0x00FF00 &&
            label.getTextFormat(6,7).color == 0xFFFFFF);
        check("Native formatted value retains color and legacy uppercase", value.text == "DONE" && value.getTextFormat(0,1).color == 0xFF8800);
        check("TEXT value rejects toggle without changing value", !p.openMCMSetOptionTextValue(2,2,token,fullID + 1,"Bad") &&
            p._optionEntries[25].strValue == "Old value");
        check("Wrong provider rejected", !p.openMCMSetOptionLabel(3,2,token,fullID,"Bad"));
        check("Wrong page rejected", !p.openMCMSetOptionLabel(2,0,token,fullID,"Bad"));
        check("Wrong full ID page rejected", !p.openMCMSetOptionLabel(2,2,token,24,"Bad"));
        check("Stale generation rejected", !p.openMCMSetOptionLabel(2,2,opening,fullID,"Bad"));
        check("Current tooltip accepted", p.openMCMSetInfoText(2,2,token,fullID,"Current help") && p._infoField.text == "Current help");
        p._highlightIndex = 25;
        check("Delayed tooltip cannot replace a new highlight", !p.openMCMSetInfoText(2,2,token,fullID,"Stale help") && p._infoField.text == "Current help");
        check("Delayed rollout cannot clear a new highlight", !p.openMCMSetInfoText(2,2,token,-2,"") && p._infoField.text == "Current help");
        p._highlightIndex = -1;
        check("No-highlight clear applies only when no option is selected", p.openMCMSetInfoText(2,2,token,-2,"") && p._infoField.text == "");
        check("Page status can update independently of highlight", p.openMCMSetInfoText(2,2,token,-1,"Working...") && p._infoField.text == "Working...");
        p._state = 1;
        check("Published page-ready status paints before manager unlock", p.openMCMSetInfoText(2,2,token,-1,"Page ready") && p._infoField.text == "Page ready" && p._state == 1);
        p.unlock(false);
        p.setModNames("Zulu", "", "Author", "New arrival");
        check("Registry refresh preserves live extension scope", p.openMCMPageToken == token && p._optionScrollRow == 7);
        p.setPageNames("First", "None", "Third");
        check("Identical raw page list preserves scope", p.openMCMPageToken == token && p.openMCMPageIndex == 2);
        p.setOpenMCMAPIEnabled(false);
        check("Disabling optional API invalidates old scope without moving navigation", p.openMCMPageToken == 0 && p.openMCMApiVersion == 0 && p._optionIndex == 24 && p._optionScrollRow == 7 && p._focus == 1);
        check("Disabling rejects queued optional and scoped legacy writes", !p.openMCMSetOptionLabel(2,2,token,fullID,"Stale") && !p.openMCMSetHighlightText(2,2,token,fullID,"Stale"));
        publish(p);
        var disabledToken:Number = p.openMCMPageToken;
        check("Disabled page can publish internal scope without enabling API", disabledToken > token && p.openMCMApiVersion == 0 && !p.openMCMSetInfoText(2,2,disabledToken,-1,"Blocked"));
        p.setOpenMCMAPIEnabled(true);
        check("Off-on round trip cannot resurrect either old page scope", p.openMCMPageToken == 0 && !p.openMCMSetInfoText(2,2,token,-1,"Stale") && !p.openMCMSetInfoText(2,2,disabledToken,-1,"Stale"));
        publish(p);
        check("Newly enabled page accepts fresh optional work", p.openMCMPageToken > disabledToken && p.openMCMSetInfoText(2,2,p.openMCMPageToken,-1,"Fresh status") && p._infoField.text == "Fresh status");
        extensions(p);
        token = p.openMCMPageToken;
        p._goBack();
        check("Back invalidates without provider close", p.openMCMPageToken == 0 && !p.openMCMSetInfoText(2,2,token,-1,"Late"));
        p.endPage();
        p.onUnload();
        p.removeMovieClip();
        p = fader.createEmptyMovieClip("configPanel", 1);
        MCMCompatPanel.install(MovieClip(p), {});
        p.startPage();
        check("Recreated panel fails closed until persisted preference is synced", p.openMCMApiVersion == 0 && p.openMCMApiEnabled == false);
        p.setModNames("Zulu", "", "Author");
        p._selectMod(p._modNames[0]);
        publish(p);
        check("Recreated panel does not reuse prior token", p.openMCMPageToken > token);
        ExternalInterface.call("recordAVM1", "openMCMApiResults", {checks:results});
        ExternalInterface.call("recordAVM1", "ready", {checks:results.length});
    }
}
