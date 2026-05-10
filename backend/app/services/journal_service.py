from pydantic import BaseModel


class JournalEntry(BaseModel):
    id: str
    symbol: str
    asset_class: str
    setup: str
    planned_action: str
    entry_zone: str
    stop: str
    target: str
    status: str
    outcome_label: str
    lesson: str


class JournalSummary(BaseModel):
    mode: str = "prototype_contract"
    total_entries: int
    pending_reviews: int
    winning_labels: int
    losing_labels: int
    entries: list[JournalEntry]
    next_steps: list[str]


def build_journal_summary() -> JournalSummary:
    entries: list[JournalEntry] = []
    return JournalSummary(
        total_entries=len(entries),
        pending_reviews=len([entry for entry in entries if entry.outcome_label == "pending"]),
        winning_labels=0,
        losing_labels=0,
        entries=entries,
        next_steps=[
            "Persist journal entries in a database.",
            "Connect paper trade outcomes to backtesting labels.",
            "Track target-before-stop outcomes by setup, regime, and asset class.",
            "Use journal outcomes to calibrate ranker confidence over time.",
        ],
    )
