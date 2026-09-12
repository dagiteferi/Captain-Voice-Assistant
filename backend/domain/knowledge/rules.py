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

    @staticmethod
    def evaluate(submission: KnowledgeSubmission) -> RuleOutcome:
        l = len(submission.raw_content.strip())
        if l < 5 or l > 500000:
            return RuleOutcome(rule_name=MinMaxLengthRule.NAME, verdict=RuleVerdict.FAIL, reason="length_out_of_bounds")
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

    # thresholds: >=0.95 -> fail, 0.40-0.95 -> needs_review, <0.40 -> pass
    @staticmethod
    def evaluate(submission: KnowledgeSubmission, similarity_fn: Callable[[KnowledgeSubmission], float] | None = None) -> RuleOutcome:
        sim = 0.0
        if similarity_fn is not None:
            sim = float(similarity_fn(submission))

        if sim >= 0.95:
            return RuleOutcome(rule_name=DuplicateSimilarityRule.NAME, verdict=RuleVerdict.FAIL, reason="near_duplicate")
        if sim >= 0.4:
            return RuleOutcome(rule_name=DuplicateSimilarityRule.NAME, verdict=RuleVerdict.NEEDS_REVIEW, reason="similarity_threshold",)
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

    api_results = []
    for r in results:
        entry = {"rule": r.rule_name, "outcome": r.verdict.value}
        if r.rule_name == DuplicateSimilarityRule.NAME and similarity_fn is not None:
            entry["similarity"] = float(similarity_fn(submission))
        api_results.append(entry)

    if submitter_role is SubmitterRole.CAPTAIN:
        role_outcome = RuleVerdict.PASS.value
    else:
        role_outcome = RuleVerdict.NEEDS_REVIEW.value
    api_results.append({"rule": TrustedRoleAutoApproveRule.NAME, "outcome": role_outcome})

    return status, api_results
