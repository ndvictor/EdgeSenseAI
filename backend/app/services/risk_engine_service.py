from pydantic import BaseModel

from app.schemas import AccountRiskProfile


class RiskCheckResult(BaseModel):
    passed: bool
    reward_risk_ratio: float
    max_dollar_risk: float
    stop_distance_percent: float
    risk_status: str
    blockers: list[str]


def evaluate_trade_risk(
    entry_price: float,
    stop_loss: float,
    target_price: float,
    profile: AccountRiskProfile,
) -> RiskCheckResult:
    risk_per_share = max(entry_price - stop_loss, 0.01)
    reward_per_share = max(target_price - entry_price, 0.01)
    reward_risk = reward_per_share / risk_per_share
    stop_distance_percent = (risk_per_share / entry_price) * 100
    max_dollar_risk = profile.account_equity * (profile.max_risk_per_trade_percent / 100)

    blockers: list[str] = []
    if reward_risk < profile.min_reward_risk_ratio:
        blockers.append("Reward/risk below account minimum.")
    if stop_distance_percent > 5:
        blockers.append("Stop distance may be too wide for a small account.")

    passed = len(blockers) == 0
    return RiskCheckResult(
        passed=passed,
        reward_risk_ratio=round(reward_risk, 2),
        max_dollar_risk=round(max_dollar_risk, 2),
        stop_distance_percent=round(stop_distance_percent, 2),
        risk_status="passed" if passed else "blocked_or_review",
        blockers=blockers,
    )
