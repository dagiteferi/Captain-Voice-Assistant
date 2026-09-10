from typing import Protocol

from domain.knowledge.entities import KnowledgeSubmission
from domain.knowledge.value_objects import (
    RuleContext,
    RuleOutcome,
    RuleVerdict,
    SubmitterRole,
)


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
