import { useState, useEffect, useCallback, useRef } from "react";
import { Loader2, TrendingUp, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface Commission {
  id: number;
  user_id: number;
  user_name: string | null;
  appointment_id: number | null;
  service_job_id: number | null;
  payment_id: number | null;
  base_amount: string | number;
  extra_amount: string | number;
  total_amount: string | number;
  calculation_note: string | null;
  calculated_at: string | null;
  period_date: string | null;
}

/* ─── Helpers ────────────────────────────────────────────────────────── */

function fmt(val: string | number) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(val));
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return new Date(Number(y), Number(m) - 1, Number(d)).toLocaleDateString("es-MX", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

const ACCENT_COLORS = [
  { bg: "#6366f110", border: "#6366f1", text: "#6366f1", avatar: "#6366f1" },
  { bg: "#10b98110", border: "#10b981", text: "#10b981", avatar: "#10b981" },
  { bg: "#f59e0b10", border: "#f59e0b", text: "#f59e0b", avatar: "#f59e0b" },
  { bg: "#ef444410", border: "#ef4444", text: "#ef4444", avatar: "#ef4444" },
  { bg: "#8b5cf610", border: "#8b5cf6", text: "#8b5cf6", avatar: "#8b5cf6" },
];

function getAccent(idx: number) { return ACCENT_COLORS[idx % ACCENT_COLORS.length]; }

function periodRange(preset: string): { from: string; to: string } {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const iso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  if (preset === "today") return { from: iso(now), to: iso(now) };
  if (preset === "week") {
    const mon = new Date(now); mon.setDate(now.getDate() - now.getDay() + 1);
    const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
    return { from: iso(mon), to: iso(sun) };
  }
  // month
  return { from: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-01`, to: iso(now) };
}

/* ─── Component ──────────────────────────────────────────────────────── */

const POLL_INTERVAL = 15_000; // ms

export default function Commissions() {
  const [items, setItems]           = useState<Commission[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [preset, setPreset]         = useState("month");
  const [dateFrom, setDateFrom]     = useState(() => periodRange("month").from);
  const [dateTo, setDateTo]         = useState(() => periodRange("month").to);
  const [expanded, setExpanded]     = useState<Set<number>>(new Set());
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [agoLabel, setAgoLabel]     = useState("");
  const isFirstLoad                 = useRef(true);

  const applyPreset = (p: string) => {
    const r = periodRange(p);
    setPreset(p);
    setDateFrom(r.from);
    setDateTo(r.to);
    isFirstLoad.current = true;
  };

  // silent = auto-refresh (no spinner, keeps expanded state)
  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError("");
    try {
      const res = await api.get<Commission[]>("/commissions/", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      setItems(res.data);
      setLastUpdated(new Date());
      if (isFirstLoad.current) {
        isFirstLoad.current = false;
        setExpanded(new Set(res.data.map(c => c.user_id)));
      } else {
        // expand only newly-appearing operators
        setExpanded(prev => {
          const next = new Set(prev);
          res.data.forEach(c => { if (!prev.has(c.user_id)) next.add(c.user_id); });
          return next;
        });
      }
    } catch {
      if (!silent) setError("Error al cargar comisiones.");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [dateFrom, dateTo]);

  // First / manual load
  useEffect(() => { load(); }, [load]);

  // Auto-refresh every 15 s
  useEffect(() => {
    const id = setInterval(() => load(true), POLL_INTERVAL);
    return () => clearInterval(id);
  }, [load]);

  // Refresh when phone switches back to this tab
  useEffect(() => {
    const handler = () => { if (document.visibilityState === "visible") load(true); };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [load]);

  // "hace X" label — updates every 5 s
  useEffect(() => {
    const update = () => {
      if (!lastUpdated) { setAgoLabel(""); return; }
      const secs = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
      setAgoLabel(secs < 60 ? `hace ${secs}s` : `hace ${Math.floor(secs / 60)}min`);
    };
    update();
    const id = setInterval(update, 5000);
    return () => clearInterval(id);
  }, [lastUpdated]);

  /* ── Derived data ── */

  const byOperator = items.reduce<Record<number, {
    name: string; total: number; base: number; extra: number; count: number; rows: Commission[];
  }>>((acc, c) => {
    if (!acc[c.user_id]) acc[c.user_id] = {
      name: c.user_name ?? `Operador #${c.user_id}`,
      total: 0, base: 0, extra: 0, count: 0, rows: [],
    };
    acc[c.user_id].total += Number(c.total_amount);
    acc[c.user_id].base  += Number(c.base_amount);
    acc[c.user_id].extra += Number(c.extra_amount);
    acc[c.user_id].count += 1;
    acc[c.user_id].rows.push(c);
    return acc;
  }, {});

  const operators = Object.entries(byOperator)
    .map(([id, data]) => ({ id: Number(id), ...data }))
    .sort((a, b) => b.total - a.total);

  const grandTotal = operators.reduce((s, op) => s + op.total, 0);

  const toggleOp = (id: number) => setExpanded(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  /* ── Render ── */

  return (
    <div className="space-y-6 max-w-4xl">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Comisiones</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {dateFrom === dateTo ? formatDate(dateFrom) : `${formatDate(dateFrom)} — ${formatDate(dateTo)}`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 mt-1">
          {/* Live indicator */}
          <div className="flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <span className="text-xs font-semibold text-emerald-700 hidden sm:inline">En vivo</span>
            {agoLabel && <span className="text-xs text-emerald-600 hidden sm:inline">· {agoLabel}</span>}
          </div>
          <button
            onClick={() => { load(true); }}
            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors"
            title="Actualizar ahora"
          >
            <RefreshCw className={cn("h-4 w-4 text-slate-500", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* ── Filtros de período ─────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 items-end">
        {[
          { key: "today", label: "Hoy" },
          { key: "week",  label: "Esta semana" },
          { key: "month", label: "Este mes" },
        ].map(p => (
          <button
            key={p.key}
            onClick={() => applyPreset(p.key)}
            className={cn(
              "px-4 py-2 rounded-xl text-sm font-semibold border-2 transition-all",
              preset === p.key
                ? "bg-slate-900 border-slate-900 text-white"
                : "border-slate-200 text-slate-500 hover:border-slate-400 hover:text-slate-800"
            )}
          >
            {p.label}
          </button>
        ))}

        <div className="flex items-end gap-2 ml-2">
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500 block">Desde</label>
            <input
              type="date"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              value={dateFrom}
              onChange={e => { setDateFrom(e.target.value); setPreset("custom"); }}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-500 block">Hasta</label>
            <input
              type="date"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              value={dateTo}
              onChange={e => { setDateTo(e.target.value); setPreset("custom"); }}
            />
          </div>
          <Button variant="outline" size="sm" onClick={() => load()} className="mb-0.5">Buscar</Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 py-20 text-slate-400">
          <TrendingUp className="h-12 w-12 mb-3 opacity-30" />
          <p className="text-sm font-medium">Sin comisiones en este período</p>
        </div>
      ) : (
        <>
          {/* ── Cards de resumen ───────────────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">

            {/* Total general */}
            <div className="rounded-xl bg-slate-900 text-white px-5 py-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">Total período</p>
                <p className="text-2xl font-bold">{fmt(grandTotal)}</p>
                <p className="text-xs text-slate-400 mt-0.5">{items.length} comisión{items.length !== 1 ? "es" : ""}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-slate-600 shrink-0" />
            </div>

            {/* Por operador */}
            {operators.map((op, i) => {
              const accent = getAccent(i);
              return (
                <div
                  key={op.id}
                  className="rounded-xl border-2 px-5 py-4 bg-white"
                  style={{ borderColor: accent.border + "40", backgroundColor: accent.bg }}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0"
                      style={{ backgroundColor: accent.avatar }}
                    >
                      {op.name[0].toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900 truncate">{op.name}</p>
                      <p className="text-xs text-slate-400">{op.count} comisión{op.count !== 1 ? "es" : ""}</p>
                    </div>
                  </div>
                  <p className="text-xl font-bold" style={{ color: accent.text }}>{fmt(op.total)}</p>
                  {op.extra > 0 && (
                    <p className="text-xs text-slate-400 mt-0.5">
                      Servicio {fmt(op.base)} + adicionales {fmt(op.extra)}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          {/* ── Detalle por operador ───────────────────────────────────── */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Detalle por operador</h2>

            {operators.map((op, i) => {
              const accent = getAccent(i);
              const open = expanded.has(op.id);
              return (
                <div key={op.id} className="rounded-xl border border-slate-200 bg-white overflow-hidden">

                  {/* Encabezado del grupo */}
                  <button
                    className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors"
                    onClick={() => toggleOp(op.id)}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                        style={{ backgroundColor: accent.avatar }}
                      >
                        {op.name[0].toUpperCase()}
                      </div>
                      <span className="font-semibold text-slate-900 text-sm">{op.name}</span>
                      <span className="text-xs text-slate-400">{op.count} registro{op.count !== 1 ? "s" : ""}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-slate-900">{fmt(op.total)}</span>
                      {open
                        ? <ChevronUp className="h-4 w-4 text-slate-400" />
                        : <ChevronDown className="h-4 w-4 text-slate-400" />
                      }
                    </div>
                  </button>

                  {/* Filas de detalle */}
                  {open && (
                    <div className="border-t border-slate-100 overflow-x-auto">
                      <table className="w-full text-sm min-w-[480px]">
                        <thead>
                          <tr className="bg-slate-50 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                            <th className="px-5 py-2.5 text-left">Fecha</th>
                            <th className="px-5 py-2.5 text-left">Detalle</th>
                            <th className="px-5 py-2.5 text-right hidden sm:table-cell">Servicio</th>
                            <th className="px-5 py-2.5 text-right hidden sm:table-cell">Adicionales</th>
                            <th className="px-5 py-2.5 text-right">Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {op.rows.map(c => (
                            <tr key={c.id} className="hover:bg-slate-50/60">
                              <td className="px-5 py-3 text-slate-500 whitespace-nowrap text-xs">
                                {formatDate(c.period_date)}
                              </td>
                              <td className="px-5 py-3 text-slate-500 text-xs">
                                <span className="line-clamp-2">
                                  {c.calculation_note ?? (c.appointment_id ? `Orden #${c.appointment_id}` : "—")}
                                </span>
                              </td>
                              <td className="px-5 py-3 text-right text-slate-600 tabular-nums hidden sm:table-cell">
                                {fmt(c.base_amount)}
                              </td>
                              <td className="px-5 py-3 text-right tabular-nums hidden sm:table-cell"
                                style={{ color: Number(c.extra_amount) > 0 ? accent.text : "#94a3b8" }}
                              >
                                {Number(c.extra_amount) > 0 ? fmt(c.extra_amount) : "—"}
                              </td>
                              <td className="px-5 py-3 text-right font-bold text-slate-900 tabular-nums">
                                {fmt(c.total_amount)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="border-t border-slate-200 bg-slate-50/80">
                            <td colSpan={2} className="px-5 py-2.5 text-xs font-semibold text-slate-500 sm:hidden">
                              Subtotal {op.name}
                            </td>
                            <td colSpan={4} className="px-5 py-2.5 text-xs font-semibold text-slate-500 hidden sm:table-cell">
                              Subtotal {op.name}
                            </td>
                            <td className="px-5 py-2.5 text-right font-bold text-slate-900 tabular-nums">
                              {fmt(op.total)}
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
