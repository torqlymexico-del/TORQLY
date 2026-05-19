import { useState, useEffect, useCallback } from "react";
import {
  Loader2, Plus, Trash2, Pencil, Check, X, TrendingUp, TrendingDown,
  Settings2, Wrench, Building2, CreditCard, BarChart2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function apiErr(err: unknown): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error inesperado.";
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";
const labelCls = "text-sm font-medium text-slate-700";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Settings {
  vat_rate: string;
  monthly_depreciation: string;
  monthly_external_fees: string;
  target_net_margin: string;
  closing_day: number;
  opening_retained_earnings: string;
  opening_retained_earnings_notes: string | null;
  opening_cash_balance: string;
  opening_cash_balance_date: string | null;
  opening_domicilios_balance: string;
  opening_domicilios_balance_date: string | null;
  payroll_liability_basis: string;
  payroll_liability_manual: string;
  cleanup_notes: string | null;
  notes: string | null;
}

interface FixedCost {
  id: number;
  name: string;
  category: string;
  monthly_amount: string;
  sort_order: number;
  is_active: boolean;
}

interface FixedAsset {
  id: number;
  asset_name: string;
  category: string;
  acquisition_date: string;
  acquisition_cost: string;
  salvage_value: string;
  useful_life_months: number;
  notes: string | null;
}

interface Payable {
  id: number;
  vendor_name: string;
  concept: string;
  category: string;
  due_date: string | null;
  amount: string;
  paid_amount: string;
  status: string;
  payment_method: string | null;
  notes: string | null;
}

interface EquityMovement {
  id: number;
  movement_type: string;
  concept: string;
  amount: string;
  movement_date: string;
  notes: string | null;
}

// ─── Tab bar ──────────────────────────────────────────────────────────────────

type Tab = "settings" | "fixed-costs" | "fixed-assets" | "payables" | "equity";

const TABS: { key: Tab; label: string; icon: typeof Settings2 }[] = [
  { key: "settings",     label: "Parámetros",   icon: Settings2  },
  { key: "fixed-costs",  label: "Gastos fijos", icon: Wrench     },
  { key: "fixed-assets", label: "Activos",      icon: Building2  },
  { key: "payables",     label: "Por pagar",    icon: CreditCard },
  { key: "equity",       label: "Capital",      icon: BarChart2  },
];

// ─── Settings tab ─────────────────────────────────────────────────────────────

function SettingsTab() {
  const [data, setData] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<Settings>("/accounting/settings");
      setData(res.data);
    } catch (e) { setError(apiErr(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  function field(key: keyof Settings, value: string) {
    setData(prev => prev ? { ...prev, [key]: value } : prev);
    setSuccess(false);
  }

  async function save() {
    if (!data) return;
    setSaving(true); setError(""); setSuccess(false);
    try {
      await api.put("/accounting/settings", {
        ...data,
        closing_day: Number(data.closing_day),
      });
      setSuccess(true);
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-slate-300" /></div>;
  if (!data) return <div className="text-sm text-red-500">{error || "Error al cargar parámetros."}</div>;

  return (
    <div className="max-w-2xl space-y-6">
      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}
      {success && <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">Parámetros guardados.</div>}

      {/* General */}
      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">General</h2>
        </div>
        <div className="px-4 py-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-1">
            <label className={labelCls}>IVA (%)</label>
            <input type="number" step="0.01" className={inputCls} value={data.vat_rate} onChange={e => field("vat_rate", e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className={labelCls}>Margen objetivo (%)</label>
            <input type="number" step="0.01" className={inputCls} value={data.target_net_margin} onChange={e => field("target_net_margin", e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className={labelCls}>Día de cierre</label>
            <input type="number" min="1" max="28" className={inputCls} value={data.closing_day} onChange={e => field("closing_day", e.target.value)} />
          </div>
          <div className="space-y-1">
            <label className={labelCls}>Dep. mensual extra ($)</label>
            <input type="number" step="0.01" className={inputCls} value={data.monthly_depreciation} onChange={e => field("monthly_depreciation", e.target.value)} />
          </div>
          <div className="space-y-1 col-span-2">
            <label className={labelCls}>Honorarios externos mensuales ($)</label>
            <input type="number" step="0.01" className={inputCls} value={data.monthly_external_fees} onChange={e => field("monthly_external_fees", e.target.value)} />
          </div>
        </div>
      </section>

      {/* Opening balances */}
      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Saldos de apertura</h2>
        </div>
        <div className="px-4 py-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className={labelCls}>Utilidades retenidas ($)</label>
              <input type="number" step="0.01" className={inputCls} value={data.opening_retained_earnings} onChange={e => field("opening_retained_earnings", e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Notas (utilidades retenidas)</label>
              <input className={inputCls} value={data.opening_retained_earnings_notes ?? ""} onChange={e => field("opening_retained_earnings_notes", e.target.value)} placeholder="Opcional" />
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Saldo inicial caja ($)</label>
              <input type="number" step="0.01" className={inputCls} value={data.opening_cash_balance} onChange={e => field("opening_cash_balance", e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Fecha saldo inicial caja</label>
              <input type="date" className={inputCls} value={data.opening_cash_balance_date ?? ""} onChange={e => field("opening_cash_balance_date", e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Saldo inicial domicilios ($)</label>
              <input type="number" step="0.01" className={inputCls} value={data.opening_domicilios_balance} onChange={e => field("opening_domicilios_balance", e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Fecha saldo domicilios</label>
              <input type="date" className={inputCls} value={data.opening_domicilios_balance_date ?? ""} onChange={e => field("opening_domicilios_balance_date", e.target.value)} />
            </div>
          </div>
        </div>
      </section>

      {/* Payroll liability */}
      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Pasivo nómina</h2>
        </div>
        <div className="px-4 py-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className={labelCls}>Base de cálculo</label>
            <select className={inputCls} value={data.payroll_liability_basis} onChange={e => field("payroll_liability_basis", e.target.value)}>
              <option value="weekly_current">Semana en curso</option>
              <option value="manual_closing">Manual al cierre</option>
            </select>
          </div>
          {data.payroll_liability_basis === "manual_closing" && (
            <div className="space-y-1">
              <label className={labelCls}>Monto manual ($)</label>
              <input type="number" step="0.01" className={inputCls} value={data.payroll_liability_manual} onChange={e => field("payroll_liability_manual", e.target.value)} />
            </div>
          )}
        </div>
      </section>

      {/* Notes */}
      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-800">Notas</h2>
        </div>
        <div className="px-4 py-4 space-y-3">
          <div className="space-y-1">
            <label className={labelCls}>Limpieza / ajustes iniciales</label>
            <textarea rows={2} className={inputCls + " resize-none"} value={data.cleanup_notes ?? ""} onChange={e => field("cleanup_notes", e.target.value)} placeholder="Notas sobre ajustes de apertura..." />
          </div>
          <div className="space-y-1">
            <label className={labelCls}>Notas generales</label>
            <textarea rows={2} className={inputCls + " resize-none"} value={data.notes ?? ""} onChange={e => field("notes", e.target.value)} placeholder="Observaciones..." />
          </div>
        </div>
      </section>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="min-w-28">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {saving ? "Guardando..." : "Guardar parámetros"}
        </Button>
      </div>
    </div>
  );
}

// ─── Fixed Costs tab ──────────────────────────────────────────────────────────

interface CostForm { name: string; category: string; monthly_amount: string; is_active: boolean; sort_order: string; }

const emptyCost: CostForm = { name: "", category: "General", monthly_amount: "", is_active: true, sort_order: "0" };

function FixedCostsTab() {
  const [costs, setCosts] = useState<FixedCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [dlg, setDlg] = useState(false);
  const [editing, setEditing] = useState<FixedCost | null>(null);
  const [form, setForm] = useState<CostForm>(emptyCost);

  const [deleteDlg, setDeleteDlg] = useState(false);
  const [toDelete, setToDelete] = useState<FixedCost | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<FixedCost[]>("/accounting/fixed-costs");
      setCosts(res.data);
    } catch (e) { setError(apiErr(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  function openAdd() { setEditing(null); setForm(emptyCost); setDlg(true); }
  function openEdit(c: FixedCost) {
    setEditing(c);
    setForm({ name: c.name, category: c.category, monthly_amount: c.monthly_amount, is_active: c.is_active, sort_order: String(c.sort_order) });
    setDlg(true);
  }

  async function handleSave() {
    setSaving(true); setError("");
    const payload = { name: form.name.trim(), category: form.category.trim() || "General", monthly_amount: parseFloat(form.monthly_amount) || 0, sort_order: parseInt(form.sort_order) || 0, is_active: form.is_active };
    try {
      if (editing) await api.put(`/accounting/fixed-costs/${editing.id}`, payload);
      else await api.post("/accounting/fixed-costs", payload);
      setDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  async function handleDelete() {
    if (!toDelete) return;
    setSaving(true);
    try {
      await api.delete(`/accounting/fixed-costs/${toDelete.id}`);
      setDeleteDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  const totalMonthly = costs.filter(c => c.is_active).reduce((s, c) => s + Number(c.monthly_amount), 0);

  const byCategory = costs.reduce<Record<string, FixedCost[]>>((acc, c) => {
    (acc[c.category] ||= []).push(c);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Total mensual activo: <span className="font-bold text-slate-900">{fmt(totalMonthly)}</span>
        </p>
        <Button size="sm" onClick={openAdd}><Plus className="h-4 w-4 mr-1" />Agregar</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-300" /></div>
      ) : costs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <Wrench className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Sin gastos fijos registrados</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(byCategory).map(([cat, items]) => (
            <div key={cat} className="rounded-lg border border-slate-200 overflow-hidden">
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{cat}</p>
              </div>
              {items.map((c, idx) => (
                <div key={c.id} className={`flex items-center gap-3 px-4 py-3 bg-white hover:bg-slate-50 ${idx > 0 ? "border-t border-slate-100" : ""}`}>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${c.is_active ? "text-slate-900" : "text-slate-400 line-through"}`}>{c.name}</p>
                  </div>
                  <span className="text-sm font-semibold text-slate-800 shrink-0">{fmt(c.monthly_amount)}<span className="text-xs font-normal text-slate-400">/mes</span></span>
                  {!c.is_active && <Badge variant="secondary" className="shrink-0">Inactivo</Badge>}
                  <button onClick={() => openEdit(c)} className="text-slate-400 hover:text-slate-700 shrink-0"><Pencil className="h-4 w-4" /></button>
                  <button onClick={() => { setToDelete(c); setDeleteDlg(true); }} className="text-slate-400 hover:text-red-500 shrink-0"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit dialog */}
      <Dialog open={dlg} onOpenChange={o => { if (!o) setDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar gasto fijo" : "Nuevo gasto fijo"}</DialogTitle>
            <DialogDescription>Costo mensual recurrente de la operación.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className={labelCls}>Nombre <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Renta, gas, etc." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Categoría</label>
                <input className={inputCls} value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} placeholder="General" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Orden</label>
                <input type="number" min="0" className={inputCls} value={form.sort_order} onChange={e => setForm(p => ({ ...p, sort_order: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Monto mensual ($) <span className="text-red-500">*</span></label>
              <input type="number" min="0.01" step="0.01" className={inputCls} value={form.monthly_amount} onChange={e => setForm(p => ({ ...p, monthly_amount: e.target.value }))} placeholder="0.00" />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
              <input type="checkbox" checked={form.is_active} onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))} className="rounded" />
              Activo
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving || !form.name.trim() || !form.monthly_amount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editing ? "Guardar" : "Agregar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={deleteDlg} onOpenChange={o => { if (!o) setDeleteDlg(false); }}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle>Eliminar gasto fijo</DialogTitle>
            <DialogDescription>¿Eliminar <span className="font-semibold">{toDelete?.name}</span>? Esta acción no se puede deshacer.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDlg(false)} disabled={saving}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Fixed Assets tab ─────────────────────────────────────────────────────────

interface AssetForm { asset_name: string; category: string; acquisition_date: string; acquisition_cost: string; salvage_value: string; useful_life_months: string; notes: string; }

const emptyAsset: AssetForm = { asset_name: "", category: "Activo fijo", acquisition_date: "", acquisition_cost: "", salvage_value: "0", useful_life_months: "60", notes: "" };

function FixedAssetsTab() {
  const [assets, setAssets] = useState<FixedAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [dlg, setDlg] = useState(false);
  const [form, setForm] = useState<AssetForm>(emptyAsset);
  const [deleteDlg, setDeleteDlg] = useState(false);
  const [toDelete, setToDelete] = useState<FixedAsset | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<FixedAsset[]>("/accounting/fixed-assets");
      setAssets(res.data);
    } catch (e) { setError(apiErr(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  function monthlyDep(a: FixedAsset) {
    const dep = (Number(a.acquisition_cost) - Number(a.salvage_value)) / a.useful_life_months;
    return dep;
  }

  async function handleAdd() {
    setSaving(true); setError("");
    try {
      await api.post("/accounting/fixed-assets", {
        asset_name: form.asset_name.trim(),
        category: form.category.trim() || "Activo fijo",
        acquisition_date: form.acquisition_date,
        acquisition_cost: parseFloat(form.acquisition_cost) || 0,
        salvage_value: parseFloat(form.salvage_value) || 0,
        useful_life_months: parseInt(form.useful_life_months) || 60,
        notes: form.notes.trim() || null,
      });
      setDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  async function handleDelete() {
    if (!toDelete) return;
    setSaving(true);
    try {
      await api.delete(`/accounting/fixed-assets/${toDelete.id}`);
      setDeleteDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  const totalMonthlyDep = assets.reduce((s, a) => s + monthlyDep(a), 0);

  return (
    <div className="space-y-4">
      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Depreciación mensual total: <span className="font-bold text-slate-900">{fmt(totalMonthlyDep)}</span>
        </p>
        <Button size="sm" onClick={() => { setForm(emptyAsset); setDlg(true); }}><Plus className="h-4 w-4 mr-1" />Agregar</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-300" /></div>
      ) : assets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <Building2 className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Sin activos fijos registrados</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs text-slate-500 uppercase tracking-wide">
                <th className="text-left px-4 py-2.5 font-medium">Activo</th>
                <th className="text-left px-4 py-2.5 font-medium hidden md:table-cell">Categoría</th>
                <th className="text-left px-4 py-2.5 font-medium hidden md:table-cell">Adquisición</th>
                <th className="text-right px-4 py-2.5 font-medium">Costo</th>
                <th className="text-right px-4 py-2.5 font-medium hidden sm:table-cell">Dep/mes</th>
                <th className="text-right px-4 py-2.5 font-medium hidden lg:table-cell">Vida útil</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {assets.map(a => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{a.asset_name}</td>
                  <td className="px-4 py-3 text-slate-500 hidden md:table-cell">{a.category}</td>
                  <td className="px-4 py-3 text-slate-500 hidden md:table-cell">{a.acquisition_date}</td>
                  <td className="px-4 py-3 text-right font-semibold">{fmt(a.acquisition_cost)}</td>
                  <td className="px-4 py-3 text-right text-slate-600 hidden sm:table-cell">{fmt(monthlyDep(a))}</td>
                  <td className="px-4 py-3 text-right text-slate-400 hidden lg:table-cell">{a.useful_life_months} meses</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => { setToDelete(a); setDeleteDlg(true); }} className="text-slate-300 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={dlg} onOpenChange={o => { if (!o) setDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Nuevo activo fijo</DialogTitle>
            <DialogDescription>Se calculará la depreciación mensual automáticamente.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className={labelCls}>Nombre del activo <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.asset_name} onChange={e => setForm(p => ({ ...p, asset_name: e.target.value }))} placeholder="Compresor, hidrolavadora, etc." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Categoría</label>
                <input className={inputCls} value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} placeholder="Activo fijo" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Fecha de adquisición <span className="text-red-500">*</span></label>
                <input type="date" className={inputCls} value={form.acquisition_date} onChange={e => setForm(p => ({ ...p, acquisition_date: e.target.value }))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Costo de adquisición ($) <span className="text-red-500">*</span></label>
                <input type="number" min="0.01" step="0.01" className={inputCls} value={form.acquisition_cost} onChange={e => setForm(p => ({ ...p, acquisition_cost: e.target.value }))} placeholder="0.00" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Valor de rescate ($)</label>
                <input type="number" min="0" step="0.01" className={inputCls} value={form.salvage_value} onChange={e => setForm(p => ({ ...p, salvage_value: e.target.value }))} placeholder="0.00" />
              </div>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Vida útil (meses)</label>
              <input type="number" min="1" className={inputCls} value={form.useful_life_months} onChange={e => setForm(p => ({ ...p, useful_life_months: e.target.value }))} />
            </div>
            {form.acquisition_cost && form.useful_life_months && (
              <p className="text-sm text-slate-600 bg-slate-50 rounded-md px-3 py-2">
                Depreciación mensual: <span className="font-bold">{fmt((parseFloat(form.acquisition_cost) - parseFloat(form.salvage_value || "0")) / parseInt(form.useful_life_months))}</span>
              </p>
            )}
            <div className="space-y-1">
              <label className={labelCls}>Notas</label>
              <input className={inputCls} value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAdd} disabled={saving || !form.asset_name.trim() || !form.acquisition_cost || !form.acquisition_date}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Agregar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={deleteDlg} onOpenChange={o => { if (!o) setDeleteDlg(false); }}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle>Dar de baja activo</DialogTitle>
            <DialogDescription>¿Dar de baja <span className="font-semibold">{toDelete?.asset_name}</span>? Se marcará como inactivo.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDlg(false)} disabled={saving}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Dar de baja
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Payables tab ─────────────────────────────────────────────────────────────

const STATUS_PAYABLE: Record<string, { label: string; cls: string }> = {
  pending:   { label: "Pendiente", cls: "bg-amber-50 text-amber-700 ring-1 ring-amber-200" },
  partial:   { label: "Parcial",   cls: "bg-blue-50 text-blue-700 ring-1 ring-blue-200"   },
  paid:      { label: "Pagado",    cls: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" },
  cancelled: { label: "Cancelado", cls: "bg-slate-100 text-slate-500 ring-1 ring-slate-200" },
};

interface PayableForm { vendor_name: string; concept: string; category: string; due_date: string; amount: string; notes: string; }
const emptyPayable: PayableForm = { vendor_name: "", concept: "", category: "General", due_date: "", amount: "", notes: "" };

interface PayUpdateForm { status: string; paid_amount: string; payment_method: string; notes: string; }

function PayablesTab() {
  const [payables, setPayables] = useState<Payable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [addDlg, setAddDlg] = useState(false);
  const [form, setForm] = useState<PayableForm>(emptyPayable);

  const [updateDlg, setUpdateDlg] = useState(false);
  const [updating, setUpdating] = useState<Payable | null>(null);
  const [upForm, setUpForm] = useState<PayUpdateForm>({ status: "paid", paid_amount: "", payment_method: "efectivo", notes: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<Payable[]>("/accounting/payables");
      setPayables(res.data);
    } catch (e) { setError(apiErr(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleAdd() {
    setSaving(true); setError("");
    try {
      await api.post("/accounting/payables", {
        vendor_name: form.vendor_name.trim(),
        concept: form.concept.trim(),
        category: form.category.trim() || "General",
        due_date: form.due_date || null,
        amount: parseFloat(form.amount) || 0,
        notes: form.notes.trim() || null,
      });
      setAddDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  function openUpdate(p: Payable) {
    setUpdating(p);
    setUpForm({ status: "paid", paid_amount: p.amount, payment_method: "efectivo", notes: "" });
    setUpdateDlg(true);
  }

  async function handleUpdate() {
    if (!updating) return;
    setSaving(true); setError("");
    try {
      await api.patch(`/accounting/payables/${updating.id}`, {
        status: upForm.status,
        paid_amount: parseFloat(upForm.paid_amount) || 0,
        payment_method: upForm.payment_method || null,
        notes: upForm.notes.trim() || null,
      });
      setUpdateDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  const totalPending = payables.reduce((s, p) => s + Number(p.amount) - Number(p.paid_amount), 0);

  return (
    <div className="space-y-4">
      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Total pendiente: <span className="font-bold text-red-600">{fmt(totalPending)}</span>
        </p>
        <Button size="sm" onClick={() => { setForm(emptyPayable); setAddDlg(true); }}><Plus className="h-4 w-4 mr-1" />Agregar</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-300" /></div>
      ) : payables.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <CreditCard className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Sin cuentas por pagar pendientes</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          {payables.map((p, idx) => {
            const st = STATUS_PAYABLE[p.status] ?? STATUS_PAYABLE.pending;
            const remaining = Number(p.amount) - Number(p.paid_amount);
            return (
              <div key={p.id} className={`flex items-center gap-4 px-4 py-3 bg-white hover:bg-slate-50 ${idx > 0 ? "border-t border-slate-100" : ""}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-slate-900">{p.vendor_name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${st.cls}`}>{st.label}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{p.concept}{p.due_date && <> · Vence {p.due_date}</>}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-bold text-slate-900">{fmt(p.amount)}</p>
                  {remaining > 0 && <p className="text-xs text-red-500">Pendiente {fmt(remaining)}</p>}
                </div>
                <Button size="sm" variant="outline" onClick={() => openUpdate(p)}>
                  <Check className="h-3.5 w-3.5 mr-1" />Pagar
                </Button>
              </div>
            );
          })}
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={addDlg} onOpenChange={o => { if (!o) setAddDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Nueva cuenta por pagar</DialogTitle>
            <DialogDescription>Registra un pago pendiente a un proveedor.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Proveedor <span className="text-red-500">*</span></label>
                <input className={inputCls} value={form.vendor_name} onChange={e => setForm(p => ({ ...p, vendor_name: e.target.value }))} placeholder="Nombre del proveedor" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Categoría</label>
                <input className={inputCls} value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))} placeholder="General" />
              </div>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Concepto <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.concept} onChange={e => setForm(p => ({ ...p, concept: e.target.value }))} placeholder="Descripción del gasto" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Monto ($) <span className="text-red-500">*</span></label>
                <input type="number" min="0.01" step="0.01" className={inputCls} value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} placeholder="0.00" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Fecha de vencimiento</label>
                <input type="date" className={inputCls} value={form.due_date} onChange={e => setForm(p => ({ ...p, due_date: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Notas</label>
              <input className={inputCls} value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAdd} disabled={saving || !form.vendor_name.trim() || !form.concept.trim() || !form.amount}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Update dialog */}
      <Dialog open={updateDlg} onOpenChange={o => { if (!o) setUpdateDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Actualizar pago — {updating?.vendor_name}</DialogTitle>
            <DialogDescription>{updating?.concept} · Total {fmt(updating?.amount)}</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className={labelCls}>Estado</label>
              <select className={inputCls} value={upForm.status} onChange={e => setUpForm(p => ({ ...p, status: e.target.value }))}>
                <option value="paid">Pagado</option>
                <option value="partial">Pago parcial</option>
                <option value="cancelled">Cancelado</option>
              </select>
            </div>
            {upForm.status !== "cancelled" && (
              <div className="space-y-1">
                <label className={labelCls}>Monto pagado ($)</label>
                <input type="number" min="0" step="0.01" className={inputCls} value={upForm.paid_amount} onChange={e => setUpForm(p => ({ ...p, paid_amount: e.target.value }))} />
              </div>
            )}
            <div className="space-y-1">
              <label className={labelCls}>Forma de pago</label>
              <select className={inputCls} value={upForm.payment_method} onChange={e => setUpForm(p => ({ ...p, payment_method: e.target.value }))}>
                <option value="efectivo">Efectivo</option>
                <option value="transferencia">Transferencia</option>
                <option value="tarjeta">Tarjeta</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Notas</label>
              <input className={inputCls} value={upForm.notes} onChange={e => setUpForm(p => ({ ...p, notes: e.target.value }))} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Equity Movements tab ─────────────────────────────────────────────────────

const MOVEMENT_TYPES: Record<string, { label: string; icon: typeof TrendingUp; cls: string }> = {
  contribution: { label: "Aportación",  icon: TrendingUp,   cls: "text-emerald-600" },
  withdrawal:   { label: "Retiro",      icon: TrendingDown, cls: "text-red-500"     },
  adjustment:   { label: "Ajuste",      icon: Settings2,    cls: "text-blue-500"    },
};

interface EquityForm { movement_type: string; concept: string; amount: string; movement_date: string; notes: string; }
const emptyEquity: EquityForm = { movement_type: "contribution", concept: "", amount: "", movement_date: new Date().toISOString().slice(0, 10), notes: "" };

function EquityTab() {
  const [movements, setMovements] = useState<EquityMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [dlg, setDlg] = useState(false);
  const [form, setForm] = useState<EquityForm>(emptyEquity);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<EquityMovement[]>("/accounting/equity-movements");
      setMovements(res.data);
    } catch (e) { setError(apiErr(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleAdd() {
    setSaving(true); setError("");
    try {
      await api.post("/accounting/equity-movements", {
        movement_type: form.movement_type,
        concept: form.concept.trim(),
        amount: parseFloat(form.amount) || 0,
        movement_date: form.movement_date,
        notes: form.notes.trim() || null,
      });
      setDlg(false);
      load();
    } catch (e) { setError(apiErr(e)); }
    finally { setSaving(false); }
  }

  const totalNet = movements.reduce((s, m) => {
    if (m.movement_type === "contribution") return s + Number(m.amount);
    if (m.movement_type === "withdrawal")   return s - Number(m.amount);
    return s + Number(m.amount);
  }, 0);

  return (
    <div className="space-y-4">
      {error && <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>}

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Capital neto: <span className={`font-bold ${totalNet >= 0 ? "text-emerald-600" : "text-red-600"}`}>{fmt(totalNet)}</span>
        </p>
        <Button size="sm" onClick={() => { setForm(emptyEquity); setDlg(true); }}><Plus className="h-4 w-4 mr-1" />Registrar</Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-slate-300" /></div>
      ) : movements.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <BarChart2 className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">Sin movimientos de capital registrados</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          {movements.map((m, idx) => {
            const mt = MOVEMENT_TYPES[m.movement_type] ?? MOVEMENT_TYPES.adjustment;
            const MIcon = mt.icon;
            const sign = m.movement_type === "withdrawal" ? "-" : m.movement_type === "contribution" ? "+" : "±";
            return (
              <div key={m.id} className={`flex items-center gap-4 px-4 py-3 bg-white hover:bg-slate-50 ${idx > 0 ? "border-t border-slate-100" : ""}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${m.movement_type === "contribution" ? "bg-emerald-50" : m.movement_type === "withdrawal" ? "bg-red-50" : "bg-blue-50"}`}>
                  <MIcon className={`h-4 w-4 ${mt.cls}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900">{m.concept}</p>
                  <p className="text-xs text-slate-400">{mt.label} · {m.movement_date}</p>
                </div>
                <p className={`text-sm font-bold shrink-0 ${mt.cls}`}>{sign}{fmt(m.amount)}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={dlg} onOpenChange={o => { if (!o) setDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Movimiento de capital</DialogTitle>
            <DialogDescription>Registra una aportación, retiro o ajuste de capital.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className={labelCls}>Tipo</label>
              <select className={inputCls} value={form.movement_type} onChange={e => setForm(p => ({ ...p, movement_type: e.target.value }))}>
                <option value="contribution">Aportación</option>
                <option value="withdrawal">Retiro</option>
                <option value="adjustment">Ajuste</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Concepto <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.concept} onChange={e => setForm(p => ({ ...p, concept: e.target.value }))} placeholder="Descripción del movimiento" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className={labelCls}>Monto ($) <span className="text-red-500">*</span></label>
                <input type="number" step="0.01" className={inputCls} value={form.amount} onChange={e => setForm(p => ({ ...p, amount: e.target.value }))} placeholder="0.00" />
              </div>
              <div className="space-y-1">
                <label className={labelCls}>Fecha <span className="text-red-500">*</span></label>
                <input type="date" className={inputCls} value={form.movement_date} onChange={e => setForm(p => ({ ...p, movement_date: e.target.value }))} />
              </div>
            </div>
            <div className="space-y-1">
              <label className={labelCls}>Notas</label>
              <input className={inputCls} value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} placeholder="Opcional" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAdd} disabled={saving || !form.concept.trim() || !form.amount || !form.movement_date}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Accounting() {
  const [tab, setTab] = useState<Tab>("settings");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Contabilidad</h1>
        <p className="text-sm text-slate-500">Parámetros financieros, costos, activos y movimientos de capital</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200 overflow-x-auto">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                tab === t.key
                  ? "border-slate-900 text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {tab === "settings"     && <SettingsTab />}
      {tab === "fixed-costs"  && <FixedCostsTab />}
      {tab === "fixed-assets" && <FixedAssetsTab />}
      {tab === "payables"     && <PayablesTab />}
      {tab === "equity"       && <EquityTab />}
    </div>
  );
}
