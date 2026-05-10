"""Paper autonomy loop for EdgeSenseAI (simulation only).

This package converts audited execution plans into simulated paper orders /
positions and feeds the downstream monitor → close review → post-trade →
learning loop chain.

Hard guarantees enforced everywhere in this package:

- Never calls a broker. ``broker_called`` is always ``False``.
- Never calls Alpaca order submit. Alpaca read paths (account snapshot, market
  data quotes) are allowed; order submit is not.
- ``submitted_order=True`` is only set on records when paper auto-submit is
  authorized AND every required env flag is set. ``live_submit`` is permanently
  ``False`` in this loop.
- No mock/synthetic prices, sizes, or symbols are introduced. Stores carry the
  real values that came from audited upstream agents.
- No fallback symbols. Missing symbol => blocker, not a default.
"""

from app.services.paper_autonomy import (  # noqa: F401
    learning_outcomes_store,
    models,
    paper_order_store,
    paper_position_store,
    paper_simulator,
    post_trade_builder,
)
