from pydantic import BaseModel

from app.schemas import AccountRiskProfile


class AccountFeasibilityResult(BaseModel):
    symbol: str
    feasibility: str
    max_position_size_dollars: float
    max_risk_dollars: float
    suggested_expression: str
    notes: list[str]


def evaluate_account_feasibility(symbol: str, current_price: float, profile: AccountRiskProfile) -> AccountFeasibilityResult:
    max_position_size = profile.account_equity * (profile.max_position_size_percent / 100)
    max_risk = profile.account_equity * (profile.max_risk_per_trade_percent / 100)

    if current_price <= max_position_size:
        feasibility = "feasible_direct_or_fractional"
        expression = "Direct share or fractional share sizing allowed after risk validation."
    elif current_price <= profile.buying_power:
        feasibility = "needs_fractional_or_smaller_size"
        expression = "Use fractional shares or wait for a cheaper expression."
    else:
        feasibility = "watch_only_or_defined_risk_option"
        expression = "Do not force direct shares. Route to defined-risk option spread or watch-only alert."

    return AccountFeasibilityResult(
        symbol=symbol,
        feasibility=feasibility,
        max_position_size_dollars=round(max_position_size, 2),
        max_risk_dollars=round(max_risk, 2),
        suggested_expression=expression,
        notes=[
            "Account feasibility is applied before final recommendation ranking.",
            "Small accounts should route expensive assets into smaller expressions instead of deleting all opportunities.",
        ],
    )
