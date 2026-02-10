export interface Payment {
  id: string;
  amount: number;
  currency: string;
  state: string;
  merchant_id: string;
  customer_email?: string;
  description?: string;
  provider?: string;
  token?: string;
  provider_ref?: string;
  idempotency_key?: string;
  correlation_id?: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
  ledger_entries?: LedgerEntry[];
}

export interface Refund {
  id: string;
  payment_id: string;
  amount: number;
  currency: string;
  state: string;
  reason?: string;
  requested_by?: string;
  approved_by?: string;
  merchant_id: string;
  correlation_id?: string;
  created_at: string;
  updated_at: string;
  ledger_entries?: LedgerEntry[];
}

export interface Dispute {
  id: string;
  payment_id: string;
  amount: number;
  state: string;
  reason: string;
  evidence?: string;
  merchant_id: string;
  correlation_id?: string;
  created_at: string;
  updated_at: string;
  ledger_entries?: LedgerEntry[];
}

export interface LedgerEntry {
  event_id: string;
  type: string;
  ref: string;
  amount: number;
  currency: string;
  merchant_id: string;
  provider?: string;
  correlation_id?: string;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface ProviderHealth {
  provider_id: string;
  circuit_state: string;
  failure_count: number;
  success_count: number;
  total_requests: number;
  last_failure_at?: string;
  last_success_at?: string;
  can_execute: boolean;
}

export interface Settlement {
  file: string;
  rows: number;
  total_amount: number;
  data: Record<string, any>[];
}

export interface ReconciliationReport {
  date: string;
  status: string;
  total_ledger: number;
  total_settlement: number;
  diff: number;
  matched: number;
  mismatched: number;
  missing_from_settlement: number;
  missing_from_ledger: number;
  mismatches: Array<{
    payment_id: string;
    ledger_amount?: number;
    settlement_amount?: number;
    diff?: number;
    issue: string;
  }>;
  generated_at: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
