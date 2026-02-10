"use client";

import { useEffect, useState } from "react";
import Tooltip from "@/components/Tooltip";
import { formatCurrency, formatDate } from "@/lib/constants";

export default function SettlementsPage() {
  const [data, setData] = useState<any>({ settlements: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/settlements")
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        Settlement Viewer
        <Tooltip text="Bank-style settlement files generated from captured payments." />
      </h1>

      {(data.settlements || []).length === 0 && !loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
          No settlement files yet. Run the seed data generator or wait for the settlement job.
        </div>
      )}

      {(data.settlements || []).map((s: any) => (
        <div key={s.file} className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">{s.file}</h2>
              <p className="text-xs text-gray-500">{s.rows} rows | Total: {formatCurrency(s.total_amount)}</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider Ref</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Settled At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {(s.data || []).map((row: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-mono text-xs">{row.payment_id}</td>
                    <td className="px-6 py-3 font-mono text-xs text-gray-500">{row.provider_ref}</td>
                    <td className="px-6 py-3">{formatCurrency(parseInt(row.amount) || 0, row.currency)}</td>
                    <td className="px-6 py-3">{row.currency}</td>
                    <td className="px-6 py-3 text-xs">{row.type}</td>
                    <td className="px-6 py-3 text-xs">{row.status}</td>
                    <td className="px-6 py-3 text-xs text-gray-500">{row.settled_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
