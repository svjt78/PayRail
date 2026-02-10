"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function PaymentsPage() {
  const [data, setData] = useState<any>({ items: [], total: 0 });
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ amount: "", currency: "USD", description: "", customer_email: "" });

  const load = () => {
    setLoading(true);
    const params = filter ? `?state=${filter}` : "";
    fetch(`/api/payments${params}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const createPayment = async () => {
    const res = await fetch("/api/payments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: parseInt(form.amount) || 0,
        currency: form.currency,
        description: form.description,
        customer_email: form.customer_email,
      }),
    });
    if (res.ok) {
      setShowCreate(false);
      setForm({ amount: "", currency: "USD", description: "", customer_email: "" });
      load();
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">
          Payments
          <Tooltip text="All payment intents and their current status." />
        </h1>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          New Payment
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        {["", "created", "authorized", "captured", "settled", "declined"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium ${filter === s ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {(data.items || []).map((p: any) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-6 py-3">
                  <Link href={`/payments/${p.id}`} className="text-blue-600 hover:underline font-mono text-xs">{p.id}</Link>
                </td>
                <td className="px-6 py-3 font-medium">{formatCurrency(p.amount, p.currency)}</td>
                <td className="px-6 py-3 text-gray-500">{p.currency}</td>
                <td className="px-6 py-3"><Badge state={p.state} /></td>
                <td className="px-6 py-3 text-gray-500">{p.provider || "-"}</td>
                <td className="px-6 py-3 text-gray-500 text-xs">{p.customer_email || "-"}</td>
                <td className="px-6 py-3 text-gray-500 text-xs">{formatDate(p.created_at)}</td>
              </tr>
            ))}
            {loading && <tr><td colSpan={7} className="px-6 py-8 text-center text-gray-400">Loading...</td></tr>}
            {!loading && (!data.items || data.items.length === 0) && (
              <tr><td colSpan={7} className="px-6 py-8 text-center text-gray-400">No payments found</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-400 mt-2">Total: {data.total || 0} payments</p>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">New Payment Intent</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Amount (cents)
                  <Tooltip text="How much to charge. 100 = $1.00." />
                </label>
                <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="e.g. 5000 = $50.00" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Currency
                  <Tooltip text="The currency for this payment (USD, EUR, GBP)." />
                </label>
                <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm">
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Customer Email
                  <Tooltip text="Contact email for the customer on this payment." />
                </label>
                <input type="email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="customer@example.com" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Description
                  <Tooltip text="A short note for your records (order ID, reason, etc.)." />
                </label>
                <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Order #123" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={createPayment} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700">Create</button>
              <button onClick={() => setShowCreate(false)} className="flex-1 border py-2 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
