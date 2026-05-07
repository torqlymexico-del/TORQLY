import { useState, useEffect, useCallback } from "react";
import { Loader2, Plus, ShoppingBag, ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client { id: number; name: string; }
interface Vehicle { id: number; plate: string; brand: string; model: string; client_id?: number | null; }
interface ServiceCatalog { id: number; name: string; base_price: string; }
interface Operator { id: number; name: string; commission_percentage: string; }

interface OrderItem {
  id: number;
  catalog_id: number | null;
  custom_name: string | null;
  unit_price: string;
  quantity: number;
}
interface OrderWasher {
  id: number;
  user_id: number;
  commission_percent: string;
  commission_amount: string;
  is_paid: boolean;
}
interface Order {
  id: number;
  client_id: number | null;
  vehicle_id: number | null;
  service_date: string | null;
  daily_sequence: number | null;
  subtotal: string;
  discount_amount: string;
  total: string;
  status: string;
  payment_status: string;
  payment_method: string | null;
  is_domicilio: boolean;
  delivery_address: string | null;
  notes: string | null;
  items: OrderItem[];
  washers: OrderWasher[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  en_cola: "En cola",
  en_proceso: "En proceso",
  listo: "Listo",
  entregado: "Entregado",
  cancelado: "Cancelado",
};
const STATUS_NEXT: Record<string, string> = {
  en_cola: "en_proceso",
  en_proceso: "listo",
  listo: "entregado",
};

function statusVariant(s: string): "default" | "warning" | "success" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "warning" | "success" | "secondary" | "destructive" | "outline"> = {
    en_cola: "secondary", en_proceso: "warning", listo: "success",
    entregado: "default", cancelado: "destructive",
  };
  return map[s] ?? "secondary";
}

function paymentVariant(s: string): "default" | "warning" | "success" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "warning" | "success" | "secondary" | "destructive" | "outline"> = {
    pendiente: "warning", parcial: "secondary", pagado: "success",
    credito: "default", cortesia: "outline",
  };
  return map[s] ?? "secondary";
}

function fmt(v: string | number): string {
  return `$${Number(v).toFixed(2)}`;
}

function todayStr() { return new Date().toISOString().slice(0, 10); }

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

type NewItemRow = { catalog_id: number | null; custom_name: string; unit_price: string; quantity: number };

// ─── Component ────────────────────────────────────────────────────────────────

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [services, setServices] = useState<ServiceCatalog[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [dateFrom, setDateFrom] = useState(todayStr());
  const [dateTo, setDateTo] = useState(todayStr());
  const [statusFilter, setStatusFilter] = useState("");

  // Expanded row
  const [expanded, setExpanded] = useState<number | null>(null);

  // New order dialog
  const [newDlg, setNewDlg] = useState(false);
  const [newClientId, setNewClientId] = useState("");
  const [newVehicleId, setNewVehicleId] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [newIsDomicilio, setNewIsDomicilio] = useState(false);
  const [newDelivery, setNewDelivery] = useState("");
  const [newItems, setNewItems] = useState<NewItemRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Payment dialog
  const [payDlg, setPayDlg] = useState(false);
  const [payOrder, setPayOrder] = useState<Order | null>(null);
  const [payMethod, setPayMethod] = useState("efectivo");
  const [payStatus, setPayStatus] = useState("pagado");
  const [discount, setDiscount] = useState("0");

  // Add item dialog
  const [itemDlg, setItemDlg] = useState(false);
  const [itemOrder, setItemOrder] = useState<Order | null>(null);
  const [itemMode, setItemMode] = useState<"catalog" | "custom">("catalog");
  const [itemCatalogId, setItemCatalogId] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemPrice, setItemPrice] = useState("");
  const [itemQty, setItemQty] = useState("1");

  // Washer dialog
  const [washerDlg, setWasherDlg] = useState(false);
  const [washerOrder, setWasherOrder] = useState<Order | null>(null);
  const [washerRows, setWasherRows] = useState<{ user_id: string; commission_percent: string }[]>([]);

  // ── Load orders ──

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<Order[]>("/orders/", { params });
      setOrders(res.data);
    } catch {
      setError("Error al cargar órdenes.");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, statusFilter]);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  // Load reference data once
  useEffect(() => {
    Promise.all([
      api.get<Client[]>("/clients/"),
      api.get<Vehicle[]>("/vehicles/"),
      api.get<ServiceCatalog[]>("/services-catalog/"),
      api.get<Operator[]>("/payroll/operators"),
    ]).then(([c, v, s, o]) => {
      setClients(c.data);
      setVehicles(v.data);
      setServices(s.data);
      setOperators(o.data);
    }).catch(() => {});
  }, []);

  // ── Helpers ──

  const clientName = (id: number | null) => clients.find(c => c.id === id)?.name ?? `Cliente #${id}`;
  const vehicleLabel = (id: number | null) => {
    const v = vehicles.find(v => v.id === id);
    return v ? `${v.plate} ${v.brand} ${v.model}` : `Veh. #${id}`;
  };

  const clientVehicles = newClientId
    ? vehicles.filter(v => v.client_id == null || v.client_id === parseInt(newClientId))
    : vehicles;

  // ── Actions ──

  async function handleAdvanceStatus(order: Order) {
    const next = STATUS_NEXT[order.status];
    if (!next) return;
    try {
      const res = await api.patch<Order>(`/orders/${order.id}/status`, { status: next });
      setOrders(prev => prev.map(o => o.id === order.id ? res.data : o));
    } catch {
      setError("Error al actualizar estado.");
    }
  }

  function resetNewForm() {
    setNewClientId(""); setNewVehicleId(""); setNewNotes("");
    setNewIsDomicilio(false); setNewDelivery(""); setNewItems([]);
    setFormError("");
  }

  async function handleCreateOrder() {
    setSaving(true);
    setFormError("");
    try {
      await api.post("/orders/", {
        client_id: newClientId ? parseInt(newClientId) : null,
        vehicle_id: newVehicleId ? parseInt(newVehicleId) : null,
        notes: newNotes || null,
        is_domicilio: newIsDomicilio,
        delivery_address: newIsDomicilio ? (newDelivery || null) : null,
        items: newItems
          .filter(i => i.custom_name.trim() || i.catalog_id)
          .map(i => ({
            catalog_id: i.catalog_id ?? null,
            custom_name: i.catalog_id ? null : (i.custom_name.trim() || null),
            unit_price: parseFloat(i.unit_price) || 0,
            quantity: i.quantity || 1,
          })),
      });
      setNewDlg(false);
      resetNewForm();
      loadOrders();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Error al crear la orden.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSetPayment() {
    if (!payOrder) return;
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${payOrder.id}/payment`, {
        payment_method: payMethod,
        payment_status: payStatus,
        discount_amount: parseFloat(discount) || 0,
      });
      setOrders(prev => prev.map(o => o.id === payOrder.id ? res.data : o));
      setPayDlg(false);
    } catch {
      setError("Error al registrar el pago.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAddItem() {
    if (!itemOrder) return;
    setSaving(true);
    try {
      const payload = itemMode === "catalog"
        ? { catalog_id: parseInt(itemCatalogId), unit_price: parseFloat(itemPrice) || 0, quantity: parseInt(itemQty) || 1 }
        : { custom_name: itemName, unit_price: parseFloat(itemPrice) || 0, quantity: parseInt(itemQty) || 1 };
      const res = await api.post<Order>(`/orders/${itemOrder.id}/items`, payload);
      setOrders(prev => prev.map(o => o.id === itemOrder.id ? res.data : o));
      setItemDlg(false);
    } catch {
      setError("Error al agregar ítem.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveItem(order: Order, itemId: number) {
    try {
      const res = await api.delete<Order>(`/orders/${order.id}/items/${itemId}`);
      setOrders(prev => prev.map(o => o.id === order.id ? res.data : o));
    } catch {
      setError("Error al eliminar ítem.");
    }
  }

  async function handleAssignWashers() {
    if (!washerOrder) return;
    setSaving(true);
    try {
      const washers = washerRows
        .filter(w => w.user_id)
        .map(w => ({ user_id: parseInt(w.user_id), commission_percent: parseFloat(w.commission_percent) || 0 }));
      const res = await api.put<Order>(`/orders/${washerOrder.id}/washers`, { washers });
      setOrders(prev => prev.map(o => o.id === washerOrder.id ? res.data : o));
      setWasherDlg(false);
    } catch {
      setError("Error al asignar lavadores.");
    } finally {
      setSaving(false);
    }
  }

  function openPayDialog(order: Order) {
    setPayOrder(order);
    setPayMethod(order.payment_method ?? "efectivo");
    setPayStatus(order.payment_status === "pendiente" ? "pagado" : order.payment_status);
    setDiscount(order.discount_amount ?? "0");
    setPayDlg(true);
  }

  function openItemDialog(order: Order) {
    setItemOrder(order);
    setItemMode("catalog");
    setItemCatalogId(""); setItemName(""); setItemPrice(""); setItemQty("1");
    setItemDlg(true);
  }

  function openWasherDialog(order: Order) {
    setWasherOrder(order);
    setWasherRows(
      order.washers.length > 0
        ? order.washers.map(w => ({ user_id: String(w.user_id), commission_percent: String(w.commission_percent) }))
        : [{ user_id: "", commission_percent: "0" }]
    );
    setWasherDlg(true);
  }

  // ── Render ──

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Órdenes de Servicio</h1>
          <p className="text-sm text-slate-500">{orders.length} orden(es)</p>
        </div>
        <Button onClick={() => { resetNewForm(); setNewDlg(true); }}>
          <Plus className="h-4 w-4 mr-1" />
          Nueva orden
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Desde</label>
          <input type="date" className="rounded-md border border-slate-200 px-3 py-2 text-sm" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Hasta</label>
          <input type="date" className="rounded-md border border-slate-200 px-3 py-2 text-sm" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Estado</label>
          <select className="rounded-md border border-slate-200 px-3 py-2 text-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <Button variant="outline" size="sm" onClick={loadOrders}>Filtrar</Button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <ShoppingBag className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">No hay órdenes para este período</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                <th className="px-4 py-3 text-left">Folio</th>
                <th className="px-4 py-3 text-left">Fecha</th>
                <th className="px-4 py-3 text-left">Cliente</th>
                <th className="px-4 py-3 text-left">Vehículo</th>
                <th className="px-4 py-3 text-left">Estado</th>
                <th className="px-4 py-3 text-left">Pago</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-center w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orders.flatMap(o => {
                const folio = o.daily_sequence
                  ? `${o.service_date?.slice(5) ?? ""}/${o.daily_sequence}`
                  : `#${o.id}`;
                return [
                  <tr
                    key={o.id}
                    className={`cursor-pointer hover:bg-slate-50 ${expanded === o.id ? "bg-slate-50" : ""}`}
                    onClick={() => setExpanded(expanded === o.id ? null : o.id)}
                  >
                    <td className="px-4 py-3 text-xs text-slate-500 font-mono">{folio}</td>
                    <td className="px-4 py-3 text-slate-600">{o.service_date ?? "—"}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {o.client_id ? clientName(o.client_id) : "—"}
                      {o.is_domicilio && <span className="ml-1 text-xs text-blue-500">(dom.)</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{o.vehicle_id ? vehicleLabel(o.vehicle_id) : "—"}</td>
                    <td className="px-4 py-3"><Badge variant={statusVariant(o.status)}>{STATUS_LABELS[o.status] ?? o.status}</Badge></td>
                    <td className="px-4 py-3"><Badge variant={paymentVariant(o.payment_status)}>{o.payment_status}</Badge></td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900">{fmt(o.total)}</td>
                    <td className="px-4 py-3 text-center">
                      {expanded === o.id
                        ? <ChevronUp className="h-4 w-4 mx-auto text-slate-400" />
                        : <ChevronDown className="h-4 w-4 mx-auto text-slate-400" />}
                    </td>
                  </tr>,
                  expanded === o.id && (
                    <tr key={`${o.id}-detail`}>
                      <td colSpan={8} className="px-6 pb-5 bg-slate-50">
                        <div className="space-y-4 pt-3" onClick={e => e.stopPropagation()}>

                          {/* Items */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Servicios</h3>
                              <Button size="sm" variant="outline" onClick={() => openItemDialog(o)}>
                                <Plus className="h-3 w-3 mr-1" /> Agregar
                              </Button>
                            </div>
                            {o.items.length === 0 ? (
                              <p className="text-xs text-slate-400">Sin servicios</p>
                            ) : (
                              <div className="space-y-1">
                                {o.items.map(item => (
                                  <div key={item.id} className="flex items-center justify-between rounded bg-white border border-slate-100 px-3 py-2 text-sm">
                                    <span>{item.custom_name ?? services.find(s => s.id === item.catalog_id)?.name ?? `Servicio #${item.catalog_id}`}</span>
                                    <div className="flex items-center gap-3">
                                      <span className="text-slate-400">×{item.quantity}</span>
                                      <span className="font-medium">{fmt(item.unit_price)}</span>
                                      <button onClick={() => handleRemoveItem(o, item.id)} className="text-red-400 hover:text-red-600">
                                        <Trash2 className="h-3.5 w-3.5" />
                                      </button>
                                    </div>
                                  </div>
                                ))}
                                <div className="text-right text-sm font-semibold text-slate-700 pr-1">
                                  Total: {fmt(o.total)}
                                  {Number(o.discount_amount) > 0 && (
                                    <span className="text-slate-400 font-normal ml-2">(desc. {fmt(o.discount_amount)})</span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Washers */}
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Lavadores</h3>
                              <Button size="sm" variant="outline" onClick={() => openWasherDialog(o)}>Asignar</Button>
                            </div>
                            {o.washers.length === 0 ? (
                              <p className="text-xs text-slate-400">Sin lavadores asignados</p>
                            ) : (
                              <div className="flex flex-wrap gap-2">
                                {o.washers.map(w => {
                                  const op = operators.find(op => op.id === w.user_id);
                                  return (
                                    <div key={w.id} className="flex items-center gap-2 rounded bg-white border border-slate-100 px-3 py-1.5 text-sm">
                                      <span className="font-medium">{op?.name ?? `#${w.user_id}`}</span>
                                      <span className="text-slate-400">{w.commission_percent}% = {fmt(w.commission_amount)}</span>
                                      {w.is_paid && <Badge variant="success">Pagado</Badge>}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>

                          {/* Actions row */}
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            {STATUS_NEXT[o.status] && (
                              <Button size="sm" onClick={() => handleAdvanceStatus(o)}>
                                → {STATUS_LABELS[STATUS_NEXT[o.status]]}
                              </Button>
                            )}
                            <Button size="sm" variant="outline" onClick={() => openPayDialog(o)}>
                              Registrar pago
                            </Button>
                            {o.notes && (
                              <span className="text-xs text-slate-500 self-center">Nota: {o.notes}</span>
                            )}
                            {o.is_domicilio && o.delivery_address && (
                              <span className="text-xs text-blue-500 self-center">📍 {o.delivery_address}</span>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ),
                ];
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── New order dialog ── */}
      <Dialog open={newDlg} onOpenChange={o => { if (!o) setNewDlg(false); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Nueva orden de servicio</DialogTitle></DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
            {formError && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{formError}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Cliente</label>
                <select className={inputCls} value={newClientId} onChange={e => { setNewClientId(e.target.value); setNewVehicleId(""); }}>
                  <option value="">Sin cliente</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Vehículo</label>
                <select className={inputCls} value={newVehicleId} onChange={e => setNewVehicleId(e.target.value)}>
                  <option value="">Sin vehículo</option>
                  {clientVehicles.map(v => <option key={v.id} value={v.id}>{v.plate} {v.brand} {v.model}</option>)}
                </select>
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={newIsDomicilio} onChange={e => setNewIsDomicilio(e.target.checked)} />
              Servicio a domicilio
            </label>
            {newIsDomicilio && (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Dirección de entrega</label>
                <input className={inputCls} value={newDelivery} onChange={e => setNewDelivery(e.target.value)} placeholder="Calle y número" />
              </div>
            )}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inputCls} value={newNotes} onChange={e => setNewNotes(e.target.value)} placeholder="Opcional" />
            </div>

            {/* Items */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">Servicios</label>
                <Button size="sm" variant="outline" type="button"
                  onClick={() => setNewItems(prev => [...prev, { catalog_id: null, custom_name: "", unit_price: "", quantity: 1 }])}>
                  <Plus className="h-3 w-3 mr-1" /> Agregar
                </Button>
              </div>
              {newItems.map((item, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-5 space-y-1">
                    <label className="text-xs text-slate-500">Catálogo</label>
                    <select className={inputCls} value={item.catalog_id ?? ""} onChange={e => {
                      const svc = services.find(s => s.id === parseInt(e.target.value));
                      setNewItems(prev => prev.map((it, i) => i === idx
                        ? { ...it, catalog_id: svc?.id ?? null, custom_name: "", unit_price: svc?.base_price ?? it.unit_price }
                        : it));
                    }}>
                      <option value="">Personalizado</option>
                      {services.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </select>
                  </div>
                  {!item.catalog_id && (
                    <div className="col-span-3 space-y-1">
                      <label className="text-xs text-slate-500">Nombre</label>
                      <input className={inputCls} value={item.custom_name} placeholder="Descripción"
                        onChange={e => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, custom_name: e.target.value } : it))} />
                    </div>
                  )}
                  <div className={`${item.catalog_id ? "col-span-6" : "col-span-3"} space-y-1`}>
                    <label className="text-xs text-slate-500">Precio</label>
                    <input type="number" min="0" step="0.01" className={inputCls} value={item.unit_price} placeholder="0.00"
                      onChange={e => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: e.target.value } : it))} />
                  </div>
                  <button type="button" className="col-span-1 text-red-400 hover:text-red-600 pb-2 flex justify-center"
                    onClick={() => setNewItems(prev => prev.filter((_, i) => i !== idx))}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleCreateOrder} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Crear orden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Payment dialog ── */}
      <Dialog open={payDlg} onOpenChange={o => { if (!o) setPayDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Registrar pago — Orden #{payOrder?.id}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Método</label>
              <select className={inputCls} value={payMethod} onChange={e => setPayMethod(e.target.value)}>
                <option value="efectivo">Efectivo</option>
                <option value="tarjeta">Tarjeta</option>
                <option value="transferencia">Transferencia</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Estado</label>
              <select className={inputCls} value={payStatus} onChange={e => setPayStatus(e.target.value)}>
                <option value="pagado">Pagado</option>
                <option value="parcial">Parcial</option>
                <option value="pendiente">Pendiente</option>
                <option value="credito">Crédito</option>
                <option value="cortesia">Cortesía</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Descuento</label>
              <input type="number" min="0" step="0.01" className={inputCls} value={discount} onChange={e => setDiscount(e.target.value)} />
            </div>
            <p className="text-sm text-slate-600">Total orden: <span className="font-bold text-slate-900">{fmt(payOrder?.total ?? 0)}</span></p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleSetPayment} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Add item dialog ── */}
      <Dialog open={itemDlg} onOpenChange={o => { if (!o) setItemDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Agregar servicio — Orden #{itemOrder?.id}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="flex rounded-md overflow-hidden border border-slate-200 text-sm">
              {(["catalog", "custom"] as const).map(mode => (
                <button key={mode} onClick={() => setItemMode(mode)}
                  className={`flex-1 py-2 ${itemMode === mode ? "bg-slate-900 text-white" : "bg-white text-slate-600 hover:bg-slate-50"}`}>
                  {mode === "catalog" ? "Del catálogo" : "Personalizado"}
                </button>
              ))}
            </div>
            {itemMode === "catalog" ? (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Servicio</label>
                <select className={inputCls} value={itemCatalogId} onChange={e => {
                  setItemCatalogId(e.target.value);
                  const svc = services.find(s => s.id === parseInt(e.target.value));
                  if (svc) setItemPrice(svc.base_price);
                }}>
                  <option value="">Seleccionar…</option>
                  {services.map(s => <option key={s.id} value={s.id}>{s.name} — {fmt(s.base_price)}</option>)}
                </select>
              </div>
            ) : (
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Nombre</label>
                <input className={inputCls} value={itemName} onChange={e => setItemName(e.target.value)} placeholder="Descripción del servicio" />
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Precio</label>
                <input type="number" min="0" step="0.01" className={inputCls} value={itemPrice} onChange={e => setItemPrice(e.target.value)} placeholder="0.00" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Cantidad</label>
                <input type="number" min="1" className={inputCls} value={itemQty} onChange={e => setItemQty(e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAddItem} disabled={saving || (!itemCatalogId && !itemName) || !itemPrice}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Agregar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Washer dialog ── */}
      <Dialog open={washerDlg} onOpenChange={o => { if (!o) setWasherDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Asignar lavadores — Orden #{washerOrder?.id}</DialogTitle></DialogHeader>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {washerRows.map((w, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                <div className="col-span-7 space-y-1">
                  <label className="text-xs text-slate-500">Lavador</label>
                  <select className={inputCls} value={w.user_id}
                    onChange={e => setWasherRows(prev => prev.map((ws, i) => i === idx ? { ...ws, user_id: e.target.value } : ws))}>
                    <option value="">Seleccionar…</option>
                    {operators.map(op => <option key={op.id} value={op.id}>{op.name}</option>)}
                  </select>
                </div>
                <div className="col-span-4 space-y-1">
                  <label className="text-xs text-slate-500">% Comisión</label>
                  <input type="number" min="0" max="100" className={inputCls} value={w.commission_percent}
                    onChange={e => setWasherRows(prev => prev.map((ws, i) => i === idx ? { ...ws, commission_percent: e.target.value } : ws))} />
                </div>
                <button type="button" className="col-span-1 text-red-400 hover:text-red-600 pb-2 flex justify-center"
                  onClick={() => setWasherRows(prev => prev.filter((_, i) => i !== idx))}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
          <Button size="sm" variant="outline" onClick={() => setWasherRows(prev => [...prev, { user_id: "", commission_percent: "0" }])}>
            <Plus className="h-3 w-3 mr-1" /> Agregar lavador
          </Button>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWasherDlg(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleAssignWashers} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
