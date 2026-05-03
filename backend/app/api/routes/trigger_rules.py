"""Trigger Rules API Routes."""

from fastapi import APIRouter

from app.services.trigger_rules_service import (
    TriggerRuleBuildRequest,
    TriggerRuleBuildResponse,
    expire_all_trigger_rules,
    expire_trigger_rule,
    get_active_trigger_rules,
    get_latest_trigger_rules,
    list_trigger_rule_builds,
    run_trigger_rule_build,
)

router = APIRouter()


@router.post("/trigger-rules/build", response_model=TriggerRuleBuildResponse)
def post_trigger_rules_build(request: TriggerRuleBuildRequest):
    """Build trigger rules from candidates or watchlist.

    Creates deterministic monitoring rules with TTL (time-to-live).
    NO buy/sell recommendations.
    """
    return run_trigger_rule_build(request)


@router.get("/trigger-rules/latest", response_model=TriggerRuleBuildResponse | dict)
def get_latest_trigger_rules_endpoint():
    """Get the most recent trigger rule build."""
    latest = get_latest_trigger_rules()
    if not latest:
        return {"message": "No trigger rules build available", "status": "not_found"}
    return latest


@router.get("/trigger-rules/active")
def get_active_trigger_rules_endpoint():
    """Get currently active (non-expired) trigger rules."""
    rules = get_active_trigger_rules()
    return {
        "rules": rules,
        "count": len(rules),
        "status": "active",
    }


@router.post("/trigger-rules/expire")
def post_expire_trigger_rules(all_rules: bool = False, rule_id: str | None = None):
    """Expire trigger rules.

    - If all_rules=True: expire all active rules
    - If rule_id provided: expire specific rule
    - Otherwise: no action
    """
    if all_rules:
        count = expire_all_trigger_rules()
        return {"expired_count": count, "status": "success", "message": f"Expired {count} rules"}
    elif rule_id:
        success = expire_trigger_rule(rule_id)
        return {
            "expired_count": 1 if success else 0,
            "status": "success" if success else "not_found",
            "message": f"Rule {rule_id} expired" if success else f"Rule {rule_id} not found",
        }
    else:
        return {"expired_count": 0, "status": "no_action", "message": "No rules specified to expire"}
