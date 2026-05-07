import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/vendors";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getAuthClient = (vendorId: number | string, token: string) => {
  return axios.create({
    baseURL: `${BASE_URL}/${vendorId}`,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
};

export const fetchDashboardData = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/dashboard");
  return data;
};

export const fetchVendorProducts = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/products");
  return data;
};

export const createProduct = async (vendorId: string | number, token: string, productData: any) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.post("/products", productData);
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

export const createBusinessInfo = async (vendorId: string | number, token: string, infoData: any) => {
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
  return data;
};
