import { useState, useEffect, useCallback } from "react";
import { Plus, Trash2, Loader2, Receipt, CreditCard, Banknote, ArrowLeftRight, Gift } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface PendingAppointment {
  id: number;
  scheduled_start: string;
  status: string;
  charge_status: string;
  estimated_price: string | number;
  client_name: string | null;
  vehicle_label: string | null;
  service_name: string | null;
  operator_name: string | null;
}

interface PaymentItem {
  id: number;
  item_type: string;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  total: string | number;
  apply_commission: boolean;
}

interface PaymentRead {
  id: number;
  ticket_number: string | null;
  payment_method: string;
  subtotal: string | number;
  extras_total: string | number;
  discount_total: string | number;
  total: string | number;
  paid_at: string;
  client_name: string | null;
  vehicle_label: string | null;
  service_name: string | null;
  cashier_name: string | null;
  items: PaymentItem[];
}

interface ExtraRow {
  description: string;
  quantity: string;
  unit_price: string;
  apply_commission: boolean;
}

/* ─── Helpers ────────────────────────────────────────────────────────── */

const PAYMENT_METHODS = [
  { value: "efectivo",      label: "Efectivo",      icon: Banknote },
  { value: "tarjeta",       label: "Tarjeta",        icon: CreditCard },
  { value: "transferencia", label: "Transferencia",  icon: ArrowLeftRight },
  { value: "cortesia",      label: "Cortesía",       icon: Gift },
];

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function formatMoney(val: string | number) {
  return `$${Number(val).toFixed(2)}`;
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function emptyExtra(): ExtraRow {
  return { description: "", quantity: "1", unit_price: "0", apply_commission: true };
}

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Pos() {
  const [pending, setPending]       = useState<PendingAppointment[]>([]);
  const [payments, setPayments]     = useState<PaymentRead[]>([]);
  const [selected, setSelected]     = useState<PendingAppointment | null>(null);
  const [loadingData, setLoadingData] = useState(false);

  // Form state
  const [method, setMethod]       = useState("efectivo");
  const [discount, setDiscount]   = useState("0");
  const [reference, setReference] = useState("");
  const [notes, setNotes]         = useState("");
  const [extras, setExtras]       = useState<ExtraRow[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState("");
  const [success, setSuccess]       = useState("");

  /* ── Data fetch ── */

  const loadData = useCallback(async () => {
    setLoadingData(true);
    try {
      const [pendRes, payRes] = await Promise.all([
        api.get<PendingAppointment[]>("/payments/pending-appointments"),
        api.get<PaymentRead[]>("/payments/", { params: { target_date: todayStr() } }),
      ]);
      setPending(pendRes.data);
      setPayments(payRes.data);
    } catch {
      setError("Error al cargar datos.");
    } finally {
      setLoadingData(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  /* ── Form reset ── */

  function selectAppointment(appt: PendingAppointment) {
    setSelected(appt);
    setMethod("efectivo");
    setDiscount("0");
    setReference("");
    setNotes("");
    setExtras([]);
    setError("");
    setSuccess("");
  }

  /* ── Totals ── */

  const subtotal      = selected ? Number(selected.estimated_price) : 0;
  const extrasTotal   = extras.reduce((acc, e) => acc + (Number(e.quantity) || 0) * (Number(e.unit_price) || 0), 0);
  const discountTotal = Number(discount) || 0;
  const total         = Math.max(0, subtotal + extrasTotal - discountTotal);

  /* ── Submit ── */

  async function handleSubmit() {
    if (!selected) return;
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      await api.post<PaymentRead>("/payments/", {
        appointment_id: selected.id,
        payment_method: method,
        discount_total: discountTotal,
        reference: reference.trim() || null,
        notes: notes.trim() || null,
        extras: extras
          .filter(e => e.description.trim())
          .map(e => ({
            description: e.description.trim(),
            quantity: Number(e.quantity) || 1,
            unit_price: Number(e.unit_price) || 0,
            apply_commission: e.apply_commission,
          })),
      });
      setSuccess(`Pago registrado. Total: ${formatMoney(total)}`);
      setSelected(null);
      loadData();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Error al registrar el pago.");
    } finally {
      setSubmitting(false);
    }
  }

  /* ── Extra row helpers ── */

  function addExtra() { setExtras(e => [...e, emptyExtra()]); }
  function removeExtra(i: number) { setExtras(e => e.filter((_, idx) => idx !== i)); }
  function updateExtra(i: number, field: keyof ExtraRow, value: string | boolean) {
    setExtras(e => e.map((row, idx) => idx === i ? { ...row, [field]: value } : row));
  }

  /* ── Render ── */

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">POS / Cobros</h1>
        <p className="text-sm text-slate-500">Registra pagos de citas completadas</p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}
      {success && (
        <div className="rounded-md bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-700">{success}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Pending appointments ── */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
            Por cobrar ({pending.length})
          </h2>

          {loadingData ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
            </div>
          ) : pending.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 py-12 text-center text-sm text-slate-400">
              No hay citas pendientes de cobro
            </div>
          ) : (
            pending.map((appt) => (
              <button
                key={appt.id}
                type="button"
                onClick={() => selectAppointment(appt)}
                className={`w-full text-left rounded-lg border p-4 transition-colors ${
                  selected?.id === appt.id
                    ? "border-slate-900 bg-slate-50 ring-2 ring-slate-900"
                    : "border-slate-200 bg-white hover:border-slate-400"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 truncate">{appt.client_name ?? "—"}</p>
                    <p className="text-sm text-slate-500">{appt.vehicle_label ?? "—"}</p>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-400">
                      {appt.service_name && <span>{appt.service_name}</span>}
                      {appt.operator_name && <span>Op: {appt.operator_name}</span>}
                      <span>{formatTime(appt.scheduled_start)}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold text-slate-900">{formatMoney(appt.estimated_price)}</p>
                    <Badge variant="warning" className="mt-1">Pendiente</Badge>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* ── Payment form ── */}
        <div>
          {!selected ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 py-20 text-center text-slate-400">
              <Receipt className="h-10 w-10 mb-2 opacity-40" />
              <p className="text-sm">Selecciona una cita para cobrar</p>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-200 bg-white p-5 space-y-5">
              {/* Appointment summary */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Cita seleccionada</p>
                <p className="font-semibold text-slate-900">{selected.client_name}</p>
                <p className="text-sm text-slate-500">{selected.vehicle_label} · {selected.service_name}</p>
                {selected.operator_name && (
                  <p className="text-xs text-slate-400 mt-0.5">Operador: {selected.operator_name}</p>
                )}
              </div>

              <Separator />

              {/* Payment method */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Método de pago</p>
                <div className="grid grid-cols-2 gap-2">
                  {PAYMENT_METHODS.map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setMethod(value)}
                      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                        method === value
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reference (for card/transfer) */}
              {(method === "tarjeta" || method === "transferencia") && (
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Referencia</label>
                  <input
                    className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                    placeholder="Número de autorización o folio"
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                  />
                </div>
              )}

              {/* Discount */}
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Descuento ($)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                />
              </div>

              {/* Extras */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-700">Extras</p>
                  <Button variant="ghost" size="sm" onClick={addExtra} className="h-7 text-xs">
                    <Plus className="h-3 w-3 mr-1" />
                    Agregar
                  </Button>
                </div>
                {extras.map((row, i) => (
                  <div key={i} className="grid grid-cols-[1fr_80px_80px_32px] gap-2 items-center">
                    <input
                      className="rounded-md border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-slate-900"
                      placeholder="Descripción"
                      value={row.description}
                      onChange={(e) => updateExtra(i, "description", e.target.value)}
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className="rounded-md border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-slate-900"
                      placeholder="Precio"
                      value={row.unit_price}
                      onChange={(e) => updateExtra(i, "unit_price", e.target.value)}
                    />
                    <input
                      type="number"
                      min="1"
                      step="1"
                      className="rounded-md border border-slate-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-slate-900"
                      placeholder="Cant."
                      value={row.quantity}
                      onChange={(e) => updateExtra(i, "quantity", e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => removeExtra(i)}
                      className="flex items-center justify-center rounded text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Notes */}
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Notas (opcional)</label>
                <textarea
                  rows={2}
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-slate-900"
                  placeholder="Observaciones del pago"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <Separator />

              {/* Totals */}
              <div className="space-y-1 text-sm">
                <div className="flex justify-between text-slate-600">
                  <span>Servicio</span>
                  <span>{formatMoney(subtotal)}</span>
                </div>
                {extrasTotal > 0 && (
                  <div className="flex justify-between text-slate-600">
                    <span>Extras</span>
                    <span>+{formatMoney(extrasTotal)}</span>
                  </div>
                )}
                {discountTotal > 0 && (
                  <div className="flex justify-between text-emerald-600">
                    <span>Descuento</span>
                    <span>-{formatMoney(discountTotal)}</span>
                  </div>
                )}
                <div className="flex justify-between font-bold text-slate-900 text-base pt-1 border-t border-slate-100">
                  <span>Total</span>
                  <span>{formatMoney(total)}</span>
                </div>
              </div>

              <Button className="w-full" onClick={handleSubmit} disabled={submitting}>
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Receipt className="mr-2 h-4 w-4" />
                )}
                Registrar pago · {formatMoney(total)}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* ── Today's payments ── */}
      {payments.length > 0 && (
        <div className="space-y-3">
          <Separator />
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
            Cobros de hoy ({payments.length})
          </h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                  <th className="px-4 py-2.5 text-left">Ticket</th>
                  <th className="px-4 py-2.5 text-left">Cliente</th>
                  <th className="px-4 py-2.5 text-left">Servicio</th>
                  <th className="px-4 py-2.5 text-left">Método</th>
                  <th className="px-4 py-2.5 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payments.map((pay) => (
                  <tr key={pay.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{pay.ticket_number ?? `#${pay.id}`}</td>
                    <td className="px-4 py-2.5 text-slate-900">{pay.client_name ?? "—"}</td>
                    <td className="px-4 py-2.5 text-slate-500">{pay.service_name ?? "—"}</td>
                    <td className="px-4 py-2.5 capitalize text-slate-600">{pay.payment_method}</td>
                    <td className="px-4 py-2.5 text-right font-semibold text-slate-900">{formatMoney(pay.total)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-slate-200 bg-slate-50">
                  <td colSpan={4} className="px-4 py-2.5 text-xs font-semibold text-slate-500">Total del día</td>
                  <td className="px-4 py-2.5 text-right font-bold text-slate-900">
                    {formatMoney(payments.reduce((s, p) => s + Number(p.total), 0))}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
