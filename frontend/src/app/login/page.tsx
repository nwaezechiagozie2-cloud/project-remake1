"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Loader2 } from "lucide-react";
import { GoogleIcon, InstagramIcon } from "@/components/brand-icons";
import { API_ROOT, apiClient, getApiErrorMessage } from "@/lib/api";
import { INSTAGRAM_OAUTH_URL } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [status, setStatus]     = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleLogin() {
    if (loading) return;
    setError("");
    setStatus("");
    setLoading(true);
    try {
      const { data } = await apiClient.post("/auth/login", { email, password });
      const { token, vendor_id } = data;
      if (!token || !vendor_id) {
        throw new Error("Login response did not include a token.");
      }
      setStatus("Login successful. Opening dashboard...");
      window.location.href = `${window.location.origin}/auth/complete#token=${encodeURIComponent(token)}&vendor_id=${encodeURIComponent(String(vendor_id))}`;
    } catch (err: unknown) {
      setError(`${getApiErrorMessage(err, "Login failed")} API: ${API_ROOT}/auth/login`);
    } finally {
      setLoading(false);
    }
  }

  const handleOAuth = (provider: "google" | "instagram") => {
    if (provider === "instagram") {
      window.location.href = INSTAGRAM_OAUTH_URL;
      return;
    }
    window.location.href = `${API_ROOT}/auth/login/${provider}`;
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center pt-[15vh] px-6 selection:bg-[#3B5EE4]/10 selection:text-[#3B5EE4]">
      <div className="w-full max-w-[340px]">
        
        {/* Logo Mark */}
        <Link href="/" className="inline-flex items-center gap-2.5 mb-14 group">
          <div className="w-8 h-8 bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 rounded-xl flex items-center justify-center font-black text-white text-sm shadow-[0_4px_12px_rgba(9,9,11,0.3)] transition-transform group-hover:scale-105">
            O
          </div>
          <span className="font-bold text-[17px] text-gray-900 tracking-tight">OmniClose</span>
        </Link>

        {/* Header */}
        <div className="mb-10">
          <h1 className="text-[24px] font-bold tracking-[-0.03em] text-gray-900 leading-tight mb-1.5">Welcome back</h1>
          <p className="text-[13px] text-gray-500 font-medium">Log in to your store dashboard</p>
        </div>

        {/* Form Body */}
        <div
          className="space-y-6"
          onKeyDown={event => {
            if (event.key === "Enter") {
              event.preventDefault();
              handleLogin();
            }
          }}
        >
          <div className="space-y-2">
            <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full bg-gray-50/50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30 focus:bg-white focus:border-[#3B5EE4]/40 transition-all placeholder:text-gray-300"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">
                Password
              </label>
              <button type="button" className="text-[11px] font-bold text-gray-400 hover:text-[#09090b] transition-colors uppercase tracking-[0.1em]">
                Forgot?
              </button>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-gray-50/50 border border-gray-100 rounded-xl px-4 py-2.5 text-[14px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30 focus:bg-white focus:border-[#3B5EE4]/40 transition-all placeholder:text-gray-300"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 rounded-xl border border-red-100">
               <p className="text-[12px] text-red-600 font-bold">{error}</p>
            </div>
          )}

          {status && (
            <div className="p-3 bg-[#EFF1FE] rounded-xl border border-[#E0E5FB]">
               <p className="text-[12px] text-[#3B5EE4] font-bold">{status}</p>
            </div>
          )}

          <button
            type="button"
            onClick={handleLogin}
            disabled={loading}
            className="w-full bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white font-bold text-[14px] py-3 rounded-xl transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2 hover:bg-[#2B4DD0] hover:shadow-[#3B5EE4]/25"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : "Sign in"}
            {!loading && <ArrowRight size={16} />}
          </button>
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => handleOAuth("google")}
              className="w-full bg-white border border-gray-100 text-gray-700 font-bold text-[13px] py-2.5 rounded-xl hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <GoogleIcon />
              Continue with Google
            </button>
            <button
              type="button"
              onClick={() => handleOAuth("instagram")}
              className="w-full bg-white border border-gray-100 text-gray-700 font-bold text-[13px] py-2.5 rounded-xl hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <InstagramIcon />
              Continue with Instagram
            </button>
          </div>
        </div>

        {/* Footer Link */}
        <div className="mt-12 pt-8 border-t border-gray-50 text-center">
          <p className="text-[13px] text-gray-500 font-medium">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-gray-900 font-bold hover:underline">
              Create one for free
            </Link>
          </p>
        </div>

      </div>
    </div>
  );
}
