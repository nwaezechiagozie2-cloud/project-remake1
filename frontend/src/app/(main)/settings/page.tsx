"use client";
import { useEffect, useState } from "react";
import {
  Shield,
  Check,
  Copy,
  UserPlus,
  Loader2,
  MessageCircle,
} from "lucide-react";
import {
  API_ROOT,
  disconnectGoogleContacts,
  fetchGoogleOAuthStatus,
  fetchInstagramCredentials,
  fetchVendorBotSettings,
  getApiErrorMessage,
  updateVendorBotSettings,
  type VendorBotSettings,
} from "@/lib/api";
import { GoogleIcon, InstagramIcon } from "@/components/brand-icons";

const defaultSettings: VendorBotSettings = {
  confirm_before_sending_account_details: false,
  enable_knowledge_base_answers: true,
  allow_product_qa: true,
  allow_office_qa: true,
  use_product_availability: true,
};

type SettingKey = keyof VendorBotSettings;

const settingRows: { key: SettingKey; label: string; desc: string }[] = [
  {
    key: "enable_knowledge_base_answers",
    label: "Business Info Answers",
    desc: "Allow the bot to answer delivery, returns, location, and policy questions.",
  },
  {
    key: "allow_product_qa",
    label: "Product Q&A",
    desc: "Allow the bot to answer specific product and price questions.",
  },
  {
    key: "allow_office_qa",
    label: "Office & Store Q&A",
    desc: "Allow the bot to answer store-hours and location questions.",
  },
  {
    key: "use_product_availability",
    label: "Use Product Availability",
    desc: "Show available or unavailable status to the AI when it searches products.",
  },
  {
    key: "confirm_before_sending_account_details",
    label: "Confirm Before Bank Details",
    desc: "Require vendor approval before payment details are sent.",
  },
];

export default function SettingsPage() {
  const [copied, setCopied] = useState(false);
  const [settings, setSettings] = useState<VendorBotSettings>(defaultSettings);
  const [googleStatus, setGoogleStatus] = useState("not_connected");
  const [instagramConnected, setInstagramConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<SettingKey | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSettings() {
      try {
        const vendorId = localStorage.getItem("otc_vendor_id");
        const token = localStorage.getItem("otc_token");
        if (!vendorId || !token) return;

        const [botSettings, google, instagram] = await Promise.allSettled([
          fetchVendorBotSettings(vendorId, token),
          fetchGoogleOAuthStatus(vendorId),
          fetchInstagramCredentials(vendorId, token),
        ]);

        if (botSettings.status === "fulfilled") setSettings(botSettings.value);
        if (google.status === "fulfilled") setGoogleStatus(google.value.status);
        if (instagram.status === "fulfilled") setInstagramConnected(Boolean(instagram.value.connected));
      } catch (err) {
        setError(getApiErrorMessage(err, "Failed to load settings"));
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, []);

  const copyWebhook = () => {
    navigator.clipboard.writeText(`${API_ROOT}/webhook`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleGoogleConnect = () => {
    window.location.href = `${API_ROOT}/auth/google?vendor_id=${localStorage.getItem("otc_vendor_id")}`;
  };

  const handleGoogleDisconnect = async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;
    try {
      await disconnectGoogleContacts(vendorId, token);
      setGoogleStatus("not_connected");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to disconnect Google Contacts"));
    }
  };

  const handleInstagramConnect = () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    if (!vendorId) return;
    window.location.href = `${API_ROOT}/auth/instagram?vendor_id=${vendorId}`;
  };

  const toggleSetting = async (key: SettingKey) => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;

    const nextValue = !settings[key];
    const previous = settings;
    setSettings({ ...settings, [key]: nextValue });
    setSavingKey(key);
    setError("");

    try {
      const updated = await updateVendorBotSettings(vendorId, token, { [key]: nextValue });
      setSettings(updated);
    } catch (err) {
      setSettings(previous);
      setError(getApiErrorMessage(err, "Failed to save setting"));
    } finally {
      setSavingKey(null);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-400" size={32} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-white selection:bg-[#059669]/10 selection:text-[#059669]">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">
        <div className="mb-12">
          <p className="text-[11px] font-bold tracking-[0.12em] uppercase text-gray-400 mb-1">Configuration</p>
          <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">Settings</h1>
          {error && <p className="mt-3 text-[12px] font-bold text-red-600">{error}</p>}
        </div>

        <div className="space-y-12">
          <section className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-pink-50 flex items-center justify-center">
                <MessageCircle size={16} className="text-pink-600" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Instagram Integration</h2>
            </div>

            <div className="p-5 bg-gray-50/50 border border-gray-100 rounded-2xl flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[13px] font-bold text-gray-900">Instagram DMs</p>
                <p className="text-[12px] text-gray-400 font-medium">
                  {instagramConnected ? "Instagram is connected." : "Connect the Instagram account that should receive and send DMs."}
                </p>
              </div>
              <button
                type="button"
                onClick={handleInstagramConnect}
                className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-5 py-2 rounded-xl shadow-sm hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                <InstagramIcon />
                Connect Instagram
              </button>
            </div>
          </section>

          <section className="space-y-6 pt-6 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
                <UserPlus size={16} className="text-red-600" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Contact Integration</h2>
            </div>

            <div className="p-5 bg-gray-50/50 border border-gray-100 rounded-2xl flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[13px] font-bold text-gray-900">Google Contacts</p>
                <p className="text-[12px] text-gray-400 font-medium">
                  Status: <span className="text-gray-700">{googleStatus.replaceAll("_", " ")}</span>
                </p>
              </div>
              {googleStatus === "connected" ? (
                <button
                  onClick={handleGoogleDisconnect}
                  className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-5 py-2 rounded-xl hover:bg-gray-50 transition-colors shadow-sm flex items-center gap-2"
                >
                  <GoogleIcon />
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={handleGoogleConnect}
                  className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-5 py-2 rounded-xl hover:bg-gray-50 transition-colors shadow-sm flex items-center gap-2"
                >
                  <GoogleIcon />
                  Continue with Google
                </button>
              )}
            </div>
          </section>

          <section className="space-y-6 pt-6 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                  <Check size={16} className="text-emerald-600" />
                </div>
                <h2 className="text-[14px] font-bold text-gray-900">Webhook</h2>
              </div>
              <button
                onClick={copyWebhook}
                className="flex items-center gap-1.5 text-[11px] font-bold text-[#09090b] hover:bg-gray-50 px-2 py-1 rounded-lg transition-colors"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy URL"}
              </button>
            </div>
            <code className="block w-full bg-gray-50 border border-gray-100 p-2.5 rounded-lg text-[13px] font-mono text-gray-500 truncate">
              {API_ROOT}/webhook
            </code>
          </section>

          <section className="space-y-6 pt-6 border-t border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <Shield size={16} className="text-[#09090b]" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Bot Settings</h2>
            </div>

            <div className="space-y-4">
              {settingRows.map(item => (
                <button
                  type="button"
                  key={item.key}
                  onClick={() => toggleSetting(item.key)}
                  className="w-full flex items-start justify-between p-4 bg-white border border-gray-100 rounded-2xl hover:bg-gray-50 transition-colors text-left group"
                >
                  <div className="space-y-1">
                    <p className="text-[13px] font-bold text-gray-900">{item.label}</p>
                    <p className="text-[12px] text-gray-400 font-medium">{item.desc}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {savingKey === item.key && <Loader2 size={13} className="animate-spin text-gray-400" />}
                    <div className={`w-10 h-6 rounded-full transition-colors relative flex items-center px-1 ${settings[item.key] ? "bg-[#059669]" : "bg-gray-200"}`}>
                      <div className={`w-4 h-4 bg-white rounded-full transition-transform ${settings[item.key] ? "translate-x-4" : "translate-x-0"}`} />
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
