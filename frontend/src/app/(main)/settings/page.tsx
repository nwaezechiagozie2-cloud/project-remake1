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
  configureTelegramWebhook,
  disconnectGoogleContacts,
  fetchGoogleOAuthStatus,
  fetchInstagramCredentials,
  fetchTelegramCredentials,
  fetchVendorBotSettings,
  fetchWhatsAppCredentials,
  getApiErrorMessage,
  updateTelegramCredentials,
  updateVendorBotSettings,
  updateWhatsAppCredentials,
  type TelegramCredentials,
  type VendorBotSettings,
  type WhatsAppCredentials,
} from "@/lib/api";
import { GoogleIcon, InstagramIcon, TelegramIcon, WhatsAppIcon } from "@/components/brand-icons";

const defaultSettings: VendorBotSettings = {
  confirm_before_sending_account_details: false,
  enable_knowledge_base_answers: true,
  use_product_availability: true,
};

type SettingKey = keyof VendorBotSettings;

const settingRows: { key: SettingKey; label: string; desc: string }[] = [
  {
    key: "enable_knowledge_base_answers",
    label: "Business Info Answers",
    desc: "Allow the bot to answer delivery, returns, location, and policy questions using your business info.",
  },
  {
    key: "use_product_availability",
    label: "Use Product Availability",
    desc: "Show available or unavailable status to the AI when it searches products.",
  },
  {
    key: "confirm_before_sending_account_details",
    label: "Confirm Before Bank Details",
    desc: "Require your approval before payment details are sent. When off, the bot sends them automatically once a customer asks to pay.",
  },
];

export default function SettingsPage() {
  const [copied, setCopied] = useState(false);
  const [settings, setSettings] = useState<VendorBotSettings>(defaultSettings);
  const [googleStatus, setGoogleStatus] = useState("not_connected");
  const [instagramConnected, setInstagramConnected] = useState(false);
  const [whatsapp, setWhatsapp] = useState<WhatsAppCredentials | null>(null);
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappToken, setWhatsappToken] = useState("");
  const [whatsappPhoneNumberId, setWhatsappPhoneNumberId] = useState("");
  const [telegram, setTelegram] = useState<TelegramCredentials | null>(null);
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<SettingKey | null>(null);
  const [savingWhatsApp, setSavingWhatsApp] = useState(false);
  const [savingTelegram, setSavingTelegram] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSettings() {
      try {
        const vendorId = localStorage.getItem("otc_vendor_id");
        const token = localStorage.getItem("otc_token");
        if (!vendorId || !token) return;

        const [botSettings, google, instagram, whatsappResult, telegramResult] = await Promise.allSettled([
          fetchVendorBotSettings(vendorId, token),
          fetchGoogleOAuthStatus(vendorId),
          fetchInstagramCredentials(vendorId, token),
          fetchWhatsAppCredentials(vendorId, token),
          fetchTelegramCredentials(vendorId, token),
        ]);

        if (botSettings.status === "fulfilled") setSettings(botSettings.value);
        if (google.status === "fulfilled") setGoogleStatus(google.value.status);
        if (instagram.status === "fulfilled") setInstagramConnected(Boolean(instagram.value.connected));
        if (whatsappResult.status === "fulfilled") {
          setWhatsapp(whatsappResult.value);
          setWhatsappNumber(whatsappResult.value.whatsapp_number || "");
          setWhatsappPhoneNumberId(whatsappResult.value.whatsapp_phone_number_id || "");
        }
        if (telegramResult.status === "fulfilled") {
          setTelegram(telegramResult.value);
          setTelegramChatId(telegramResult.value.telegram_vendor_chat_id || "");
        }
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

  const copyTelegramWebhook = () => {
    navigator.clipboard.writeText(`${API_ROOT}/telegram/webhook`);
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

  const handleSaveWhatsApp = async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;
    setSavingWhatsApp(true);
    setError("");
    try {
      const updated = await updateWhatsAppCredentials(vendorId, token, {
        ...(whatsappNumber.trim() ? { whatsapp_number: whatsappNumber.trim() } : {}),
        ...(whatsappToken.trim() ? { whatsapp_token: whatsappToken.trim() } : {}),
        ...(whatsappPhoneNumberId.trim() ? { whatsapp_phone_number_id: whatsappPhoneNumberId.trim() } : {}),
      });
      setWhatsapp(updated);
      setWhatsappNumber(updated.whatsapp_number || "");
      setWhatsappPhoneNumberId(updated.whatsapp_phone_number_id || "");
      setWhatsappToken("");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save WhatsApp settings"));
    } finally {
      setSavingWhatsApp(false);
    }
  };

  const handleSaveTelegram = async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;
    setSavingTelegram(true);
    setError("");
    try {
      const updated = await updateTelegramCredentials(vendorId, token, {
        ...(telegramToken.trim() ? { telegram_bot_token: telegramToken.trim() } : {}),
        ...(telegramChatId.trim() ? { telegram_vendor_chat_id: telegramChatId.trim() } : {}),
      });
      setTelegram(updated);
      setTelegramToken("");
      setTelegramChatId(updated.telegram_vendor_chat_id || "");
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to save Telegram settings"));
    } finally {
      setSavingTelegram(false);
    }
  };

  const handleConfigureTelegramWebhook = async () => {
    const vendorId = localStorage.getItem("otc_vendor_id");
    const token = localStorage.getItem("otc_token");
    if (!vendorId || !token) return;
    setSavingTelegram(true);
    setError("");
    try {
      await configureTelegramWebhook(vendorId, token);
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to configure Telegram webhook"));
    } finally {
      setSavingTelegram(false);
    }
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
    <div className="flex-1 overflow-y-auto bg-white selection:bg-[#3B5EE4]/10 selection:text-[#3B5EE4]">
      <div className="max-w-[780px] px-8 pt-10 pb-16 mx-auto">
        <div className="mb-12">
          <p className="text-[11px] font-bold tracking-[0.12em] uppercase text-gray-400 mb-1">Configuration</p>
          <h1 className="text-[24px] font-bold tracking-[-0.02em] text-gray-900">Settings</h1>
          {error && <p className="mt-3 text-[12px] font-bold text-red-600">{error}</p>}
        </div>

        <div className="space-y-12">
          <section className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center">
                <WhatsAppIcon className="h-4 w-4" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">WhatsApp Integration</h2>
            </div>

            <div className="p-5 bg-gray-50/50 border border-gray-100 rounded-2xl space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="text-[13px] font-bold text-gray-900">Cloud API Credentials</p>
                  <p className="text-[12px] text-gray-400 font-medium">
                    {whatsapp?.connected ? "WhatsApp credentials are saved." : "Add the Meta phone number ID, business number, and access token."}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={copyWebhook}
                  className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 transition-colors flex items-center gap-2"
                >
                  <Copy size={14} />
                  Webhook
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="space-y-1.5">
                  <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Business Number</span>
                  <input
                    value={whatsappNumber}
                    onChange={event => setWhatsappNumber(event.target.value)}
                    placeholder="2348012345678"
                    className="w-full bg-white border border-gray-100 rounded-xl px-3 py-2.5 text-[13px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30"
                  />
                </label>
                <label className="space-y-1.5">
                  <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Phone Number ID</span>
                  <input
                    value={whatsappPhoneNumberId}
                    onChange={event => setWhatsappPhoneNumberId(event.target.value)}
                    placeholder="Meta phone number ID"
                    className="w-full bg-white border border-gray-100 rounded-xl px-3 py-2.5 text-[13px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30"
                  />
                </label>
                <label className="space-y-1.5 md:col-span-2">
                  <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Access Token</span>
                  <input
                    type="password"
                    value={whatsappToken}
                    onChange={event => setWhatsappToken(event.target.value)}
                    placeholder={whatsapp?.has_access_token ? "Saved token" : "EAAB..."}
                    className="w-full bg-white border border-gray-100 rounded-xl px-3 py-2.5 text-[13px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30"
                  />
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveWhatsApp}
                  disabled={savingWhatsApp || (!whatsappNumber.trim() && !whatsappToken.trim() && !whatsappPhoneNumberId.trim())}
                  className="bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white text-[12px] font-bold px-5 py-2 rounded-xl hover:bg-[#2B4DD0] disabled:opacity-50 transition-colors flex items-center gap-2"
                >
                  {savingWhatsApp && <Loader2 size={14} className="animate-spin" />}
                  Save WhatsApp
                </button>
                <span className="text-[12px] text-gray-400 font-medium">
                  {whatsapp?.has_access_token ? "Token saved" : "Token not saved"}
                </span>
              </div>

              <code className="block w-full bg-white border border-gray-100 p-2.5 rounded-lg text-[12px] font-mono text-gray-500 truncate">
                {API_ROOT}/webhook
              </code>
            </div>
          </section>

          <section className="space-y-6 pt-6 border-t border-gray-100">
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
              <div className="w-8 h-8 rounded-lg bg-sky-50 flex items-center justify-center">
                <TelegramIcon className="h-4 w-4" />
              </div>
              <h2 className="text-[14px] font-bold text-gray-900">Telegram Integration</h2>
            </div>

            <div className="p-5 bg-gray-50/50 border border-gray-100 rounded-2xl space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="text-[13px] font-bold text-gray-900">Telegram Bot</p>
                  <p className="text-[12px] text-gray-400 font-medium">
                    {telegram?.connected ? "Telegram bot token is saved." : "Add your bot token to receive and send Telegram messages."}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={copyTelegramWebhook}
                  className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 transition-colors flex items-center gap-2"
                >
                  <Copy size={14} />
                  Webhook
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="space-y-1.5">
                  <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Bot Token</span>
                  <input
                    type="password"
                    value={telegramToken}
                    onChange={event => setTelegramToken(event.target.value)}
                    placeholder={telegram?.has_bot_token ? "Saved token" : "123456:ABC..."}
                    className="w-full bg-white border border-gray-100 rounded-xl px-3 py-2.5 text-[13px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30"
                  />
                </label>
                <label className="space-y-1.5">
                  <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-[0.1em]">Owner Chat ID</span>
                  <input
                    value={telegramChatId}
                    onChange={event => setTelegramChatId(event.target.value)}
                    placeholder="Optional approval chat"
                    className="w-full bg-white border border-gray-100 rounded-xl px-3 py-2.5 text-[13px] font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#3B5EE4]/30"
                  />
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleSaveTelegram}
                  disabled={savingTelegram || (!telegramToken.trim() && !telegramChatId.trim())}
                  className="bg-[#3B5EE4] shadow-lg shadow-[#3B5EE4]/15 text-white text-[12px] font-bold px-5 py-2 rounded-xl hover:bg-[#2B4DD0] disabled:opacity-50 transition-colors flex items-center gap-2"
                >
                  {savingTelegram && <Loader2 size={14} className="animate-spin" />}
                  Save Telegram
                </button>
                <button
                  type="button"
                  onClick={handleConfigureTelegramWebhook}
                  disabled={savingTelegram || !telegram?.connected}
                  className="bg-white border border-gray-100 text-[12px] font-bold text-gray-700 px-5 py-2 rounded-xl shadow-sm hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  Configure webhook
                </button>
              </div>

              <code className="block w-full bg-white border border-gray-100 p-2.5 rounded-lg text-[12px] font-mono text-gray-500 truncate">
                {API_ROOT}/telegram/webhook
              </code>
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
                <div className="w-8 h-8 rounded-lg bg-[#EFF1FE] flex items-center justify-center">
                  <Check size={16} className="text-[#3B5EE4]" />
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
                    <div className={`w-10 h-6 rounded-full transition-colors relative flex items-center px-1 ${settings[item.key] ? "bg-[#3B5EE4]" : "bg-gray-200"}`}>
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
