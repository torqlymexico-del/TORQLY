import { useState, useEffect, useCallback } from "react";
import { Loader2, DollarSign, Receipt, Clock, Package, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface BasicSummary {
  target_date: string;
  total_sales: string | number;
  cash_total: string | number;
  card_total: string | number;
  transfer_total: string | number;
  courtesy_total: string | number;
  discounts_total: string | number;
  commissions_total: string | number;
  cost_total: string | number;
  estimated_profit: string | number;
  services_charged: number;
  services_canceled: number;
  pending_charges: number;
}

interface DailyRow {
  date: string;
  total_sales: string | number;
  transactions: number;
  average_ticket: string | number;
}

interface WeeklyData {
  date_from: string;
  date_to: string;
  sales_by_day?: DailyRow[];
  summary?: { total_sales: number; transactions: number; average_ticket: number };
}

type Tab = "resumen" | "semanal" | "servicios";

/* ─── Helpers ────────────────────────────────────────────────────────── */

function todayStr() { return new Date().toISOString().slice(0, 10); }
function weekAgoStr() {
  const d = new Date();
  d.setDate(d.getDate() - 6);
  return d.toISOString().slice(0, 10);
}
function fmt(v: string | number) { return `$${Number(v).toFixed(2)}`; }
function fmtDate(iso: string) {
  return new Date(iso + "T12:00:00").toLocaleDateString("es-MX", { weekday: "short", day: "2-digit", month: "short" });
}

/* ─── Stat card ──────────────────────────────────────────────────────── */

function StatCard({ label, value, sub, icon: Icon, accent }: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <div className={`p-1.5 rounded-md ${accent ?? "bg-slate-100"}`}>
          <Icon className="h-4 w-4 text-slate-600" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Reports() {
  const [tab, setTab]           = useState<Tab>("resumen");

  // Resumen
  const [summaryDate, setSummaryDate] = useState(todayStr());
  const [summary, setSummary]         = useState<BasicSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Semanal
  const [weekFrom, setWeekFrom] = useState(weekAgoStr());
  const [weekTo, setWeekTo]     = useState(todayStr());
  const [weekly, setWeekly]     = useState<WeeklyData | null>(null);
  const [weeklyLoading, setWeeklyLoading] = useState(false);

  // Servicios
  const [svcFrom, setSvcFrom]   = useState(weekAgoStr());
  const [svcTo, setSvcTo]       = useState(todayStr());
  const [svcData, setSvcData]   = useState<{ sold_services?: { service_name: string; sold_count: number; revenue: number }[] } | null>(null);
  const [svcLoading, setSvcLoading] = useState(false);

  const [error, setError] = useState("");

  /* ── Loaders ── */

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setError("");
    try {
      const res = await api.get<BasicSummary>("/reports/basic-summary", {
        params: { target_date: summaryDate },
      });
      setSummary(res.data);
    } catch {
      setError("Error al cargar el resumen.");
    } finally {
      setSummaryLoading(false);
    }
  }, [summaryDate]);

  const loadWeekly = useCallback(async () => {
    setWeeklyLoading(true);
    setError("");
    try {
      const res = await api.get<WeeklyData>("/reports/weekly", {
        params: { date_from: weekFrom, date_to: weekTo },
      });
      setWeekly(res.data);
    } catch {
      setError("Error al cargar reporte semanal.");
    } finally {
      setWeeklyLoading(false);
    }
  }, [weekFrom, weekTo]);

  const loadServices = useCallback(async () => {
    setSvcLoading(true);
    setError("");
    try {
      const res = await api.get<typeof svcData>("/reports/services", {
        params: { date_from: svcFrom, date_to: svcTo },
      });
      setSvcData(res.data);
    } catch {
      setError("Error al cargar reporte de servicios.");
    } finally {
      setSvcLoading(false);
    }
  }, [svcFrom, svcTo]);

  useEffect(() => { if (tab === "resumen") loadSummary(); }, [tab, loadSummary]);
  useEffect(() => { if (tab === "semanal") loadWeekly(); }, [tab, loadWeekly]);
  useEffect(() => { if (tab === "servicios") loadServices(); }, [tab, loadServices]);

  /* ── Render ── */

  const TABS: { key: Tab; label: string }[] = [
    { key: "resumen",   label: "Resumen diario" },
    { key: "semanal",   label: "Semanal" },
    { key: "servicios", label: "Servicios" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Reportes</h1>
        <p className="text-sm text-slate-500">Análisis de operación</p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setError(""); }}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "border-slate-900 text-slate-900"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Resumen diario ── */}
      {tab === "resumen" && (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Fecha</label>
              <input
                type="date"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                value={summaryDate}
                onChange={e => setSummaryDate(e.target.value)}
              />
            </div>
            <Button variant="outline" size="sm" onClick={loadSummary}>Consultar</Button>
          </div>

          {summaryLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
            </div>
          ) : summary ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                <StatCard label="Ventas totales"   value={fmt(summary.total_sales)}     icon={DollarSign}   accent="bg-emerald-100" />
                <StatCard label="Utilidad estimada" value={fmt(summary.estimated_profit)} icon={TrendingUp}   accent="bg-blue-100" />
                <StatCard label="Servicios cobrados" value={String(summary.services_charged)} icon={Receipt}  accent="bg-violet-100" />
                <StatCard label="Pendientes de cobro" value={String(summary.pending_charges)} icon={Clock}   accent="bg-amber-100" />
              </div>

              <Separator />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {/* Métodos de pago */}
                <div>
                  <p className="text-sm font-semibold text-slate-700 mb-3">Métodos de pago</p>
                  <div className="space-y-2">
                    {[
                      { label: "Efectivo",       val: summary.cash_total },
                      { label: "Tarjeta",        val: summary.card_total },
                      { label: "Transferencia",  val: summary.transfer_total },
                      { label: "Cortesía",       val: summary.courtesy_total },
                    ].map(({ label, val }) => (
                      <div key={label} className="flex justify-between text-sm py-1.5 border-b border-slate-100">
                        <span className="text-slate-600">{label}</span>
                        <span className="font-medium text-slate-900">{fmt(val)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Deducciones */}
                <div>
                  <p className="text-sm font-semibold text-slate-700 mb-3">Deducciones</p>
                  <div className="space-y-2">
                    {[
                      { label: "Descuentos",   val: summary.discounts_total,   cls: "text-red-600" },
                      { label: "Comisiones",   val: summary.commissions_total, cls: "text-orange-600" },
                      { label: "Costo estimado", val: summary.cost_total,      cls: "text-slate-600" },
                    ].map(({ label, val, cls }) => (
                      <div key={label} className="flex justify-between text-sm py-1.5 border-b border-slate-100">
                        <span className="text-slate-600">{label}</span>
                        <span className={`font-medium ${cls}`}>{fmt(val)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between text-sm py-1.5">
                      <span className="text-slate-500">Cancelados</span>
                      <span className="font-medium text-slate-700">{summary.services_canceled}</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* ── Semanal ── */}
      {tab === "semanal" && (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Desde</label>
              <input
                type="date"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                value={weekFrom}
                onChange={e => setWeekFrom(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Hasta</label>
              <input
                type="date"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                value={weekTo}
                onChange={e => setWeekTo(e.target.value)}
              />
            </div>
            <Button variant="outline" size="sm" onClick={loadWeekly}>Consultar</Button>
          </div>

          {weeklyLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
            </div>
          ) : weekly && weekly.sales_by_day ? (
            <>
              {weekly.summary && (
                <div className="grid grid-cols-3 gap-4">
                  <StatCard label="Total ventas"   value={fmt(weekly.summary.total_sales)}   icon={DollarSign} accent="bg-emerald-100" />
                  <StatCard label="Transacciones"  value={String(weekly.summary.transactions)} icon={Receipt}  accent="bg-blue-100" />
                  <StatCard label="Ticket promedio" value={fmt(weekly.summary.average_ticket)} icon={TrendingUp} accent="bg-violet-100" />
                </div>
              )}
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                      <th className="px-4 py-2.5 text-left">Día</th>
                      <th className="px-4 py-2.5 text-right">Transacciones</th>
                      <th className="px-4 py-2.5 text-right">Ticket promedio</th>
                      <th className="px-4 py-2.5 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {weekly.sales_by_day.map(row => (
                      <tr key={row.date} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 capitalize text-slate-700">{fmtDate(row.date)}</td>
                        <td className="px-4 py-2.5 text-right text-slate-600">{row.transactions}</td>
                        <td className="px-4 py-2.5 text-right text-slate-600">{fmt(row.average_ticket)}</td>
                        <td className="px-4 py-2.5 text-right font-semibold text-slate-900">{fmt(row.total_sales)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : weekly ? (
            <p className="text-sm text-slate-400 text-center py-8">Sin ventas en este período</p>
          ) : null}
        </div>
      )}

      {/* ── Servicios ── */}
      {tab === "servicios" && (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Desde</label>
              <input
                type="date"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                value={svcFrom}
                onChange={e => setSvcFrom(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-500">Hasta</label>
              <input
                type="date"
                className="rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                value={svcTo}
                onChange={e => setSvcTo(e.target.value)}
              />
            </div>
            <Button variant="outline" size="sm" onClick={loadServices}>Consultar</Button>
          </div>

          {svcLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
            </div>
          ) : svcData?.sold_services && svcData.sold_services.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                    <th className="px-4 py-2.5 text-left">Servicio</th>
                    <th className="px-4 py-2.5 text-right">Vendidos</th>
                    <th className="px-4 py-2.5 text-right">Ingresos</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {svcData.sold_services.map((s, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5 text-slate-900">{s.service_name}</td>
                      <td className="px-4 py-2.5 text-right text-slate-600">{s.sold_count}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-slate-900">{fmt(s.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : svcData ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Package className="h-10 w-10 mb-2 opacity-40" />
              <p className="text-sm">Sin servicios cobrados en este período</p>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
