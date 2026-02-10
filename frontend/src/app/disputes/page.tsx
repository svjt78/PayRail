"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function DisputesPage() {
  const [data, setData] = useState<any>({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ payment_id: "", amount: "", reason: "" });

  const load = () => {
    setLoading(true);
    fetch("/api/disputes")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const createDispute = async () => {
    await fetch("/api/disputes", {
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">
          Disputes
          <Tooltip text="Chargeback and dispute cases opened against payments." />
        </h1>
        <button onClick={() => setShowCreate(true)} className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700">
          Open Dispute
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {(data.items || []).map((d: any) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <td className="px-6 py-3">
                  <Link href={`/disputes/${d.id}`} className="text-blue-600 hover:underline font-mono text-xs">{d.id}</Link>
                </td>
                <td className="px-6 py-3 font-mono text-xs text-gray-500">{d.payment_id}</td>
                <td className="px-6 py-3">{formatCurrency(d.amount)}</td>
                <td className="px-6 py-3"><Badge state={d.state} /></td>
                <td className="px-6 py-3 text-gray-500 text-xs max-w-xs truncate">{d.reason}</td>
                <td className="px-6 py-3 text-gray-500 text-xs">{formatDate(d.created_at)}</td>
              </tr>
            ))}
            {!loading && (!data.items || data.items.length === 0) && (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-400">No disputes</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">Open Dispute</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Payment ID
                  <Tooltip text="The payment this dispute is about." />
                </label>
                <input type="text" value={form.payment_id} onChange={(e) => setForm({ ...form, payment_id: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="pi_..." />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Amount (cents)
                  <Tooltip text="Amount under dispute (in cents)." />
                </label>
                <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Reason
                  <Tooltip text="Reason for opening this dispute." />
                </label>
                <input type="text" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Unauthorized transaction" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={createDispute} className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm hover:bg-red-700">Open Dispute</button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border py-2 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
