"use client";
import { useEffect, useState } from "react";
import { Search, SlidersHorizontal, Trash2, FileText, Globe, MessageSquare, Loader2, Plus, X } from "lucide-react";
import { fetchBusinessInfo, createBusinessInfo, deleteBusinessInfo } from "@/lib/api";

function TopicIcon({ type }: { type: string }) {
  let hue = 210;
  let Icon = FileText;
  
  if (type === "TEXT") {
    hue = 160; 
    Icon = MessageSquare;
  } else if (type === "PDF") {
    hue = 280;
    Icon = FileText;
  } else {
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
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newInfo, setNewInfo] = useState({ title: "", content: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      const data = await fetchBusinessInfo(vendorId, token);
      setItems(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newInfo.title || !newInfo.content) return;
    setSaving(true);
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      await createBusinessInfo(vendorId, token, { ...newInfo, source_type: "TEXT" });
      setNewInfo({ title: "", content: "" });
      setShowAddModal(false);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this information? The AI will no longer be able to use it.")) return;
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      await deleteBusinessInfo(vendorId, token, id);
      await loadData();
    } catch (err) {
      console.error(err);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">

        {/* Title row */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">AI Context</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Business Information</h1>
          </div>
          <button 
            onClick={() => setShowAddModal(true)}
            className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <Plus size={16} /> Add Information
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search info…"
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:border-[#059669]/40 placeholder:text-gray-400 transition-all"
            />
          </div>
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-8 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Information Block</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Type</span>
          <span className="col-span-2 flex justify-end"></span>
        </div>

        {/* Context rows */}
        <div className="space-y-0.5">
          {items.length === 0 ? (
             <div className="py-12 text-center">
                <p className="text-[13px] text-gray-400 font-medium">No business information uploaded yet.</p>
             </div>
          ) : (
            items.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors group"
              >
                <div className="col-span-8 flex items-center gap-3">
                  <TopicIcon type={item.source_type} />
                  <div>
                    <p className="text-[13px] font-semibold text-gray-900 leading-tight">{item.title}</p>
                    <p className="text-[11px] text-gray-400 font-medium mt-0.5 truncate max-w-[300px]">{item.content}</p>
                  </div>
                </div>
                <div className="col-span-2">
                  <span className="text-[12px] font-medium text-gray-500">{item.source_type}</span>
                </div>
                <div className="col-span-2 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => handleDelete(item.id)}
                    className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors" title="Delete">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Add Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-6">
             <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-50 flex items-center justify-between">
                   <h2 className="text-[16px] font-bold text-gray-900">Add Business Information</h2>
                   <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                      <X size={20} />
                   </button>
                </div>
                <div className="p-6 space-y-4">
                   <div className="space-y-1.5">
                      <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Document Title</label>
                      <input 
                        value={newInfo.title}
                        onChange={e => setNewInfo({...newInfo, title: e.target.value})}
                        placeholder="e.g. Shipping & Returns Policy"
                        className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
                      />
                   </div>
                   <div className="space-y-1.5">
                      <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Information Content</label>
                      <textarea 
                        value={newInfo.content}
                        onChange={e => setNewInfo({...newInfo, content: e.target.value})}
                        rows={6}
                        placeholder="Paste your business details here. The AI will read this to answer customer questions."
                        className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20 resize-none"
                      />
                   </div>
                </div>
                <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
                   <button 
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 text-[13px] font-bold text-gray-500 hover:text-gray-700">Cancel</button>
                   <button 
                    onClick={handleAdd}
                    disabled={saving}
                    className="bg-[#059669] text-white px-6 py-2 rounded-xl text-[13px] font-bold shadow-sm hover:bg-[#047857] disabled:opacity-50 flex items-center gap-2"
                   >
                      {saving && <Loader2 size={14} className="animate-spin" />}
                      Save Information
                   </button>
                </div>
             </div>
          </div>
        )}

      </div>
    </div>
  );
}
