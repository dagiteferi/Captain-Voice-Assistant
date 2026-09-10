"""Policies for orchestrator decisions."""


def default_policy(context):
    return {"route": "default", "reason": "no special handling"}
