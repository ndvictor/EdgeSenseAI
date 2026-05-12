# EdgeSenseAI - cleanStart

AI-native small-account edge signal and trading recommendation platform for stocks, options, and Bitcoin/crypto.

Focused for $1K-$10K buying power with agent-driven live watchlists, urgent edge signal alerts, statistical ranking, account-aware risk filtering, paper trading, and backtesting.

## Local ports

- Frontend: `3900`
- Backend: `8900`
- Postgres: `55532`
- Redis: `56390`

## Product focus

- Stocks: day trade, swing, 1-month
- Options: day trade, swing, earnings plays
- Bitcoin/Crypto: intraday, swing, 1-month/cycle
- Edge signals: urgent small-account signals that need fast alerts

## Safety

Research and paper-trading first. No live execution by default.

## Protected operations

- Backend protected mutations/RUN endpoints require `OPS_ADMIN_TOKEN`.
- Frontend server routes also need `OPS_ADMIN_TOKEN` plus `BACKEND_BASE_URL` or `NEXT_PUBLIC_API_URL`.
- Do not expose `OPS_ADMIN_TOKEN` with a `NEXT_PUBLIC_` prefix; it must stay server-side.
