from application.knowledge.retrieval import expand_search_queries, lexical_overlap_score


def test_expand_dagi_birth_query_includes_full_name():
    queries = expand_search_queries("when dagi were born")
    assert queries[0] == "when dagi were born"
    assert any("Dagmawi Teferi" in item for item in queries)
    assert any("born" in item.lower() for item in queries[1:])


def test_lexical_score_prefers_birth_fact_over_unrelated_cv_text():
    query = "when dagi were born"
    birth = "Subject: Dagmawi Teferi (also known as Dagi).\nI was born in 1999 at Adama."
    other = "Dagmawi Teferi builds FastAPI microservices and RAG pipelines."
    assert lexical_overlap_score(query, birth) > lexical_overlap_score(query, other)
