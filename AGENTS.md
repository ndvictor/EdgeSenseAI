# EdgeSenseAI — agent instructions

## Alpaca buying power (MCP verification)

After you change or review **backend** code or deployment env that affects **Alpaca account reads**, **buying power**, **paper snapshot**, or **execution routing**, finish by calling the **`user-alpaca`** MCP tool **`get_account_info`** (read its schema first), and confirm buying power / balances look sane. If MCP is unavailable or not authenticated, say so and point to `/api/paper-trading/alpaca` or the Alpaca dashboard.

Skip this when the task did not touch those areas. Do not move app logic to MCP—users still use the backend API only.

More detail: `.cursor/rules/alpaca-buying-power-mcp-verification.mdc`.
