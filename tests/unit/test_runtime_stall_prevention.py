from skills.search import SearchSkill


def test_search_query_rewrite_removes_output_format_tail():
    query = "the top three recent AI assistant releases and provide a concise bullet summary with source website names"
    rewritten = SearchSkill.rewrite_query(query)

    assert rewritten == "top three recent AI assistant releases"


def test_search_query_rewrite_keeps_short_queries():
    query = "find weather tokyo"
    rewritten = SearchSkill.rewrite_query(query)

    assert rewritten == "weather tokyo"
