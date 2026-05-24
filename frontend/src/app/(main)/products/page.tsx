"use client";
import { useCallback, useEffect, useState } from "react";
import { Search, Trash2, Loader2, Plus, X, Pencil, ToggleLeft, ToggleRight, Upload, FileText, PackageCheck, ClipboardPaste } from "lucide-react";
import {
  createProduct,
  deleteProduct,
  fetchCatalogueImportItems,
  fetchCatalogueUploads,
  fetchVendorProducts,
  getApiErrorMessage,
  importCatalogueItems,
  updateProduct,
  updateProductAvailability,
  uploadCatalogue,
  type ProductPayload,
} from "@/lib/api";

type Product = {
  id: number;
  name: string;
  price: number;
  description?: string | null;
  extra_details?: string | null;
  currency: string;
  image_url?: string | null;
  video_url?: string | null;
  in_stock: boolean;
};

type ProductForm = {
  name: string;
  price: string;
  description: string;
  extra_details: string;
  currency: string;
  image_url: string;
  video_url: string;
  in_stock: boolean;
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

const emptyForm: ProductForm = {
  name: "",
  price: "",
  description: "",
  extra_details: "",
  currency: "NGN",
  image_url: "",
  video_url: "",
  in_stock: true,
};

const statusStyle: Record<string, string> = {
  "In Stock": "text-emerald-500 bg-emerald-50",
  "Out of Stock": "text-red-700 bg-red-50",
};

function ProductInitial({ name }: { name: string }) {
  const letter = name ? name[0].toUpperCase() : "?";
  const hues = [30, 210, 160, 280, 200];
  const hue = hues[name.charCodeAt(0) % hues.length];
  return (
    <span
      className="w-8 h-8 rounded-xl flex items-center justify-center text-[13px] font-bold text-white shrink-0 select-none"
      style={{ background: `hsl(${hue} 55% 55%)` }}
    >
      {letter}
    </span>
  );
}

function toPayload(form: ProductForm): ProductPayload {
  return {
    name: form.name.trim(),
    price: Number.parseFloat(form.price),
    description: form.description.trim() || null,
    extra_details: form.extra_details.trim() || null,
    currency: form.currency.trim().toUpperCase() || "NGN",
    image_url: form.image_url.trim() || null,
    video_url: form.video_url.trim() || null,
    in_stock: form.in_stock,
  };
}

function formFromProduct(product: Product): ProductForm {
  return {
    name: product.name,
    price: String(product.price),
    description: product.description || "",
    extra_details: product.extra_details || "",
    currency: product.currency || "NGN",
    image_url: product.image_url || "",
    video_url: product.video_url || "",
    in_stock: product.in_stock,
  };
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

function textToBase64(text: string) {
  if (typeof window === "undefined") return "";
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return window.btoa(binary);
}

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState<"all" | "in" | "out">("all");
  const [error, setError] = useState("");

  const [uploads, setUploads] = useState<CatalogueUpload[]>([]);
  const [draftItems, setDraftItems] = useState<CatalogueItem[]>([]);
  const [selectedDraftIds, setSelectedDraftIds] = useState<Set<number>>(new Set());
  const [selectedUploadId, setSelectedUploadId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pasteName, setPasteName] = useState("");

  const auth = useCallback(() => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return null;
    return { vendorId, token };
  }, []);

  const loadProducts = useCallback(async () => {
    const credentials = auth();
    if (!credentials) return;
    try {
      const data = await fetchVendorProducts(credentials.vendorId, credentials.token, {
        search: search.trim() || undefined,
        in_stock: stockFilter === "all" ? undefined : stockFilter === "in",
      });
      setItems(data.items || []);
      setError("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load products"));
    } finally {
      setLoading(false);
    }
  }, [auth, search, stockFilter]);

  const loadUploads = useCallback(async () => {
    const credentials = auth();
    if (!credentials) return;
    try {
      const data = await fetchCatalogueUploads(credentials.vendorId, credentials.token);
      setUploads(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to load catalogue uploads"));
    }
  }, [auth]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      loadProducts();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [loadProducts]);

  useEffect(() => {
    loadUploads();
  }, [loadUploads]);

  const openCreate = () => {
    setEditingProduct(null);
    setForm(emptyForm);
    setShowModal(true);
  };

  const openEdit = (product: Product) => {
    setEditingProduct(product);
    setForm(formFromProduct(product));
    setShowModal(true);
  };

  async function handleSave() {
    if (!form.name.trim() || !form.price) return;
    setSaving(true);
    try {
      const credentials = auth();
      if (!credentials) return;
      const payload = toPayload(form);
      if (editingProduct) {
        await updateProduct(credentials.vendorId, credentials.token, editingProduct.id, payload);
      } else {
        await createProduct(credentials.vendorId, credentials.token, payload);
      }
      setShowModal(false);
      await loadProducts();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save product"));
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleAvailability(product: Product) {
    const credentials = auth();
    if (!credentials) return;
    setItems(items.map(item => item.id === product.id ? { ...item, in_stock: !item.in_stock } : item));
    try {
      await updateProductAvailability(credentials.vendorId, credentials.token, product.id, !product.in_stock);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update availability"));
      await loadProducts();
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this product?")) return;
    const credentials = auth();
    if (!credentials) return;
    try {
      await deleteProduct(credentials.vendorId, credentials.token, id);
      await loadProducts();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete product"));
    }
  }

  async function handleCatalogueFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const credentials = auth();
    if (!credentials) return;

    setUploading(true);
    try {
      const contentBase64 = await fileToBase64(file);
      const upload = await uploadCatalogue(credentials.vendorId, credentials.token, {
        file_name: file.name,
        mime_type: file.type || "text/plain",
        content_base64: contentBase64,
      });
      await loadUploads();
      await selectUpload(upload.id);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to upload catalogue"));
    } finally {
      setUploading(false);
    }
  }

  async function handlePasteSubmit() {
    const trimmed = pasteText.trim();
    if (!trimmed) return;
    const credentials = auth();
    if (!credentials) return;

    setUploading(true);
    try {
      const contentBase64 = textToBase64(pasteText);
      const fileName = pasteName.trim() || `pasted-catalogue-${new Date().toISOString().slice(0, 10)}.txt`;
      const upload = await uploadCatalogue(credentials.vendorId, credentials.token, {
        file_name: fileName,
        mime_type: "text/plain",
        content_base64: contentBase64,
      });
      setShowPasteModal(false);
      setPasteText("");
      setPasteName("");
      await loadUploads();
      await selectUpload(upload.id);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to submit catalogue text"));
    } finally {
      setUploading(false);
    }
  }

  async function selectUpload(uploadId: number) {
    const credentials = auth();
    if (!credentials) return;
    try {
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
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
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
    const credentials = auth();
    if (!credentials) return;
    try {
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
      await loadProducts();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to import catalogue items"));
    } finally {
      setImporting(false);
    }
  }

  const importableDrafts = draftItems.filter(item => !item.product_id);
  const selectedDrafts = draftItems.filter(item => selectedDraftIds.has(item.id) && !item.product_id);
  const allDraftsSelected = importableDrafts.length > 0 && importableDrafts.every(item => selectedDraftIds.has(item.id));

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[860px] px-8 pt-10 pb-16 mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">Catalog</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Products</h1>
            {error && <p className="mt-2 text-[12px] font-bold text-red-600">{error}</p>}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPasteModal(true)}
              className="bg-white border border-gray-100 text-gray-700 text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition-colors flex items-center gap-2 shadow-sm"
            >
              <ClipboardPaste size={16} /> Paste catalogue
            </button>
            <label className="bg-white border border-gray-100 text-gray-700 text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition-colors flex items-center gap-2 cursor-pointer shadow-sm">
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              Upload catalogue
              <input
                type="file"
                accept=".txt,.csv,.pdf,.doc,.docx,text/plain,text/csv,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={handleCatalogueFile}
                disabled={uploading}
              />
            </label>
            <button
              onClick={openCreate}
              className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-[#047857] transition-colors flex items-center gap-2"
            >
              <Plus size={16} /> Add product
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
              <p className="text-[13px] text-gray-400 font-medium">No catalogue files or pasted text yet.</p>
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
                    <span className="w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm" style={{ background: "hsl(280 55% 55%)" }}>
                      <FileText size={14} strokeWidth={2.5} />
                    </span>
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
                        />
                        <p className="text-[11px] text-gray-400 font-medium truncate">{item.raw_text || "No raw text"}</p>
                      </div>
                      <div className="col-span-2 flex items-center justify-end gap-1">
                        <input
                          value={item.currency}
                          onChange={event => updateDraftItem(item.id, { currency: event.target.value.toUpperCase().slice(0, 3) })}
                          disabled={Boolean(item.product_id)}
                          className="w-12 bg-transparent border border-transparent rounded-lg px-1 py-1 text-right text-[12px] font-bold font-mono text-gray-700 focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                        />
                        <input
                          type="number"
                          value={item.price ?? ""}
                          onChange={event => updateDraftItem(item.id, { price: event.target.value === "" ? null : Number(event.target.value) })}
                          disabled={Boolean(item.product_id)}
                          className="w-24 bg-transparent border border-transparent rounded-lg px-1 py-1 text-right text-[12px] font-bold font-mono text-gray-900 focus:bg-white focus:border-emerald-200 focus:outline-none disabled:text-gray-400"
                          placeholder="No price"
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
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        <div className="flex flex-wrap items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={event => setSearch(event.target.value)}
              placeholder="Search products..."
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:border-[#059669]/40 placeholder:text-gray-400 transition-all"
            />
          </div>
          {(["all", "in", "out"] as const).map(value => (
            <button
              key={value}
              type="button"
              onClick={() => setStockFilter(value)}
              className={`px-3 py-2 rounded-xl text-[12px] font-bold border transition-colors ${
                stockFilter === value ? "border-emerald-700/30 bg-emerald-50 text-emerald-700" : "border-gray-100 text-gray-500 hover:bg-gray-50"
              }`}
            >
              {value === "all" ? "All" : value === "in" ? "In stock" : "Out"}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-5 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Product</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-right">Price</span>
          <span className="col-span-3 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-center">Availability</span>
          <span className="col-span-2"></span>
        </div>

        {loading ? (
          <div className="py-12 flex justify-center">
            <Loader2 className="animate-spin text-gray-400" size={28} />
          </div>
        ) : (
          <div className="space-y-0.5">
            {items.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-[13px] text-gray-400 font-medium">No products in your catalog.</p>
              </div>
            ) : (
              items.map(product => (
                <div
                  key={product.id}
                  className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <div className="col-span-5 flex items-center gap-3 min-w-0">
                    <ProductInitial name={product.name} />
                    <div className="min-w-0">
                      <p className="text-[13px] font-semibold text-gray-900 leading-tight truncate">{product.name}</p>
                      <p className="text-[11px] text-gray-400 font-medium mt-0.5 truncate">{product.description || "No description"}</p>
                    </div>
                  </div>
                  <div className="col-span-2 text-right">
                    <span className="text-[13px] font-bold font-mono text-gray-900">
                      {product.currency} {product.price.toLocaleString()}
                    </span>
                  </div>
                  <div className="col-span-3 flex justify-center">
                    <button
                      type="button"
                      onClick={() => handleToggleAvailability(product)}
                      className={`text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 ${product.in_stock ? statusStyle["In Stock"] : statusStyle["Out of Stock"]}`}
                    >
                      {product.in_stock ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                      {product.in_stock ? "In Stock" : "Out of Stock"}
                    </button>
                  </div>
                  <div className="col-span-2 flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEdit(product)}
                      className="text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                      title="Edit"
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(product.id)}
                      className="text-gray-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                      title="Delete"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {showModal && (
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-6">
            <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-50 flex items-center justify-between">
                <h2 className="text-[16px] font-bold text-gray-900">{editingProduct ? "Edit Product" : "Add New Product"}</h2>
                <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={20} />
                </button>
              </div>
              <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Product Name" value={form.name} onChange={value => setForm({ ...form, name: value })} placeholder="e.g. Leather Bag" />
                  <Field label="Price" type="number" value={form.price} onChange={value => setForm({ ...form, price: value })} placeholder="15000" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Currency" value={form.currency} onChange={value => setForm({ ...form, currency: value.toUpperCase().slice(0, 3) })} placeholder="NGN" />
                  <label className="space-y-1.5">
                    <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Availability</span>
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, in_stock: !form.in_stock })}
                      className={`w-full px-4 py-2.5 rounded-xl text-[13px] font-bold text-left ${form.in_stock ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}
                    >
                      {form.in_stock ? "In Stock" : "Out of Stock"}
                    </button>
                  </label>
                </div>
                <Field label="Short Description" value={form.description} onChange={value => setForm({ ...form, description: value })} placeholder="What is this product?" />
                <label className="space-y-1.5 block">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">AI Context / Extra Details</span>
                  <textarea
                    value={form.extra_details}
                    onChange={event => setForm({ ...form, extra_details: event.target.value })}
                    rows={3}
                    placeholder="Materials, sizes, or anything the AI should know."
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20 resize-none"
                  />
                </label>
                <Field label="Image URL" value={form.image_url} onChange={value => setForm({ ...form, image_url: value })} placeholder="https://..." />
                <Field label="Video URL" value={form.video_url} onChange={value => setForm({ ...form, video_url: value })} placeholder="https://..." />
              </div>
              <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
                <button onClick={() => setShowModal(false)} className="px-4 py-2 text-[13px] font-bold text-gray-500 hover:text-gray-700">Cancel</button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-[#059669] text-white px-6 py-2 rounded-xl text-[13px] font-bold shadow-sm hover:bg-[#047857] disabled:opacity-50 flex items-center gap-2"
                >
                  {saving && <Loader2 size={14} className="animate-spin" />}
                  {editingProduct ? "Save Changes" : "Add to Catalog"}
                </button>
              </div>
            </div>
          </div>
        )}

        {showPasteModal && (
          <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-6">
            <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-50 flex items-center justify-between">
                <h2 className="text-[16px] font-bold text-gray-900">Paste catalogue text</h2>
                <button onClick={() => setShowPasteModal(false)} className="text-gray-400 hover:text-gray-600">
                  <X size={20} />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <Field
                  label="Label (optional)"
                  value={pasteName}
                  onChange={setPasteName}
                  placeholder="e.g. WhatsApp broadcast list"
                />
                <label className="space-y-1.5 block">
                  <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Catalogue text</span>
                  <textarea
                    value={pasteText}
                    onChange={event => setPasteText(event.target.value)}
                    rows={10}
                    placeholder={"Paste your product list here. One product per line works best, e.g.\nLeather bag - 15000\nWooden lamp - 25000"}
                    className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[13px] font-mono focus:outline-none focus:ring-2 focus:ring-[#059669]/20 resize-none"
                  />
                </label>
              </div>
              <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3">
                <button onClick={() => setShowPasteModal(false)} className="px-4 py-2 text-[13px] font-bold text-gray-500 hover:text-gray-700">Cancel</button>
                <button
                  onClick={handlePasteSubmit}
                  disabled={uploading || !pasteText.trim()}
                  className="bg-[#059669] text-white px-6 py-2 rounded-xl text-[13px] font-bold shadow-sm hover:bg-[#047857] disabled:opacity-50 flex items-center gap-2"
                >
                  {uploading && <Loader2 size={14} className="animate-spin" />}
                  Submit
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="space-y-1.5 block">
      <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">{label}</span>
      <input
        type={type}
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
      />
    </label>
  );
}
