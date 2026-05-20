import axios, { AxiosError } from "axios";

export const API_ROOT = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001")
  .replace(/\/$/, "")
  .replace(/\/vendors$/, "");
const VENDORS_ROOT = `${API_ROOT}/vendors`;

type ApiErrorPayload = {
  error?: {
    message?: string;
  };
  detail?: string;
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
  allow_product_qa: boolean;
  allow_office_qa: boolean;
  use_product_availability: boolean;
};

export type CatalogueUploadPayload = {
  file_name: string;
  mime_type: string;
  content_base64: string;
};

export function getApiErrorMessage(error: unknown, fallback = "Request failed") {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiErrorPayload | undefined;
    if (!error.response) {
      return `Cannot reach backend at ${API_ROOT}. Start FastAPI on that port or set NEXT_PUBLIC_API_URL to the running backend URL.`;
    }
    return data?.error?.message || data?.detail || error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

export const apiClient = axios.create({
  baseURL: API_ROOT,
  headers: {
    "Content-Type": "application/json",
  },
});

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
    (error: AxiosError) => Promise.reject(error),
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

export const fetchInstagramCredentials = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/instagram-credentials");
  return data;
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
