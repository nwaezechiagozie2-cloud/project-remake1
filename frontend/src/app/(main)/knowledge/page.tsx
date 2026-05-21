"use client";
import { useCallback, useEffect, useState } from "react";
import { Search, Trash2, FileText, Globe, MessageSquare, Loader2, Plus, X, Upload, PackageCheck } from "lucide-react";
import {
  createBusinessInfo,
  deleteBusinessInfo,
  fetchBusinessInfo,
  fetchCatalogueImportItems,
  fetchCatalogueUploads,
  getApiErrorMessage,
  importCatalogueItems,
  uploadCatalogue,
} from "@/lib/api";

type BusinessInfo = {
  id: number;
  title: string;
  content: string;
  source_type: string;
};

type CatalogueUpload = {
  id: number;
  file_name: string;
  status: string;
  error_message?: string | null;
  created_at: string;
};

type CatalogueItem = {
  id: number;
  upload_id: number;
  name: string;
  description?: string | null;
  price: number | null;
  currency: string;
  in_stock: boolean;
  raw_text?: string | null;
  status: string;
  product_id?: number | null;
};

function TopicIcon({ type }: { type: string }) {
  let hue = 210;
  let Icon = FileText;

  if (type === "TEXT") {
    hue = 160;
    Icon = MessageSquare;
  } else if (type === "PDF" || type === "CATALOGUE") {
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

function fileToBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",", 2)[1] : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function KnowledgePage() {
  const [items, setItems] = useState<BusinessInfo[]>([]);
  const [uploads, setUploads] = useState<CatalogueUpload[]>([]);
  const [draftItems, setDraftItems] = useState<CatalogueItem[]>([]);
  const [selectedDraftIds, setSelectedDraftIds] = useState<Set<number>>(new Set());
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newInfo, setNewInfo] = useState({ title: "", content: "" });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const auth = useCallback(async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return null;
    return { vendorId, token };
  }, []);

  const loadData = useCallback(async () => {
    try {
      const credentials = await auth();
      if (!credentials) return;
      const [businessInfo, catalogueUploads] = await Promise.all([
        fetchBusinessInfo(credentials.vendorId, credentials.token),
        fetchCatalogueUploads(credentials.vendorId, credentials.token),
      ]);
      setItems(businessInfo);
      setUploads(catalogueUploads);
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load knowledge data"));
    } finally {
      setLoading(false);
    }
  }, [auth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleAdd() {
    if (!newInfo.title || !newInfo.content) return;
    setSaving(true);
    try {
      const credentials = await auth();
      if (!credentials) return;
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
    try {
      const credentials = await auth();
      if (!credentials) return;
      await deleteBusinessInfo(credentials.vendorId, credentials.token, id);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete information"));
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setUploading(true);
    try {
      const credentials = await auth();
      if (!credentials) return;
      const contentBase64 = await fileToBase64(file);
      const upload = await uploadCatalogue(credentials.vendorId, credentials.token, {
        file_name: file.name,
        mime_type: file.type || "text/plain",
        content_base64: contentBase64,
      });
      await loadData();
      await selectUpload(upload.id);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to upload catalogue"));
    } finally {
      setUploading(false);
    }
  }

  async function selectUpload(uploadId: number) {
    try {
      const credentials = await auth();
      if (!credentials) return;
      setSelectedUploadId(uploadId);
      const data = await fetchCatalogueImportItems(credentials.vendorId, credentials.token, uploadId);
      setDraftItems(data);
      setSelectedDraftIds(new Set(data.filter((item: CatalogueItem) => !item.product_id).map((item: CatalogueItem) => item.id)));
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load catalogue items"));
    }
  }

  function updateDraftItem(itemId: number, patch: Partial<CatalogueItem>) {
    setDraftItems(current => current.map(item => (item.id === itemId ? { ...item, ...patch } : item)));
  }

  function toggleDraftSelection(itemId: number) {
    setSelectedDraftIds(current => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  function toggleAllDrafts() {
    const importableIds = draftItems.filter(item => !item.product_id).map(item => item.id);
    setSelectedDraftIds(current => {
      if (importableIds.every(id => current.has(id))) return new Set();
      return new Set(importableIds);
    });
  }

  async function handleImportSelected() {
    try {
      const credentials = await auth();
      if (!credentials) return;
      const selectedItems = draftItems.filter(item => selectedDraftIds.has(item.id) && !item.product_id);
      if (selectedItems.length === 0) return;

      const invalidItem = selectedItems.find(item => !item.name.trim() || item.price === null || Number.isNaN(Number(item.price)) || Number(item.price) <= 0);
      if (invalidItem) {
        setError("Every selected product needs a name and valid price before import.");
        return;
      }

      setImporting(true);
      await importCatalogueItems(credentials.vendorId, credentials.token, selectedItems.map(item => ({
        id: item.id,
        name: item.name.trim(),
        description: item.description || null,
        price: Number(item.price),
        currency: item.currency || "NGN",
        in_stock: item.in_stock,
      })));
      if (selectedUploadId) await selectUpload(selectedUploadId);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to import catalogue items"));
    } finally {
      setImporting(false);
    }
  }

  const filteredItems = items.filter(item => {
    const term = search.trim().toLowerCase();
    if (!term) return true;
    return item.title.toLowerCase().includes(term) || item.content.toLowerCase().includes(term);
  });
  const importableDrafts = draftItems.filter(item => !item.product_id);
  const selectedDrafts = draftItems.filter(item => selectedDraftIds.has(item.id) && !item.product_id);
  const allDraftsSelected = importableDrafts.length > 0 && importableDrafts.every(item => selectedDraftIds.has(item.id));

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
              Upload catalogue
              <input
                type="file"
                accept=".txt,.csv,.pdf,.doc,.docx,text/plain,text/csv,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-[#047857] transition-colors flex items-center gap-2"
            >
              <Plus size={16} /> Add information
            </button>
          </div>
        </div>

        <section className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[14px] font-bold text-gray-900">Catalogue uploads</h2>
            <p className="text-[12px] font-medium text-gray-400">Review parsed draft products before importing.</p>
          </div>

          {uploads.length === 0 ? (
            <div className="py-8 text-center border border-gray-100 rounded-2xl bg-gray-50/40">
              <p className="text-[13px] text-gray-400 font-medium">No catalogue files uploaded yet.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {uploads.map(upload => (
                <button
                  type="button"
                  key={upload.id}
                  onClick={() => selectUpload(upload.id)}
                  className={`w-full grid grid-cols-12 items-center px-3 py-3 rounded-xl text-left transition-colors border ${
                    selectedUploadId === upload.id ? "border-emerald-700/30 bg-emerald-50/40" : "border-transparent hover:bg-gray-50"
                  }`}
                >
                  <div className="col-span-7 flex items-center gap-3 min-w-0">
                    <TopicIcon type="CATALOGUE" />
                    <div className="min-w-0">
                      <p className="text-[13px] font-semibold text-gray-900 truncate">{upload.file_name}</p>
                      <p className="text-[11px] text-gray-400 font-medium">{new Date(upload.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <div className="col-span-3">
                    <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">{upload.status}</span>
                  </div>
                  <div className="col-span-2 text-right">
                    <span className="text-[12px] font-bold text-gray-700">Review</span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {selectedUploadId && (
            <div className="mt-5 border border-gray-100 rounded-2xl overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/60 flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-bold text-gray-900">Parsed draft products</p>
                  <p className="text-[11px] font-bold text-gray-400">{selectedDrafts.length} of {importableDrafts.length} importable selected</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={toggleAllDrafts}
                    disabled={importableDrafts.length === 0}
                    className="text-[12px] font-bold px-3 py-2 rounded-lg border border-gray-200 text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-white"
                  >
                    {allDraftsSelected ? "Unselect all" : "Select all"}
                  </button>
                  <button
                    type="button"
                    onClick={handleImportSelected}
                    disabled={importing || selectedDrafts.length === 0}
                    className="text-[12px] font-bold px-3 py-2 rounded-lg bg-gray-900 text-white disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center gap-1.5"
                  >
                    {importing ? <Loader2 size={13} className="animate-spin" /> : <PackageCheck size={13} />}
                    Import selected
                  </button>
                </div>
              </div>
              {draftItems.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-[13px] text-gray-400 font-medium">No product candidates were parsed from this upload.</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {draftItems.map(item => (
                    <div key={item.id} className="grid grid-cols-12 items-center px-4 py-3">
                      <div className="col-span-1">
                        <input
                          type="checkbox"
                          checked={selectedDraftIds.has(item.id)}
                          onChange={() => toggleDraftSelection(item.id)}
                          disabled={Boolean(item.product_id)}
                          className="h-4 w-4 accent-[#059669] disabled:opacity-40"
                          aria-label={`Select ${item.name}`}
                        />
                      </div>
                      <div className="col-span-5 min-w-0 pr-3">
                        <input
                          value={item.name}
                          onChange={event => updateDraftItem(item.id, { name: event.target.value })}
                          disabled={Boolean(item.product_id)}
                          className="w-full bg-transparent border border-transparent rounded-lg px-2 py-1 text-[13px] font-semibold text-gray-900 truncate focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                          title="Double-click or focus to edit product name"
                        />
                        <p className="text-[11px] text-gray-400 font-medium truncate">{item.raw_text || "No raw text"}</p>
                      </div>
                      <div className="col-span-2 flex items-center justify-end gap-1">
                        <input
                          value={item.currency}
                          onChange={event => updateDraftItem(item.id, { currency: event.target.value.toUpperCase().slice(0, 3) })}
                          disabled={Boolean(item.product_id)}
                          className="w-12 bg-transparent border border-transparent rounded-lg px-1 py-1 text-right text-[12px] font-bold font-mono text-gray-700 focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                          title="Double-click or focus to edit currency"
                        />
                        <input
                          type="number"
                          value={item.price ?? ""}
                          onChange={event => updateDraftItem(item.id, { price: event.target.value === "" ? null : Number(event.target.value) })}
                          disabled={Boolean(item.product_id)}
                          className="w-24 bg-transparent border border-transparent rounded-lg px-1 py-1 text-right text-[12px] font-bold font-mono text-gray-900 focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                          placeholder="No price"
                          title="Double-click or focus to edit price"
                        />
                      </div>
                      <div className="col-span-2 text-center">
                        <span className={`text-[11px] font-bold px-2 py-1 rounded-full ${item.in_stock ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
                          {item.product_id ? "IMPORTED" : item.status}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <input
                          value={item.description || ""}
                          onChange={event => updateDraftItem(item.id, { description: event.target.value })}
                          disabled={Boolean(item.product_id)}
                          className="w-full bg-transparent border border-transparent rounded-lg px-2 py-1 text-[12px] font-medium text-gray-500 truncate focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                          placeholder="Description"
                          title="Double-click or focus to edit description"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        <div className="flex items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="Search info..."
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:border-[#059669]/40 placeholder:text-gray-400 transition-all"
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
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
                  />
                </label>
                <label className="space-y-1.5 block">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Information Content</span>
                  <textarea
                    value={newInfo.content}
                    onChange={event => setNewInfo({ ...newInfo, content: event.target.value })}
                    rows={6}
                    placeholder="Paste your business details here. The AI will read this to answer customer questions."
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20 resize-none"
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
