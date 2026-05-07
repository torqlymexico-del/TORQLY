import { useState, useEffect, useCallback } from "react";
import { Loader2, Plus, Wallet } from "lucide-react";
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

function fmt(v: string | number | null | undefined): string {
  if (v == null) return "—";
  return `$${Number(v).toFixed(2)}`;
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

function StatCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg bg-white border border-slate-200 p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-lg font-bold ${highlight ? "text-emerald-700" : "text-slate-900"}`}>{value}</p>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function CashSessions() {
  const [session, setSession] = useState<CashSession | null | undefined>(undefined);
  const [sessions, setSessions] = useState<CashSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  // Open session dialog
  const [openDlg, setOpenDlg] = useState(false);
  const [openAmount, setOpenAmount] = useState("0");
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

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [openRes, listRes] = await Promise.all([
        api.get<CashSession | null>("/cash-sessions/open"),
        api.get<CashSession[]>("/cash-sessions/"),
      ]);
      setSession(openRes.data ?? null);
      setSessions(listRes.data);
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
      setOpenAmount("0");
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

  function openCloseDialog() {
    if (!session) return;
    const expected = Number(session.opening_amount) + Number(session.total_sales_cash) - Number(session.total_expenses);
    setCloseAmount(expected.toFixed(2));
    setCloseDlg(true);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Caja</h1>
          <p className="text-sm text-slate-500">Sesiones de caja registradora</p>
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
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 space-y-5">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold text-emerald-900">Sesión #{session.id} — Abierta</h2>
              <p className="text-sm text-emerald-700 mt-0.5">Efectivo inicial: {fmt(session.opening_amount)}</p>
            </div>
            <Badge variant="success">Abierta</Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <StatCard label="Ventas efectivo" value={fmt(session.total_sales_cash)} />
            <StatCard label="Ventas tarjeta" value={fmt(session.total_sales_card)} />
            <StatCard label="Ventas transf." value={fmt(session.total_sales_transfer)} />
            <StatCard label="Total ventas" value={fmt(session.total_sales)} highlight />
            <StatCard label="Egresos" value={fmt(session.total_expenses)} />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => {
              setMovType("egreso"); setMovCategory("general");
              setMovAmount(""); setMovDesc("");
              setMovDlg(true);
            }}>
              <Plus className="h-4 w-4 mr-1" /> Movimiento
            </Button>
            <Button variant="destructive" onClick={openCloseDialog}>
              Cerrar caja
            </Button>
          </div>
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
      {sessions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Historial</h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">Estado</th>
                  <th className="px-4 py-3 text-right">Apertura</th>
                  <th className="px-4 py-3 text-right">Ventas</th>
                  <th className="px-4 py-3 text-right">Egresos</th>
                  <th className="px-4 py-3 text-right">Cierre</th>
                  <th className="px-4 py-3 text-right">Diferencia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map(s => {
                  const diff = Number(s.difference_amount ?? 0);
                  return (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-slate-500">#{s.id}</td>
                      <td className="px-4 py-3">
                        <Badge variant={s.status === "abierta" ? "success" : "secondary"}>{s.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right">{fmt(s.opening_amount)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.total_sales)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.total_expenses)}</td>
                      <td className="px-4 py-3 text-right">{fmt(s.closing_amount)}</td>
                      <td className={`px-4 py-3 text-right font-medium ${diff < 0 ? "text-red-600" : diff > 0 ? "text-emerald-600" : "text-slate-500"}`}>
                        {s.difference_amount != null ? fmt(s.difference_amount) : "—"}
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
            <DialogDescription>Ingresa el monto inicial en efectivo.</DialogDescription>
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
            <DialogDescription>Ingresa el efectivo físico contado en caja.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {session && (
              <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-500">Apertura</span>
                  <span>{fmt(session.opening_amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">+ Ventas efectivo</span>
                  <span>{fmt(session.total_sales_cash)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">− Egresos</span>
                  <span>{fmt(session.total_expenses)}</span>
                </div>
                <div className="flex justify-between font-semibold border-t border-slate-200 pt-1 mt-1">
                  <span>Esperado</span>
                  <span>{fmt(Number(session.opening_amount) + Number(session.total_sales_cash) - Number(session.total_expenses))}</span>
                </div>
              </div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Efectivo contado</label>
              <input type="number" min="0" step="0.01" className={inputCls} value={closeAmount} onChange={e => setCloseAmount(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={closeNotes} onChange={e => setCloseNotes(e.target.value)} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseDlg(false)} disabled={saving}>Cancelar</Button>
            <Button variant="destructive" onClick={handleCloseSession} disabled={saving}>
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
                <option value="ingreso">Ingreso</option>
                <option value="egreso">Egreso</option>
                <option value="retiro">Retiro</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Categoría</label>
              <input className={inputCls} value={movCategory} onChange={e => setMovCategory(e.target.value)} placeholder="general" />
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
    </div>
  );
}
