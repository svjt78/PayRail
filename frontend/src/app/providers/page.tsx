"use client";

import { useEffect, useState } from "react";
import Badge from "@/components/Badge";
import Tooltip from "@/components/Tooltip";
import { CIRCUIT_COLORS, formatDate } from "@/lib/constants";

export default function ProvidersPage() {
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<Record<string, any>>({});

  const load = () => {
    fetch("/api/providers")
      .then((r) => r.json())
      .then((d) => setProviders(d.providers || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); const interval = setInterval(load, 5000); return () => clearInterval(interval); }, []);

  const updateConfig = (providerId: string, field: string, value: string) => {
    setConfigs((prev) => ({
      ...prev,
      [providerId]: {
        ...(prev[providerId] || {}),
        [field]: value,
      },
    }));
  };

  const injectFailure = async (providerId: string) => {
    const raw = configs[providerId] || {};
    const payload: Record<string, any> = { provider_id: providerId };
    [
      "timeout_rate",
      "decline_rate",
      "error_rate",
      "duplicate_webhook_rate",
      "settlement_mismatch_rate",
      "latency_ms_min",
      "latency_ms_max",
    ].forEach((k) => {
      const v = raw[k];
      if (v === "" || v == null) return;
      payload[k] = k.includes("latency") ? parseInt(v, 10) : parseFloat(v);
    });

    await fetch("/api/providers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    load();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        Provider Health Board
        <Tooltip text="Live status and circuit breaker state per provider." />
      </h1>
      <p className="text-sm text-gray-500 mb-6">Auto-refreshes every 5 seconds</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {providers.map((p) => (
          <div key={p.provider_id} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">{p.provider_id}</h2>
              <Badge state={p.circuit_state} />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="text-center p-3 bg-gray-50 rounded">
                <p className="text-2xl font-bold text-green-600">{p.success_count}</p>
                <p className="text-xs text-gray-500">Successes</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded">
                <p className="text-2xl font-bold text-red-600">{p.failure_count}</p>
                <p className="text-xs text-gray-500">Failures</p>
              </div>
            </div>

            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Total Requests</dt>
                <dd>{p.total_requests}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Can Execute</dt>
                <dd className={p.can_execute ? "text-green-600" : "text-red-600"}>
                  {p.can_execute ? "Yes" : "No"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Last Success</dt>
                <dd className="text-xs">{p.last_success_at ? formatDate(p.last_success_at) : "-"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Last Failure</dt>
                <dd className="text-xs">{p.last_failure_at ? formatDate(p.last_failure_at) : "-"}</dd>
              </div>
            </dl>

            {/* Circuit State Visual */}
            <div className="mt-4 pt-4 border-t">
              <div className="flex items-center gap-2">
                {["closed", "open", "half_open"].map((state) => (
                  <div
                    key={state}
                    className={`flex-1 text-center py-2 rounded text-xs font-medium ${
                      p.circuit_state === state
                        ? CIRCUIT_COLORS[state]
                        : "bg-gray-100 text-gray-400"
                    }`}
                  >
                    {state.replace("_", " ")}
                  </div>
                ))}
              </div>
            </div>

            {/* Failure Injection */}
            <div className="mt-4 pt-4 border-t">
            <h3 className="text-sm font-medium text-gray-700 mb-2">
              Failure Injection
              <Tooltip text="Simulate provider issues for testing." />
            </h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <input
                  type="number"
                  step="0.01"
                  placeholder="timeout_rate"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.timeout_rate || ""}
                  onChange={(e) => updateConfig(p.provider_id, "timeout_rate", e.target.value)}
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="decline_rate"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.decline_rate || ""}
                  onChange={(e) => updateConfig(p.provider_id, "decline_rate", e.target.value)}
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="error_rate"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.error_rate || ""}
                  onChange={(e) => updateConfig(p.provider_id, "error_rate", e.target.value)}
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="duplicate_webhook_rate"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.duplicate_webhook_rate || ""}
                  onChange={(e) => updateConfig(p.provider_id, "duplicate_webhook_rate", e.target.value)}
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="settlement_mismatch_rate"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.settlement_mismatch_rate || ""}
                  onChange={(e) => updateConfig(p.provider_id, "settlement_mismatch_rate", e.target.value)}
                />
                <input
                  type="number"
                  placeholder="latency_ms_min"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.latency_ms_min || ""}
                  onChange={(e) => updateConfig(p.provider_id, "latency_ms_min", e.target.value)}
                />
                <input
                  type="number"
                  placeholder="latency_ms_max"
                  className="border rounded px-2 py-1"
                  value={configs[p.provider_id]?.latency_ms_max || ""}
                  onChange={(e) => updateConfig(p.provider_id, "latency_ms_max", e.target.value)}
                />
              </div>
              <button
                onClick={() => injectFailure(p.provider_id)}
                className="mt-3 w-full bg-gray-900 text-white py-2 rounded text-xs hover:bg-black"
              >
                Apply Failure Config
              </button>
            </div>
          </div>
        ))}
      </div>

      {loading && <p className="text-gray-400 mt-4">Loading...</p>}
    </div>
  );
}
