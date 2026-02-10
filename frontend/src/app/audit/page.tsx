"use client";

import { useEffect, useState } from "react";
import Tooltip from "@/components/Tooltip";
import { formatDate } from "@/lib/constants";

type AuditType = "payments" | "refunds" | "disputes" | "vault-access";

export default function AuditPage() {
  const [auditType, setAuditType] = useState<AuditType>("payments");
  const [entries, setEntries] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetch(`/api/audit?type=${auditType}&limit=200`)
      .then((r) => r.json())
      .then((d) => {
        setEntries(d.entries || []);
        setTotal(d.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [auditType]);

  const exportAudit = () => {
    const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_${auditType}_${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">
          Audit Log
          <Tooltip text="Immutable event history across payments, refunds, disputes, and vault access." />
        </h1>
        <button onClick={exportAudit} className="bg-gray-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-900">
          Export JSON
        </button>
      </div>

      {/* Type Filter */}
      <div className="flex gap-2 mb-4">
        {(["payments", "refunds", "disputes", "vault-access"] as AuditType[]).map((t) => (
          <button
            key={t}
            onClick={() => setAuditType(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium ${auditType === t ? "bg-gray-800 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          >
            {t.replace("-", " ")}
          </button>
        ))}
      </div>

      <p className="text-xs text-gray-400 mb-4">Total entries: {total}</p>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {auditType === "vault-access" ? (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Token</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Requester</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Purpose</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Correlation ID</th>
                </>
              ) : (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Event ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ref</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                </>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {entries.map((e, i) =>
              auditType === "vault-access" ? (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-xs">{formatDate(e.timestamp)}</td>
                  <td className="px-6 py-3 text-xs font-medium">{e.action}</td>
                  <td className="px-6 py-3 font-mono text-xs">{e.token}</td>
                  <td className="px-6 py-3 text-xs">{e.requester}</td>
                  <td className="px-6 py-3 text-xs">{e.purpose}</td>
                  <td className="px-6 py-3 font-mono text-xs text-gray-400">{e.correlation_id}</td>
                </tr>
              ) : (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono text-xs">{e.event_id}</td>
                  <td className="px-6 py-3 text-xs font-medium">{e.type}</td>
                  <td className="px-6 py-3 font-mono text-xs">{e.ref}</td>
                  <td className="px-6 py-3 text-xs">{e.amount}</td>
                  <td className="px-6 py-3 text-xs">{e.provider || "-"}</td>
                  <td className="px-6 py-3 text-xs text-gray-500">{formatDate(e.timestamp)}</td>
                </tr>
              ),
            )}
            {!loading && entries.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-400">No audit entries</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
