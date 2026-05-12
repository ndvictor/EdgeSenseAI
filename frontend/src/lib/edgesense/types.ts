export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonRecord = Record<string, JsonValue | undefined>;

export type AgentChainEntry = {
  agent?: string;
  name?: string;
  status?: string;
  active?: boolean;
  confidence?: number | null;
  audit_status?: string | null;
  audit_result?: JsonValue;
  reasoning_outputs?: JsonValue;
};

export type ControlTowerResponse = {
  status?: string;
  mode?: string;
  broker_called?: boolean;
  submitted_order?: boolean;
  live_submit_enabled?: boolean;
  paper_auto_enabled?: boolean;
  summary?: JsonRecord;
  agent_chain?: AgentChainEntry[];
  reasoning_outputs?: JsonValue;
  reasoning_monitor?: JsonValue;
  evidence_truth?: JsonValue;
  alpha_hero?: JsonValue;
  alpha_recommendation?: JsonValue;
  watchlist_agent_decision?: JsonValue;
  alpha_agent_decision?: JsonValue;
  account_feasibility_decision?: JsonValue;
  feasibility_flags?: JsonValue;
  execution_plan?: JsonValue;
  execution_flags?: JsonValue;
  feedback_loop?: JsonValue;
  paper_orders?: JsonValue[];
  orders?: JsonValue[];
  open_positions?: JsonValue[];
  closed_positions?: JsonValue[];
  learning_outcomes?: JsonValue[];
  blockers?: JsonValue[];
  warnings?: JsonValue[];
  approvals_required?: JsonValue[];
  alerts?: JsonValue[];
  latest_reviews?: JsonValue;
  agent_capability_flags?: Record<string, boolean>;
};

export type PaperAutonomyStatus = {
  status?: string;
  mode?: string;
  broker_called?: boolean;
  live_submit_enabled?: boolean;
  paper_auto_enabled?: boolean;
  paper_trading_enabled?: boolean;
  live_trading_enabled?: boolean;
  broker_execution_enabled?: boolean;
  active_workflow_run_id?: string | null;
  workflow_run_id?: string | null;
  autonomy_status?: string;
  agent_capability_flags?: Record<string, boolean>;
};

export type TradingMode = "paper" | "live";

export type EdgeSenseBundle = {
  controlTower: ControlTowerResponse | null;
  status: PaperAutonomyStatus | null;
  orders: JsonValue[];
  openPositions: JsonValue[];
  closedPositions: JsonValue[];
  learningOutcomes: JsonValue[];
  loadedAt: string;
};
