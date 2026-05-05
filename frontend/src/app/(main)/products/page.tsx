import { Search, SlidersHorizontal, MoreHorizontal, ArrowUpRight } from "lucide-react";

const products = [
  { name: "Retro Analog Clock",       sku: "CLK-001", price: "₦14,500", stock: 24, status: "In Stock"    },
  { name: "Minimalist Desk Lamp",     sku: "LMP-004", price: "₦25,000", stock: 8,  status: "In Stock"    },
  { name: "Ergonomic Wooden Chair",   sku: "CHR-012", price: "₦85,000", stock: 2,  status: "Low Stock"   },
  { name: "Ceramic Pour-Over Set",    sku: "KIT-007", price: "₦18,750", stock: 0,  status: "Out of Stock"},
  { name: "Handwoven Throw Blanket",  sku: "HME-022", price: "₦9,500",  stock: 31, status: "In Stock"    },
];

const statusStyle: Record<string, string> = {
  "In Stock":     "text-emerald-500 bg-emerald-50",
  "Low Stock":    "text-amber-700   bg-amber-50",
  "Out of Stock": "text-red-700     bg-red-50",
};

function ProductInitial({ name }: { name: string }) {
  const letter = name[0].toUpperCase();
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
  return (
    <div className="flex-1 overflow-y-auto bg-white">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">

        {/* Title row */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-gray-400 mb-1">Catalog</p>
            <h1 className="text-[22px] font-bold tracking-[-0.02em] text-gray-900">Products</h1>
          </div>
          <button className="bg-[#059669] text-white text-[13px] font-bold px-4 py-2.5 rounded-xl hover:bg-gray-700 transition-colors">
            + Add product
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
          <button className="flex items-center gap-1.5 border border-gray-200 bg-white rounded-xl px-3 py-2 text-[13px] font-semibold text-gray-600 hover:bg-gray-50 transition-colors">
            <SlidersHorizontal size={13} /> Filter
          </button>
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-12 px-3 py-2 border-b border-gray-100 mb-1">
          <span className="col-span-5 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Product</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">SKU</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-right">Price</span>
          <span className="col-span-2 text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em] text-center">Status</span>
          <span className="col-span-1"></span>
        </div>

        {/* Product rows */}
        <div className="space-y-0.5">
          {products.map((p, i) => (
            <div
              key={i}
              className="grid grid-cols-12 items-center px-3 py-3.5 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer group"
            >
              <div className="col-span-5 flex items-center gap-3">
                <ProductInitial name={p.name} />
                <div>
                  <p className="text-[13px] font-semibold text-gray-900 leading-tight">{p.name}</p>
                  <p className="text-[11px] text-gray-400 font-medium mt-0.5">{p.stock} units</p>
                </div>
              </div>
              <div className="col-span-2">
                <span className="text-[12px] font-mono font-semibold text-gray-400">{p.sku}</span>
              </div>
              <div className="col-span-2 text-right">
                <span className="text-[13px] font-bold font-mono text-gray-900">{p.price}</span>
              </div>
              <div className="col-span-2 flex justify-center">
                <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full ${statusStyle[p.status]}`}>
                  {p.status}
                </span>
              </div>
              <div className="col-span-1 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="text-gray-400 hover:text-gray-700 p-1 rounded-lg hover:bg-gray-100 transition-colors">
                  <MoreHorizontal size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
