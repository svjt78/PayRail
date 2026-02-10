"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function RefundDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [refund, setRefund] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8026";
    fetch(`${API}/refunds/${id}`)
      .then((r) => r.json())
      .then(setRefund)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-gray-400">Loading...</div>;
  if (!refund) return <div className="text-red-500">Refund not found</div>;

  return (
    <div>
      <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4 block">&larr; Back</button>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold font-mono">{refund.id}</h1>
        <Badge state={refund.state} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Refund Details
            <Tooltip text="Key fields for this refund request." />
          </h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">Payment ID<Tooltip text="The payment being refunded." /></dt><dd className="font-mono text-xs">{refund.payment_id}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Amount<Tooltip text="Amount refunded to the customer." /></dt><dd className="font-medium">{formatCurrency(refund.amount, refund.currency)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Reason<Tooltip text="Why the refund was requested." /></dt><dd>{refund.reason || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Requested By<Tooltip text="Who created the refund request." /></dt><dd>{refund.requested_by || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Approved By<Tooltip text="Approver for maker-checker workflow." /></dt><dd>{refund.approved_by || "-"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Created<Tooltip text="When the refund was created." /></dt><dd>{formatDate(refund.created_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Updated<Tooltip text="Last update time for this refund." /></dt><dd>{formatDate(refund.updated_at)}</dd></div>
          </dl>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Ledger Entries
            <Tooltip text="Audit trail of refund events." />
          </h2>
          <div className="space-y-3">
            {(refund.ledger_entries || []).map((e: any, i: number) => (
              <div key={i} className="border rounded p-3 text-xs">
                <div className="flex justify-between mb-1">
                  <span className="font-medium">{e.type}</span>
                  <span className="text-gray-400">{formatDate(e.timestamp)}</span>
                </div>
                <div className="text-gray-500">
                  Event: <span className="font-mono">{e.event_id}</span>
                </div>
              </div>
            ))}
            {(!refund.ledger_entries || refund.ledger_entries.length === 0) && (
              <p className="text-gray-400 text-sm">No ledger entries</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
