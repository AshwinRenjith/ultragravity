import subprocess
import sys


def main() -> int:
    print("Unsafe coordinate-based sender is disabled to prevent random clicks.")
    print("Use guarded AppleScript instead:")
    print("  osascript scripts/send_whatsapp_guarded.applescript 'Ayush Benny' 'hi' draft")
    print("  osascript scripts/send_whatsapp_guarded.applescript 'Ayush Benny' 'hi' send")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
