on run argv
    if (count of argv) < 3 then
        error "Usage: osascript send_whatsapp_guarded.applescript <contact> <message> <draft|send>"
    end if

    set targetContact to item 1 of argv
    set messageText to item 2 of argv
    set mode to item 3 of argv

    if mode is not "draft" and mode is not "send" then
        error "Mode must be draft or send"
    end if

    tell application "WhatsApp" to activate
    delay 1.0

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true

            set hasWindow to false
            repeat with i from 1 to 25
                if (count of windows) > 0 then
                    set hasWindow to true
                    exit repeat
                end if
                delay 0.2
            end repeat

            if hasWindow is false then
                error "WhatsApp window not accessible; check app is open and Accessibility permission is granted."
            end if

            keystroke "f" using command down
            delay 0.25
            keystroke targetContact
            delay 0.55

            key code 125
            delay 0.15
            key code 36
            delay 0.7
        end tell
    end tell

    set verified to false
    tell application "System Events"
        tell process "WhatsApp"
            set win1 to front window
            repeat with stItem in (static texts of win1)
                try
                    set labelText to value of stItem as text
                    if labelText contains targetContact then
                        set verified to true
                        exit repeat
                    end if
                end try
            end repeat
        end tell
    end tell

    if verified is false then
        error "Recipient verification failed; message not sent."
    end if

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            keystroke messageText
            delay 0.2

            if mode is "send" then
                key code 36
                return "SENT"
            else
                return "DRAFT_READY"
            end if
        end tell
    end tell
end run
