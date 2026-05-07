import { useState, useEffect, useCallback } from "react";
import { Loader2, DollarSign, ChevronDown, ChevronUp, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Operator {
  id: number;
  name: string;
  role: string;
  commission_percentage: string;
  weekly_salary: string;
}

interface OperatorSummary {
  user_id: number;
  name: string;
  pending_commissions: Array<{
    id: number;
    order_id: number;
    commission_amount: string;
    commission_percent: string;
  }>;
  deductions: Array<{
    id: number;
    deduction_type: string;
    quantity: number;
    unit_amount: string;
    total_amount: string;
    notes: string | null;
  }>;
  total_pending_commissions: number;
  total_deductions: number;
  net_payable: number;
}

function fmt(v: string | number | null | undefined): string {
  if (v == null) return "—";
  return `$${Number(v).toFixed(2)}`;
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

// ─── Component ────────────────────────────────────────────────────────────────

export default function Payroll() {
  const [operators, setOperators] = useState<Operator[]>([]);
  const [summaries, setSummaries] = useState<Record<number, OperatorSummary>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loadingSummary, setLoadingSummary] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  // Deduction dialog
  const [dedDlg, setDedDlg] = useState(false);
  const [dedOperator, setDedOperator] = useState<Operator | null>(null);
  const [dedType, setDedType] = useState("trapos");
  const [dedQty, setDedQty] = useState("1");
  const [dedUnit, setDedUnit] = useState("");
  const [dedNotes, setDedNotes] = useState("");

  // Commission payment dialog
  const [comDlg, setComDlg] = useState(false);
  const [comOperator, setComOperator] = useState<Operator | null>(null);
  const [comAmount, setComAmount] = useState("");
  const [comSource, setComSource] = useState("efectivo");
  const [comNotes, setComNotes] = useState("");

  // Salary payment dialog
  const [salDlg, setSalDlg] = useState(false);
  const [salOperator, setSalOperator] = useState<Operator | null>(null);
  const [salAmount, setSalAmount] = useState("");
  const [salSource, setSalSource] = useState("efectivo");
  const [salNotes, setSalNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<Operator[]>("/payroll/operators");
      setOperators(res.data);
    } catch {
      setError("Error al cargar operadores.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function toggleExpand(op: Operator) {
    if (expanded === op.id) { setExpanded(null); return; }
    setExpanded(op.id);
    if (!summaries[op.id]) {
      setLoadingSummary(op.id);
      try {
        const res = await api.get<OperatorSummary>(`/payroll/operators/${op.id}/summary`);
        setSummaries(prev => ({ ...prev, [op.id]: res.data }));
      } catch {
        setError("Error al cargar el resumen del operador.");
      } finally {
        setLoadingSummary(null);
      }
    }
  }

  function refreshSummary(userId: number) {
    api.get<OperatorSummary>(`/payroll/operators/${userId}/summary`).then(res => {
      setSummaries(prev => ({ ...prev, [userId]: res.data }));
    });
  }

  async function handleDeduction() {
    if (!dedOperator) return;
    setSaving(true);
    try {
      await api.post("/payroll/deductions", {
        user_id: dedOperator.id,
        deduction_type: dedType || "trapos",
        quantity: parseInt(dedQty) || 1,
        unit_amount: parseFloat(dedUnit) || 0,
        notes: dedNotes.trim() || null,
      });
      setDedDlg(false);
      refreshSummary(dedOperator.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al registrar la deducción.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePayCommission() {
    if (!comOperator) return;
    setSaving(true);
    try {
      await api.post("/payroll/pay-commission", {
        user_id: comOperator.id,
        amount: parseFloat(comAmount) || 0,
        payment_source: comSource,
        notes: comNotes.trim() || null,
      });
      setComDlg(false);
      refreshSummary(comOperator.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al registrar el pago de comisión.");
    } finally {
      setSaving(false);
    }
  }

  async function handlePaySalary() {
    if (!salOperator) return;
    setSaving(true);
    try {
      await api.post("/payroll/pay-salary", {
        user_id: salOperator.id,
        amount: parseFloat(salAmount) || 0,
        payment_source: salSource,
        notes: salNotes.trim() || null,
      });
      setSalDlg(false);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al registrar el pago de sueldo.");
    } finally {
      setSaving(false);
    }
  }

  function openDeduction(op: Operator) {
    setDedOperator(op); setDedType("trapos"); setDedQty("1"); setDedUnit(""); setDedNotes("");
    setDedDlg(true);
  }

  function openCommissionPay(op: Operator) {
    setComOperator(op);
    const summary = summaries[op.id];
    setComAmount(summary ? String(summary.total_pending_commissions) : "");
    setComSource("efectivo"); setComNotes("");
    setComDlg(true);
  }

  function openSalaryPay(op: Operator) {
    setSalOperator(op);
    setSalAmount(op.weekly_salary ?? "");
    setSalSource("efectivo"); setSalNotes("");
    setSalDlg(true);
  }

  const roleLabel = (role: string) => {
    const map: Record<string, string> = { operador: "Operador", lavador: "Lavador", admin: "Admin", supervisor: "Supervisor" };
    return map[role] ?? role;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Nómina</h1>
        <p className="text-sm text-slate-500">Comisiones, deducciones y pagos de operadores</p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : operators.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <DollarSign className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">No hay operadores registrados</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          {operators.map((op, idx) => {
            const summary = summaries[op.id];
            const isExpanded = expanded === op.id;
            return (
              <div key={op.id} className={idx > 0 ? "border-t border-slate-200" : ""}>
                {/* Operator row */}
                <div className={`flex items-center gap-4 px-4 py-3 hover:bg-slate-50 ${isExpanded ? "bg-slate-50" : "bg-white"}`}>
                  <button className="flex-1 flex items-center gap-4 text-left" onClick={() => toggleExpand(op)}>
                    <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-700 font-semibold text-sm shrink-0">
                      {op.name[0]?.toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900">{op.name}</p>
                      <p className="text-xs text-slate-500">{roleLabel(op.role)} · {op.commission_percentage}% comisión</p>
                    </div>
                    {summary && (
                      <div className="text-right shrink-0">
                        <p className={`font-bold ${summary.net_payable > 0 ? "text-amber-600" : "text-slate-500"}`}>
                          {fmt(summary.net_payable)}
                        </p>
                        <p className="text-xs text-slate-400">por pagar</p>
                      </div>
                    )}
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />}
                  </button>
                  <div className="flex gap-1 shrink-0">
                    <Button size="sm" variant="outline" onClick={() => openDeduction(op)}>
                      <Plus className="h-3 w-3 mr-1" /> Deducción
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => openCommissionPay(op)}>
                      Pagar comisión
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => openSalaryPay(op)}>
                      Pagar sueldo
                    </Button>
                  </div>
                </div>

                {/* Expanded summary */}
                {isExpanded && (
                  <div className="border-t border-slate-100 bg-slate-50 px-6 pb-5 pt-4">
                    {loadingSummary === op.id ? (
                      <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-slate-300" /></div>
                    ) : summary ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Pending commissions */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Comisiones pendientes</h3>
                            <Badge variant="warning">{fmt(summary.total_pending_commissions)}</Badge>
                          </div>
                          {summary.pending_commissions.length === 0 ? (
                            <p className="text-xs text-slate-400">Sin comisiones pendientes</p>
                          ) : (
                            <div className="space-y-1">
                              {summary.pending_commissions.map(c => (
                                <div key={c.id} className="flex justify-between rounded bg-white border border-slate-100 px-3 py-2 text-sm">
                                  <span className="text-slate-600">Orden #{c.order_id}</span>
                                  <span className="font-medium">{fmt(c.commission_amount)} ({c.commission_percent}%)</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Deductions */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Deducciones</h3>
                            <Badge variant="destructive">{fmt(summary.total_deductions)}</Badge>
                          </div>
                          {summary.deductions.length === 0 ? (
                            <p className="text-xs text-slate-400">Sin deducciones</p>
                          ) : (
                            <div className="space-y-1">
                              {summary.deductions.map(d => (
                                <div key={d.id} className="flex justify-between rounded bg-white border border-slate-100 px-3 py-2 text-sm">
                                  <div>
                                    <span className="font-medium capitalize">{d.deduction_type}</span>
                                    <span className="text-slate-400 ml-2">×{d.quantity}</span>
                                    {d.notes && <span className="text-xs text-slate-400 ml-2">({d.notes})</span>}
                                  </div>
                                  <span className="text-red-600 font-medium">{fmt(d.total_amount)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">No se pudo cargar el resumen.</p>
                    )}

                    {summary && (
                      <div className="mt-4 rounded-lg border border-slate-200 bg-white px-4 py-3">
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <p className="text-xs text-slate-500">Comisiones pendientes</p>
                            <p className="font-bold text-amber-600">{fmt(summary.total_pending_commissions)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Total deducciones</p>
                            <p className="font-bold text-red-600">{fmt(summary.total_deductions)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Neto a pagar</p>
                            <p className={`font-bold text-lg ${summary.net_payable >= 0 ? "text-emerald-600" : "text-red-600"}`}>{fmt(summary.net_payable)}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Deduction dialog ── */}
      <Dialog open={dedDlg} onOpenChange={o => { if (!o) setDedDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Agregar deducción — {dedOperator?.name}</DialogTitle>
            <DialogDescription>Registra una deducción al operador (e.g. trapos, herramientas).</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Tipo</label>
              <input className={inputCls} value={dedType} onChange={e => setDedType(e.target.value)} placeholder="trapos" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Cantidad</label>
                <input type="number" min="1" className={inputCls} value={dedQty} onChange={e => setDedQty(e.target.value)} />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Precio unitario</label>
                <input type="number" min="0" step="0.01" className={inputCls} value={dedUnit} onChange={e => setDedUnit(e.target.value)} placeholder="0.00" />
              </div>
            </div>
            {dedUnit && dedQty && (
              <p className="text-sm text-slate-600">Total: <span className="font-bold">{fmt(parseFloat(dedUnit) * parseInt(dedQty))}</span></p>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={dedNotes} onChange={e => setDedNotes(e.target.value)} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDedDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleDeduction} disabled={saving || !dedUnit}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Commission payment dialog ── */}
      <Dialog open={comDlg} onOpenChange={o => { if (!o) setComDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Pagar comisión — {comOperator?.name}</DialogTitle>
            <DialogDescription>Registra el pago de comisiones al operador.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Monto a pagar <span className="text-red-500">*</span></label>
              <input type="number" min="0.01" step="0.01" className={inputCls} value={comAmount} onChange={e => setComAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Fuente de pago</label>
              <select className={inputCls} value={comSource} onChange={e => setComSource(e.target.value)}>
                <option value="efectivo">Efectivo</option>
                <option value="transferencia">Transferencia</option>
                <option value="tarjeta">Tarjeta</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={comNotes} onChange={e => setComNotes(e.target.value)} placeholder="Opcional" />
            </div>
            {comOperator && summaries[comOperator.id] && (
              <p className="text-sm text-slate-600">
                Pendiente: <span className="font-bold text-amber-600">{fmt(summaries[comOperator.id].total_pending_commissions)}</span>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setComDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handlePayCommission} disabled={saving || !comAmount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Pagar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Salary payment dialog ── */}
      <Dialog open={salDlg} onOpenChange={o => { if (!o) setSalDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Pagar sueldo — {salOperator?.name}</DialogTitle>
            <DialogDescription>Registra el pago de sueldo al operador.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Monto a pagar <span className="text-red-500">*</span></label>
              <input type="number" min="0.01" step="0.01" className={inputCls} value={salAmount} onChange={e => setSalAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Fuente de pago</label>
              <select className={inputCls} value={salSource} onChange={e => setSalSource(e.target.value)}>
                <option value="efectivo">Efectivo</option>
                <option value="transferencia">Transferencia</option>
                <option value="tarjeta">Tarjeta</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={salNotes} onChange={e => setSalNotes(e.target.value)} placeholder="Opcional" />
            </div>
            {salOperator && (
              <p className="text-sm text-slate-600">
                Sueldo semanal: <span className="font-bold">{fmt(salOperator.weekly_salary)}</span>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSalDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handlePaySalary} disabled={saving || !salAmount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Pagar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
