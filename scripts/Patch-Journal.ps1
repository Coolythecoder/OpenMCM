[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ExportedScriptsPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Replace-ExactlyOnce {
    param(
        [Parameter(Mandatory)] [string] $Text,
        [Parameter(Mandatory)] [string] $Needle,
        [Parameter(Mandatory)] [string] $Replacement,
        [Parameter(Mandatory)] [string] $Description
    )

    # FFDec and PowerShell can disagree on CRLF versus LF. The importer accepts
    # either, so normalize generated ActionScript before checking exact anchors.
    $Text = $Text.Replace("`r`n", "`n")
    $Needle = $Needle.Replace("`r`n", "`n")
    $Replacement = $Replacement.Replace("`r`n", "`n")

    $first = $Text.IndexOf($Needle, [StringComparison]::Ordinal)
    if ($first -lt 0) {
        throw "Journal patch anchor was not found: $Description"
    }
    if ($Text.IndexOf($Needle, $first + $Needle.Length, [StringComparison]::Ordinal) -ge 0) {
        throw "Journal patch anchor was not unique: $Description"
    }
    return $Text.Substring(0, $first) + $Replacement + $Text.Substring($first + $Needle.Length)
}

$packagesPath = Join-Path (Resolve-Path -LiteralPath $ExportedScriptsPath) '__Packages'
$journalPath = Join-Path $packagesPath 'Quest_Journal.as'
$systemPagePath = Join-Path $packagesPath 'SystemPage.as'

if (-not (Test-Path -LiteralPath $journalPath -PathType Leaf)) {
    throw "FFDec did not export Quest_Journal.as at '$journalPath'."
}
if (-not (Test-Path -LiteralPath $systemPagePath -PathType Leaf)) {
    throw "FFDec did not export SystemPage.as at '$systemPagePath'."
}

$journal = Get-Content -LiteralPath $journalPath -Raw
$journal = Replace-ExactlyOnce -Text $journal `
    -Needle '      this.BottomBar_mc.InitBar();' `
    -Replacement "      this.BottomBar_mc.InitBar();`n      MCMCompatBootstrap.install(this);" `
    -Description 'Quest_Journal.InitExtensions'

$hostMethods = @'
   function DisableTabs(abEnable)
   {
      this.QuestsTab.disabled = abEnable;
      this.StatsTab.disabled = abEnable;
      this.SystemTab.disabled = abEnable;
   }
   function ConfigPanelOpen()
   {
      if(this.ConfigPanel == undefined)
      {
         this.ConfigPanel = MCMCompatBootstrap.install(this);
      }
      this.DisableTabs(true);
      this.SystemFader.Page_mc.endPage();
      this.DoHideMenu();
      _root.ConfigPanelFader._visible = true;
      MCMCompatBootstrap.raisePanel();
      gfx.managers.FocusHandler.instance.setFocus(this.ConfigPanel,0);
      MCMCompatBootstrap.playSound("UIMenuOK");
      this.ConfigPanel.startPage();
   }
   function ConfigPanelClose()
   {
      if(this.ConfigPanel != undefined)
      {
         MCMCompatBootstrap.playSound("UIMenuCancel");
         this.ConfigPanel.endPage();
      }
      _root.ConfigPanelFader._visible = false;
      gfx.managers.FocusHandler.instance.setFocus(this,0);
      this.DoShowMenu();
      this.SystemFader.Page_mc.startPage();
      this.DisableTabs(false);
   }
'@

$journal = Replace-ExactlyOnce -Text $journal `
    -Needle '   function SetShowMod()' `
    -Replacement ($hostMethods + "`n   function SetShowMod()") `
    -Description 'Quest_Journal.ConfigPanel host methods'

[IO.File]::WriteAllText($journalPath, $journal, [Text.UTF8Encoding]::new($false))

$systemPage = Get-Content -LiteralPath $systemPagePath -Raw
$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle '      this.CategoryList.entryList.push({text:"$SETTINGS"});' `
    -Replacement "      this.CategoryList.entryList.push({text:`"`$SETTINGS`"});`n      this.CategoryList.entryList.push({text:`"`$MOD CONFIGURATION`"});" `
    -Description 'SystemPage MCM category'

$disabledBranch = @'
      if(event.entry.disabled)
      {
         gfx.io.GameDelegate.call("PlaySound",["UIMenuCancel"]);
      }
      else if(this.iCurrentState == SystemPage.MAIN_STATE)
'@

$mcmBranch = @'
      if(event.entry.disabled)
      {
         gfx.io.GameDelegate.call("PlaySound",["UIMenuCancel"]);
      }
      else if(this.iCurrentState == SystemPage.MAIN_STATE && event.entry.text == "$MOD CONFIGURATION")
      {
         _root.QuestJournalFader.Menu_mc.ConfigPanelOpen();
         this.CategoryList.setInteractive(true);
         return;
      }
      else if(this.iCurrentState == SystemPage.MAIN_STATE)
'@

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle $disabledBranch `
    -Replacement $mcmBranch `
    -Description 'SystemPage MCM selection handler'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle '         _loc3_ = event.index;' `
    -Replacement @'
         _loc3_ = event.index;
         if(event.entry.text == "$CONTROLS" || event.entry.text == "$HELP" || event.entry.text == "$QUIT")
         {
            _loc3_ -= 1;
         }
'@ `
    -Description 'SystemPage indices after the SkyUI-positioned MCM category'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle '            _loc3_ = event.index + 1;' `
    -Replacement '            _loc3_ += 1;' `
    -Description 'SystemPage optional-mod-manager index adjustment'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle 'this.CategoryList.entryList[5],this.CategoryList.entryList[8],true' `
    -Replacement 'this.CategoryList.entryList[5],this.CategoryList.entryList[9],true' `
    -Description 'SystemPage shown-mod-manager permission indices'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle 'this.CategoryList.entryList[4],this.CategoryList.entryList[7],true' `
    -Replacement 'this.CategoryList.entryList[4],this.CategoryList.entryList[8],true' `
    -Description 'SystemPage hidden-mod-manager permission indices'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle 'this.CategoryList.entryList[5],this.CategoryList.entryList[8],false' `
    -Replacement 'this.CategoryList.entryList[5],this.CategoryList.entryList[9],false' `
    -Description 'SystemPage shown-mod-manager update indices'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle "         this.CategoryList.entryList[6].disabled = false;`n         this.CategoryList.entryList[7].disabled = false;" `
    -Replacement "         this.CategoryList.entryList[7].disabled = false;`n         this.CategoryList.entryList[8].disabled = false;" `
    -Description 'SystemPage shown-mod-manager enabled entries'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle 'this.CategoryList.entryList[4],this.CategoryList.entryList[7],false' `
    -Replacement 'this.CategoryList.entryList[4],this.CategoryList.entryList[8],false' `
    -Description 'SystemPage hidden-mod-manager update indices'

$systemPage = Replace-ExactlyOnce -Text $systemPage `
    -Needle "         this.CategoryList.entryList[5].disabled = false;`n         this.CategoryList.entryList[6].disabled = false;" `
    -Replacement "         this.CategoryList.entryList[6].disabled = false;`n         this.CategoryList.entryList[7].disabled = false;" `
    -Description 'SystemPage hidden-mod-manager enabled entries'

[IO.File]::WriteAllText($systemPagePath, $systemPage, [Text.UTF8Encoding]::new($false))

Write-Host 'Patched vanilla Quest_Journal.as and SystemPage.as for OpenMCM.'
