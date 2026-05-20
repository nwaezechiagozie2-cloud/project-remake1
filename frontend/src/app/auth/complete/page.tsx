"use client";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

export default function AuthCompletePage() {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    window.setTimeout(() => {
      const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      const token = params.get("token");
      const vendorId = params.get("vendor_id");

      if (!token || !vendorId) {
        setHasError(true);
        window.setTimeout(() => {
          window.location.replace("/login");
        }, 1200);
        return;
      }

      localStorage.setItem("otc_token", token);
      localStorage.setItem("otc_vendor_id", vendorId);
      window.location.replace("/dashboard");
    }, 0);
  }, []);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-6">
      <div className="flex items-center gap-3 text-gray-600">
        <Loader2 size={18} className="animate-spin" />
        <p className="text-[13px] font-bold">
          {hasError ? "Missing login token. Please sign in again." : "Completing sign in..."}
        </p>
      </div>
    </div>
  );
}
