"use client";
import { useCallback, useEffect, useState } from "react";
import { Search, Trash2, FileText, Globe, MessageSquare, Loader2, Plus, X, Upload } from "lucide-react";
import {
  createBusinessInfo,
  deleteBusinessInfo,
  fetchBusinessInfo,
  getApiErrorMessage,
} from "@/lib/api";

type BusinessInfo = {
  id: number;
  title: string;
  content: string;
  source_type: string;
};

const TEXT_FILE_EXTS = [".txt", ".csv", ".md", ".markdown"];
const TEXT_FILE_MIMES = ["text/plain", "text/csv", "text/markdown"];

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
  const [items, setItems] = useState<BusinessInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newInfo, setNewInfo] = useState({ title: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const auth = useCallback(() => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return null;
    return { vendorId, token };
  }, []);

  const loadData = useCallback(async () => {
    const credentials = auth();
    if (!credentials) return;
    try {
      const businessInfo = await fetchBusinessInfo(credentials.vendorId, credentials.token);
      setItems(businessInfo);
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load business info"));
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleAdd() {
    if (!newInfo.title || !newInfo.content) return;
    const credentials = auth();
    if (!credentials) return;
    setSaving(true);
    try {
      await createBusinessInfo(credentials.vendorId, credentials.token, { ...newInfo, source_type: "TEXT" });
      setNewInfo({ title: "", content: "" });
      setShowAddModal(false);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save information"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this information? The AI will no longer be able to use it.")) return;
    const credentials = auth();
    if (!credentials) return;
    try {
      await deleteBusinessInfo(credentials.vendorId, credentials.token, id);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete information"));
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const lowerName = file.name.toLowerCase();
    const looksTextual =
      TEXT_FILE_MIMES.includes(file.type) ||
      TEXT_FILE_EXTS.some(ext => lowerName.endsWith(ext));

    if (!looksTextual) {
      setError("Only .txt, .csv, or .md files are supported here for now. For PDFs, paste the text content via Add information.");
      return;
    }

    const credentials = auth();
    if (!credentials) return;

    setUploading(true);
    try {
      const text = await file.text();
      const trimmed = text.trim();
      if (!trimmed) {
        setError("That file was empty.");
        return;
      }
      const title = file.name.replace(/\.[^.]+$/, "") || "Untitled";
      await createBusinessInfo(credentials.vendorId, credentials.token, {
        title,
        content: trimmed,
        source_type: "TEXT",
      });
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to upload file"));
    } finally {
      setUploading(false);
    }
  }

  const filteredItems = items.filter(item => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    return item.title.toLowerCase().includes(term) || item.content.toLowerCase().includes(term);
  });

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[860px] px-8 pt-10 pb-16 mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">AI Context</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Business Information</h1>
            {error && <p className="mt-2 text-[12px] font-bold text-red-600">{error}</p>}
          </div>
          <div className="flex items-center gap-2">
            <label className="bg-white border border-gray-100 text-gray-700 text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition-colors flex items-center gap-2 cursor-pointer shadow-sm">
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              Upload file
              <input
                type="file"
                accept=".txt,.csv,.md,.markdown,text/plain,text/csv,text/markdown"
                className="hidden"
                onChange={handleFileUpload}
                disabled={uploading}
              />
            </label>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-[#2B4DD0] hover:shadow-[#3B5EE4]/25 transition-colors flex items-center gap-2"
            >
              <Plus size={16} /> Add information
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="Search info..."
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30 focus:border-[#3B5EE4]/40 placeholder:text-gray-400 transition-all"
            />
          </div>
        </div>

        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-8 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Information Block</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Type</span>
          <span className="col-span-2 flex justify-end"></span>
        </div>

        <div className="space-y-0.5">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-[13px] text-gray-400 font-medium">No business information uploaded yet.</p>
            </div>
          ) : (
            filteredItems.map(item => (
              <div
                key={item.id}
                className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors group"
              >
                <div className="col-span-8 flex items-center gap-3 min-w-0">
                  <TopicIcon type={item.source_type} />
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-gray-900 leading-tight truncate">{item.title}</p>
                    <p className="text-[11px] text-gray-400 font-medium mt-0.5 truncate max-w-[420px]">{item.content}</p>
                  </div>
                </div>
                <div className="col-span-2">
                  <span className="text-[12px] font-medium text-gray-500">{item.source_type}</span>
                </div>
                <div className="col-span-2 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

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
                <label className="space-y-1.5 block">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Document Title</span>
                  <input
                    value={newInfo.title}
                    onChange={event => setNewInfo({ ...newInfo, title: event.target.value })}
                    placeholder="e.g. Shipping & Returns Policy"
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20"
                  />
                </label>
                <label className="space-y-1.5 block">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Information Content</span>
                  <textarea
                    value={newInfo.content}
                    onChange={event => setNewInfo({ ...newInfo, content: event.target.value })}
                    rows={6}
                    placeholder="Paste your business details here. The AI will read this to answer customer questions."
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/20 resize-none"
                  />
                </label>
              </div>
              <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-[13px] font-bold text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAdd}
                  disabled={saving}
                  className="bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white px-6 py-2 rounded-xl text-[13px] font-bold shadow-sm hover:bg-[#2B4DD0] hover:shadow-[#3B5EE4]/25 disabled:opacity-50 flex items-center gap-2"
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
