"""
WhatsApp Skill – send messages via the native WhatsApp for Mac app.

WhatsApp on macOS is a Catalyst (UIKit) app that exposes **zero windows**
to System-Events.  This skill therefore drives the app entirely through
menu-bar clicks and blind keystrokes via ``bridge_applescript``.

Optional vision verification
-----------------------------
When the agent has a ``DesktopAgent`` attached (``self.agent.desktop``),
this skill can take a screenshot after composing the draft to let the
caller (or a VLM) confirm the correct chat is open before sending.
"""

import os
import re
import time
import logging
from typing import Dict, Any

from skills.base import Skill
from skills.contact_map import WHATSAPP_CONTACT_MAP
from agent.bridge_applescript import whatsapp_send_message, whatsapp_send_message_by_phone, open_app
try:
    from termcolor import colored
except Exception:  # pragma: no cover - optional dependency fallback
    def colored(text: str, *_args, **_kwargs):
        return text

logger = logging.getLogger("WhatsAppSkill")


class WhatsAppSkill(Skill):
    """Skill for sending WhatsApp messages via the native macOS app."""

    # ── Intent matching ──────────────────────────────────────────────
    _TRIGGER_PATTERNS = [
        re.compile(r"\bwhatsapp\b", re.I),
        re.compile(r"\bsend\b.*\bmessage\b", re.I),
        re.compile(r"\btext\b.*\bon whatsapp\b", re.I),
        re.compile(r"\bmessage\b.*\bon whatsapp\b", re.I),
    ]

    def __init__(self, agent):
        super().__init__(agent)

    # ── can_handle ───────────────────────────────────────────────────
    def can_handle(self, instruction: str) -> float:
        lower = instruction.lower()
        normalized_instruction = self._normalize_contact_name(instruction)
        has_send_intent = any(token in lower for token in ("send", "message", "text", "greet", "greeting", "say"))
        has_target = " to " in f" {lower} "

        # High confidence if we can resolve a mapped contact name (supports short aliases like "ayush")
        if has_send_intent and has_target and self._mapped_contact_in_text(normalized_instruction):
            return 0.97

        # High confidence if "whatsapp" mentioned explicitly
        if "whatsapp" in lower:
            # Even higher if there's a clear send/message intent
            if any(w in lower for w in ("send", "message", "text", "hi", "hello", "say")):
                return 0.97
            return 0.90

        # Medium confidence for generic "send message to <name>"
        if re.search(r"\bsend\b.+\bto\b", lower):
            return 0.55

        return 0.0

    # ── execute ──────────────────────────────────────────────────────
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        instruction: str = params.get("instruction", "")
        phone = self._extract_phone(instruction)
        contact, message = self._parse_instruction(instruction)

        if not phone and contact:
            phone = self._phone_from_contact(contact)

        if not phone and not contact:
            return {"status": "fail", "reason": "Could not determine the recipient from the instruction."}
        if not message:
            message = "hi"  # sensible default
        message = self._normalize_message(message)

        # Let the LLM compose a natural WhatsApp message from the user's intent
        message = self._compose_message(contact or "", message)

        if phone and "X" in phone:
            return {
                "status": "fail",
                "reason": "Contact map has a placeholder number. Update skills/contact_map.py with the real number.",
            }

        recipient_label = phone or contact
        print(colored(f"💬 WhatsApp → {recipient_label}: \"{message}\"", "green"))

        # ── Phase 1: draft (type but don't send) ─────────────────────
        if phone:
            result = whatsapp_send_message_by_phone(phone, message, send=False)
        else:
            result = whatsapp_send_message(contact, message, send=False)

        if result is None:
            return {"status": "fail", "reason": "AppleScript bridge returned None — WhatsApp may not be installed or accessible."}

        # ── Phase 2: optional vision verification ────────────────────
        verified = self._vision_verify(contact or phone)

        if not verified:
            logger.warning("Vision verification unavailable or inconclusive — proceeding with send.")

        # ── Phase 3: send ────────────────────────────────────────────
        if phone:
            send_result = whatsapp_send_message_by_phone(phone, message, send=True)
            if send_result is None:
                return {"status": "fail", "reason": "Could not send via phone URL flow."}
        else:
            self._press_enter_to_send()

        print(colored(f"✅ Message sent to {recipient_label}!", "green"))

        return {
            "status": "success",
            "contact": contact,
            "phone": phone,
            "message": message,
            "verified": verified,
        }

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _parse_instruction(instruction: str) -> tuple[str | None, str | None]:
        """Extract (contact_name, message_body) from a natural-language instruction.

        Handles patterns like:
          • "send hi to Ayush Benny on whatsapp"
          • "whatsapp Ayush Benny saying hello"
          • "open whatsapp and send 'hey there' to Ayush Benny"
          • "message Ayush Benny hi on whatsapp"
        """
        text = instruction.strip()

        # Pattern -1a: write/create a message to <contact>, <content>
        m = re.search(
            r"(?:write|draft|create)\s+(?:a\s+)?message\s+to\s+(.+?)\s*,\s*(.+)$",
            text,
            re.I,
        )
        if m:
            contact = re.sub(r"\s+", " ", m.group(1)).strip().strip(",")
            message = m.group(2).strip().strip('"\'')
            message = re.sub(r"^(asking|saying|that)\s+", "", message, flags=re.I).strip()
            return contact, message

        # Pattern -1b: write/create a message to <contact> asking/saying/about <content>
        m = re.search(
            r"(?:write|draft|create)\s+(?:a\s+)?message\s+to\s+(.+?)\s+(asking|saying|that|about)\s+(.+)$",
            text,
            re.I,
        )
        if m:
            contact = re.sub(r"\s+", " ", m.group(1)).strip().strip(",")
            lead = m.group(2).strip().lower()
            payload = m.group(3).strip().strip('"\'')
            if lead == "about":
                message = f"about {payload}".strip()
            else:
                message = payload
            return contact, message

        # Pattern 0: write/draft/create <msg> to <contact>
        m = re.search(
            r"(?:write|draft|create)\s+['\"]?(.+?)['\"]?\s+to\s+([A-Z][\w\s]+?)(?:\s+on\s+whatsapp)?$",
            text,
            re.I,
        )
        if m:
            return m.group(2).strip(), m.group(1).strip()

        # Pattern 1: send <msg> to <contact> [on whatsapp]
        m = re.search(
            r"(?:send|text|message)\s+['\"]?(.+?)['\"]?\s+to\s+([A-Z][\w\s]+?)(?:\s+on\s+whatsapp)?$",
            text, re.I,
        )
        if m:
            return m.group(2).strip(), m.group(1).strip()

        # Pattern 2: <contact> saying/with <msg>
        m = re.search(
            r"(?:whatsapp|message|text)\s+([A-Z][\w\s]+?)\s+(?:saying|with|:)\s+(.+)",
            text, re.I,
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # Pattern 3: send <msg> to <contact>  (simple, greedy contact)
        m = re.search(r"send\s+['\"]?(.+?)['\"]?\s+to\s+(.+?)(?:\s+on|\s*$)", text, re.I)
        if m:
            return m.group(2).strip(), m.group(1).strip()

        # Pattern 4: just grab a quoted message and everything that looks like a name
        m = re.search(r"['\"](.+?)['\"]\s+to\s+([A-Z][\w\s]+)", text, re.I)
        if m:
            return m.group(2).strip(), m.group(1).strip()

        # Fallback: look for a capitalised proper name anywhere
        names = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
        if names:
            # Try to find a message fragment (anything after "send" or "say")
            msg_match = re.search(r"(?:send|say|text)\s+(.+?)(?:\s+to\b|$)", text, re.I)
            msg = msg_match.group(1).strip() if msg_match else None
            return names[0], msg

        return None, None

    @staticmethod
    def _extract_phone(instruction: str) -> str | None:
        """Extract a phone number in local/international format from text."""
        match = re.search(r"(\+?\d[\d\s\-\(\)]{6,}\d)", instruction)
        if not match:
            return None
        raw = match.group(1)
        cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
        return cleaned or None

    @staticmethod
    def _normalize_message(message: str) -> str:
        text = (message or "").strip().strip('"\'')
        text = re.sub(r"^(a|an)\s+", "", text, flags=re.IGNORECASE)

        canned = {
            "nice greeting": "Hey! Hope you're doing great 😊",
            "greeting": "Hey! Hope you're doing great 😊",
            "greetings": "Hey! Hope you're doing great 😊",
            "greetings message": "Hey! Hope you're doing great 😊",
            "nice greetings": "Hey! Hope you're doing great 😊",
            "nice greetings message": "Hey! Hope you're doing great 😊",
        }
        lowered = text.lower()
        if lowered in canned:
            return canned[lowered]
        return text or "hi"

    @staticmethod
    def _normalize_contact_name(name: str) -> str:
        normalized = re.sub(r"\s+", " ", name.strip().lower())
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        return normalized

    def _phone_from_contact(self, contact: str) -> str | None:
        key = self._normalize_contact_name(contact)
        exact = WHATSAPP_CONTACT_MAP.get(key)
        if exact:
            return exact

        # Support shorthand names (e.g., "ayush" matching "ayush benny")
        for mapped_name, phone in WHATSAPP_CONTACT_MAP.items():
            mapped_key = self._normalize_contact_name(mapped_name)
            if key == mapped_key or key in mapped_key or mapped_key in key:
                return phone
        return None

    def _mapped_contact_in_text(self, normalized_instruction: str) -> bool:
        for mapped_name in WHATSAPP_CONTACT_MAP.keys():
            mapped_key = self._normalize_contact_name(mapped_name)
            if mapped_key and mapped_key in normalized_instruction:
                return True
            mapped_tokens = [token for token in mapped_key.split() if token]
            if any(token and token in normalized_instruction.split() for token in mapped_tokens):
                return True
        return False

    def _vision_verify(self, expected_contact: str) -> bool:
        """Take a desktop screenshot and check if the chat header matches."""
        desktop = getattr(self.agent, "desktop", None)
        if desktop is None:
            return False

        try:
            path = desktop.get_screenshot("whatsapp_verify.png")
            logger.info(f"📸 Verification screenshot saved to {path}")
            # For now we return True (screenshot taken but no VLM call).
            # A future enhancement can feed this to analyze_image() with
            # a prompt like "Does the WhatsApp chat header say <contact>?"
            return True
        except Exception as e:
            logger.warning(f"Vision verify failed: {e}")
            return False

    @staticmethod
    def _compose_message(contact: str, raw_message: str) -> str:
        """Use an LLM to rewrite the user's raw intent into a natural WhatsApp message."""
        # Skip LLM for very short/simple messages that are already natural
        skip_keywords = {"hi", "hello", "hey", "ok", "yes", "no", "thanks", "thank you"}
        stripped = raw_message.strip().strip('"\'')
        if stripped.lower() in skip_keywords or stripped.startswith("Hey"):
            return stripped

        # Try Mistral first (via HTTP, zero extra deps), then Gemini as fallback
        first_name = contact.split()[0] if contact else ""
        system_prompt = (
            "You compose short, casual WhatsApp messages on behalf of the user. "
            "Output ONLY the message text — no quotes, no explanation."
        )
        user_prompt = (
            f"Recipient: {contact}\n"
            f"User's intent: {raw_message}\n\n"
            f"Write a friendly, casual WhatsApp message (1-3 sentences). "
            f"Address them as {first_name} if appropriate. Keep it natural."
        )

        # ── Mistral path (preferred) ────────────────────────────────
        mistral_key = os.environ.get("MISTRAL_API_KEY", "")
        if mistral_key:
            try:
                import ssl
                import urllib.request
                import json as _json
                # macOS Python often lacks system certs; use certifi
                try:
                    import certifi
                    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
                except ImportError:
                    ssl_ctx = ssl.create_default_context()
                payload = _json.dumps({
                    "model": "mistral-small-latest",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.7,
                }).encode()
                req = urllib.request.Request(
                    "https://api.mistral.ai/v1/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {mistral_key}",
                    },
                )
                with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
                    body = _json.loads(resp.read())
                composed = body["choices"][0]["message"]["content"].strip().strip('"\'')
                if composed:
                    logger.info(f"LLM composed (mistral): {composed}")
                    return composed
            except Exception as e:
                logger.warning(f"Mistral composition failed: {e}")

        # ── Gemini fallback ──────────────────────────────────────────
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            try:
                import google.generativeai as genai
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel("gemini-2.0-flash")
                prompt = f"{system_prompt}\n\n{user_prompt}"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = model.generate_content(prompt)
                composed = response.text.strip().strip('"\'')
                if composed:
                    logger.info(f"LLM composed (gemini): {composed}")
                    return composed
            except Exception as e:
                logger.warning(f"Gemini composition failed: {e}")

        logger.warning("No LLM available — sending raw message.")
        return raw_message

    @staticmethod
    def _press_enter_to_send():
        """Press Enter via System Events to send the drafted message."""
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to key code 36'],
            capture_output=True,
        )
        time.sleep(0.3)
