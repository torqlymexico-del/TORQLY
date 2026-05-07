import { useState, useEffect, useCallback } from "react";
import { Loader2, Plus, Wallet, Ban, TrendingUp, TrendingDown, ArrowDownLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CashSession {
  id: number;
  opening_amount: string;
  closed_by_id: number | null;
  closing_amount: string | null;
  expected_amount: string | null;
  difference_amount: string | null;
  total_sales_cash: string;
  total_sales_card: string;
  total_sales_transfer: string;
  total_sales: string;
  total_expenses: string;
  status: string;
  notes: string | null;
}

interface CashMovement {
  id: number;
  session_id: number;
  movement_type: string;
  category: string;
  amount: string;
  description: string | null;
  is_void: boolean;
  void_reason: string | null;
  created_by_id: number | null;
  created_at: string | null;
}

function fmt(v: string | number | null | undefined): string {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

function StatCard({ label, value, sub, color = "default" }: {
  label: string; value: string; sub?: string;
  color?: "default" | "green" | "red" | "blue" | "amber";
}) {
  const colors = {
    default: "bg-white border-slate-200 text-slate-900",
    green: "bg-emerald-50 border-emerald-200 text-emerald-800",
    red: "bg-red-50 border-red-200 text-red-800",
    blue: "bg-blue-50 border-blue-200 text-blue-800",
    amber: "bg-amber-50 border-amber-200 text-amber-800",
  };
  return (
    <div className={`rounded-lg border p-3 ${colors[color]}`}>
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-lg font-bold">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

const MOV_LABELS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  ingreso: { label: "Ingreso", color: "text-emerald-700 bg-emerald-50 border-emerald-200", icon: <TrendingUp className="h-3 w-3" /> },
  egreso: { label: "Egreso", color: "text-red-700 bg-red-50 border-red-200", icon: <TrendingDown className="h-3 w-3" /> },
  retiro: { label: "Retiro", color: "text-amber-700 bg-amber-50 border-amber-200", icon: <ArrowDownLeft className="h-3 w-3" /> },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function CashSessions() {
  const [session, setSession] = useState<CashSession | null | undefined>(undefined);
  const [sessions, setSessions] = useState<CashSession[]>([]);
  const [movements, setMovements] = useState<CashMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Open session dialog
  const [openDlg, setOpenDlg] = useState(false);
  const [openAmount, setOpenAmount] = useState("500");
  const [openNotes, setOpenNotes] = useState("");

  // Close session dialog
  const [closeDlg, setCloseDlg] = useState(false);
  const [closeAmount, setCloseAmount] = useState("");
  const [closeNotes, setCloseNotes] = useState("");

  // Movement dialog
  const [movDlg, setMovDlg] = useState(false);
  const [movType, setMovType] = useState("egreso");
  const [movCategory, setMovCategory] = useState("general");
  const [movAmount, setMovAmount] = useState("");
  const [movDesc, setMovDesc] = useState("");

  // Void dialog
  const [voidDlg, setVoidDlg] = useState(false);
  const [voidTarget, setVoidTarget] = useState<CashMovement | null>(null);
  const [voidReason, setVoidReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [openRes, listRes] = await Promise.all([
        api.get<CashSession | null>("/cash-sessions/open"),
        api.get<CashSession[]>("/cash-sessions/"),
      ]);
      const openSession = openRes.data ?? null;
      setSession(openSession);
      setSessions(listRes.data);

      if (openSession) {
        const movRes = await api.get<CashMovement[]>(`/cash-sessions/${openSession.id}/movements`);
        setMovements(movRes.data);
      } else {
        setMovements([]);
      }
    } catch {
      setError("Error al cargar la caja.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleOpenSession() {
    setSaving(true);
    setError("");
    try {
      await api.post("/cash-sessions/open", {
        opening_amount: parseFloat(openAmount) || 0,
        notes: openNotes || null,
      });
      setOpenDlg(false);
      setOpenAmount("500");
      setOpenNotes("");
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al abrir la caja.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCloseSession() {
    if (!session) return;
    setSaving(true);
    setError("");
    try {
      await api.post(`/cash-sessions/${session.id}/close`, {
        closing_amount: parseFloat(closeAmount) || 0,
        notes: closeNotes || null,
      });
      setCloseDlg(false);
      setCloseNotes("");
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al cerrar la caja.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAddMovement() {
    if (!session || !movAmount) return;
    setSaving(true);
    setError("");
    try {
      await api.post(`/cash-sessions/${session.id}/movements`, {
        movement_type: movType,
        category: movCategory || "general",
        amount: parseFloat(movAmount),
        description: movDesc || null,
      });
      setMovDlg(false);
      setMovAmount("");
      setMovDesc("");
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al registrar el movimiento.");
    } finally {
      setSaving(false);
    }
  }

  async function handleVoidMovement() {
    if (!voidTarget || !voidReason.trim()) return;
    setSaving(true);
    setError("");
    try {
      await api.post(`/cash-sessions/movements/${voidTarget.id}/void`, { void_reason: voidReason });
      setVoidDlg(false);
      setVoidTarget(null);
      setVoidReason("");
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al anular el movimiento.");
    } finally {
      setSaving(false);
    }
  }

  function openCloseDialog() {
    if (!session) return;
    const expected = Number(session.opening_amount) + Number(session.total_sales_cash) - Number(session.total_expenses);
    setCloseAmount(expected.toFixed(2));
    setCloseDlg(true);
  }

  const expected = session
    ? Number(session.opening_amount) + Number(session.total_sales_cash) - Number(session.total_expenses)
    : 0;

  const closeDiff = parseFloat(closeAmount || "0") - expected;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Caja</h1>
          <p className="text-sm text-slate-500">Control de efectivo y movimientos</p>
        </div>
        {session === null && (
          <Button onClick={() => setOpenDlg(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Abrir caja
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : session ? (
        /* ── Open session view ── */
        <div className="space-y-4">
          {/* Session header */}
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-emerald-900">Sesión #{session.id}</h2>
                <Badge variant="success">Abierta</Badge>
              </div>
              <p className="text-sm text-emerald-700 mt-0.5">Efectivo inicial: {fmt(session.opening_amount)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-emerald-600 font-medium uppercase tracking-wide">Efectivo en caja</p>
              <p className="text-2xl font-bold text-emerald-900">{fmt(expected)}</p>
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard label="Ventas efectivo" value={fmt(session.total_sales_cash)} color="green" />
            <StatCard label="Ventas tarjeta" value={fmt(session.total_sales_card)} color="blue" />
            <StatCard label="Ventas transf." value={fmt(session.total_sales_transfer)} color="blue" />
            <StatCard label="Egresos / Retiros" value={fmt(session.total_expenses)} color="red" />
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => {
              setMovType("egreso"); setMovCategory("general");
              setMovAmount(""); setMovDesc("");
              setMovDlg(true);
            }}>
              <Plus className="h-4 w-4 mr-1" /> Registrar movimiento
            </Button>
            <Button variant="destructive" onClick={openCloseDialog}>
              Cerrar caja
            </Button>
          </div>

          {/* Movements list */}
          {movements.length > 0 && (
            <div className="rounded-lg border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 border-b border-slate-200 px-4 py-2">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Movimientos manuales</p>
              </div>
              <div className="divide-y divide-slate-100">
                {movements.map(m => {
                  const meta = MOV_LABELS[m.movement_type] ?? { label: m.movement_type, color: "text-slate-700 bg-slate-50 border-slate-200", icon: null };
                  return (
                    <div key={m.id} className={`flex items-center gap-3 px-4 py-3 ${m.is_void ? "opacity-50" : ""}`}>
                      <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-medium ${meta.color}`}>
                        {meta.icon}{meta.label}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{m.category}</p>
                        {m.description && <p className="text-xs text-slate-500 truncate">{m.description}</p>}
                        {m.is_void && m.void_reason && <p className="text-xs text-red-500">Anulado: {m.void_reason}</p>}
                      </div>
                      <p className={`text-sm font-semibold tabular-nums ${m.movement_type === "ingreso" ? "text-emerald-700" : "text-red-700"}`}>
                        {m.movement_type === "ingreso" ? "+" : "−"}{fmt(m.amount)}
                      </p>
                      {!m.is_void && (
                        <button
                          onClick={() => { setVoidTarget(m); setVoidReason(""); setVoidDlg(true); }}
                          className="text-slate-400 hover:text-red-500 transition-colors"
                          title="Anular"
                        >
                          <Ban className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ── No open session ── */
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Wallet className="h-14 w-14 mb-3 opacity-30" />
          <p className="text-sm">No hay caja abierta</p>
          <Button className="mt-4" onClick={() => setOpenDlg(true)}>
            <Plus className="h-4 w-4 mr-1" /> Abrir caja
          </Button>
        </div>
      )}

      {/* ── Session history ── */}
      {sessions.filter(s => s.status !== "abierta").length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Historial de sesiones</h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-right">Apertura</th>
                  <th className="px-4 py-3 text-right">Ventas totales</th>
                  <th className="px-4 py-3 text-right">Egresos</th>
                  <th className="px-4 py-3 text-right">Esperado</th>
                  <th className="px-4 py-3 text-right">Contado</th>
                  <th className="px-4 py-3 text-right">Diferencia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.filter(s => s.status !== "abierta").map(s => {
                  const diff = Number(s.difference_amount ?? 0);
                  return (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-slate-500">#{s.id}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.opening_amount)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.total_sales)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.total_expenses)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.expected_amount)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.closing_amount)}</td>
                      <td className={`px-4 py-3 text-right font-semibold ${diff < 0 ? "text-red-600" : diff > 0 ? "text-emerald-600" : "text-slate-400"}`}>
                        {s.difference_amount != null ? (diff >= 0 ? "+" : "") + fmt(s.difference_amount) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Open session dialog ── */}
      <Dialog open={openDlg} onOpenChange={o => { if (!o) setOpenDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Abrir caja</DialogTitle>
            <DialogDescription>Ingresa el efectivo inicial en caja.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Efectivo inicial</label>
              <input type="number" min="0" step="0.01" className={inputCls} value={openAmount} onChange={e => setOpenAmount(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={openNotes} onChange={e => setOpenNotes(e.target.value)} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleOpenSession} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Abrir caja
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Close session dialog ── */}
      <Dialog open={closeDlg} onOpenChange={o => { if (!o) setCloseDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Cerrar caja</DialogTitle>
            <DialogDescription>Cuenta el efectivo físico e ingresa el total.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {session && (
              <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm space-y-1.5">
                <div className="flex justify-between text-slate-600">
                  <span>Apertura</span><span>{fmt(session.opening_amount)}</span>
                </div>
                <div className="flex justify-between text-emerald-700">
                  <span>+ Ventas efectivo</span><span>{fmt(session.total_sales_cash)}</span>
                </div>
                <div className="flex justify-between text-red-700">
                  <span>− Egresos / Retiros</span><span>{fmt(session.total_expenses)}</span>
                </div>
                <div className="flex justify-between font-semibold border-t border-slate-200 pt-1.5 mt-1">
                  <span>Esperado en caja</span><span>{fmt(expected)}</span>
                </div>
              </div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Efectivo contado <span className="text-red-500">*</span></label>
              <input
                type="number" min="0" step="0.01" className={inputCls}
                value={closeAmount} onChange={e => setCloseAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>
            {closeAmount && (
              <div className={`rounded-lg border px-4 py-3 text-sm flex justify-between font-semibold ${
                closeDiff < 0 ? "bg-red-50 border-red-200 text-red-700" :
                closeDiff > 0 ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                "bg-slate-50 border-slate-200 text-slate-600"
              }`}>
                <span>Diferencia</span>
                <span>{closeDiff >= 0 ? "+" : ""}{fmt(closeDiff)}</span>
              </div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={closeNotes} onChange={e => setCloseNotes(e.target.value)} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseDlg(false)} disabled={saving}>Cancelar</Button>
            <Button variant="destructive" onClick={handleCloseSession} disabled={saving || !closeAmount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Cerrar caja
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Movement dialog ── */}
      <Dialog open={movDlg} onOpenChange={o => { if (!o) setMovDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Registrar movimiento</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Tipo</label>
              <select className={inputCls} value={movType} onChange={e => setMovType(e.target.value)}>
                <option value="ingreso">Ingreso — entra efectivo a caja</option>
                <option value="egreso">Egreso — sale efectivo de caja</option>
                <option value="retiro">Retiro — retiro de fondos</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Categoría</label>
              <input className={inputCls} value={movCategory} onChange={e => setMovCategory(e.target.value)} placeholder="ej. gastos, proveedor, comisión" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Monto <span className="text-red-500">*</span></label>
              <input type="number" min="0.01" step="0.01" className={inputCls} value={movAmount} onChange={e => setMovAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Descripción</label>
              <input className={inputCls} value={movDesc} onChange={e => setMovDesc(e.target.value)} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMovDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAddMovement} disabled={saving || !movAmount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Void movement dialog ── */}
      <Dialog open={voidDlg} onOpenChange={o => { if (!o) { setVoidDlg(false); setVoidTarget(null); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Anular movimiento</DialogTitle>
            <DialogDescription>
              {voidTarget && (
                <>Anularás: <strong>{voidTarget.category}</strong> por <strong>{fmt(voidTarget.amount)}</strong></>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Motivo <span className="text-red-500">*</span></label>
            <input className={inputCls} value={voidReason} onChange={e => setVoidReason(e.target.value)} placeholder="Describe el motivo de la anulación" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setVoidDlg(false); setVoidTarget(null); }} disabled={saving}>Cancelar</Button>
            <Button variant="destructive" onClick={handleVoidMovement} disabled={saving || !voidReason.trim()}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Anular
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
