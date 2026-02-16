from .base import Skill
from typing import Dict, Any, Optional
import json

class ExtractionSkill(Skill):
    """
    Skill for extracting the main content of a page and converting it to Markdown-like text.
    Useful for summarization and reading capability without visual analysis.
    """

    def can_handle(self, instruction: str) -> float:
        """
        High confidence if instruction contains 'extract', 'read', 'summarize', 'scrape', or 'get content'.
        Avoid running on SERPs (Search Engine Result Pages) unless 'results' is explicitly requested,
        to allow the agent to navigate to a real article first.
        """
        # Context check: Are we on a search engine?
        if not self.agent.browser.page:
            return 0.1
            
        page_url = self.agent.browser.page.url
        is_serp = "google.com" in page_url or "duckduckgo.com" in page_url or "bing.com" in page_url
        
        lower_instr = instruction.lower()
        if is_serp and "results" not in lower_instr:
             # If we are on a search page and user didn't ask to summarize 'results', 
             # likely they want to summarize the *destination* page.
             return 0.1
             
        keywords = ["extract", "read", "summarize", "scrape", "what does the page say", "get content"]
        if any(keyword in lower_instr for keyword in keywords):
            return 0.9
        return 0.1

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Executing ExtractionSkill...")
        page = self.agent.browser.page
        
        # Inject a script to extract main text. 
        # We'll use a simple heuristic: standard block elements, ignoring scripts/styles/navs if possible.
        # Fallback to body.innerText if heuristic fails.
        
        extraction_script = """
        () => {
            function isVisible(elem) {
                return !!( elem.offsetWidth || elem.offsetHeight || elem.getClientRects().length );
            }
            
            function getReadableText(root) {
                // Clone to not mess up the page
                let clone = root.cloneNode(true);
                
                // Remove clutter
                const clutter = ['script', 'style', 'noscript', 'iframe', 'svg', 'header', 'footer', 'nav', 'aside'];
                clutter.forEach(tag => {
                    const elements = clone.querySelectorAll(tag);
                    elements.forEach(el => el.remove());
                });
                
                // Extract headings and paragraphs
                let markdown = "";
                const blocks = clone.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, blockquote, pre');
                
                blocks.forEach(el => {
                    if (!isVisible(el)) return;
                    
                    let text = el.innerText.trim();
                    if (!text) return;
                    
                    const tag = el.tagName.toLowerCase();
                    if (tag.startsWith('h')) {
                        const level = parseInt(tag.charAt(1));
                        markdown += '#'.repeat(level) + ' ' + text + '\\n\\n';
                    } else if (tag === 'li') {
                        markdown += '- ' + text + '\\n';
                    } else if (tag === 'pre') {
                        markdown += '```\\n' + text + '\\n```\\n\\n';
                    } else if (tag === 'blockquote') {
                        markdown += '> ' + text + '\\n\\n';
                    } else {
                        markdown += text + '\\n\\n';
                    }
                });
                
                return markdown;
            }
            
            let content = getReadableText(document.body);
            if (!content || content.length < 50) {
                 // Fallback
                 return "FALLBACK_TEXT_ONLY:\\n" + document.body.innerText;
            }
            return content;
        }
        """
        
        try:
            markdown_content = page.evaluate(extraction_script)
            # Truncate if too huge to prevent token explosion in downstream tasks, 
            # though Gemini 1.5/2.5 Flash has huge context.
            preview = markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
            self.logger.info(f"Extracted {len(markdown_content)} chars. Preview: {preview}")
            
            return {
                "status": "success", 
                "content": markdown_content,
                "length": len(markdown_content)
            }
        except Exception as e:
            return {"status": "fail", "reason": str(e)}
