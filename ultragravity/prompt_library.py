from __future__ import annotations

import json


class PromptLibrary:
    def __init__(self, debug_reasoning: bool = False):
        self.debug_reasoning = debug_reasoning

    @staticmethod
    def _compact(text: str) -> str:
        return " ".join(text.strip().split())

    def build_action_prompt(
        self,
        goal: str,
        mode: str,
        delta_context: str,
    ) -> str:
        reasoning_rule = (
            '"reasoning":"<=30 words"' if self.debug_reasoning else '"reasoning":""'
        )
        schema = {
            "action": "click|type|scroll|wait|done|fail",
            "target_element": {"description": "string", "coordinates": [0, 0]},
            "value": "string",
            "reasoning": "debug-only",
        }

        prompt = f"""
        Role: UI automation planner.
        Goal: {goal}
        Mode: {mode}
        Delta: {delta_context}

        Output strict JSON only. No markdown.
        Required keys: action,target_element,value,reasoning.
        Allowed actions: click,type,scroll,wait,done,fail.
        If action is not click/type, set coordinates as [].
        If debug reasoning is disabled, set reasoning to empty string.

        JSON schema example:
        {json.dumps(schema, separators=(',', ':'))}

        Reasoning rule: {reasoning_rule}
        """
        return self._compact(prompt)

    def build_chunk_summary_prompt(self, goal: str, chunk: str, chunk_index: int, total_chunks: int) -> str:
        prompt = f"""
        Role: concise summarizer.
        Goal: {goal}
        Chunk: {chunk_index + 1}/{total_chunks}

        Summarize only facts relevant to the goal.
        Keep 5-8 bullets max. Avoid repetition.
        If evidence is weak, say so explicitly.

        Content:
        {chunk}
        """
        return self._compact(prompt)

    def build_merge_summary_prompt(self, goal: str, chunk_summaries: list[str]) -> str:
        joined = "\n\n".join(chunk_summaries)
        prompt = f"""
        Role: synthesis engine.
        Goal: {goal}

        Merge the chunk summaries into one coherent final answer.
        Keep it concise, structured, and non-redundant.
        Mention uncertainty where evidence conflicts.
        Format in Markdown.

        Chunk summaries:
        {joined}
        """
        return self._compact(prompt)
