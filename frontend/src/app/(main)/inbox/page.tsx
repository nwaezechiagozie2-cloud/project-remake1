"use client";
import { useEffect, useState } from "react";
import { Search, MessageCircle, Send } from "lucide-react";

type Chat = {
  id: string;
  name: string;
  preview: string;
  time: string;
};

function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const initials = name.split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase();
  const hues = [210, 160, 280, 30, 340, 200];
  const hue = hues[(name.charCodeAt(0) || 0) % hues.length];
  const cls =
    size === "lg" ? "w-16 h-16 text-[18px]" : size === "sm" ? "w-7 h-7 text-[11px]" : "w-10 h-10 text-[13px]";
  return (
    <span
      className={`${cls} rounded-full flex items-center justify-center font-bold text-white shrink-0 select-none`}
      style={{ background: `hsl(${hue} 55% 52%)` }}
    >
      {initials || "?"}
    </span>
  );
}

export default function InboxPage() {
  const [chats] = useState<Chat[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [vendorName, setVendorName] = useState("Your store");

  useEffect(() => {
    const stored = localStorage.getItem("otc_vendor_name");
    if (stored) setVendorName(stored);
  }, []);

  const selectedChat = chats.find(c => c.id === selectedChatId) || null;

  return (
    <div className="flex w-full h-screen overflow-hidden text-gray-800 bg-white">

      {/* ── Left panel: vendor + chat list ── */}
      <div className="w-[300px] border-r border-gray-100 flex flex-col shrink-0">
        <div className="px-6 pt-8 pb-5 border-b border-gray-100 flex flex-col items-center text-center">
          <Avatar name={vendorName} size="lg" />
          <h2 className="mt-3 text-[15px] font-bold text-gray-900 tracking-tight truncate max-w-full">{vendorName}</h2>
          <p className="text-[12px] text-gray-400 font-medium mt-0.5">Owner</p>
        </div>

        <div className="px-4 py-3 border-b border-gray-100">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search chats"
              className="w-full bg-gray-50 rounded-xl pl-8 pr-3 py-2 text-[13px] font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30 placeholder:text-gray-400 transition-all border-0"
              disabled
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          <p className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.12em] px-5 py-3">Chats</p>
          {chats.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <p className="text-[12px] text-gray-400 font-medium leading-relaxed">
                No customer chats yet. New conversations from WhatsApp and Instagram will show up here.
              </p>
            </div>
          ) : (
            chats.map(c => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedChatId(c.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 ${
                  selectedChatId === c.id ? "bg-gray-50" : ""
                }`}
              >
                <Avatar name={c.name} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className={`text-[13px] font-semibold truncate ${selectedChatId === c.id ? "text-gray-900" : "text-gray-700"}`}>{c.name}</span>
                    <span className={`text-[11px] font-medium shrink-0 ml-2 ${selectedChatId === c.id ? "text-[#3B5EE4]" : "text-gray-400"}`}>{c.time}</span>
                  </div>
                  <p className={`text-[12px] truncate font-medium ${selectedChatId === c.id ? "text-[#3B5EE4]" : "text-gray-400"}`}>{c.preview}</p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Center: chat window ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedChat ? (
          <>
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between shrink-0">
              <div>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.1em] mb-0.5">Chat with</p>
                <h2 className="text-[16px] font-bold text-gray-900 tracking-tight">{selectedChat.name}</h2>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-8 py-6 bg-[#fafafa] flex items-center justify-center">
              <p className="text-[12px] text-gray-400 font-medium">No messages loaded yet.</p>
            </div>

            <div className="px-6 py-4 border-t border-gray-100 bg-white shrink-0">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  placeholder="Type your message"
                  className="flex-1 bg-transparent text-[13px] font-medium text-gray-800 focus:outline-none placeholder:text-gray-400 py-1"
                  disabled
                />
                <button
                  type="button"
                  disabled
                  className="w-9 h-9 bg-gray-200 text-gray-400 rounded-xl flex items-center justify-center cursor-not-allowed"
                >
                  <Send size={15} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center bg-[#fafafa] px-8 text-center">
            <div className="w-14 h-14 rounded-full bg-white border border-gray-100 flex items-center justify-center mb-5 shadow-sm">
              <MessageCircle size={22} className="text-gray-300" />
            </div>
            <p className="text-[14px] font-bold text-gray-700 mb-1.5">No chat selected</p>
            <p className="text-[12.5px] text-gray-400 font-medium max-w-xs leading-relaxed">
              Customer conversations from WhatsApp and Instagram will appear here once messages start coming in.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
