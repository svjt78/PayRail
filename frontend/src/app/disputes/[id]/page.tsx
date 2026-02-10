"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function DisputeDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [dispute, setDispute] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState("");
  const [actionLoading, setActionLoading] = useState("");

  const load = () => {
    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8026";
    fetch(`${API}/disputes/${id}`)
      .then((r) => r.json())
      .then(setDispute)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const submitEvidence = async () => {
    setActionLoading("evidence");
    await fetch("/api/disputes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ _action: "submit-evidence", dispute_id: id, evidence }),
    });
    setActionLoading("");
    load();
  };

  const resolve = async (outcome: string) => {
    setActionLoading(outcome);
    await fetch("/api/disputes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ _action: "resolve", dispute_id: id, outcome }),
    });
    setActionLoading("");
    load();
  };

  if (loading) return <div className="text-gray-400">Loading...</div>;
  if (!dispute) return <div className="text-red-500">Dispute not found</div>;

  return (
    <div>
      <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4 block">&larr; Back</button>
      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold font-mono">{dispute.id}</h1>
        <Badge state={dispute.state} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Dispute Details
            <Tooltip text="Key fields for this dispute case." />
          </h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">Payment ID<Tooltip text="The payment being disputed." /></dt><dd className="font-mono text-xs">{dispute.payment_id}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Amount<Tooltip text="Amount under dispute." /></dt><dd className="font-medium">{formatCurrency(dispute.amount)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Reason<Tooltip text="Reason for the dispute." /></dt><dd>{dispute.reason}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Evidence<Tooltip text="Evidence provided to support the case." /></dt><dd className="max-w-xs truncate">{dispute.evidence || "None submitted"}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Created<Tooltip text="When the dispute was opened." /></dt><dd>{formatDate(dispute.created_at)}</dd></div>
          </dl>

          {/* Actions */}
          <div className="mt-6 space-y-3">
            {dispute.state === "opened" && (
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Submit Evidence</label>
                <textarea value={evidence} onChange={(e) => setEvidence(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm mb-2" rows={3} placeholder="Evidence details..." />
                <button onClick={submitEvidence} disabled={!evidence || !!actionLoading}
                  className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
                  {actionLoading === "evidence" ? "..." : "Submit Evidence"}
                </button>
              </div>
            )}
            {dispute.state === "under_review" && (
              <div className="flex gap-2">
                <button onClick={() => resolve("won")} disabled={!!actionLoading}
                  className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 disabled:opacity-50">
                  {actionLoading === "won" ? "..." : "Resolve: Won"}
                </button>
                <button onClick={() => resolve("lost")} disabled={!!actionLoading}
                  className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
                  {actionLoading === "lost" ? "..." : "Resolve: Lost"}
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">
            Ledger Entries
            <Tooltip text="Audit trail for dispute events." />
          </h2>
          <div className="space-y-3">
            {(dispute.ledger_entries || []).map((e: any, i: number) => (
              <div key={i} className="border rounded p-3 text-xs">
                <div className="flex justify-between mb-1">
                  <span className="font-medium">{e.type}</span>
                  <span className="text-gray-400">{formatDate(e.timestamp)}</span>
                </div>
              </div>
            ))}
            {(!dispute.ledger_entries || dispute.ledger_entries.length === 0) && (
              <p className="text-gray-400 text-sm">No ledger entries</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
