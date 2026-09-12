from application.knowledge.retrieval import build_search_query, lexical_overlap_score


def test_nickname_is_rewritten_in_place_so_one_search_covers_it():
    # One string means one embedding request; the nickname must not need a
    # second search of its own.
    assert build_search_query("when dagi were born") == "when Dagmawi Teferi were born"


def test_query_with_the_full_name_is_searched_as_written():
    assert build_search_query("when was dagmawi born") == "when was dagmawi born"


def test_lexical_score_prefers_birth_fact_over_unrelated_cv_text():
    query = "when dagi were born"
    birth = "Subject: Dagmawi Teferi (also known as Dagi).\nI was born in 1999 at Adama."
    other = "Dagmawi Teferi builds FastAPI microservices and RAG pipelines."
    assert lexical_overlap_score(query, birth) > lexical_overlap_score(query, other)
