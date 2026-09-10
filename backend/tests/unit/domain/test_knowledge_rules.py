import pytest
from uuid import uuid4

from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.rules import (
    MinMaxLengthRule,
    BlocklistKeywordRule,
    DuplicateSimilarityRule,
    TrustedRoleAutoApproveRule,
    evaluate_submission,
)
from domain.knowledge.value_objects import SubmitterRole, SubmissionStatus


def make_submission(text: str):
    return KnowledgeSubmission(submitted_by="u1", submitter_role=SubmitterRole.CREW, raw_content=text)


def test_min_max_length_rule_pass():
    s = make_submission("a" * 25)
    res = MinMaxLengthRule.evaluate(s)
    assert res.verdict.name == "PASS"


def test_min_max_length_rule_fail_short():
    s = make_submission("short")
    res = MinMaxLengthRule.evaluate(s)
    assert res.verdict.name == "FAIL"


def test_blocklist_rule_detects_blocked():
    s = make_submission("this contains password in text")
    res = BlocklistKeywordRule.evaluate(s)
    assert res.verdict.name == "FAIL"


def test_duplicate_similarity_pass_and_needs_review_and_fail():
    s = make_submission("clean content with some words to compare")

    # similarity low -> pass
    r = DuplicateSimilarityRule.evaluate(s, similarity_fn=lambda _: 0.1)
    assert r.verdict.name == "PASS"

    # similarity moderate -> needs_review
    r = DuplicateSimilarityRule.evaluate(s, similarity_fn=lambda _: 0.5)
    assert r.verdict.name == "NEEDS_REVIEW"

    # similarity very high -> fail
    r = DuplicateSimilarityRule.evaluate(s, similarity_fn=lambda _: 0.99)
    assert r.verdict.name == "FAIL"


def test_trusted_role_autoapprove_and_outcomes():
    s = make_submission("a" * 50)

    # all pass -> captain auto-approve
    status, results = evaluate_submission(s, SubmitterRole.CAPTAIN, similarity_fn=lambda _: 0.0)
    assert status == SubmissionStatus.APPROVED

    # all pass -> crew pending
    status, results = evaluate_submission(s, SubmitterRole.CREW, similarity_fn=lambda _: 0.0)
    assert status == SubmissionStatus.PENDING

    # guest always pending
    status, results = evaluate_submission(s, SubmitterRole.GUEST, similarity_fn=lambda _: 0.0)
    assert status == SubmissionStatus.PENDING

    # hard fail from blocklist overrides captain
    s2 = make_submission("this has secret info")
    status, results = evaluate_submission(s2, SubmitterRole.CAPTAIN, similarity_fn=lambda _: 0.0)
    assert status == SubmissionStatus.REJECTED
