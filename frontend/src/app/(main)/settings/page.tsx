"use client";
import { useState } from "react";
import { MessageSquare, Shield, Key, Check, Copy, UserPlus, HelpCircle, ArrowUpRight } from "lucide-react";

export default function SettingsPage() {
  const [copied, setCopied] = useState(false);

  const copyWebhook = () => {
    navigator.clipboard.writeText("https://api.onetapcloser.com/webhook");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleGoogleConnect = () => {
    // Navigate to the backend google auth flow
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/auth/google?vendor_id=${localStorage.getItem("otc_vendor_id")}`;
  };

  return (
    <div className="flex-1 overflow-y-auto bg-white selection:bg-[#059669]/10 selection:text-[#059669]">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">
        
        {/* Header */}
        <div className="mb-12">
          <p className="text-[11px] font-bold tracking-[0.12em] uppercase text-gray-400 mb-1">Configuration</p>
          <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">Settings</h1>
        </div>

        <div className="space-y-12">
          
          {/* Section: WhatsApp Connectivity */}
          <section className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                  <MessageSquare size={16} className="text-emerald-500" />
                </div>
                <h2 className="text-[14px] font-bold text-gray-900">WhatsApp Integration</h2>
              </div>
              <a 
                href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started" 
                target="_blank" 
                className="text-[11px] font-bold text-gray-400 hover:text-gray-900 flex items-center gap-1 transition-colors"
              >
                Setup Guide <ArrowUpRight size={12} />
              </a>
            </div>

            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.05em]">WhatsApp Number</label>
                    <div className="group relative">
                      <HelpCircle size={10} className="text-gray-300" />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-[#059669] text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 font-medium">
                        Enter your registered WhatsApp Business number including the + and country code.
                      </div>
                    </div>
                  </div>
                  <input 
                    type="text" 
                    placeholder="+234..." 
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:bg-white transition-all"
                  />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <label className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.05em]">Phone Number ID</label>
                    <div className="group relative">
                      <HelpCircle size={10} className="text-gray-300" />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-[#059669] text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 font-medium">
                        Found in your Meta App Dashboard under WhatsApp &gt; API Setup.
                      </div>
                    </div>
                  </div>
                  <input 
                    type="text" 
                    placeholder="Meta ID" 
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:bg-white transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                   <label className="text-[11px] font-bold text-gray-400 uppercase tracking-[0.05em]">Permanent Access Token</label>
                   <div className="group relative">
                      <HelpCircle size={10} className="text-gray-300" />
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-[#059669] text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 font-medium">
                        Generated in Meta Business Suite. This never expires and allows the bot to send messages.
                      </div>
                    </div>
                </div>
                <div className="relative">
                  <input 
                    type="password" 
                    placeholder="EAAx..." 
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium pr-10 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:bg-white transition-all"
                  />
                  <Key size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400" />
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-3 mt-4">
                <div className="flex items-center justify-between">
                  <p className="text-[12px] font-bold text-gray-700">Webhook URL</p>
                  <button 
                    onClick={copyWebhook}
                    className="flex items-center gap-1.5 text-[11px] font-bold text-[#09090b] hover:bg-white px-2 py-1 rounded-lg transition-colors"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    {copied ? "Copied" : "Copy URL"}
                  </button>
                </div>
                <p className="text-[12px] text-gray-500 leading-relaxed">
                  Paste this URL into your Meta App dashboard under <span className="text-gray-900 font-semibold">WhatsApp &gt; Configuration</span>.
                </p>
                <code className="block w-full bg-white border border-gray-100 p-2.5 rounded-lg text-[13px] font-mono text-gray-400 truncate">
                  https://api.onetapcloser.com/webhook
                </code>
              </div>

              <div className="pt-4 flex justify-end">
                <button className="bg-[#059669] text-white px-6 py-2.5 rounded-xl text-[13px] font-bold hover:bg-[#047857] transition-colors shadow-sm">
                  Save Changes
                </button>
              </div>
            </div>
          </section>

          {/* Section: Google Integration */}
          <section className="space-y-6 pt-6 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                <UserPlus size={16} className="text-red-600" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Contact Integration</h2>
            </div>
            
            <div className="p-5 bg-gray-50/50 border border-gray-100 rounded-2xl flex items-center justify-between">
              <div className="space-y-1">
                 <p className="text-[13px] font-bold text-gray-900">Google Contacts</p>
                 <p className="text-[12px] text-gray-400 font-medium">Sync new WhatsApp customers to your Google account automatically.</p>
              </div>
              <button 
                onClick={handleGoogleConnect}
                className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-5 py-2 rounded-xl hover:bg-gray-50 transition-colors shadow-sm flex items-center gap-2"
              >
                <img src="https://www.google.com/favicon.ico" className="w-3.5 h-3.5" alt="Google" />
                Connect Google
              </button>
            </div>
          </section>

          {/* Section: Bot Behavior */}
          <section className="space-y-6 pt-6 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <Shield size={16} className="text-[#09090b]" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Bot Settings</h2>
            </div>
            
            <div className="space-y-4">
               {[
                 { label: "AI Knowledge Answers", desc: "Allow the bot to answer general business questions.", enabled: true },
                 { label: "Auto-share Account Details", desc: "Send payment info as soon as purchase intent is detected.", enabled: false },
                 { label: "Product Q&A", desc: "Allow bot to answer specific product-related inquiries.", enabled: true }
               ].map(item => (
                 <div key={item.label} className="flex items-start justify-between p-4 bg-white border border-gray-100 rounded-2xl hover:bg-gray-50 transition-colors cursor-pointer group">
                    <div className="space-y-1">
                       <p className="text-[13px] font-bold text-gray-900">{item.label}</p>
                       <p className="text-[12px] text-gray-400 font-medium">{item.desc}</p>
                    </div>
                    <div className={`w-10 h-6 rounded-full transition-colors relative flex items-center px-1 ${item.enabled ? 'bg-[#059669]' : 'bg-gray-200'}`}>
                       <div className={`w-4 h-4 bg-white rounded-full transition-transform ${item.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </div>
                 </div>
               ))}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
