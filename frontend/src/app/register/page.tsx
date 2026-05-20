"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2, CheckCircle2 } from "lucide-react";
import { API_ROOT, apiClient, getApiErrorMessage } from "@/lib/api";

export default function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError]     = useState("");
  const [status, setStatus]   = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  async function handleRegister() {
    if (loading) return;
    setError("");
    setStatus("");
    setLoading(true);
    try {
      const { data } = await apiClient.post("/auth/register", form);
      const { token, vendor_id } = data;
      if (!token || !vendor_id) {
        throw new Error("Registration response did not include a token.");
      }
      setStatus("Account created. Opening dashboard...");
      window.location.href = `${window.location.origin}/auth/complete#token=${encodeURIComponent(token)}&vendor_id=${encodeURIComponent(String(vendor_id))}`;
    } catch (err: unknown) {
      setError(`${getApiErrorMessage(err, "Registration failed")} API: ${API_ROOT}/auth/register`);
    } finally {
      setLoading(false);
    }
  }

  const fields: { key: string; label: string; type?: string; placeholder: string }[] = [
    { key: "name",                    label: "Business Name",        placeholder: "e.g. Acme Studio" },
    { key: "email",                   label: "Work Email",           type: "email", placeholder: "name@company.com" },
    { key: "password",                label: "Password",             type: "password", placeholder: "Min. 8 characters" },
  ];

  return (
    <div className="min-h-screen bg-white flex flex-col items-center pt-[10vh] px-6 selection:bg-[#059669]/10 selection:text-[#059669]">
      <div className="w-full max-w-[340px]">
        
        {/* Logo Mark */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-14 group">
          <div className="w-8 h-8 bg-[#059669] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-[0_4px_12px_rgba(9,9,11,0.3)] transition-transform group-hover:scale-105">
            O
          </div>
          <span className="font-bold text-[17px] text-gray-900 tracking-tight">OmniClose</span>
        </Link>

        {/* Header */}
        <div className="mb-10">
          <h1 className="text-[24px] font-bold tracking-[-0.03em] text-gray-900 leading-tight mb-1.5">Start your operation</h1>
          <p className="text-[13px] text-gray-500 font-medium leading-relaxed">Join 200+ vendors automating their sales.</p>
        </div>

        {/* Form Body */}
        <div
          className="space-y-6"
          onKeyDown={event => {
            if (event.key === "Enter") {
              event.preventDefault();
              handleRegister();
            }
          }}
        >
          {fields.map(f => (
            <div key={f.key} className="space-y-2">
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">
                {f.label}
              </label>
              <input
                type={f.type || "text"}
                required
                value={(form as Record<string, string>)[f.key]}
                onChange={set(f.key)}
                placeholder={f.placeholder}
                className="w-full bg-gray-50/50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#059669]/30 focus:bg-white focus:border-[#059669]/40 transition-all placeholder:text-gray-300"
              />
            </div>
          ))}

          {error && (
            <div className="p-3 bg-red-50 rounded-xl border border-red-100">
               <p className="text-[12px] text-red-600 font-bold">{error}</p>
            </div>
          )}

          {status && (
            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
               <p className="text-[12px] text-emerald-700 font-bold">{status}</p>
            </div>
          )}

          <div className="space-y-4">
            <button
              type="button"
              onClick={handleRegister}
              disabled={loading}
              className="w-full bg-[#059669] text-white font-bold text-[14px] py-3 rounded-xl transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2 hover:bg-[#047857]"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : "Create account"}
              {!loading && <ArrowRight size={16} />}
            </button>
            <p className="text-[11px] text-gray-400 font-medium text-center leading-relaxed">
              By clicking &quot;Create account&quot;, you agree to our Terms of Service and Privacy Policy.
            </p>
          </div>
        </div>

        {/* List of benefits — small, dense, professional */}
        <div className="mt-14 space-y-4">
           {[
             "Free 14-day trial",
             "Priority WhatsApp support",
             "AI catalog sync"
           ].map(text => (
             <div key={text} className="flex items-center gap-2.5">
               <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />
               <span className="text-[12px] font-bold text-gray-600">{text}</span>
             </div>
           ))}
        </div>

        {/* Footer Link */}
        <div className="mt-12 pt-8 border-t border-gray-50 text-center">
          <p className="text-[13px] text-gray-500 font-medium">
            Already registered?{" "}
            <Link href="/login" className="text-gray-900 font-bold hover:underline">
              Sign in to store
            </Link>
          </p>
        </div>

      </div>
    </div>
  );
}
