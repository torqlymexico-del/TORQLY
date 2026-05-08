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

export interface DashboardOrders {
  total_today: number;
  en_cola: number;
  en_proceso: number;
  listo: number;
  entregado: number;
  cancelado: number;
  revenue_today: string;
  pending_payment: number;
}

export interface DashboardOrderSummary {
  id: number;
  daily_sequence: number | null;
  status: string;
  payment_status: string;
  total: string;
  vehicle: { plate: string | null; brand: string | null; model: string | null; color: string | null } | null;
  client_name: string | null;
  washer_names: string[];
}

export interface WasherLoad {
  user_id: number;
  name: string;
  total: number;
  completed: number;
}

export interface DashboardData {
  totals: {
    users: number;
    clients: number;
    vehicles: number;
    services: number;
    appointments_today: number;
    sales_today: string;
    commissions_today: string;
    pending_charges_today: number;
    pending_services_today: number;
    in_progress_services_today: number;
    finished_services_today: number;
  };
  orders: DashboardOrders;
  orders_today: DashboardOrderSummary[];
  washer_load: WasherLoad[];
  low_stock_alerts: { id: number; name: string; stock: number; minimum_stock: number }[];
  operator_load: { operator_id: number; operator_name: string; pending: number; in_progress: number; finished: number; total: number }[];
}
