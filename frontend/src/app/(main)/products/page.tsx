"use client";
import { useCallback, useEffect, useState } from "react";
import { Search, Trash2, Loader2, Plus, X, Pencil, ToggleLeft, ToggleRight } from "lucide-react";
import {
  createProduct,
  deleteProduct,
  fetchVendorProducts,
  getApiErrorMessage,
  updateProduct,
  updateProductAvailability,
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

  const loadData = useCallback(async () => {
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      const data = await fetchVendorProducts(vendorId, token, {
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
  }, [search, stockFilter]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      loadData();
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [loadData]);

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
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      const payload = toPayload(form);
      if (editingProduct) {
        await updateProduct(vendorId, token, editingProduct.id, payload);
      } else {
        await createProduct(vendorId, token, payload);
      }
      setShowModal(false);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save product"));
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleAvailability(product: Product) {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;

    setItems(items.map(item => item.id === product.id ? { ...item, in_stock: !item.in_stock } : item));
    try {
      await updateProductAvailability(vendorId, token, product.id, !product.in_stock);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to update availability"));
      await loadData();
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this product?")) return;
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      await deleteProduct(vendorId, token, id);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to delete product"));
    }
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">Catalog</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Products</h1>
            {error && <p className="mt-2 text-[12px] font-bold text-red-600">{error}</p>}
          </div>
          <button
            onClick={openCreate}
            className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-[#047857] transition-colors flex items-center gap-2"
          >
            <Plus size={16} /> Add product
          </button>
        </div>

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
