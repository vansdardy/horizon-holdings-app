; ---------------------------------------------------------------------------
; Installer customisation: make the desktop icon a choice, not an assumption.
;
; electron-builder's assisted installer has no checkbox for this — it either
; always creates a desktop shortcut or never does. Adding one means writing a
; page by hand, which is what this file is.
;
; The part that is easy to get wrong is not the page. It is that an UPDATE runs
; this same installer silently, with no user and no dialogs. A naive
; implementation reads an unticked checkbox on every update and quietly deletes
; the desktop icon of someone who wanted one — or worse, recreates the icon of
; someone who did not, on every single release. So the answer is recorded in the
; registry when a human answers it, and replayed on silent installs.
;
; `createDesktopShortcut` is set to false in package.json so that this file owns
; the shortcut completely. Two pieces of code creating the same shortcut, one of
; which respects the checkbox, is how it ends up on the desktop anyway.
; ---------------------------------------------------------------------------

!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"

; shortcutName in package.json becomes SHORTCUT_NAME. The fallback keeps this
; file working if that setting is ever removed, rather than silently producing
; a shortcut called ".lnk".
!ifndef SHORTCUT_NAME
  !define SHORTCUT_NAME "${PRODUCT_FILENAME}"
!endif

!define HH_PREF_KEY "Software\HorizonHoldings"

; Everything to do with the PAGE is skipped while the uninstaller is being
; built. electron-builder compiles this same script twice — once with
; BUILD_UNINSTALLER defined — and that pass has no wizard pages at all, so the
; page functions end up defined and never called. NSIS reports that as
; "warning 6010: install function not referenced", and electron-builder treats
; warnings as errors, so the build fails with no obvious connection to pages.
!ifndef BUILD_UNINSTALLER

; Declared inside the guard for the same reason: NSIS warns about variables that
; are never referenced, and in the uninstaller pass nothing touches these.
Var HHDesktopCheckbox
Var HHMakeDesktopShortcut

; Inserted after the "choose install location" page.
!macro customPageAfterChangeDir
  Page custom hhShortcutPageCreate hhShortcutPageLeave
!macroend

Function hhShortcutPageCreate
  ; The header is set by talking to the wizard's own labels (1037 is the title,
  ; 1038 the subtitle) rather than with MUI_HEADER_TEXT. electron-builder
  ; includes this file BEFORE it includes MUI2, so that macro does not exist yet
  ; at the point these lines are parsed, and using it fails the build with an
  ; error that only names a line number.
  GetDlgItem $0 $HWNDPARENT 1037
  SendMessage $0 ${WM_SETTEXT} 0 "STR:Shortcuts"
  GetDlgItem $0 $HWNDPARENT 1038
  SendMessage $0 ${WM_SETTEXT} 0 "STR:Choose where Horizon Holdings appears."

  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 24u "The Start menu entry is always created. The desktop icon is optional."
  Pop $1

  ${NSD_CreateCheckbox} 0 32u 100% 12u "Create a desktop icon"
  Pop $HHDesktopCheckbox

  ; Default to whatever was chosen last time. A reinstall should not quietly
  ; undo a decision the user already made; a first install defaults to ticked,
  ; which is what people expect from a Windows installer.
  ReadRegStr $2 SHCTX "${HH_PREF_KEY}" "DesktopShortcut"
  ${If} $2 == "0"
    ${NSD_SetState} $HHDesktopCheckbox 0
  ${Else}
    ${NSD_SetState} $HHDesktopCheckbox 1
  ${EndIf}

  nsDialogs::Show
FunctionEnd

Function hhShortcutPageLeave
  ${NSD_GetState} $HHDesktopCheckbox $HHMakeDesktopShortcut
FunctionEnd

!endif ; BUILD_UNINSTALLER

!macro customInstall
  ; A silent run means an update: no page was shown, so the checkbox variable
  ; holds nothing meaningful. Replay the stored answer instead of acting on it.
  ${If} ${Silent}
    ReadRegStr $R0 SHCTX "${HH_PREF_KEY}" "DesktopShortcut"
    ${If} $R0 == "0"
      StrCpy $HHMakeDesktopShortcut 0
    ${Else}
      StrCpy $HHMakeDesktopShortcut 1
    ${EndIf}
  ${EndIf}

  ${If} $HHMakeDesktopShortcut == 1
    CreateShortCut "$DESKTOP\${SHORTCUT_NAME}.lnk" "$INSTDIR\${APP_EXECUTABLE_FILENAME}"
    WriteRegStr SHCTX "${HH_PREF_KEY}" "DesktopShortcut" "1"
  ${Else}
    Delete "$DESKTOP\${SHORTCUT_NAME}.lnk"
    WriteRegStr SHCTX "${HH_PREF_KEY}" "DesktopShortcut" "0"
  ${EndIf}
!macroend

!macro customUnInstall
  Delete "$DESKTOP\${SHORTCUT_NAME}.lnk"
  ; The preference key is deliberately NOT deleted here. An update runs the old
  ; uninstaller before installing the new version, so removing the key would
  ; erase the user's answer moments before customInstall reads it — and every
  ; update would put the icon back on the desktop of the person who unticked it.
  ; One small registry value left behind is a much better outcome.
!macroend
