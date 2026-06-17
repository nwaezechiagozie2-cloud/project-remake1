"use client";

import { MessageCircle } from "lucide-react";

type Chat = {
  id: string;
  name: string;
  preview: string;
  time: string;
};

export default function DashboardPage() {
  const chats: Chat[] = [];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[780px] px-4 pt-6 pb-16 mx-auto md:px-8 md:pt-10">
        <div className="mb-6">
          <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">
            Inbox
          </p>
          <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">
            Recent chats
          </h1>
        </div>

        {chats.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <MessageCircle size={20} className="text-gray-400" />
            </div>
            <p className="text-[13px] font-semibold text-gray-700 mb-1">No chats yet</p>
            <p className="text-[12px] text-gray-400 max-w-xs leading-relaxed">
              New customer conversations will appear here once messages start coming in.
            </p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {chats.map(c => (
              <div
                key={c.id}
                className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[13px] font-semibold text-gray-900 truncate">{c.name}</p>
                    <p className="text-[11px] text-gray-400 font-medium shrink-0">{c.time}</p>
                  </div>
                  <p className="text-[12px] text-gray-500 truncate">{c.preview}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
