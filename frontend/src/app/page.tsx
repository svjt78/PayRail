"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function Dashboard() {
  const [payments, setPayments] = useState<any>({ items: [], total: 0 });
  const [refunds, setRefunds] = useState<any>({ items: [], total: 0 });
  const [disputes, setDisputes] = useState<any>({ items: [], total: 0 });
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/payments?limit=10").then((r) => r.json()).then(setPayments).catch(() => {});
    fetch("/api/refunds?limit=10").then((r) => r.json()).then(setRefunds).catch(() => {});
    fetch("/api/disputes?limit=10").then((r) => r.json()).then(setDisputes).catch(() => {});
    fetch("/api/providers").then((r) => r.json()).then((d) => setProviders(d.providers || [])).catch(() => {});
  }, []);

  const totalAmount = payments.items?.reduce((s: number, p: any) => s + (p.amount || 0), 0) || 0;
  const capturedCount = payments.items?.filter((p: any) => p.state === "captured" || p.state === "settled").length || 0;
  const pendingRefunds = refunds.items?.filter((r: any) => r.state === "pending_approval").length || 0;
  const openDisputes = disputes.items?.filter((d: any) => d.state === "opened" || d.state === "under_review").length || 0;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        Dashboard
        <Tooltip text="Quick overview of payments, refunds, disputes, and provider health." />
      </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Payments</p>
          <p className="text-3xl font-bold">{payments.total || 0}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Recent Volume</p>
          <p className="text-3xl font-bold">{formatCurrency(totalAmount)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Pending Refunds</p>
          <p className="text-3xl font-bold text-yellow-600">{pendingRefunds}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Open Disputes</p>
          <p className="text-3xl font-bold text-red-600">{openDisputes}</p>
        </div>
      </div>

      {/* Provider Status */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Provider Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map((p) => (
            <div key={p.provider_id} className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
              <div>
                <p className="font-medium">{p.provider_id}</p>
                <p className="text-xs text-gray-500">
                  {p.success_count} successes / {p.failure_count} failures
                </p>
              </div>
              <Badge state={p.circuit_state} />
            </div>
          ))}
        </div>
      </div>

      {/* Recent Payments */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Payments</h2>
          <Link href="/payments" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">State</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {(payments.items || []).slice(0, 10).map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <Link href={`/payments/${p.id}`} className="text-blue-600 hover:underline font-mono text-xs">{p.id}</Link>
                  </td>
                  <td className="px-6 py-3">{formatCurrency(p.amount, p.currency)}</td>
                  <td className="px-6 py-3"><Badge state={p.state} /></td>
                  <td className="px-6 py-3 text-gray-500">{p.provider || "-"}</td>
                  <td className="px-6 py-3 text-gray-500 text-xs">{formatDate(p.created_at)}</td>
                </tr>
              ))}
              {(!payments.items || payments.items.length === 0) && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-400">No payments yet. Seed data to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
