
import subprocess
import logging
import time
import urllib.parse
from ultragravity.actions import Action, RiskLevel

logger = logging.getLogger("AppleScriptBridge")
_gateway = None


def set_action_gateway(gateway):
    global _gateway
    _gateway = gateway


def _risk_for_operation(operation: str) -> RiskLevel:
    if operation in {"notify", "open_app"}:
        return RiskLevel.R1
    if operation in {"set_volume", "create_note", "run_script"}:
        return RiskLevel.R2
    return RiskLevel.R2

def run_applescript(script: str, operation: str = "run_script", scope: list[str] | None = None, reason: str = ""):
    """Executes an AppleScript command."""
    def _execute_script() -> str | None:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"AppleScript Error: {e.stderr}")
            return None

    if _gateway is None:
        return _execute_script()

    action = Action(
        tool_name="applescript",
        operation=operation,
        params={"script_preview": script[:120]},
        risk_level=_risk_for_operation(operation),
        scope=scope or ["macOS"],
        reversible=False,
        reason=reason or "AppleScript bridge operation",
    )
    result = _gateway.execute(action, _execute_script)
    if not result.allowed or not result.executed:
        logger.warning(f"AppleScript action blocked or failed: {result.error}")
        return None
    return result.result

def open_app(app_name: str):
    """Activates or launches an application."""
    script = f'tell application "{app_name}" to activate'
    return run_applescript(script, operation="open_app", scope=[app_name], reason=f"Open application {app_name}")

def create_note(content: str):
    """Creates a new note in the Notes app."""
    # Ensure Notes is open
    open_app("Notes")
    
    script = f'''
    tell application "Notes"
        tell account "iCloud"
            make new note at folder "Notes" with properties {{body: "{content}"}}
        end tell
    end tell
    '''
    # Fallback to default account if iCloud fails or is named differently
    # But for now let's try a simpler approach if that fails:
    # Just "make new note" in default account
    
    # Robust script:
    script = f'''
    tell application "Notes"
        activate
        delay 0.5
        make new note with properties {{body: "{content}"}}
    end tell
    '''
    return run_applescript(script, operation="create_note", scope=["Notes"], reason="Create note in Notes app")

def set_volume(level: int):
    """Sets system volume (0-100)."""
    script = f'set volume output volume {level}'
    return run_applescript(script, operation="set_volume", scope=["system_audio"], reason=f"Set system volume to {level}")

def system_notify(title: str, text: str):
    """Sends a system notification."""
    script = f'display notification "{text}" with title "{title}"'
    return run_applescript(script, operation="notify", scope=["notifications"], reason="Send system notification")


# ---------------------------------------------------------------------------
# WhatsApp for Mac  (Catalyst app – menu-bar + keystroke driven)
# ---------------------------------------------------------------------------


def whatsapp_send_message(contact: str, message: str, send: bool = False) -> str | None:
    """Send a message via WhatsApp for Mac using menu-bar navigation.

    WhatsApp on macOS is a Catalyst app that exposes **zero windows** to
    System-Events, so we cannot inspect or target UI elements.  Instead we
    drive the app entirely through:
      1. Menu-bar clicks  (File → Search / ⌘F)
      2. Blind keystrokes (type contact name, arrow-select, type message)

    Parameters
    ----------
    contact : str
        Display name exactly as it appears in WhatsApp (case-sensitive).
    message : str
        The text to type into the chat box.
    send : bool
        If *True*, press Enter to actually send.  Default is *False*
        (draft mode — the message is typed but not sent).

    Returns
    -------
    str | None
        Status string from AppleScript, or None on failure.
    """
    mode = "send" if send else "draft"
    # Escape double-quotes for AppleScript string safety
    safe_contact = contact.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')

    script = f'''
    tell application "WhatsApp" to activate
    delay 1.5

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
        end tell

        -- Open search (Cmd+F)
        keystroke "f" using command down
        delay 0.8

        -- Clear & type contact name
        keystroke "a" using command down
        delay 0.1
        key code 51
        delay 0.2
        keystroke "{safe_contact}"
        delay 2.0

        -- Select first search result (auto-highlighted)
        key code 36
        delay 1.5

        -- Type message
        keystroke "{safe_message}"
        delay 0.3
    end tell

    if "{mode}" is "send" then
        tell application "System Events" to key code 36
        return "SENT"
    else
        return "DRAFT"
    end if
    '''
    return run_applescript(
        script,
        operation="whatsapp_send",
        scope=["WhatsApp"],
        reason=f"WhatsApp {mode}: '{message}' → {contact}",
    )


def whatsapp_send_message_by_phone(phone: str, message: str, send: bool = False) -> str | None:
    """Open a WhatsApp chat by phone number using whatsapp:// URL scheme.

    This is the most reliable path on macOS because it bypasses UI navigation
    and directly opens the target chat.
    """
    cleaned_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if not cleaned_phone:
        logger.error("Invalid phone for WhatsApp URL flow")
        return None

    encoded_phone = urllib.parse.quote(cleaned_phone)
    encoded_text = urllib.parse.quote(message)
    url = f"whatsapp://send?phone={encoded_phone}&text={encoded_text}"

    def _open_url() -> str | None:
        try:
            subprocess.run(["open", url], check=True)
            time.sleep(1.2)
            if send:
                subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to key code 36'],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return "SENT_BY_PHONE_URL"
            return "DRAFT_BY_PHONE_URL"
        except subprocess.CalledProcessError as e:
            logger.error(f"WhatsApp URL Error: {e}")
            return None

    if _gateway is None:
        return _open_url()

    action = Action(
        tool_name="open_url",
        operation="whatsapp_send_phone",
        params={"url_preview": url[:120]},
        risk_level=RiskLevel.R2,
        scope=["WhatsApp"],
        reversible=False,
        reason=f"WhatsApp {'send' if send else 'draft'} by phone",
    )
    result = _gateway.execute(action, _open_url)
    if not result.allowed or not result.executed:
        logger.warning(f"WhatsApp URL action blocked or failed: {result.error}")
        return None
    return result.result
