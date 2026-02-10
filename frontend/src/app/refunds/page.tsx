"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function RefundsPage() {
  const [data, setData] = useState<any>({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ payment_id: "", amount: "", reason: "" });

  const load = () => {
    setLoading(true);
    fetch("/api/refunds")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const createRefund = async () => {
    await fetch("/api/refunds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        payment_id: form.payment_id,
        amount: parseInt(form.amount) || 0,
        reason: form.reason,
      }),
    });
    setShowCreate(false);
    setForm({ payment_id: "", amount: "", reason: "" });
    load();
  };

  const approveRefund = async (refundId: string) => {
    await fetch("/api/refunds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ _action: "approve", refund_id: refundId }),
    });
    load();
  };

  const rejectRefund = async (refundId: string) => {
    await fetch("/api/refunds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ _action: "reject", refund_id: refundId }),
    });
    load();
  };

  const pending = (data.items || []).filter((r: any) => r.state === "pending_approval");
  const others = (data.items || []).filter((r: any) => r.state !== "pending_approval");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">
          Refunds
          <Tooltip text="Refund requests and their approval status." />
        </h1>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          New Refund
        </button>
      </div>

      {/* Pending Approval Queue */}
      {pending.length > 0 && (
        <div className="mb-6">
            <h2 className="text-lg font-semibold mb-3 text-yellow-700">
              Pending Approval ({pending.length})
              <Tooltip text="Refunds awaiting a different approver (maker-checker)." />
            </h2>
          <div className="space-y-2">
            {pending.map((r: any) => (
              <div key={r.id} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <Link href={`/refunds/${r.id}`} className="font-mono text-xs text-blue-600 hover:underline">{r.id}</Link>
                  <span className="mx-2 text-gray-400">|</span>
                  <span className="text-sm">{formatCurrency(r.amount, r.currency)}</span>
                  <span className="mx-2 text-gray-400">|</span>
                  <span className="text-xs text-gray-500">Payment: {r.payment_id}</span>
                  <span className="mx-2 text-gray-400">|</span>
                  <span className="text-xs text-gray-500">By: {r.requested_by}</span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => approveRefund(r.id)} className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700">Approve</button>
                  <button onClick={() => rejectRefund(r.id)} className="bg-red-600 text-white px-3 py-1 rounded text-xs hover:bg-red-700">Reject</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Refunds Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requested By</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Approved By</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {(data.items || []).map((r: any) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-6 py-3">
                  <Link href={`/refunds/${r.id}`} className="text-blue-600 hover:underline font-mono text-xs">{r.id}</Link>
                </td>
                <td className="px-6 py-3 font-mono text-xs text-gray-500">{r.payment_id}</td>
                <td className="px-6 py-3">{formatCurrency(r.amount, r.currency)}</td>
                <td className="px-6 py-3"><Badge state={r.state} /></td>
                <td className="px-6 py-3 text-gray-500">{r.requested_by || "-"}</td>
                <td className="px-6 py-3 text-gray-500">{r.approved_by || "-"}</td>
                <td className="px-6 py-3 text-gray-500 text-xs">{formatDate(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">New Refund Request</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Payment ID
                  <Tooltip text="The payment being refunded." />
                </label>
                <input type="text" value={form.payment_id} onChange={(e) => setForm({ ...form, payment_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="pi_..." />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Amount (cents)
                  <Tooltip text="How much to refund (in cents)." />
                </label>
                <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Reason
                  <Tooltip text="Why the refund is being requested." />
                </label>
                <input type="text" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Customer requested" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={createRefund} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700">Submit</button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border py-2 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
