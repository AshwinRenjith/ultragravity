tell application "WhatsApp" to activate
delay 0.8

tell application "System Events"
    tell process "WhatsApp"
        set frontmost to true
        set outputLines to {}
        set win1 to front window

        set end of outputLines to "WINDOW:" & (name of win1 as text)

        repeat with tfItem in (text fields of win1)
            try
                set tfName to name of tfItem as text
                set tfValue to value of tfItem as text
                set end of outputLines to "TEXTFIELD:" & tfName & "|" & tfValue
            end try
        end repeat

        repeat with stItem in (static texts of win1)
            try
                set stValue to value of stItem as text
                if stValue is not "" then
                    set end of outputLines to "STATIC:" & stValue
                end if
            end try
        end repeat

        repeat with btnItem in (buttons of win1)
            try
                set btnName to name of btnItem as text
                set end of outputLines to "BUTTON:" & btnName
            end try
        end repeat

        set AppleScript's text item delimiters to linefeed
        return outputLines as text
    end tell
end tell
