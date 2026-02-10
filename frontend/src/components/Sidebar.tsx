"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "H" },
  { href: "/payments", label: "Payments", icon: "P" },
  { href: "/refunds", label: "Refunds", icon: "R" },
  { href: "/disputes", label: "Disputes", icon: "D" },
  { href: "/providers", label: "Providers", icon: "V" },
  { href: "/settlements", label: "Settlements", icon: "S" },
  { href: "/reconciliation", label: "Reconciliation", icon: "C" },
  { href: "/audit", label: "Audit Log", icon: "A" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-xl font-bold tracking-tight">PayRail</h1>
        <p className="text-xs text-gray-400 mt-1">Merchant Console</p>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center px-6 py-3 text-sm transition-colors ${
                isActive
                  ? "bg-gray-800 text-white border-r-2 border-blue-500"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              <span className="w-6 h-6 rounded bg-gray-700 flex items-center justify-center text-xs font-bold mr-3">
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        PayRail Demo v1.0
      </div>
    </aside>
  );
}
