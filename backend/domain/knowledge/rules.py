from __future__ import annotations

from typing import Callable, List

from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.value_objects import (
    RuleOutcome,
    RuleVerdict,
    SubmitterRole,
    SubmissionStatus,
)


class MinMaxLengthRule:
    NAME = "MinMaxLengthRule"

    # Below this there is no fact worth indexing. The upper bound is only a
    # guard against a runaway upload: long documents are split into chunks at
    # index time, so length alone is no reason to reject a real document.
    MIN_CHARS = 20
    MAX_CHARS = 200_000

    @staticmethod
    def evaluate(submission: KnowledgeSubmission) -> RuleOutcome:
        length = len(submission.raw_content.strip())
        if length < MinMaxLengthRule.MIN_CHARS:
            return RuleOutcome(rule_name=MinMaxLengthRule.NAME, verdict=RuleVerdict.FAIL, reason="too_short")
        if length > MinMaxLengthRule.MAX_CHARS:
            return RuleOutcome(rule_name=MinMaxLengthRule.NAME, verdict=RuleVerdict.FAIL, reason="too_long")
        return RuleOutcome(rule_name=MinMaxLengthRule.NAME, verdict=RuleVerdict.PASS)


class BlocklistKeywordRule:
    NAME = "BlocklistKeywordRule"

    BLOCKED = {"password", "secret", "ssn", "classified"}

    @staticmethod
    def evaluate(submission: KnowledgeSubmission) -> RuleOutcome:
        text = submission.raw_content.lower()
        for kw in BlocklistKeywordRule.BLOCKED:
            if kw in text:
                return RuleOutcome(rule_name=BlocklistKeywordRule.NAME, verdict=RuleVerdict.FAIL, reason=f"blocked_keyword:{kw}")
        return RuleOutcome(rule_name=BlocklistKeywordRule.NAME, verdict=RuleVerdict.PASS)


class DuplicateSimilarityRule:
    NAME = "DuplicateSimilarityRule"

    # Resembling existing content never rejects a submission: a CV restated in
    # a new document is still knowledge, and re-indexing replaces a submission's
    # own chunks rather than duplicating them. High similarity is reported so a
    # reviewer can judge it.
    NEAR_DUPLICATE = 0.95
    SIMILAR = 0.4

    @staticmethod
    def evaluate(submission: KnowledgeSubmission, similarity_fn: Callable[[KnowledgeSubmission], float] | None = None) -> RuleOutcome:
        sim = 0.0
        if similarity_fn is not None:
            sim = float(similarity_fn(submission))

        if sim >= DuplicateSimilarityRule.NEAR_DUPLICATE:
            return RuleOutcome(rule_name=DuplicateSimilarityRule.NAME, verdict=RuleVerdict.NEEDS_REVIEW, reason="near_duplicate")
        if sim >= DuplicateSimilarityRule.SIMILAR:
            return RuleOutcome(rule_name=DuplicateSimilarityRule.NAME, verdict=RuleVerdict.NEEDS_REVIEW, reason="similarity_threshold")
        return RuleOutcome(rule_name=DuplicateSimilarityRule.NAME, verdict=RuleVerdict.PASS)


class TrustedRoleAutoApproveRule:
    NAME = "TrustedRoleAutoApproveRule"

    @staticmethod
    def decide(submitter_role: SubmitterRole, rule_outcomes: List[RuleOutcome]) -> SubmissionStatus:
        # If any hard-fail exists, reject
        for r in rule_outcomes:
            if r.verdict == RuleVerdict.FAIL:
                return SubmissionStatus.REJECTED

        # Captain auto-approve when no fails
        if submitter_role == SubmitterRole.CAPTAIN:
            return SubmissionStatus.APPROVED

        # Crew: needs review even if all pass
        if submitter_role == SubmitterRole.CREW:
            return SubmissionStatus.PENDING

        # Guest: always pending
        return SubmissionStatus.PENDING


def evaluate_submission(submission: KnowledgeSubmission, submitter_role: SubmitterRole, similarity_fn: Callable[[KnowledgeSubmission], float] | None = None) -> tuple[SubmissionStatus, list[dict]]:
    """Evaluate a submission through the rule chain and return final status and rule results.

    Returns a tuple of (SubmissionStatus, rule_results_list) where each rule result is a dict
    matching the API: {"rule": name, "outcome": "pass|fail|needs_review", "similarity": float?}
    """
    results = []

    r1 = MinMaxLengthRule.evaluate(submission)
    results.append(r1)

    r2 = BlocklistKeywordRule.evaluate(submission)
    results.append(r2)

    r3 = DuplicateSimilarityRule.evaluate(submission, similarity_fn)
    results.append(r3)

    status = TrustedRoleAutoApproveRule.decide(submitter_role, results)

    # Build API-friendly dicts
    api_results = []
    for r in results:
        entry = {"rule": r.rule_name, "outcome": r.verdict.value}
        if r.rule_name == DuplicateSimilarityRule.NAME and similarity_fn is not None:
            entry["similarity"] = float(similarity_fn(submission))
        api_results.append(entry)

    return status, api_results
