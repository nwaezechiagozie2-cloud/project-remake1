"use client";
import { useEffect, useState } from "react";
import { TrendingUp, AlertCircle, CheckCircle, ArrowUpRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { fetchDashboardData, getApiErrorMessage } from "@/lib/api";

type DashboardData = {
  vendor?: {
    whatsapp_number?: string | null;
  };
  products?: unknown[];
  business_info?: unknown[];
};

const orders = [
  { id: "#10403", name: "Sarah Jenkins",  product: "Retro Analog Clock",    amount: "₦14,500", status: "paid",    time: "2m ago"  },
  { id: "#10399", name: "John Mensah",    product: "Minimalist Desk Lamp",  amount: "₦25,000", status: "pending", time: "18m ago" },
  { id: "#10398", name: "Michael Tunde",  product: "Ergonomic Chair",       amount: "₦85,000", status: "paid",    time: "1h ago"  },
  { id: "#10391", name: "Amara Okoye",    product: "Ceramic Pour-Over Set", amount: "₦18,750", status: "paid",    time: "3h ago"  },
];

const statusBadge: Record<string, string> = {
  paid:    "text-emerald-700 bg-emerald-50",
  pending: "text-amber-700  bg-amber-50",
};

function Avatar({ name }: { name: string }) {
  const initials = name.split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase();
  const hues = [210, 160, 280, 30, 200];
  return (
    <span
      className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold text-white shrink-0 select-none"
      style={{ background: `hsl(${hues[name.charCodeAt(0) % hues.length]} 60% 52%)` }}
    >
      {initials}
    </span>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const vendorId = localStorage.getItem("otc_vendor_id");
        const token = localStorage.getItem("otc_token");
        if (!vendorId || !token) {
          throw new Error("Missing authentication credentials");
        }
        const dashboardData = await fetchDashboardData(vendorId, token);
        setData(dashboardData);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, "Failed to load dashboard data"));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-red-500 font-bold">{error}</p>
      </div>
    );
  }

  const isWhatsAppConnected = Boolean(data?.vendor?.whatsapp_number);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">

        {/* Setup Prompt Banner — visible only when WhatsApp is not connected */}
        {!isWhatsAppConnected && (
          <div className="mb-10 bg-white border border-emerald-700/20 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="space-y-1">
               <div className="flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-emerald-700"></span>
                  <p className="text-[13px] font-bold text-gray-900">WhatsApp setup required</p>
               </div>
               <p className="text-[12px] text-gray-500 font-medium max-w-md leading-relaxed">
                 You haven&apos;t connected your WhatsApp Business account yet. Connect now to start receiving inquiries and orders.
               </p>
            </div>
            <button
              disabled
              className="bg-gray-100 text-gray-400 px-5 py-2 rounded-xl text-[12px] font-bold cursor-not-allowed border border-gray-200 shrink-0"
            >
              Connect WhatsApp
            </button>
          </div>
        )}

        {/* Page title */}
        <div className="flex items-start justify-between mb-10">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">Overview</p>
            <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">Command Center</h1>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/settings">
              <button className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-4 py-1.5 rounded-lg hover:bg-gray-50 transition-colors shadow-sm">
                Connectivity settings
              </button>
            </Link>
            <button className="text-[12px] font-semibold text-gray-400 hover:text-gray-700 flex items-center gap-1 transition-colors">
              This week <ArrowUpRight size={13} />
            </button>
          </div>
        </div>

        {/* KPI section — three stacked items with a visual mark, not a card/table */}
        <div className="mb-10 space-y-0">
          {/* KPI 1 */}
          <div className="flex items-center justify-between py-5 border-b border-gray-100 group hover:bg-gray-50/60 px-4 -mx-4 rounded-xl transition-colors cursor-default">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                <TrendingUp size={15} className="text-[#09090b]" />
              </div>
              <div>
                <p className="text-[12px] font-semibold text-gray-500">Active Inquiries</p>
                <p className="text-[11px] text-gray-400 font-medium">Across all active WhatsApp conversations</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-[32px] font-black tracking-[-0.04em] text-gray-900 leading-none">14</p>
              <p className="text-[11px] text-emerald-500 font-semibold mt-1">↑ 2 since yesterday</p>
            </div>
          </div>

          {/* KPI 2 */}
          <div className="flex items-center justify-between py-5 border-b border-gray-100 group hover:bg-gray-50/60 px-4 -mx-4 rounded-xl transition-colors cursor-default">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
                <AlertCircle size={15} className="text-amber-500" />
              </div>
              <div>
                <p className="text-[12px] font-semibold text-gray-500">Pending Hand-offs</p>
                <p className="text-[11px] text-gray-400 font-medium">Conversations requiring your attention</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-[32px] font-black tracking-[-0.04em] text-amber-500 leading-none">3</p>
              <p className="text-[11px] text-gray-400 font-semibold mt-1">Require action</p>
            </div>
          </div>

          {/* KPI 3 */}
          <div className="flex items-center justify-between py-5 group hover:bg-gray-50/60 px-4 -mx-4 rounded-xl transition-colors cursor-default">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                <CheckCircle size={15} className="text-emerald-500" />
              </div>
              <div>
                <p className="text-[12px] font-semibold text-gray-500">Bot Resolution Rate</p>
                <p className="text-[11px] text-gray-400 font-medium">Inquiries closed without human input</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-[32px] font-black tracking-[-0.04em] text-emerald-700 leading-none">92%</p>
              <p className="text-[11px] text-emerald-700 font-semibold mt-1">Strong deflection</p>
            </div>
          </div>
        </div>

        {/* Orders */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[14px] font-bold text-gray-900">Recent orders</h2>
          <button className="text-[12px] font-semibold text-[#09090b] hover:underline">View all</button>
        </div>

        {/* Col headers */}
        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-4 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Customer</span>
          <span className="col-span-4 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Product</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-right">Amount</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-right">Status</span>
        </div>

        <div className="space-y-0.5">
          {orders.map(o => (
            <div
              key={o.id}
              className="grid grid-cols-12 items-center px-3 py-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer"
            >
              <div className="col-span-4 flex items-center gap-2.5">
                <Avatar name={o.name} />
                <div>
                  <p className="text-[13px] font-semibold text-gray-900 leading-tight">{o.name}</p>
                  <p className="text-[11px] text-gray-400 font-medium">{o.id} · {o.time}</p>
                </div>
              </div>
              <div className="col-span-4">
                <p className="text-[13px] text-gray-600 font-medium truncate">{o.product}</p>
              </div>
              <div className="col-span-2 text-right">
                <p className="text-[13px] font-bold font-mono text-gray-900">{o.amount}</p>
              </div>
              <div className="col-span-2 flex justify-end">
                <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full capitalize ${statusBadge[o.status]}`}>
                  {o.status}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* AI Insight — inline at bottom, no sidebar panel */}
        <div className="mt-10 pt-6 border-t border-gray-100">
          <p className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] mb-3">AI Insight</p>
          <p className="text-[13px] font-semibold text-gray-800 leading-relaxed max-w-lg">
            The bot currently manages <span className="text-[#09090b]">{data?.products?.length || 0} products</span> and <span className="text-[#09090b]">{data?.business_info?.length || 0} information blocks</span>. Consider adding answers on <span className="text-gray-900">shipping timelines</span> to improve deflection further.
          </p>
          <Link href="/knowledge">
            <button className="mt-3 text-[12px] font-bold text-[#09090b] hover:underline flex items-center gap-1">
              Edit knowledge base <ArrowUpRight size={12} />
            </button>
          </Link>
        </div>

      </div>
    </div>
  );
}
