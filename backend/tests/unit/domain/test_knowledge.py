from uuid import uuid4

import pytest

from domain.exceptions import InvalidSubmissionTransition
from domain.knowledge.entities import Chunk, KnowledgeSubmission
from domain.knowledge.rules import (
    BlocklistKeywordRule,
    DuplicateSimilarityRule,
    MinMaxLengthRule,
    evaluate_submission,
)
from domain.knowledge.value_objects import RuleVerdict, SubmissionStatus, SubmitterRole


def _submission(
    content: str = "The vessel maintains a standing heading of two seven zero true.",
    role: SubmitterRole = SubmitterRole.CREW,
) -> KnowledgeSubmission:
    return KnowledgeSubmission(
        submitted_by="user-1",
        submitter_role=role,
        raw_content=content,
    )


def test_cannot_index_until_approved() -> None:
    submission = _submission()
    with pytest.raises(InvalidSubmissionTransition):
        submission.mark_indexed()


def test_approved_submission_can_be_indexed() -> None:
    submission = _submission()
    submission.approve(reviewed_by="captain-1")
    submission.mark_indexed()
    assert submission.status is SubmissionStatus.INDEXED
    assert submission.reviewed_by == "captain-1"


def test_cannot_approve_after_reject() -> None:
    submission = _submission()
    submission.reject(reviewed_by="captain-1")
    with pytest.raises(InvalidSubmissionTransition):
        submission.approve()


def test_empty_chunk_rejected() -> None:
    with pytest.raises(ValueError):
        Chunk(document_id=uuid4(), content="  ")


def test_length_rule_fails_short_content() -> None:
    outcome = MinMaxLengthRule.evaluate(_submission("too short"))
    assert outcome.verdict is RuleVerdict.FAIL


def test_blocklist_rule_fails_on_hit() -> None:
    outcome = BlocklistKeywordRule.evaluate(
        _submission("This is classified material for the log.")
    )
    assert outcome.verdict is RuleVerdict.FAIL


def test_duplicate_rule_uses_similarity_fn() -> None:
    submission = _submission()
    assert (
        DuplicateSimilarityRule.evaluate(submission, similarity_fn=lambda _: 0.5).verdict
        is RuleVerdict.NEEDS_REVIEW
    )
    assert (
        DuplicateSimilarityRule.evaluate(submission, similarity_fn=lambda _: 0.99).verdict
        is RuleVerdict.FAIL
    )


def test_guest_never_auto_approves_even_when_checks_pass() -> None:
    status, _ = evaluate_submission(
        _submission(role=SubmitterRole.GUEST),
        SubmitterRole.GUEST,
        similarity_fn=lambda _: 0.0,
    )
    assert status is SubmissionStatus.PENDING


def test_captain_auto_approves_when_checks_pass() -> None:
    status, _ = evaluate_submission(
        _submission(role=SubmitterRole.CAPTAIN),
        SubmitterRole.CAPTAIN,
        similarity_fn=lambda _: 0.0,
    )
    assert status is SubmissionStatus.APPROVED


def test_crew_passing_checks_goes_to_review() -> None:
    status, _ = evaluate_submission(
        _submission(role=SubmitterRole.CREW),
        SubmitterRole.CREW,
        similarity_fn=lambda _: 0.0,
    )
    assert status is SubmissionStatus.PENDING


def test_hard_fail_rejects_regardless_of_role() -> None:
    status, results = evaluate_submission(
        _submission("no"),
        SubmitterRole.CAPTAIN,
        similarity_fn=lambda _: 0.0,
    )
    assert status is SubmissionStatus.REJECTED
    assert any(item["rule"] == "MinMaxLengthRule" and item["outcome"] == "fail" for item in results)
