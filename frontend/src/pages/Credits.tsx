import { useState, useEffect, useCallback } from "react";
import { Loader2, Plus, CreditCard, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client { id: number; name: string; }

interface CreditAccount {
  id: number;
  client_id: number;
  credit_limit: string;
  current_balance: string;
  is_active: boolean;
  notes: string | null;
}

interface CreditMovement {
  id: number;
  account_id: number;
  client_id: number;
  order_id: number | null;
  movement_type: string;
  amount: string;
  description: string | null;
}

function fmt(v: string | number): string {
  return `$${Number(v).toFixed(2)}`;
}

function movTypeLabel(t: string): string {
  const map: Record<string, string> = { cargo: "Cargo", pago: "Pago", cortesia: "Cortesía", ajuste: "Ajuste" };
  return map[t] ?? t;
}

function movTypeVariant(t: string): "default" | "warning" | "success" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "warning" | "success" | "secondary" | "destructive" | "outline"> = {
    cargo: "warning", pago: "success", cortesia: "secondary", ajuste: "outline",
  };
  return map[t] ?? "secondary";
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

// ─── Component ────────────────────────────────────────────────────────────────

export default function Credits() {
  const [accounts, setAccounts] = useState<CreditAccount[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [movements, setMovements] = useState<Record<number, CreditMovement[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loadingMov, setLoadingMov] = useState<number | null>(null);

  // Account dialog
  const [acctDlg, setAcctDlg] = useState(false);
  const [editAcct, setEditAcct] = useState<CreditAccount | null>(null);
  const [acctClientId, setAcctClientId] = useState("");
  const [acctLimit, setAcctLimit] = useState("0");
  const [acctNotes, setAcctNotes] = useState("");
  const [acctActive, setAcctActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Charge / Payment dialog
  const [movDlg, setMovDlg] = useState<"charge" | "payment" | null>(null);
  const [movAcct, setMovAcct] = useState<CreditAccount | null>(null);
  const [movAmount, setMovAmount] = useState("");
  const [movDesc, setMovDesc] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [acctRes, clientRes] = await Promise.all([
        api.get<CreditAccount[]>("/credits/"),
        api.get<Client[]>("/clients/"),
      ]);
      setAccounts(acctRes.data);
      setClients(clientRes.data);
    } catch {
      setError("Error al cargar cuentas de crédito.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const clientName = (id: number) => clients.find(c => c.id === id)?.name ?? `Cliente #${id}`;

  async function toggleExpand(acct: CreditAccount) {
    if (expanded === acct.client_id) {
      setExpanded(null);
      return;
    }
    setExpanded(acct.client_id);
    if (!movements[acct.client_id]) {
      setLoadingMov(acct.client_id);
      try {
        const res = await api.get<CreditMovement[]>(`/credits/${acct.client_id}/movements`);
        setMovements(prev => ({ ...prev, [acct.client_id]: res.data }));
      } catch {
        setError("Error al cargar movimientos.");
      } finally {
        setLoadingMov(null);
      }
    }
  }

  function openCreate() {
    setEditAcct(null);
    setAcctClientId(""); setAcctLimit("0"); setAcctNotes(""); setAcctActive(true);
    setFormError("");
    setAcctDlg(true);
  }

  function openEdit(acct: CreditAccount) {
    setEditAcct(acct);
    setAcctClientId(String(acct.client_id));
    setAcctLimit(acct.credit_limit);
    setAcctNotes(acct.notes ?? "");
    setAcctActive(acct.is_active);
    setFormError("");
    setAcctDlg(true);
  }

  async function handleSaveAccount() {
    if (!acctClientId) { setFormError("Selecciona un cliente."); return; }
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        client_id: parseInt(acctClientId),
        credit_limit: parseFloat(acctLimit) || 0,
        is_active: acctActive,
        notes: acctNotes.trim() || null,
      };
      if (editAcct) {
        await api.put(`/credits/${editAcct.client_id}`, payload);
      } else {
        await api.post("/credits/", payload);
      }
      setAcctDlg(false);
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Error al guardar la cuenta.");
    } finally {
      setSaving(false);
    }
  }

  async function handleMovement() {
    if (!movAcct || !movAmount) return;
    setSaving(true);
    try {
      const endpoint = movDlg === "charge" ? "charge" : "payment";
      await api.post(`/credits/${movAcct.client_id}/${endpoint}`, {
        amount: parseFloat(movAmount),
        description: movDesc.trim() || null,
      });
      // refresh movements and accounts
      setMovements(prev => {
        const copy = { ...prev };
        delete copy[movAcct.client_id];
        return copy;
      });
      setMovDlg(null);
      setMovAmount(""); setMovDesc("");
      load();
      if (expanded === movAcct.client_id) {
        // reload movements for this client
        api.get<CreditMovement[]>(`/credits/${movAcct.client_id}/movements`).then(res => {
          setMovements(prev => ({ ...prev, [movAcct.client_id]: res.data }));
        });
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al registrar el movimiento.");
    } finally {
      setSaving(false);
    }
  }

  // Clients without an account
  const existingClientIds = new Set(accounts.map(a => a.client_id));
  const availableClients = editAcct ? clients : clients.filter(c => !existingClientIds.has(c.id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Créditos</h1>
          <p className="text-sm text-slate-500">{accounts.length} cuenta(s) de crédito</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" />
          Nueva cuenta
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : accounts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <CreditCard className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">No hay cuentas de crédito</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          {accounts.map((acct, idx) => {
            const balance = Number(acct.current_balance);
            const limit = Number(acct.credit_limit);
            const isExpanded = expanded === acct.client_id;
            return (
              <div key={acct.id} className={idx > 0 ? "border-t border-slate-200" : ""}>
                {/* Account row */}
                <div className={`flex items-center gap-4 px-4 py-3 hover:bg-slate-50 ${isExpanded ? "bg-slate-50" : "bg-white"}`}>
                  <button className="flex-1 flex items-center gap-4 text-left" onClick={() => toggleExpand(acct)}>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900">{clientName(acct.client_id)}</p>
                      <p className="text-xs text-slate-500">Límite: {fmt(acct.credit_limit)}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className={`font-bold text-lg ${balance > 0 ? "text-amber-600" : "text-slate-900"}`}>{fmt(acct.current_balance)}</p>
                      <p className="text-xs text-slate-400">saldo pendiente</p>
                    </div>
                    <Badge variant={acct.is_active ? "success" : "secondary"}>{acct.is_active ? "Activa" : "Inactiva"}</Badge>
                    {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />}
                  </button>
                  <div className="flex gap-1 shrink-0">
                    <Button size="sm" variant="outline" onClick={() => { setMovAcct(acct); setMovAmount(""); setMovDesc(""); setMovDlg("charge"); }}>
                      + Cargo
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { setMovAcct(acct); setMovAmount(""); setMovDesc(""); setMovDlg("payment"); }}>
                      − Pago
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => openEdit(acct)}>Editar</Button>
                  </div>
                </div>

                {/* Expanded movements */}
                {isExpanded && (
                  <div className="border-t border-slate-100 bg-slate-50 px-6 pb-4 pt-3">
                    {loadingMov === acct.client_id ? (
                      <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-slate-300" /></div>
                    ) : (movements[acct.client_id] ?? []).length === 0 ? (
                      <p className="text-xs text-slate-400 py-2">Sin movimientos</p>
                    ) : (
                      <div className="space-y-1">
                        {(movements[acct.client_id] ?? []).slice().reverse().map(mv => (
                          <div key={mv.id} className="flex items-center justify-between rounded bg-white border border-slate-100 px-3 py-2 text-sm">
                            <div className="flex items-center gap-3">
                              <Badge variant={movTypeVariant(mv.movement_type)}>{movTypeLabel(mv.movement_type)}</Badge>
                              <span className="text-slate-600">{mv.description ?? "—"}</span>
                              {mv.order_id && <span className="text-xs text-slate-400">Orden #{mv.order_id}</span>}
                            </div>
                            <span className={`font-semibold ${mv.movement_type === "pago" ? "text-emerald-600" : "text-amber-600"}`}>
                              {mv.movement_type === "pago" ? "+" : "−"}{fmt(mv.amount)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    {acct.credit_limit && limit > 0 && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs text-slate-500 mb-1">
                          <span>Utilizado</span>
                          <span>{fmt(balance)} / {fmt(limit)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${balance / limit > 0.8 ? "bg-red-500" : balance / limit > 0.5 ? "bg-amber-400" : "bg-emerald-500"}`}
                            style={{ width: `${Math.min(100, (balance / limit) * 100)}%` }}
                          />
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

      {/* ── Account dialog ── */}
      <Dialog open={acctDlg} onOpenChange={o => { if (!o) setAcctDlg(false); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editAcct ? "Editar cuenta" : "Nueva cuenta de crédito"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {formError && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{formError}</div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Cliente <span className="text-red-500">*</span></label>
              <select className={inputCls} value={acctClientId} onChange={e => setAcctClientId(e.target.value)} disabled={!!editAcct}>
                <option value="">Seleccionar cliente…</option>
                {(editAcct ? clients : availableClients).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Límite de crédito</label>
              <input type="number" min="0" step="0.01" className={inputCls} value={acctLimit} onChange={e => setAcctLimit(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={acctNotes} onChange={e => setAcctNotes(e.target.value)} placeholder="Opcional" />
            </div>
            {editAcct && (
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={acctActive} onChange={e => setAcctActive(e.target.checked)} />
                Cuenta activa
              </label>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAcctDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleSaveAccount} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editAcct ? "Guardar cambios" : "Crear cuenta"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Charge / Payment dialog ── */}
      <Dialog open={movDlg !== null} onOpenChange={o => { if (!o) setMovDlg(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {movDlg === "charge" ? "Registrar cargo" : "Registrar pago"} — {movAcct ? clientName(movAcct.client_id) : ""}
            </DialogTitle>
            <DialogDescription>
              {movDlg === "charge"
                ? "Agrega un cargo a la cuenta del cliente."
                : "Registra un pago a cuenta del cliente."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Monto <span className="text-red-500">*</span></label>
              <input type="number" min="0.01" step="0.01" className={inputCls} value={movAmount} onChange={e => setMovAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Descripción</label>
              <input className={inputCls} value={movDesc} onChange={e => setMovDesc(e.target.value)} placeholder="Opcional" />
            </div>
            {movAcct && (
              <p className="text-sm text-slate-600">
                Saldo actual: <span className="font-semibold text-amber-600">{fmt(movAcct.current_balance)}</span>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMovDlg(null)} disabled={saving}>Cancelar</Button>
            <Button
              variant={movDlg === "charge" ? "default" : "default"}
              onClick={handleMovement}
              disabled={saving || !movAmount}
            >
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {movDlg === "charge" ? "Registrar cargo" : "Registrar pago"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
