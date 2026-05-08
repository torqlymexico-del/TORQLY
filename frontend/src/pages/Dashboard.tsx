import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, TrendingUp, Clock, CheckCircle, AlertCircle, Users, ChevronRight, Package } from "lucide-react";
import api, { type DashboardData } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// ─── Design tokens ────────────────────────────────────────────────────────────

const STATUS_DOT: Record<string, string> = {
  en_cola:    "bg-amber-400",
  en_proceso: "bg-blue-500",
  listo:      "bg-emerald-500",
  entregado:  "bg-slate-400",
  cancelado:  "bg-red-400",
};

const PAY_LABEL: Record<string, string> = {
  pendiente: "Por cobrar",
  pagado:    "Pagado",
  parcial:   "Parcial",
  credito:   "Crédito",
  cortesia:  "Cortesía",
};

const PAY_COLOR: Record<string, string> = {
  pendiente: "text-orange-500",
  pagado:    "text-emerald-600",
  parcial:   "text-blue-600",
  credito:   "text-violet-600",
  cortesia:  "text-sky-600",
};

function fmt(v: string | number | null | undefined) {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function vehicleLabel(v: DashboardData["orders_today"][0]["vehicle"]) {
  if (!v) return "Sin vehículo";
  return [v.brand, v.model, v.color].filter(Boolean).join(" ") || "Vehículo";
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon: Icon, iconBg }: {
  label: string; value: string | number; sub?: string;
  icon: typeof TrendingUp; iconBg: string;
}) {
  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1 leading-none">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuth();
  const [data,    setData]    = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    api.get<DashboardData>("/dashboard/summary")
      .then(r  => setData(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const o = data?.orders;

  const activeOrders   = (o?.en_cola ?? 0) + (o?.en_proceso ?? 0);
  const completedToday = o?.entregado ?? 0;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Buenos días";
    if (h < 19) return "Buenas tardes";
    return "Buenas noches";
  })();

  return (
    <div className="space-y-5 pb-16">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{greeting}, {user?.name?.split(" ")[0]}.</h1>
        <p className="text-sm text-slate-400 mt-0.5">Resumen de hoy</p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0" />
          No se pudo cargar el dashboard. Recarga la página.
        </div>
      )}

      {/* Stat cards */}
      {loading ? (
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100 h-24 animate-pulse">
              <div className="h-3 bg-slate-100 rounded w-1/2 mb-3" />
              <div className="h-7 bg-slate-100 rounded w-1/3" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Ingresos hoy"
            value={fmt(o?.revenue_today ?? "0")}
            icon={TrendingUp}
            iconBg="bg-emerald-50 text-emerald-600"
          />
          <StatCard
            label="En proceso"
            value={activeOrders}
            sub={`${o?.en_cola ?? 0} en cola · ${o?.en_proceso ?? 0} lavando`}
            icon={Clock}
            iconBg="bg-blue-50 text-blue-600"
          />
          <StatCard
            label="Entregados"
            value={completedToday}
            sub={`${o?.total_today ?? 0} totales hoy`}
            icon={CheckCircle}
            iconBg="bg-slate-100 text-slate-600"
          />
          <StatCard
            label="Por cobrar"
            value={o?.pending_payment ?? 0}
            sub={o?.listo ? `${o.listo} listos sin pago` : undefined}
            icon={AlertCircle}
            iconBg="bg-orange-50 text-orange-600"
          />
        </div>
      )}

      {/* Status breakdown */}
      {!loading && o && o.total_today > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Estado de órdenes</p>
          <div className="flex gap-2 flex-wrap">
            {[
              { k: "en_cola",    label: "En cola",   n: o.en_cola,    bg: "bg-amber-50 text-amber-700" },
              { k: "en_proceso", label: "Lavando",   n: o.en_proceso, bg: "bg-blue-50 text-blue-700" },
              { k: "listo",      label: "Listo",     n: o.listo,      bg: "bg-emerald-50 text-emerald-700" },
              { k: "entregado",  label: "Entregado", n: o.entregado,  bg: "bg-slate-100 text-slate-600" },
              { k: "cancelado",  label: "Cancelado", n: o.cancelado,  bg: "bg-red-50 text-red-600" },
            ].filter(s => s.n > 0).map(s => (
              <div key={s.k} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${s.bg}`}>
                <span>{s.n}</span>
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Washer load */}
      {!loading && (data?.washer_load?.length ?? 0) > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="px-4 pt-4 pb-2">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Lavadores hoy</p>
          </div>
          <div className="divide-y divide-slate-100">
            {data!.washer_load.map(w => (
              <div key={w.user_id} className="px-4 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                  <Users className="h-4 w-4 text-slate-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800">{w.name}</p>
                  <p className="text-xs text-slate-400">{w.completed} terminados · {w.total} asignados</p>
                </div>
                {/* Progress bar */}
                <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: w.total > 0 ? `${Math.round((w.completed / w.total) * 100)}%` : "0%" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Low stock alerts */}
      {!loading && (data?.low_stock_alerts?.length ?? 0) > 0 && (
        <div className="bg-amber-50 border border-amber-100 rounded-2xl overflow-hidden">
          <div className="px-4 pt-4 pb-2 flex items-center gap-2">
            <Package className="h-4 w-4 text-amber-600" />
            <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Stock bajo</p>
          </div>
          <div className="divide-y divide-amber-100">
            {data!.low_stock_alerts.slice(0, 4).map(p => (
              <div key={p.id} className="px-4 py-2.5 flex items-center justify-between">
                <span className="text-sm text-amber-800">{p.name}</span>
                <span className="text-xs font-bold text-amber-700">{p.stock} / {p.minimum_stock} mín.</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Today's orders list */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="px-4 pt-4 pb-2 flex items-center justify-between">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Órdenes de hoy</p>
          <Link to="/orders" className="flex items-center gap-1 text-blue-500 text-xs font-semibold">
            Ver todas <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-slate-300" />
          </div>
        ) : (data?.orders_today?.length ?? 0) === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-slate-400">Sin órdenes hoy todavía.</p>
            <Link to="/orders" className="inline-block mt-2 text-sm text-blue-500 font-semibold">
              Crear primera orden →
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {data!.orders_today.map(order => {
              const folio = order.daily_sequence != null
                ? `#${String(order.daily_sequence).padStart(3, "0")}`
                : `#${order.id}`;
              const vLabel = vehicleLabel(order.vehicle);
              const plate  = order.vehicle?.plate;

              return (
                <Link key={order.id} to="/orders"
                  className="px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[order.status] ?? "bg-slate-300"}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 font-mono shrink-0">{folio}</span>
                      <span className="text-sm font-semibold text-slate-900 truncate">{vLabel}</span>
                      {plate && (
                        <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded shrink-0 tracking-widest">
                          {plate}
                        </span>
                      )}
                    </div>
                    {order.washer_names.length > 0 && (
                      <p className="text-xs text-slate-400 mt-0.5 truncate">{order.washer_names.join(", ")}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-slate-900">{fmt(order.total)}</p>
                    <p className={`text-[11px] font-semibold ${PAY_COLOR[order.payment_status] ?? "text-slate-400"}`}>
                      {PAY_LABEL[order.payment_status] ?? order.payment_status}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
