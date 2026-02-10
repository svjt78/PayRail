"use client";

export default function Tooltip({ text }: { text: string }) {
  return (
    <span
      className="ml-2 inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-200 text-[10px] text-gray-700 cursor-help align-middle"
      title={text}
      aria-label={text}
      role="img"
    >
      ?
    </span>
  );
}
