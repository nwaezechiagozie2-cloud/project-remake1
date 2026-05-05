import { Search, SlidersHorizontal, MoreHorizontal, FileText, Globe, MessageSquare } from "lucide-react";

const knowledgeItems = [
  { topic: "Business Hours & Location", type: "Text Snippet", scope: "Global",     status: "Active", iconType: "text" },
  { topic: "Shipping & Delivery Policy", type: "Document",     scope: "Global",     status: "Active", iconType: "doc"  },
  { topic: "Refunds & Returns",         type: "Text Snippet", scope: "Global",     status: "Active", iconType: "text" },
  { topic: "Wholesale Pricing 2026",    type: "PDF File",     scope: "B2B Only",   status: "Draft",  iconType: "doc"  },
  { topic: "Brand Persona Guidelines",  type: "Prompt",       scope: "Bot Persona",status: "Active", iconType: "bot"  },
];

const statusStyle: Record<string, string> = {
  "Active": "text-emerald-500 bg-emerald-50",
  "Draft":  "text-amber-700   bg-amber-50",
};

function TopicIcon({ type }: { type: string }) {
  let hue = 210;
  let Icon = FileText;
  
  if (type === "text") {
    hue = 160; 
    Icon = MessageSquare;
  } else if (type === "doc") {
    hue = 280;
    Icon = FileText;
  } else if (type === "bot") {
    hue = 30; 
    Icon = Globe;
  }

  return (
    <span
      className="w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm"
      style={{ background: `hsl(${hue} 55% 55%)` }}
    >
      <Icon size={14} strokeWidth={2.5} />
    </span>
  );
}

export default function KnowledgePage() {
  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">

        {/* Title row */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">AI Context</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Knowledge Base</h1>
          </div>
          <button className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-700 transition-colors">
            + Add context
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search context…"
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:border-[#059669]/40 placeholder:text-gray-400 transition-all"
            />
          </div>
          <button className="flex items-center gap-1.5 border border-gray-200 bg-white rounded-xl px-3 py-2 text-[13px] font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
            <SlidersHorizontal size={13} /> Filter
          </button>
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-6 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Topic</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Type</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-center">Status</span>
          <span className="col-span-2 flex justify-end"></span>
        </div>

        {/* Context rows */}
        <div className="space-y-0.5">
          {knowledgeItems.map((item, i) => (
            <div
              key={i}
              className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer group"
            >
              <div className="col-span-6 flex items-center gap-3">
                <TopicIcon type={item.iconType} />
                <div>
                  <p className="text-[13px] font-semibold text-gray-900 leading-tight">{item.topic}</p>
                  <p className="text-[11px] text-gray-400 font-medium mt-0.5">{item.scope}</p>
                </div>
              </div>
              <div className="col-span-2">
                <span className="text-[12px] font-medium text-gray-500">{item.type}</span>
              </div>
              <div className="col-span-2 flex justify-center">
                <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${statusStyle[item.status]}`}>
                  {item.status}
                </span>
              </div>
              <div className="col-span-2 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="Options">
                  <MoreHorizontal size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
