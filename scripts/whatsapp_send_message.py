from __future__ import annotations

import argparse
import random
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def human_type(page, selector: str, text: str) -> None:
    page.click(selector)
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.04, 0.12))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a WhatsApp Web message with human-like typing.")
    parser.add_argument("--contact", required=True, help="Exact contact or chat name")
    parser.add_argument("--message", required=True, help="Message text to send")
    args = parser.parse_args()

    profile_dir = Path("data/whatsapp_profile")
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1366, "height": 800},
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

        print("Opened WhatsApp Web. Waiting for chat UI...")

        search_selectors = [
            "div[aria-label='Search input textbox']",
            "div[contenteditable='true'][data-tab='3']",
            "div[contenteditable='true'][title='Search input textbox']",
        ]

        search_selector = None
        for sel in search_selectors:
            try:
                page.wait_for_selector(sel, timeout=15000)
                search_selector = sel
                break
            except PlaywrightTimeoutError:
                continue

        if search_selector is None:
            print("Chat list/search did not appear. If QR is visible, scan it and re-run.")
            context.close()
            return 2

        time.sleep(random.uniform(0.4, 0.9))
        human_type(page, search_selector, args.contact)
        time.sleep(random.uniform(0.8, 1.5))
        page.keyboard.press("Enter")

        message_selectors = [
            "div[aria-label='Type a message']",
            "div[contenteditable='true'][data-tab='10']",
            "footer div[contenteditable='true']",
        ]

        message_selector = None
        for sel in message_selectors:
            try:
                page.wait_for_selector(sel, timeout=10000)
                message_selector = sel
                break
            except PlaywrightTimeoutError:
                continue

        if message_selector is None:
            print("Opened chat, but message box was not found.")
            context.close()
            return 3

        time.sleep(random.uniform(0.4, 0.9))
        human_type(page, message_selector, args.message)
        time.sleep(random.uniform(0.3, 0.8))
        page.keyboard.press("Enter")

        print(f"Message sent: {args.message} -> {args.contact}")
        time.sleep(2)
        context.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
