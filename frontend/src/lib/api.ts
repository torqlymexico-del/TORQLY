import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

export interface UserRead {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  company_id: number | null;
  privacy_policy_version: string | null;
}

export interface DashboardData {
  today_revenue: number;
  today_appointments: number;
  pending_services: number;
  active_operators: number;
  recent_appointments: Appointment[];
  low_stock_count: number;
  unread_notifications: number;
}

export interface Appointment {
  id: number;
  status: string;
  scheduled_start: string;
  client?: { name: string };
  service_catalog?: { name: string };
  operator?: { name: string };
}
