from ultragravity.context_shaper import ContextShaper
from ultragravity.prompt_library import PromptLibrary


def test_prompt_library_action_prompt_compact_and_schema_guided():
    library = PromptLibrary(debug_reasoning=False)
    prompt = library.build_action_prompt(
        goal="Find the latest model release notes",
        mode="BROWSER",
        delta_context="state_changed=True; last_action=click",
    )

    assert "Output strict JSON only" in prompt
    assert "Allowed actions" in prompt
    assert "reasoning to empty string" in prompt
    assert "\n" not in prompt


def test_prompt_library_chunk_and_merge_prompts_compact():
    library = PromptLibrary(debug_reasoning=True)
    chunk_prompt = library.build_chunk_summary_prompt("Summarize", "A B C", 0, 3)
    merge_prompt = library.build_merge_summary_prompt("Summarize", ["one", "two"])

    assert "Chunk: 1/3" in chunk_prompt
    assert "Merge the chunk summaries" in merge_prompt
    assert "\n" not in chunk_prompt
    assert "\n" not in merge_prompt


def test_context_shaper_chunking_and_ranking():
    shaper = ContextShaper()
    content = (
        "alpha beta gamma " * 200
        + "\n\n"
        + "unrelated text " * 150
        + "\n\n"
        + "alpha model release token savings " * 120
    )

    chunks = shaper.chunk_text(content, chunk_chars=700, overlap_chars=70)
    ranked = shaper.rank_chunks(chunks, query="model release token", top_k=3)

    assert len(chunks) >= 3
    assert 1 <= len(ranked) <= 3
    assert ranked[0].score >= ranked[-1].score


def test_context_shaper_delta_context_includes_state_signals():
    shaper = ContextShaper()
    delta = shaper.build_delta_context(
        state_changed=True,
        changed_by_url=False,
        changed_by_image=True,
        last_action="scroll",
        current_url="https://example.com",
    )

    assert "state_changed=True" in delta
    assert "changed_by_url=False" in delta
    assert "changed_by_image=True" in delta
    assert "last_action=scroll" in delta
    assert "url=https://example.com" in delta
