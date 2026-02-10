import { STATE_COLORS } from "@/lib/constants";

export default function Badge({ state }: { state: string }) {
  const color = STATE_COLORS[state] || "bg-gray-100 text-gray-800";
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}
    >
      {state.replace(/_/g, " ")}
    </span>
  );
}
