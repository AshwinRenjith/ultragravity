
from agent.bridge_applescript import create_note, open_app, system_notify
import time

print("Testing AppleScript Bridge...")

print("1. Sending Notification...")
system_notify("Ultragravity", "Desktop Agent Connected.")
time.sleep(2)

print("2. Opening Notes App...")
print(open_app("Notes"))
time.sleep(2)

print("3. Creating a Test Note...")
result = create_note("This is a test note created by Ultragravity AI.\n\nIt demonstrates that the Python-AppleScript bridge is functioning correctly.")
print(f"Result: {result}")

print("Done.")
