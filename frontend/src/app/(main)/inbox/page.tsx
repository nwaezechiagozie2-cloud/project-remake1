import { Search, Bell, FileText, Link2, MoreHorizontal, Send } from "lucide-react";

function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const initials = name.split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase();
  const hues = [210, 160, 280, 30, 340, 200];
  const hue  = hues[name.charCodeAt(0) % hues.length];
  const cls  = size === "lg" ? "w-16 h-16 text-[18px]" : size === "sm" ? "w-7 h-7 text-[11px]" : "w-10 h-10 text-[13px]";
  return (
    <span
      className={`${cls} rounded-full flex items-center justify-center font-bold text-white shrink-0 select-none relative`}
      style={{ background: `hsl(${hue} 55% 52%)` }}
    >
      {initials}
      <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-white" />
    </span>
  );
}

const chats = [
  { name: "Dina Harrison",  preview: "Yay! I have a tons of stories...", time: "12:31", active: true  },
  { name: "John Shinoda",   preview: "Hey man, how R U???",               time: "08:30", active: false },
  { name: "Mandy Guoles",   preview: "Let me be alone, please...",         time: "16:43", active: false },
  { name: "Sam Pettersen",  preview: "Hey dude, where is my...",           time: "18:29", active: false },
];

const messages = [
  { from: "other", text: "Hey Travis, would U like to drink some coffee with me?)",              time: "20:21" },
  { from: "me",    text: "Sure! At 11:00 am?",                                                    time: "20:22" },
  { from: "other", text: "Emm, no. Maybe at 10? Cuz I have to finish my homework. My professor is jackass...", time: "20:24" },
];

const files = [
  { name: "PhotoDanver.jpg", date: "10.03.2021 · 11:43", size: "175 Kb" },
  { name: "PhotoDanver.jpg", date: "07.03.2021 · 10:23", size: "175 Kb" },
];

const links = [
  { domain: "Dribbble.com",  date: "10.12.2020", time: "10:32pm" },
  { domain: "Awwwards.com",  date: "10.12.2020", time: "10:32pm" },
];

export default function InboxPage() {
  return (
    <div className="flex w-full h-screen overflow-hidden text-gray-800 bg-white">

      {/* ── Left panel: profile + chat list ── */}
      <div className="w-[300px] border-r border-gray-100 flex flex-col shrink-0">

        {/* Vendor profile header */}
        <div className="px-6 pt-8 pb-5 border-b border-gray-100 flex flex-col items-center text-center">
          <Avatar name="Travis Taylor" size="lg" />
          <h2 className="mt-3 text-[15px] font-bold text-gray-900 tracking-tight">Travis Taylor</h2>
          <p className="text-[12px] text-gray-400 font-medium mt-0.5">Vendor · OmniClose</p>
        </div>

        {/* Search */}
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search chats"
              className="w-full bg-gray-50 rounded-xl pl-8 pr-3 py-2 text-[13px] font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 placeholder:text-gray-400 transition-all border-0"
            />
          </div>
        </div>

        {/* Chat list */}
        <div className="flex-1 overflow-y-auto py-1">
          <p className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.12em] px-5 py-3">Chats</p>
          {chats.map(c => (
            <div
              key={c.name}
              className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-gray-50 ${c.active ? "bg-gray-50" : ""}`}
            >
              <Avatar name={c.name} size="sm" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className={`text-[13px] font-semibold truncate ${c.active ? "text-gray-900" : "text-gray-700"}`}>{c.name}</span>
                  <span className={`text-[11px] font-medium shrink-0 ml-2 ${c.active ? "text-emerald-700" : "text-gray-400"}`}>{c.time}</span>
                </div>
                <p className={`text-[12px] truncate font-medium ${c.active ? "text-emerald-700" : "text-gray-400"}`}>{c.preview}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Center: chat window ── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Chat header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
          <div>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.1em] mb-0.5">Chat with</p>
            <h2 className="text-[16px] font-bold text-gray-900 tracking-tight">Dina Harrison</h2>
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <span className="text-[12px] font-medium">20 March 2026</span>
            <button className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors">
              <Bell size={15} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-5 bg-[#fafafa]">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col gap-1.5 ${m.from === "me" ? "items-end" : "items-start"}`}>
              <div
                className={`px-4 py-3 text-[14px] font-medium max-w-[70%] leading-relaxed shadow-sm ${
                  m.from === "me"
                    ? "bg-white text-gray-900 border border-emerald-700/30 rounded-2xl rounded-tr-sm"
                    : "bg-white text-gray-800 border border-gray-100 rounded-2xl rounded-tl-sm"
                }`}
              >
                {m.text}
              </div>
              <span className="text-[11px] text-gray-400 font-medium px-1">{m.time}</span>
            </div>
          ))}
        </div>

        {/* Input bar */}
        <div className="px-6 py-4 border-t border-gray-100 bg-white shrink-0">
          <div className="flex items-center gap-3">
            <Avatar name="Travis Taylor" size="sm" />
            <input
              type="text"
              placeholder="Type your message"
              className="flex-1 bg-transparent text-[13px] font-medium text-gray-800 focus:outline-none placeholder:text-gray-400 py-1"
            />
            <button className="text-gray-400 hover:text-gray-700 transition-colors p-1">
              <MoreHorizontal size={18} />
            </button>
            <button className="w-9 h-9 bg-gray-900 hover:bg-black text-white rounded-xl flex items-center justify-center transition-colors shadow-sm">
              <Send size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Right panel: contact detail ── */}
      <div className="w-[240px] border-l border-gray-100 flex flex-col items-center py-8 px-5 shrink-0 overflow-y-auto bg-white">
        <Avatar name="Dina Harrison" size="lg" />
        <h2 className="mt-3 text-[15px] font-bold text-gray-900 tracking-tight">Dina Harrison</h2>
        <p className="text-[12px] text-gray-400 font-medium mt-0.5">Customer</p>

        {/* Shared files */}
        <div className="w-full mt-8">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Shared Files</p>
            <button className="text-[11px] font-semibold text-[#09090b] hover:underline">see all</button>
          </div>
          <div className="space-y-3">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-2.5 group cursor-pointer">
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 group-hover:bg-gray-200 transition-colors">
                  <FileText size={14} className="text-gray-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold text-gray-800 truncate">{f.name}</p>
                  <p className="text-[10px] text-gray-400 font-medium">{f.date} · {f.size}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Shared links */}
        <div className="w-full mt-7">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Shared Links</p>
            <button className="text-[11px] font-semibold text-[#09090b] hover:underline">see all</button>
          </div>
          <div className="space-y-3">
            {links.map((l, i) => (
              <div key={i} className="flex items-center gap-2.5 group cursor-pointer">
                <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 group-hover:bg-gray-200 transition-colors">
                  <Link2 size={14} className="text-gray-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold text-gray-800 truncate">{l.domain}</p>
                  <p className="text-[10px] text-gray-400 font-medium">{l.date} · {l.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
