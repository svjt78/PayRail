export const STATE_COLORS: Record<string, string> = {
  created: "bg-gray-100 text-gray-800",
  authorized: "bg-blue-100 text-blue-800",
  captured: "bg-indigo-100 text-indigo-800",
  settled: "bg-green-100 text-green-800",
  declined: "bg-red-100 text-red-800",
  reversed: "bg-orange-100 text-orange-800",
  chargeback: "bg-red-100 text-red-800",
  pending_approval: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  opened: "bg-yellow-100 text-yellow-800",
  under_review: "bg-blue-100 text-blue-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-red-100 text-red-800",
  closed: "bg-green-100 text-green-800",
  open: "bg-red-100 text-red-800",
  half_open: "bg-yellow-100 text-yellow-800",
};

export const CIRCUIT_COLORS: Record<string, string> = {
  closed: "bg-green-100 text-green-800",
  open: "bg-red-100 text-red-800",
  half_open: "bg-yellow-100 text-yellow-800",
};

export function formatCurrency(amount: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount / 100);
}

export function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}
