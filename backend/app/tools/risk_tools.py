from typing import Any

from app.schemas import AccountRiskProfile
from app.services.account_feasibility_service import evaluate_account_feasibility
from app.services.risk_engine_service import evaluate_trade_risk


def build_paper_account_profile(
    account_size: float | None = None,
    max_risk_per_trade: float | None = None,
) -> AccountRiskProfile:
    equity = account_size if account_size and account_size > 0 else AccountRiskProfile().account_equity
    risk_percent = max_risk_per_trade if max_risk_per_trade and max_risk_per_trade > 0 else AccountRiskProfile().max_risk_per_trade_percent
    return AccountRiskProfile(
        account_mode="paper",
        account_equity=equity,
        buying_power=equity,
        cash=equity,
        max_risk_per_trade_percent=risk_percent,
        paper_only=True,
        source="edge_radar_request",
    )


def review_signal_risk(signal: dict[str, Any], profile: AccountRiskProfile) -> dict[str, Any]:
    entry_price = float(signal.get("entry_price") or signal.get("current_price") or 0)
    if entry_price <= 0:
        return {
            "symbol": signal.get("symbol", "UNKNOWN"),
            "passed": False,
            "risk_status": "blocked_or_review",
            "blockers": ["No usable entry price available for risk review."],
            "paper_only": True,
            "human_approval_required": True,
            "data_source": "placeholder",
        }

    stop_loss = float(signal.get("stop_loss") or entry_price * 0.97)
    target_price = float(signal.get("target_price") or entry_price * 1.06)
    risk_result = evaluate_trade_risk(entry_price, stop_loss, target_price, profile)
    feasibility = evaluate_account_feasibility(str(signal.get("symbol", "UNKNOWN")), entry_price, profile)
    blockers = list(risk_result.blockers)
    if feasibility.feasibility == "watch_only_or_defined_risk_option":
        blockers.append("Account feasibility requires watch-only or defined-risk expression.")
    return {
        "symbol": signal.get("symbol", "UNKNOWN"),
        "passed": risk_result.passed and not blockers,
        "risk_status": "passed" if risk_result.passed and not blockers else "blocked_or_review",
        "reward_risk_ratio": risk_result.reward_risk_ratio,
        "max_dollar_risk": risk_result.max_dollar_risk,
        "stop_distance_percent": risk_result.stop_distance_percent,
        "account_feasibility": feasibility.model_dump(),
        "blockers": blockers,
        "paper_only": True,
        "human_approval_required": True,
        "data_source": signal.get("data_source", "placeholder"),
    }


def review_signals_for_paper_only(
    signals: list[dict[str, Any]],
    account_size: float | None = None,
    max_risk_per_trade: float | None = None,
) -> dict[str, Any]:
    profile = build_paper_account_profile(account_size, max_risk_per_trade)
    reviews = [review_signal_risk(signal, profile) for signal in signals]
    return {
        "profile": profile.model_dump(),
        "reviews": reviews,
        "paper_only": True,
        "live_trading_allowed": False,
        "approval_required": bool(signals),
        "data_source": "source_backed" if any(review.get("data_source") == "source_backed" for review in reviews) else "placeholder",
    }
