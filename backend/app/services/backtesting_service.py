from pydantic import BaseModel


class BacktestMetric(BaseModel):
    name: str
    value: str
    status: str


class BacktestProfile(BaseModel):
    profile_name: str
    objective: str
    horizon: str
    status: str
    metrics: list[BacktestMetric]
    next_steps: list[str]


class BacktestingResponse(BaseModel):
    mode: str = "prototype_contract"
    profiles: list[BacktestProfile]


def build_backtesting_summary() -> BacktestingResponse:
    return BacktestingResponse(
        profiles=[
            BacktestProfile(
                profile_name="Small Account Momentum v1",
                objective="Rank RVOL, breakout, and trend-pullback candidates for $1K-$10K accounts.",
                horizon="day_trade_to_swing",
                status="contract_ready",
                metrics=[
                    BacktestMetric(name="Win Rate", value="pending", status="needs historical labels"),
                    BacktestMetric(name="Expectancy", value="pending", status="needs target-before-stop labels"),
                    BacktestMetric(name="Max Drawdown", value="pending", status="needs account simulation"),
                    BacktestMetric(name="Profit Factor", value="pending", status="needs trade outcomes"),
                ],
                next_steps=[
                    "Build labeling service for target-before-stop outcome.",
                    "Add walk-forward train/validation windows.",
                    "Store feature snapshots at signal time.",
                ],
            ),
            BacktestProfile(
                profile_name="Options Defined-Risk v1",
                objective="Validate options-flow candidates after IV, OI, spread, and underlying confirmation.",
                horizon="swing_to_earnings",
                status="contract_ready",
                metrics=[
                    BacktestMetric(name="Average R", value="pending", status="needs options spread outcomes"),
                    BacktestMetric(name="IV Crush Loss", value="pending", status="needs IV history"),
                    BacktestMetric(name="Spread Quality", value="pending", status="needs options chain snapshots"),
                ],
                next_steps=[
                    "Connect options chain provider.",
                    "Persist IV/OI/spread snapshots.",
                    "Evaluate debit spread outcomes instead of naked option assumptions.",
                ],
            ),
        ]
    )
