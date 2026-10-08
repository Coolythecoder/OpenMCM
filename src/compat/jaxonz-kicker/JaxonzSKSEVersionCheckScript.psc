Scriptname JaxonzSKSEVersionCheckScript extends Quest

; OpenMCM compatibility adaptation of Jaxonz's shared version checker.
; SE port by insaneplumber: https://www.nexusmods.com/skyrimspecialedition/mods/36801
; Distributed under the upstream permission to modify with credit, for
; noncommercial use. This adapted script is not relicensed under MIT.
; Only the original Kicker quest may substitute the MCM manager for SkyUI.

String Property strModName Auto
String Property sSKSEVersionRequired = "2.0.17" Auto
Int Property iMinVersionRelease = 46 Auto
Int Property iWarnUser = 1 Auto
Int iWarnNever = 0
Int iWarnOnFail = 1
Int iWarnAlways = 2
Int Property iSkyUIRequired = 1 Auto
Int iSkyUINotRequired = 0
Int iSkyUINotOptional = 1
; The original PEX has BOTH this variable and the identically named auto
; property (backed by ::iSkyUIRequired_var). Keep its saved-variable ABI.
; Explicit Self.iSkyUIRequired reads select the property, matching the PEX.
Int iSkyUIRequired = 2
String Property sUserWarningMessage Auto

Event OnInit()
	CheckSKSEVersion(iWarnUser)
	CheckSkyUIVersion(iWarnUser)
EndEvent

Bool Function CheckSKSEVersion(Int iWarnUserFlag)
;check the current SKSE version and display a message if below minimum required
	Int iVersion
	Int iVersionMinor
	Int iVersionBeta
	Int iVersionRelease
	String CurrentSKSEVersionString
	String MinimumSKSEVersionString
	Bool bGoodEnough
	String strWarningMessage

	iVersionRelease = SKSE.GetVersionRelease()
	iVersion = SKSE.GetVersion()
	iVersionMinor = SKSE.GetVersionMinor()
	iVersionBeta = SKSE.GetVersionBeta()

	CurrentSKSEVersionString = iVersion + "." + iVersionMinor + "." + iVersionBeta + " rel " + iVersionRelease

	If SKSE.GetVersionRelease() < iMinVersionRelease
		strWarningMessage = strModName + " was compiled with SKSE  " + sSKSEVersionRequired + "\n\n"
	Else
		bGoodEnough = True
	EndIf

	If !iVersionRelease
		strWarningMessage += "It appears that SKSE is not installed or that Skyrim was not started via SKSE_loader.exe with sufficient privilege.\n\n"
	EndIf

	If bGoodEnough && (iWarnUserFlag == iWarnAlways)
		strWarningMessage = "A sufficient version of SKSE is installed.\n\n" + strWarningMessage
		Debug.MessageBox(strWarningMessage)
	ElseIf (iWarnUserFlag != iWarnNever) && !bGoodEnough
		strWarningMessage = "Warning:\n" + strWarningMessage
		If iVersion
			strWarningMessage += "The SKSE version installed may not be sufficient.\n\n"
		Else
			strWarningMessage += strModName + " will not run.\n\n"
		EndIf

		If sUserWarningMessage != ""
			strWarningMessage += sUserWarningMessage + "\n\n"
		EndIf

		strWarningMessage += "Please visit http://skse.silverlock.org/ for the newest version."
		Debug.MessageBox(strWarningMessage)
	EndIf

	Return bGoodEnough
EndFunction

Bool Function CheckSkyUIVersion(Int iWarnUserFlag)
	Bool bSkyUIInstalled = Quest.GetQuest("SKI_MainInstance")
	; Do not weaken this shared checker for another Jaxonz mod. Form identity
	; is load-order independent and does not trust an editable name property.
	If !bSkyUIInstalled && Self == Game.GetFormFromFile(0x000D62, "JaxonzMCMKicker.esp")
		Quest mcmManager = Quest.GetQuest("SKI_ConfigManagerInstance")
		If mcmManager != None
			If iWarnUserFlag == iWarnAlways
				Debug.MessageBox(strModName + " has an MCM configuration manager installed.\n\n")
			EndIf
			Return Self.iSkyUIRequired as Bool
		EndIf
	EndIf

	; Preserve the upstream full-SkyUI behavior for every other quest and
	; for Kicker when its manager is absent, including warning/return rules.
	String strWarning = strModName
	If Self.iSkyUIRequired == iSkyUINotRequired
		strWarning += " does not require SkyUI.\n\n"
	ElseIf Self.iSkyUIRequired == iSkyUINotOptional
		strWarning += " leverages SkyUI.\n\n"
	ElseIf Self.iSkyUIRequired == Self.iSkyUIRequired
		strWarning += " requires SkyUI.\n\n"
	EndIf

	If !bSkyUIInstalled
		strWarning += "This system does not appear to have SkyUI installed.\n\n"
	Else
		strWarning += "This system has SkyUI installed.\n\n"
	EndIf

	If iWarnUserFlag == iWarnNever
		;do nothing
	ElseIf bSkyUIInstalled && (iWarnUserFlag == iWarnAlways)
		Debug.MessageBox(strWarning)
	ElseIf !bSkyUIInstalled && (Self.iSkyUIRequired == iSkyUINotOptional)
		strWarning += "Some features may not be availalble."
		Debug.MessageBox(strWarning)
	ElseIf !bSkyUIInstalled && (Self.iSkyUIRequired == Self.iSkyUIRequired)
		strWarning += strModName + " will not run correctly without it. Please install SkyUI."
		Debug.MessageBox(strWarning)
	EndIf

	Return bSkyUIInstalled && Self.iSkyUIRequired
EndFunction
