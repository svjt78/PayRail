"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

const TIMELINE_STATES = ["created", "authorized", "captured", "settled"];

export default function PaymentDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [payment, setPayment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");

  const load = () => {
    fetch(`/api/payments?_detail=${id}`)
      .then(async (r) => {
        // Use the detail endpoint via direct API call
        const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8026";
        const res = await fetch(`${API}/payment-intents/${id}`);
        return res.json();
      })
      .then(setPayment)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const doAction = async (action: string, body: any = {}) => {
    setActionLoading(action);
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8026";
      const res = await fetch(`${API}/payment-intents/${id}/${action}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Merchant-Id": "m_001",
          "X-Role": "operator",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      if (res.ok) load();
    } finally {
      setActionLoading("");
    }
  };

  if (loading) return <div className="text-gray-400">Loading...</div>;
  if (!payment) return <div className="text-red-500">Payment not found</div>;

  const currentIdx = TIMELINE_STATES.indexOf(payment.state);

  return (
    <div>
      <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4 block">&larr; Back</button>

      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold font-mono">{payment.id}</h1>
        <Badge state={payment.state} />
      </div>

      {/* State Timeline */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-sm font-medium text-gray-500 mb-4">
          Payment Timeline
          <Tooltip text="Tracks the payment from created to settled. Stops if declined, reversed, or chargeback." />
        </h2>
        <div className="flex items-center gap-2">
          {TIMELINE_STATES.map((s, i) => {
            const isActive = payment.state === s;
            const isPast = currentIdx >= 0 && i <= currentIdx;
            const isDeclined = payment.state === "declined" || payment.state === "reversed" || payment.state === "chargeback";
            return (
              <div key={s} className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                  isActive ? "bg-blue-600 text-white" :
                  isPast ? "bg-green-500 text-white" :
                  "bg-gray-200 text-gray-500"
                }`}>
                  {isPast && !isActive ? "\u2713" : i + 1}
                </div>
                <span className={`text-xs ${isActive ? "font-bold" : "text-gray-500"}`}>{s}</span>
                {i < TIMELINE_STATES.length - 1 && (
                  <div className={`w-8 h-0.5 ${isPast ? "bg-green-500" : "bg-gray-200"}`} />
                )}
              </div>
            );
          })}
          {(payment.state === "declined" || payment.state === "reversed" || payment.state === "chargeback") && (
            <div className="flex items-center gap-2 ml-4">
              <div className="w-8 h-8 rounded-full bg-red-500 text-white flex items-center justify-center text-xs font-bold">!</div>
              <span className="text-xs font-bold text-red-600">{payment.state}</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Details */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Payment Details
            <Tooltip text="Key fields that describe this payment and its processing." />
          </h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">Amount<Tooltip text="How much the customer is charged." /></dt><dd className="font-medium">{formatCurrency(payment.amount, payment.currency)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Currency<Tooltip text="The currency for this payment." /></dt><dd>{payment.currency}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Provider<Tooltip text="Processor selected during authorization." /></dt><dd>{payment.provider || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Provider Ref<Tooltip text="Processor reference ID for this charge." /></dt><dd className="font-mono text-xs">{payment.provider_ref || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Token<Tooltip text="Safe stand-in for the card number." /></dt><dd className="font-mono text-xs">{payment.token || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Customer<Tooltip text="Customer email on the payment." /></dt><dd>{payment.customer_email || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Merchant<Tooltip text="Merchant account that created the payment." /></dt><dd>{payment.merchant_id}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Idempotency Key<Tooltip text="Prevents accidental duplicate processing." /></dt><dd className="font-mono text-xs">{payment.idempotency_key || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Correlation ID<Tooltip text="Tracking ID across services and logs." /></dt><dd className="font-mono text-xs">{payment.correlation_id || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Created<Tooltip text="When the payment was first recorded." /></dt><dd>{formatDate(payment.created_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Updated<Tooltip text="Last time this payment changed." /></dt><dd>{formatDate(payment.updated_at)}</dd></div>
          </dl>

          {/* Actions */}
          <div className="mt-6 flex gap-2">
            {payment.state === "created" && (
              <button
                onClick={() => doAction("authorize", { pan: "4111111111111111", expiry: "12/28" })}
                disabled={!!actionLoading}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading === "authorize" ? "..." : "Authorize"}
              </button>
            )}
            {payment.state === "authorized" && (
              <>
                <button
                  onClick={() => doAction("capture")}
                  disabled={!!actionLoading}
                  className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === "capture" ? "..." : "Capture"}
                </button>
                <button
                  onClick={() => doAction("cancel")}
                  disabled={!!actionLoading}
                  className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading === "cancel" ? "..." : "Cancel"}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Ledger Entries */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Ledger Entries
            <Tooltip text="Immutable audit trail for this payment." />
          </h2>
          <div className="space-y-3">
            {(payment.ledger_entries || []).map((e: any, i: number) => (
              <div key={i} className="border rounded p-3 text-xs">
                <div className="flex justify-between mb-1">
                  <span className="font-medium">{e.type}</span>
                  <span className="text-gray-400">{formatDate(e.timestamp)}</span>
                </div>
                <div className="text-gray-500">
                  Event: <span className="font-mono">{e.event_id}</span> | Amount: {formatCurrency(e.amount, e.currency)}
                </div>
              </div>
            ))}
            {(!payment.ledger_entries || payment.ledger_entries.length === 0) && (
              <p className="text-gray-400 text-sm">No ledger entries</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
