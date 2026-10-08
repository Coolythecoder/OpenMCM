Scriptname OpenMCMExample extends SKI_ConfigBase

Bool enabled = True
Float intensity = 1.0
Int modeIndex = 0
Int accentColor = 0x4FA3FF
Int shortcutKey = 34
String profileName = "Default"
String[] modeNames

Int enabledOID
Int intensityOID
Int modeOID
Int colorOID
Int keyOID
Int inputOID

Event OnConfigInit()
	ModName = "OpenMCM Example"

	Pages = new String[1]
	Pages[0] = "General"

	modeNames = new String[3]
	modeNames[0] = "Quiet"
	modeNames[1] = "Balanced"
	modeNames[2] = "Strong"
EndEvent

Event OnPageReset(String a_page)
	SetCursorFillMode(TOP_TO_BOTTOM)
	AddHeaderOption("Example settings")
	enabledOID = AddToggleOption("Enabled", enabled)
	intensityOID = AddSliderOption("Intensity", intensity, "{1}")
	modeOID = AddMenuOption("Mode", modeNames[modeIndex])
	colorOID = AddColorOption("Accent", accentColor)
	keyOID = AddKeyMapOption("Shortcut", shortcutKey, OPTION_FLAG_WITH_UNMAP)
	inputOID = AddInputOption("Profile", profileName)
EndEvent

Event OnOptionHighlight(Int a_option)
	If a_option == enabledOID
		SetInfoText("Turns the example feature on or off.")
	ElseIf a_option == intensityOID
		SetInfoText("Demonstrates a floating-point slider dialog.")
	ElseIf a_option == modeOID
		SetInfoText("Demonstrates a menu dialog.")
	ElseIf a_option == colorOID
		SetInfoText("Demonstrates the RGB color dialog.")
	ElseIf a_option == keyOID
		SetInfoText("Select to remap; press the unmap control to clear it.")
	ElseIf a_option == inputOID
		SetInfoText("Demonstrates the SkyUI 6 / MCM Helper text-input option.")
	EndIf
EndEvent

Event OnOptionSelect(Int a_option)
	If a_option == enabledOID
		enabled = !enabled
		SetToggleOptionValue(enabledOID, enabled)
	EndIf
EndEvent

Event OnOptionDefault(Int a_option)
	If a_option == enabledOID
		enabled = True
		SetToggleOptionValue(enabledOID, enabled)
	ElseIf a_option == intensityOID
		intensity = 1.0
		SetSliderOptionValue(intensityOID, intensity, "{1}")
	ElseIf a_option == modeOID
		modeIndex = 0
		SetMenuOptionValue(modeOID, modeNames[modeIndex])
	ElseIf a_option == colorOID
		accentColor = 0x4FA3FF
		SetColorOptionValue(colorOID, accentColor)
	ElseIf a_option == keyOID
		shortcutKey = 34
		SetKeyMapOptionValue(keyOID, shortcutKey)
	ElseIf a_option == inputOID
		profileName = "Default"
		SetInputOptionValue(inputOID, profileName)
	EndIf
EndEvent

Event OnOptionSliderOpen(Int a_option)
	If a_option == intensityOID
		SetSliderDialogStartValue(intensity)
		SetSliderDialogDefaultValue(1.0)
		SetSliderDialogRange(0.0, 5.0)
		SetSliderDialogInterval(0.1)
	EndIf
EndEvent

Event OnOptionSliderAccept(Int a_option, Float a_value)
	If a_option == intensityOID
		intensity = a_value
		SetSliderOptionValue(intensityOID, intensity, "{1}")
	EndIf
EndEvent

Event OnOptionMenuOpen(Int a_option)
	If a_option == modeOID
		SetMenuDialogOptions(modeNames)
		SetMenuDialogStartIndex(modeIndex)
		SetMenuDialogDefaultIndex(0)
	EndIf
EndEvent

Event OnOptionMenuAccept(Int a_option, Int a_index)
	If a_option == modeOID
		modeIndex = a_index
		SetMenuOptionValue(modeOID, modeNames[modeIndex])
	EndIf
EndEvent

Event OnOptionColorOpen(Int a_option)
	If a_option == colorOID
		SetColorDialogStartColor(accentColor)
		SetColorDialogDefaultColor(0x4FA3FF)
	EndIf
EndEvent

Event OnOptionColorAccept(Int a_option, Int a_color)
	If a_option == colorOID
		accentColor = a_color
		SetColorOptionValue(colorOID, accentColor)
	EndIf
EndEvent

Event OnOptionKeyMapChange(Int a_option, Int a_keyCode, String a_conflictControl, String a_conflictName)
	If a_option == keyOID
		shortcutKey = a_keyCode
		SetKeyMapOptionValue(keyOID, shortcutKey)
	EndIf
EndEvent

Event OnOptionInputOpen(Int a_option)
	If a_option == inputOID
		SetInputDialogStartText(profileName)
	EndIf
EndEvent

Event OnOptionInputAccept(Int a_option, String a_input)
	If a_option == inputOID
		profileName = a_input
		SetInputOptionValue(inputOID, profileName)
	EndIf
EndEvent
