"use client";
import { useEffect, useState } from "react";
import { Search, SlidersHorizontal, Trash2, MoreHorizontal, Loader2, Plus, X } from "lucide-react";
import { fetchVendorProducts, createProduct, deleteProduct } from "@/lib/api";

const statusStyle: Record<string, string> = {
  "In Stock":     "text-emerald-500 bg-emerald-50",
  "Low Stock":    "text-amber-700   bg-amber-50",
  "Out of Stock": "text-red-700     bg-red-50",
};

function ProductInitial({ name }: { name: string }) {
  const letter = name ? name[0].toUpperCase() : "?";
  const hues = [30, 210, 160, 280, 200];
  const hue  = hues[name.charCodeAt(0) % hues.length];
  return (
    <span
      className="w-8 h-8 rounded-xl flex items-center justify-center text-[13px] font-bold text-white shrink-0 select-none"
      style={{ background: `hsl(${hue} 55% 55%)` }}
    >
      {letter}
    </span>
  );
}

export default function ProductsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newProduct, setNewProduct] = useState({
    name: "",
    price: "",
    description: "",
    extra_details: "",
    in_stock: true
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      const data = await fetchVendorProducts(vendorId, token);
      setItems(data.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newProduct.name || !newProduct.price) return;
    setSaving(true);
    try {
      const vendorId = localStorage.getItem("otc_vendor_id");
      const token = localStorage.getItem("otc_token");
      if (!vendorId || !token) return;
      await createProduct(vendorId, token, {
        ...newProduct,
        price: parseFloat(newProduct.price),
        currency: "NGN"
      });
      setNewProduct({ name: "", price: "", description: "", extra_details: "", in_stock: true });
      setShowAddModal(false);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
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
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">Catalog</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Products</h1>
          </div>
          <button 
            onClick={() => setShowAddModal(true)}
            className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <Plus size={16} /> Add product
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-6">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search products…"
              className="bg-gray-50 border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-[13px] font-medium text-gray-700 w-56 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:border-[#059669]/40 placeholder:text-gray-400 transition-all"
            />
          </div>
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-6 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Product</span>
          <span className="col-span-3 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-right">Price</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-center">Status</span>
          <span className="col-span-1"></span>
        </div>

        {/* Product rows */}
        <div className="space-y-0.5">
          {items.length === 0 ? (
             <div className="py-12 text-center">
                <p className="text-[13px] text-gray-400 font-medium">No products in your catalog.</p>
             </div>
          ) : (
            items.map((p) => (
              <div
                key={p.id}
                className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors group"
              >
                <div className="col-span-6 flex items-center gap-3">
                  <ProductInitial name={p.name} />
                  <div>
                    <p className="text-[13px] font-semibold text-gray-900 leading-tight">{p.name}</p>
                    <p className="text-[11px] text-gray-400 font-medium mt-0.5">{p.description || "No description"}</p>
                  </div>
                </div>
                <div className="col-span-3 text-right">
                  <span className="text-[13px] font-bold font-mono text-gray-900">₦{p.price.toLocaleString()}</span>
                </div>
                <div className="col-span-2 flex justify-center">
                  <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${p.in_stock ? statusStyle["In Stock"] : statusStyle["Out of Stock"]}`}>
                    {p.in_stock ? "In Stock" : "Out of Stock"}
                  </span>
                </div>
                <div className="col-span-1 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => handleDelete(p.id)}
                    className="text-gray-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    <Trash2 size={15} />
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
                   <h2 className="text-[16px] font-bold text-gray-900">Add New Product</h2>
                   <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                      <X size={20} />
                   </button>
                </div>
                <div className="p-6 space-y-4">
                   <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                         <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Product Name</label>
                         <input 
                           value={newProduct.name}
                           onChange={e => setNewProduct({...newProduct, name: e.target.value})}
                           placeholder="e.g. Leather Bag"
                           className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
                         />
                      </div>
                      <div className="space-y-1.5">
                         <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Price (NGN)</label>
                         <input 
                           type="number"
                           value={newProduct.price}
                           onChange={e => setNewProduct({...newProduct, price: e.target.value})}
                           placeholder="e.g. 15000"
                           className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
                         />
                      </div>
                   </div>
                   <div className="space-y-1.5">
                      <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Short Description</label>
                      <input 
                        value={newProduct.description}
                        onChange={e => setNewProduct({...newProduct, description: e.target.value})}
                        placeholder="What is this product?"
                        className="w-full bg-gray-50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-[#059669]/20"
                      />
                   </div>
                   <div className="space-y-1.5">
                      <label className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">AI Context / Extra Details</label>
                      <textarea 
                        value={newProduct.extra_details}
                        onChange={e => setNewProduct({...newProduct, extra_details: e.target.value})}
                        rows={3}
                        placeholder="Materials, sizes, or anything the AI should know when selling this."
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
                      Add to Catalog
                   </button>
                </div>
             </div>
          </div>
        )}

      </div>
    </div>
  );
}
