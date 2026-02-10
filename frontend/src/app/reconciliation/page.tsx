"use client";

import { useEffect, useState } from "react";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { formatCurrency } from "@/lib/constants";

export default function ReconciliationPage() {
  const [data, setData] = useState<any>({ reports: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/reconciliation")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        Reconciliation Reports
        <Tooltip text="Compare ledger totals vs settlement files to detect mismatches." />
      </h1>

      {(data.reports || []).length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
          No reconciliation reports yet. Reports are generated hourly by the ledger-jobs service.
        </div>
      )}

      {(data.reports || []).map((r: any, i: number) => (
        <div key={i} className="bg-white rounded-lg shadow mb-6 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Report: {r.date}</h2>
            <Badge state={r.status === "clean" ? "settled" : "declined"} />
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded p-3 text-center">
              <p className="text-xl font-bold">{formatCurrency(r.total_ledger)}</p>
              <p className="text-xs text-gray-500">Ledger Total</p>
            </div>
            <div className="bg-gray-50 rounded p-3 text-center">
              <p className="text-xl font-bold">{formatCurrency(r.total_settlement)}</p>
              <p className="text-xs text-gray-500">Settlement Total</p>
            </div>
            <div className={`rounded p-3 text-center ${r.diff !== 0 ? "bg-red-50" : "bg-green-50"}`}>
              <p className={`text-xl font-bold ${r.diff !== 0 ? "text-red-600" : "text-green-600"}`}>{formatCurrency(Math.abs(r.diff))}</p>
              <p className="text-xs text-gray-500">Difference</p>
            </div>
            <div className="bg-gray-50 rounded p-3 text-center">
              <p className="text-xl font-bold text-green-600">{r.matched}</p>
              <p className="text-xs text-gray-500">Matched</p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
            <div className="flex justify-between border rounded p-2">
              <span className="text-gray-500">Mismatched</span>
              <span className="font-medium text-red-600">{r.mismatched}</span>
            </div>
            <div className="flex justify-between border rounded p-2">
              <span className="text-gray-500">Missing (Settlement)</span>
              <span className="font-medium text-orange-600">{r.missing_from_settlement}</span>
            </div>
            <div className="flex justify-between border rounded p-2">
              <span className="text-gray-500">Missing (Ledger)</span>
              <span className="font-medium text-orange-600">{r.missing_from_ledger}</span>
            </div>
          </div>

          {/* Mismatches Table */}
          {(r.mismatches || []).length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">Mismatches</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Payment ID</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Ledger Amount</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Settlement Amount</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Diff</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Issue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {r.mismatches.map((m: any, j: number) => (
                      <tr key={j}>
                        <td className="px-4 py-2 font-mono text-xs">{m.payment_id}</td>
                        <td className="px-4 py-2">{m.ledger_amount != null ? formatCurrency(m.ledger_amount) : "-"}</td>
                        <td className="px-4 py-2">{m.settlement_amount != null ? formatCurrency(m.settlement_amount) : "-"}</td>
                        <td className="px-4 py-2 text-red-600">{m.diff != null ? formatCurrency(Math.abs(m.diff)) : "-"}</td>
                        <td className="px-4 py-2 text-xs">{m.issue.replace(/_/g, " ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <p className="text-xs text-gray-400 mt-4">Generated: {r.generated_at}</p>
        </div>
      ))}
    </div>
  );
}
