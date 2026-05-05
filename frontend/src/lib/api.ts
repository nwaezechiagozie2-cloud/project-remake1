import axios from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/vendors";

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

export const fetchVendorBotSettings = async (vendorId: string | number, token: string) => {
  const client = getAuthClient(vendorId, token);
  const { data } = await client.get("/bot-settings");
  return data;
};
