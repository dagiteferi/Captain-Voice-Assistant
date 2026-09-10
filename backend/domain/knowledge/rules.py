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
        if l < 20 or l > 4000:
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

    # Build API-friendly dicts
    api_results = []
    for r in results:
        entry = {"rule": r.rule_name, "outcome": r.verdict.value}
        if r.rule_name == DuplicateSimilarityRule.NAME and similarity_fn is not None:
            entry["similarity"] = float(similarity_fn(submission))
        api_results.append(entry)

    return status, api_results
from __future__ import annotations

from typing import Callable, List

from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.value_objects import (



class KnowledgeRule(Protocol):
    name: str

    def check(
        self, submission: KnowledgeSubmission, context: RuleContext
    ) -> RuleOutcome: ...


class MinMaxLengthRule:
    name = "min_max_length"

    def __init__(self, min_chars: int = 20, max_chars: int = 4000) -> None:
        self.min_chars = min_chars
        self.max_chars = max_chars

    def check(
        self, submission: KnowledgeSubmission, context: RuleContext
    ) -> RuleOutcome:
        length = len(submission.raw_content.strip())
        if length < self.min_chars:
            return RuleOutcome(self.name, RuleVerdict.FAIL, "content is too short")
        if length > self.max_chars:
            return RuleOutcome(self.name, RuleVerdict.FAIL, "content is too long")
        return RuleOutcome(self.name, RuleVerdict.PASS)


class BlocklistKeywordRule:
    name = "blocklist_keyword"

    def __init__(self, blocklist: frozenset[str]) -> None:
        self.blocklist = {word.lower() for word in blocklist}

    def check(
        self, submission: KnowledgeSubmission, context: RuleContext
    ) -> RuleOutcome:
        tokens = {token.strip(".,!?;:()[]{}\"'").lower() for token in submission.raw_content.split()}
        hits = sorted(tokens & self.blocklist)
        if hits:
            return RuleOutcome(
                self.name, RuleVerdict.FAIL, f"blocked terms: {', '.join(hits)}"
            )
        return RuleOutcome(self.name, RuleVerdict.PASS)


class DuplicateSimilarityRule:
    name = "duplicate_similarity"

    def __init__(self, threshold: float = 0.92) -> None:
        self.threshold = threshold

    def check(
        self, submission: KnowledgeSubmission, context: RuleContext
    ) -> RuleOutcome:
        if context.max_similarity >= self.threshold:
            return RuleOutcome(self.name, RuleVerdict.FAIL, "near-duplicate of existing knowledge")
        return RuleOutcome(self.name, RuleVerdict.PASS)


class TrustedRoleAutoApproveRule:
    name = "trusted_role"

    def __init__(self, auto_approve_roles: frozenset[SubmitterRole] | None = None) -> None:
        self.auto_approve_roles = auto_approve_roles or frozenset({SubmitterRole.CAPTAIN})

    def check(
        self, submission: KnowledgeSubmission, context: RuleContext
    ) -> RuleOutcome:
        if submission.submitter_role is SubmitterRole.GUEST:
            return RuleOutcome(self.name, RuleVerdict.NEEDS_REVIEW, "guest submissions always need review")
        if submission.submitter_role in self.auto_approve_roles:
            return RuleOutcome(self.name, RuleVerdict.PASS, "trusted role")
        return RuleOutcome(self.name, RuleVerdict.NEEDS_REVIEW, "role requires human review")


def run_rule_chain(
    submission: KnowledgeSubmission,
    rules: list[KnowledgeRule],
    context: RuleContext,
) -> list[RuleOutcome]:
    outcomes: list[RuleOutcome] = []
    for rule in rules:
        outcome = rule.check(submission, context)
        outcomes.append(outcome)
        if outcome.verdict is RuleVerdict.FAIL:
            break
    return outcomes


def decide_from_outcomes(
    submission: KnowledgeSubmission, outcomes: list[RuleOutcome]
) -> RuleVerdict:
    if any(outcome.verdict is RuleVerdict.FAIL for outcome in outcomes):
        return RuleVerdict.FAIL
    if submission.submitter_role is SubmitterRole.GUEST:
        return RuleVerdict.NEEDS_REVIEW
    if submission.submitter_role is SubmitterRole.CAPTAIN:
        return RuleVerdict.PASS
    return RuleVerdict.NEEDS_REVIEW
