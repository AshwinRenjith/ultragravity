import re
from typing import Dict, Any
from .base import Skill

class SearchSkill(Skill):
    """
    Skill for handling web searches on common search engines (Google, DuckDuckGo, Bing).
    Optimized to identify search bars and submit queries without requiring full VLM analysis loops.
    """

    @staticmethod
    def rewrite_query(raw_query: str) -> str:
        query = " ".join((raw_query or "").strip().split())
        if not query:
            return ""

        query = query.strip("'\" ")

        tail_patterns = [
            r"\b(and|then)\s+(provide|give|return|summari[sz]e|write|format|include|list|show)\b.*$",
            r"\b(with|including)\s+(source|sources|citation|citations|website|websites|links?)\b.*$",
            r"\b(in|as)\s+(a|an)?\s*(concise|short|bullet|bulleted|table|json|report)\b.*$",
        ]
        for pattern in tail_patterns:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip(" ,.;:-")

        query = re.sub(r"^(search|find|look\s*up)\s+(for\s+)?", "", query, flags=re.IGNORECASE)
        query = re.sub(r"^(the)\s+", "", query, flags=re.IGNORECASE)
        query = " ".join(query.split())

        if len(query.split()) < 2:
            return " ".join((raw_query or "").strip().split())
        return query

    def can_handle(self, instruction: str) -> float:
        """
        High confidence if instruction contains 'search' or 'find'.
        Avoids triggering if instruction is about verification or if we are already on a results page.
        """
        lower_instr = instruction.lower()
        if lower_instr.startswith("verify") or lower_instr.startswith("check"):
            return 0.0

        if "search" not in lower_instr and "find" not in lower_instr and "look up" not in lower_instr:
             return 0.1

        # Check if browser is active
        if not self.agent.browser.page:
            # If browser isn't open, we can't check URL, but if instruction is strong "Search",
            # we might want to handle it. For now, if browser is closed, assume we are in Desktop mode
            # and ignore, OR (better) let the Core switch modes.
            # But to fix the crash:
            return 0.1 

        # Check if we are already on a search result page
        page_url = self.agent.browser.page.url
        if "google.com/search" in page_url or "duckduckgo.com/?q=" in page_url:
            # If we are already on a search page, we probably don't need to search again immediately
            # unless the query is different. But checking query diff is hard without parsing params.
            # safe heuristic: if on SERP, let the VLM decide next step (click).
            return 0.0
            
        keywords = ["search", "find", "google", "look up"]
        if any(keyword in lower_instr for keyword in keywords):
            return 0.9
        return 0.1

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        if not query:
            # Try to extract query from instruction if not explicitly provided
            instruction = params.get("instruction", "")
            match = re.search(r"(?:search|find|look up)\s+(?:for\s+)?['\"]?([^'\"]+)['\"]?", instruction, re.IGNORECASE)
            if match:
                query = match.group(1)
            else:
                return {"status": "fail", "reason": "No search query provided."}

        query = self.rewrite_query(query)
        if not query:
            return {"status": "fail", "reason": "Search query was empty after rewriting."}

        self.logger.info(f"Executing SearchSkill with query: '{query}'")
        page = self.agent.browser.page
        
        # Common search input selectors
        search_selectors = [
            "textarea[name='q']", # Google now uses textarea
            "input[name='q']", # DuckDuckGo, Bing standard
            "input[type='search']",
            "input[aria-label='Search']",
            "input[title='Search']",
            "[aria-label='Search']"
        ]
        
        target_selector = None
        # Wait for the page to be ready specifically for search
        try:
            page.wait_for_selector("body", timeout=5000)
        except:
            pass

        for selector in search_selectors:
            if page.is_visible(selector):
                target_selector = selector
                break
        
        if target_selector:
            self.logger.info(f"Found search bar with selector: {target_selector}")
            try:
                # Use human_type instead of fill to look natural
                # We need to rely on the browser agent's method
                self.agent.browser.human_type(query, selector=target_selector)
                
                # Small human pause before hitting Enter
                import time
                import random
                time.sleep(random.uniform(0.5, 1.5))
                
                page.press(target_selector, "Enter")
                # Wait for navigation or results
                page.wait_for_load_state("networkidle", timeout=5000)
                return {"status": "success", "message": f"Searched for '{query}'"}
            except Exception as e:
                return {"status": "fail", "reason": str(e)}
        else:
            # Fallback strategy: If we are not on a search page, or blocked (e.g. CAPTCHA),
            # Navigate to DuckDuckGo and try there.
            current_url = page.url
            if "duckduckgo.com" not in current_url:
                self.logger.info("Search bar not found. Navigating to fallback engine (DuckDuckGo)...")
                try:
                    page.goto("https://duckduckgo.com")
                    page.wait_for_load_state("networkidle")
                    # Recursive call to execute search on new page
                    return self.execute(params)
                except Exception as e:
                    return {"status": "fail", "reason": f"Fallback failed: {str(e)}"}
            
            return {"status": "fail", "reason": "Could not find a standard search bar even after fallback."}
