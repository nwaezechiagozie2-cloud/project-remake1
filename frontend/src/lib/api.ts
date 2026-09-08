import axios, { AxiosError } from "axios";

export const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001")
  .replace(/\/$/, "")
  .replace(/\/vendors$/, "");
const VENDORS_ROOT = `${API_ROOT}/vendors`;

type ApiErrorPayload = {
  error?: {
    message?: string;
  };
  detail?: string | { msg?: string; loc?: unknown[] } | { msg?: string; loc?: unknown[] }[];
};

export type ProductPayload = {
  name?: string;
  price?: number;
  description?: string | null;
  extra_details?: string | null;
  currency?: string;
  image_url?: string | null;
  video_url?: string | null;
  in_stock?: boolean;
};

export type VendorBotSettings = {
  confirm_before_sending_account_details: boolean;
  enable_knowledge_base_answers: boolean;
  use_product_availability: boolean;
  sheets_sync_enabled: boolean;
};

export type SheetsConfig = {
  google_connected: boolean;
  spreadsheet_id: string | null;
  spreadsheet_title: string | null;
  tab_name: string | null;
  sync_enabled: boolean;
  sync_status: "healthy" | "not_connected" | "reauth_needed" | "spreadsheet_unavailable" | "error";
  pending_orders: number;
  synced_orders: number;
  last_error: string | null;
};

export type CatalogueUploadPayload = {
  file_name: string;
  mime_type: string;
  content_base64: string;
};

export type CatalogueBulkImportItemPayload = {
  id: number;
  name: string;
  price: number;
  currency: string;
  description?: string | null;
  in_stock?: boolean;
};

export type VendorProfile = {
  vendor_id: number;
  name: string;
  email: string;
  email_verified: boolean;
  email_verified_at: string | null;
  pending_email: string | null;
  providers: Record<string, boolean>;
};

export type TelegramCredentials = {
  telegram_vendor_chat_id: string | null;
  has_bot_token: boolean;
  connected: boolean;
  webhook_url: string;
  message: string;
};

export type WhatsAppCredentials = {
  whatsapp_number: string | null;
  whatsapp_phone_number_id: string | null;
  has_access_token: boolean;
  connected: boolean;
  webhook_url: string;
  message: string;
};

export function getApiErrorMessage(error: unknown, fallback = "Request failed") {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorPayload | undefined;
    if (!error.response) {
      return `Cannot reach backend at ${API_ROOT}. Start FastAPI on that port or set NEXT_PUBLIC_API_URL to the running backend URL.`;
    }
    return data?.error?.message || formatApiDetail(data?.detail) || error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

function formatApiDetail(detail: ApiErrorPayload["detail"]) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map(item => {
        const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
        return [location, item.msg].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join("; ");
  }
  return detail.msg || JSON.stringify(detail);
}

export const apiClient = axios.create({
  baseURL: API_ROOT,
  headers: {
    "Content-Type": "application/json",
  },
});

let handled401 = false;

const handle401 = () => {
  if (handled401) return;
  handled401 = true;
  localStorage.removeItem("otc_token");
  localStorage.removeItem("otc_vendor_id");
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.replace("/login");
  }
};

export const getAuthClient = (vendorId: number | string, token: string) => {
  const client = axios.create({
    baseURL: `${VENDORS_ROOT}/${vendorId}`,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  client.interceptors.response.use(
    response => response,
    (error: AxiosError) => {
      if (error.response?.status === 401) {
        handle401();
      }
      return Promise.reject(error);
    },
  );

  return client;
};

export const fetchDashboardData = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/dashboard");
  return data;
};

export const fetchVendorProducts = async (
  vendorId: string | number,
  token: string,
  params?: { search?: string; in_stock?: boolean },
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/products", { params });
  return data;
};

export const createProduct = async (vendorId: string | number, token: string, productData: ProductPayload) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/products", productData);
  return data;
};

export const updateProduct = async (
  vendorId: string | number,
  token: string,
  productId: number,
  productData: ProductPayload,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.patch(`/products/${productId}`, productData);
  return data;
};

export const updateProductAvailability = async (
  vendorId: string | number,
  token: string,
  productId: number,
  inStock: boolean,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.patch(`/products/${productId}/availability`, { in_stock: inStock });
  return data;
};

export const deleteProduct = async (vendorId: string | number, token: string, productId: number) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.delete(`/products/${productId}`);
  return data;
};

export const fetchBusinessInfo = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/business-info");
  return data;
};

export const createBusinessInfo = async (vendorId: string | number, token: string, infoData: unknown) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/business-info", infoData);
  return data;
};

export const deleteBusinessInfo = async (vendorId: string | number, token: string, infoId: number) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.delete(`/business-info/${infoId}`);
  return data;
};

export const fetchVendorBotSettings = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/bot-settings");
  return data as VendorBotSettings;
};

export const updateVendorBotSettings = async (
  vendorId: string | number,
  token: string,
  settings: Partial<VendorBotSettings>,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.put("/bot-settings", settings);
  return data as VendorBotSettings;
};

export const fetchGoogleOAuthStatus = async (vendorId: string | number) => {
  const { data } = await apiClient.get("/auth/google/status", { params: { vendor_id: vendorId } });
  return data;
};

export const fetchGoogleSheetsOAuthStatus = async (vendorId: string | number) => {
  const { data } = await apiClient.get("/auth/google/sheets/status", { params: { vendor_id: vendorId } });
  return data;
};

export const fetchSheetsConfig = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/sheets-config");
  return data as SheetsConfig;
};

export const updateSheetsConfig = async (
  vendorId: string | number,
  token: string,
  payload: { spreadsheet_url: string },
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.put("/sheets-config", payload);
  return data as SheetsConfig;
};

export const disconnectSheets = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.delete("/sheets-config");
  return data as SheetsConfig;
};

export const disconnectGoogleContacts = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.delete("/google-contacts");
  return data;
};

export const fetchInstagramCredentials = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/instagram-credentials");
  return data;
};

export const fetchWhatsAppCredentials = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/whatsapp-credentials");
  return data as WhatsAppCredentials;
};

export const updateWhatsAppCredentials = async (
  vendorId: string | number,
  token: string,
  payload: { whatsapp_number?: string; whatsapp_token?: string; whatsapp_phone_number_id?: string },
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.put("/whatsapp-credentials", payload);
  return data as WhatsAppCredentials;
};

export const fetchTelegramCredentials = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/telegram-credentials");
  return data as TelegramCredentials;
};

export const updateTelegramCredentials = async (
  vendorId: string | number,
  token: string,
  payload: { telegram_bot_token?: string; telegram_vendor_chat_id?: string },
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.put("/telegram-credentials", payload);
  return data as TelegramCredentials;
};

export const configureTelegramWebhook = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/telegram-webhook");
  return data as { status: string; webhook_url: string };
};

export const fetchCatalogueUploads = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/catalogue/uploads");
  return data;
};

export const uploadCatalogue = async (
  vendorId: string | number,
  token: string,
  payload: CatalogueUploadPayload,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/catalogue/uploads", payload);
  return data;
};

export const fetchCatalogueImportItems = async (
  vendorId: string | number,
  token: string,
  uploadId: number,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get(`/catalogue/uploads/${uploadId}/items`);
  return data;
};

export const importCatalogueItem = async (
  vendorId: string | number,
  token: string,
  itemId: number,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post(`/catalogue/items/${itemId}/import`);
  return data;
};

export const importCatalogueItems = async (
  vendorId: string | number,
  token: string,
  items: CatalogueBulkImportItemPayload[],
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/catalogue/items/import-bulk", { items });
  return data;
};

export const fetchVendorProfile = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/profile");
  return data as VendorProfile;
};

export const requestEmailVerification = async (email: string) => {
  const { data } = await apiClient.post("/auth/verify-email/request", { email });
  return data;
};

export const confirmEmailVerification = async (token: string) => {
  const { data } = await apiClient.post("/auth/verify-email/confirm", { token });
  return data;
};

export const requestEmailChange = async (vendorId: string | number, token: string, newEmail: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/profile/email-change/request", { new_email: newEmail });
  return data;
};

export const confirmEmailChange = async (vendorId: string | number, token: string, verificationToken: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/profile/email-change/confirm", { token: verificationToken });
  return data as VendorProfile;
};

export const changePassword = async (
  vendorId: string | number,
  token: string,
  currentPassword: string,
  newPassword: string,
) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/profile/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return data;
};

export const updateVendorProfile = async (vendorId: string | number, token: string, name: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.patch("/profile", { name });
  return data as VendorProfile;
};
