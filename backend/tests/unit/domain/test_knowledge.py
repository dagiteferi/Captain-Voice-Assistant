from uuid import uuid4

import pytest

from domain.exceptions import InvalidSubmissionTransition
from domain.knowledge.entities import Chunk, KnowledgeSubmission
from domain.knowledge.rules import (
    BlocklistKeywordRule,
    DuplicateSimilarityRule,
    MinMaxLengthRule,
    TrustedRoleAutoApproveRule,
    decide_from_outcomes,
    run_rule_chain,
)
from domain.knowledge.value_objects import RuleContext, RuleVerdict, SubmitterRole


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
    assert submission.status.value == "indexed"
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
    outcome = MinMaxLengthRule().check(_submission("too short"), RuleContext())
    assert outcome.verdict is RuleVerdict.FAIL


def test_blocklist_rule_fails_on_hit() -> None:
    rule = BlocklistKeywordRule(frozenset({"classified"}))
    outcome = rule.check(_submission("This is classified material for the log."), RuleContext())
    assert outcome.verdict is RuleVerdict.FAIL


def test_duplicate_rule_uses_context_score() -> None:
    rule = DuplicateSimilarityRule(threshold=0.92)
    assert rule.check(_submission(), RuleContext(max_similarity=0.5)).verdict is RuleVerdict.PASS
    assert rule.check(_submission(), RuleContext(max_similarity=0.95)).verdict is RuleVerdict.FAIL


def test_guest_never_auto_approves_even_when_checks_pass() -> None:
    submission = _submission(role=SubmitterRole.GUEST)
    outcomes = run_rule_chain(
        submission,
        [
            MinMaxLengthRule(),
            BlocklistKeywordRule(frozenset({"secret-xyz"})),
            DuplicateSimilarityRule(),
            TrustedRoleAutoApproveRule(),
        ],
        RuleContext(),
    )
    assert decide_from_outcomes(submission, outcomes) is RuleVerdict.NEEDS_REVIEW


def test_captain_auto_approves_when_checks_pass() -> None:
    submission = _submission(role=SubmitterRole.CAPTAIN)
    outcomes = run_rule_chain(
        submission,
        [
            MinMaxLengthRule(),
            BlocklistKeywordRule(frozenset()),
            DuplicateSimilarityRule(),
            TrustedRoleAutoApproveRule(),
        ],
        RuleContext(),
    )
    assert decide_from_outcomes(submission, outcomes) is RuleVerdict.PASS


def test_crew_passing_checks_goes_to_review() -> None:
    submission = _submission(role=SubmitterRole.CREW)
    outcomes = run_rule_chain(
        submission,
        [MinMaxLengthRule(), TrustedRoleAutoApproveRule()],
        RuleContext(),
    )
    assert decide_from_outcomes(submission, outcomes) is RuleVerdict.NEEDS_REVIEW


def test_hard_fail_stops_the_chain() -> None:
    outcomes = run_rule_chain(
        _submission("no"),
        [MinMaxLengthRule(), TrustedRoleAutoApproveRule()],
        RuleContext(),
    )
    assert len(outcomes) == 1
    assert outcomes[0].verdict is RuleVerdict.FAIL
