"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, MessageSquare, Package, BookOpen, Settings, LogOut, UserCircle } from "lucide-react";
import { ReactNode, useEffect, useState } from "react";

const nav = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
  { href: "/inbox",     icon: MessageSquare,   label: "Inbox"    },
  { href: "/products",  icon: Package,          label: "Products" },
  { href: "/knowledge", icon: BookOpen,         label: "Knowledge"},
  { href: "/profile",   icon: UserCircle,       label: "Profile"  },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [checkedAuth, setCheckedAuth] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const token = localStorage.getItem("otc_token");
      const vendorId = localStorage.getItem("otc_vendor_id");
      if (!token || !vendorId) {
        router.replace("/login");
        return;
      }
      setCheckedAuth(true);
    }, 50);
    return () => window.clearTimeout(timeout);
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("otc_token");
    localStorage.removeItem("otc_vendor_id");
    router.replace("/login");
  };

  if (!checkedAuth) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-100 border-t-emerald-700 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-white">
      {/* Sidebar — full height, clean border, no background box */}
      <aside className="w-[72px] border-r border-gray-100 flex flex-col items-center py-6 gap-3 shrink-0 sticky top-0 h-screen">
        {/* Logo mark */}
        <Link href="/" className="w-9 h-9 mb-4 rounded-full bg-[#059669] flex items-center justify-center text-white font-black text-[15px] shrink-0 shadow-[0_4px_12px_rgba(15,23,42,0.35)]">
          O
        </Link>

        {nav.map(({ href, icon: Icon, label }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all ${
                active
                  ? "text-emerald-700"
                  : "text-gray-400 hover:text-gray-700 hover:bg-gray-100"
              }`}
            >
              <Icon size={19} strokeWidth={active ? 2 : 1.5} />
            </Link>
          );
        })}

        <div className="mt-auto">
          <Link
            href="/settings"
            title="Settings"
            className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all ${
              path === "/settings" || path.startsWith("/settings/")
                ? "text-emerald-700"
                : "text-gray-400 hover:text-gray-700 hover:bg-gray-100"
            }`}
          >
            <Settings size={19} strokeWidth={path === "/settings" || path.startsWith("/settings/") ? 2 : 1.5} />
          </Link>
          <button
            type="button"
            title="Logout"
            onClick={handleLogout}
            className="w-10 h-10 mt-3 flex items-center justify-center rounded-xl transition-all text-gray-400 hover:text-gray-700 hover:bg-gray-100"
          >
            <LogOut size={19} strokeWidth={1.5} />
          </button>
        </div>
      </aside>

      {/* Page content */}
      <div className="flex-1 flex flex-col min-w-0">
        {children}
      </div>
    </div>
  );
}
