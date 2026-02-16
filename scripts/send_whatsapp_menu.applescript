-- send_whatsapp_menu.applescript
-- Menu-bar driven WhatsApp message sender for macOS Catalyst app.
-- Avoids all window/UI-element access (Catalyst apps report 0 windows).
-- Uses: menu clicks + blind keystrokes only.
--
-- Usage:
--   osascript scripts/send_whatsapp_menu.applescript <contact> <message> [draft|send]
--   draft = types message but does NOT press Enter (default)
--   send  = types message and presses Enter to send

on run argv
	-- Parse arguments
	if (count of argv) < 2 then
		error "Usage: osascript send_whatsapp_menu.applescript <contact> <message> [draft|send]"
	end if
	
	set contactName to item 1 of argv
	set messageText to item 2 of argv
	
	set sendMode to "draft"
	if (count of argv) ≥ 3 then
		set sendMode to item 3 of argv
	end if
	
	-- Step 1: Activate WhatsApp
	tell application "WhatsApp" to activate
	delay 1.5
	
	-- Step 2: Ensure WhatsApp is frontmost
	tell application "System Events"
		tell process "WhatsApp"
			set frontmost to true
		end tell
	end tell
	delay 0.3
	
	-- Step 3: Open search via Cmd+F (universal shortcut in WhatsApp)
	tell application "System Events"
		keystroke "f" using command down
	end tell
	delay 0.8
	
	-- Step 4: Clear any existing search text and type contact name
	tell application "System Events"
		keystroke "a" using command down
		delay 0.1
		key code 51 -- delete/backspace
		delay 0.2
		keystroke contactName
	end tell
	delay 2.0 -- wait for search results to populate
	
	-- Step 5: Select the first search result
	-- In WhatsApp Mac, the first result is auto-highlighted.
	-- Press Return to open it directly from the search field.
	tell application "System Events"
		key code 36 -- return/enter to open first result
	end tell
	delay 1.5 -- wait for chat to fully load
	
	-- Step 6: Type the message into the chat input
	tell application "System Events"
		keystroke messageText
	end tell
	delay 0.3
	
	if sendMode is "send" then
		-- Step 7: Send the message
		tell application "System Events"
			key code 36 -- return/enter
		end tell
		return "SENT: Message '" & messageText & "' sent to " & contactName
	else
		return "DRAFT: Message '" & messageText & "' typed for " & contactName & " (not sent). Press Enter to send."
	end if
end run
