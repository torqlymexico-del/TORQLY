import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Loader2, Plus, ShoppingBag, ChevronDown, ChevronUp, Trash2, Search, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client { id: number; name: string; phone?: string | null; }
interface Vehicle { id: number; plate: string | null; brand: string | null; model: string | null; color: string | null; client_id?: number | null; }
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
  en_cola: "En cola", en_proceso: "En proceso", listo: "Listo",
  entregado: "Entregado", cancelado: "Cancelado",
};
const STATUS_NEXT: Record<string, { label: string; value: string }> = {
  en_cola:    { label: "Iniciar",  value: "en_proceso" },
  en_proceso: { label: "Listo",    value: "listo" },
  listo:      { label: "Entregar", value: "entregado" },
};
const STATUS_COLORS: Record<string, string> = {
  en_cola:    "bg-amber-100 text-amber-800",
  en_proceso: "bg-blue-100 text-blue-800",
  listo:      "bg-emerald-100 text-emerald-800",
  entregado:  "bg-slate-100 text-slate-600",
  cancelado:  "bg-red-100 text-red-700",
};
const PAY_COLORS: Record<string, string> = {
  pendiente: "bg-amber-100 text-amber-800",
  pagado:    "bg-emerald-100 text-emerald-800",
  parcial:   "bg-blue-100 text-blue-800",
  credito:   "bg-purple-100 text-purple-800",
  cortesia:  "bg-sky-100 text-sky-700",
};
const PAY_LABELS: Record<string, string> = {
  pendiente: "Pendiente", pagado: "Pagado", parcial: "Parcial",
  credito: "Crédito", cortesia: "Cortesía",
};
const PAY_METHOD_LABELS: Record<string, string> = {
  efectivo: "Efectivo", tarjeta: "Tarjeta", transferencia: "Transferencia",
  deposito: "Depósito", credito: "Crédito", cortesia: "Cortesía",
};
const PAY_METHODS = [
  { value: "efectivo", label: "Efectivo" },
  { value: "tarjeta", label: "Tarjeta" },
  { value: "transferencia", label: "Transferencia" },
  { value: "deposito", label: "Depósito" },
  { value: "credito", label: "Crédito — cartera" },
  { value: "cortesia", label: "Cortesía" },
];

type Scope = "today" | "date" | "history";
type Filter = "all" | "active" | "done" | "paid" | "pending_pay";

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmt(v: string | number | null | undefined) {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function normalize(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s#]/g, " ").replace(/\s+/g, " ").trim();
}
const inp = "w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";
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

  // Scope / filter / search
  const [scope, setScope] = useState<Scope>("today");
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [search, setSearch] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  // Expanded card
  const [expanded, setExpanded] = useState<number | null>(null);

  // Edit mode (inline per card)
  const [editOrder, setEditOrder] = useState<number | null>(null);
  const [editSection, setEditSection] = useState<string | null>(null);
  const [editWasherIds, setEditWasherIds] = useState<Set<number>>(new Set());
  const [editTotal, setEditTotal] = useState("");
  const [editStatus, setEditStatus] = useState("");
  const [editPayMethod, setEditPayMethod] = useState("");
  const [editReason, setEditReason] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  // New order dialog
  const [newDlg, setNewDlg] = useState(false);
  const [newClientId, setNewClientId] = useState("");
  const [newVehicleId, setNewVehicleId] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [newItems, setNewItems] = useState<NewItemRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Payment dialog
  const [payDlg, setPayDlg] = useState(false);
  const [payOrder, setPayOrder] = useState<Order | null>(null);
  const [payMethod, setPayMethod] = useState("efectivo");
  const [tendered, setTendered] = useState("");

  // ── Load ──────────────────────────────────────────────────────────────────

  const loadOrders = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const params: Record<string, string> = {};
      const today = todayStr();
      if (scope === "today") { params.date_from = today; params.date_to = today; }
      else if (scope === "date") { params.date_from = selectedDate; params.date_to = selectedDate; }
      const res = await api.get<Order[]>("/orders/", { params });
      setOrders(res.data);
    } catch { setError("Error al cargar órdenes."); }
    finally { setLoading(false); }
  }, [scope, selectedDate]);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  useEffect(() => {
    Promise.all([
      api.get<Client[]>("/clients/"),
      api.get<Vehicle[]>("/vehicles/"),
      api.get<ServiceCatalog[]>("/services-catalog/"),
      api.get<Operator[]>("/payroll/operators"),
    ]).then(([c, v, s, o]) => {
      setClients(c.data); setVehicles(v.data); setServices(s.data); setOperators(o.data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) {
        e.preventDefault(); searchRef.current?.focus(); searchRef.current?.select();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const clientName = (id: number | null) => clients.find(c => c.id === id)?.name ?? "";
  const getVehicle = (id: number | null) => vehicles.find(v => v.id === id);
  const opName = (id: number) => operators.find(op => op.id === id)?.name ?? `#${id}`;

  function folio(o: Order) {
    if (!o.daily_sequence) return `#${o.id}`;
    const day = o.service_date ? o.service_date.slice(5).replace("-", "/") : "";
    return day ? `${day} · #${String(o.daily_sequence).padStart(3, "0")}` : `#${String(o.daily_sequence).padStart(3, "0")}`;
  }

  function orderIndex(o: Order) {
    const v = getVehicle(o.vehicle_id);
    return normalize([
      folio(o), String(o.id), o.service_date ?? "",
      clientName(o.client_id), v?.plate ?? "", v?.brand ?? "", v?.model ?? "", v?.color ?? "",
      o.washers.map(w => opName(w.user_id)).join(" "),
      STATUS_LABELS[o.status] ?? o.status,
      PAY_LABELS[o.payment_status] ?? o.payment_status,
    ].join(" "));
  }

  // ── Filtered orders ───────────────────────────────────────────────────────

  const filtered = useMemo(() => {
    let list = [...orders];
    if (filter === "active") list = list.filter(o => ["en_cola", "en_proceso", "listo"].includes(o.status));
    else if (filter === "done") list = list.filter(o => o.status === "entregado");
    else if (filter === "paid") list = list.filter(o => o.payment_status === "pagado");
    else if (filter === "pending_pay") list = list.filter(o => o.payment_status === "pendiente" && o.status !== "cancelado");
    const q = normalize(search);
    if (q) list = list.filter(o => orderIndex(o).includes(q));
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, filter, search, clients, vehicles, operators]);

  const isPaid = (o: Order) => ["pagado", "credito", "cortesia"].includes(o.payment_status);
  const canCharge = (o: Order) => o.status !== "cancelado" && !isPaid(o);

  // ── Edit mode ─────────────────────────────────────────────────────────────

  function openEdit(o: Order) {
    setEditOrder(o.id);
    setEditSection(null);
    setEditWasherIds(new Set(o.washers.map(w => w.user_id)));
    setEditTotal(Number(o.total).toFixed(2));
    setEditStatus(o.status);
    setEditPayMethod(o.payment_method ?? "efectivo");
    setEditReason("");
    setCancelReason("");
  }

  function closeEdit() {
    setEditOrder(null);
    setEditSection(null);
  }

  function toggleSection(name: string) {
    setEditSection(prev => prev === name ? null : name);
    setEditReason("");
    setCancelReason("");
  }

  function toggleExpanded(id: number) {
    setExpanded(prev => {
      if (prev === id) { closeEdit(); return null; }
      closeEdit();
      return id;
    });
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async function advanceStatus(o: Order) {
    const next = STATUS_NEXT[o.status];
    if (!next) return;
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: next.value });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
    } catch { setError("Error al actualizar estado."); }
  }

  async function handleEditWashers(o: Order) {
    if (editWasherIds.size === 0) { setError("Selecciona al menos un lavador."); return; }
    setSaving(true);
    try {
      const washers = Array.from(editWasherIds).map(uid => ({
        user_id: uid,
        commission_percent: parseFloat(operators.find(op => op.id === uid)?.commission_percentage ?? "0") || 0,
      }));
      const res = await api.put<Order>(`/orders/${o.id}/washers`, { washers });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
      setEditSection(null);
    } catch { setError("Error al asignar lavadores."); }
    finally { setSaving(false); }
  }

  async function handleEditTotal(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/total`, { total: parseFloat(editTotal), reason: editReason || null });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
      setEditSection(null);
    } catch { setError("Error al actualizar el monto."); }
    finally { setSaving(false); }
  }

  async function handleEditStatus(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: editStatus });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
      setEditSection(null);
    } catch { setError("Error al actualizar estado."); }
    finally { setSaving(false); }
  }

  async function handleEditPayMethod(o: Order) {
    setSaving(true);
    try {
      const isCourtesy = editPayMethod === "cortesia";
      const isCredit = editPayMethod === "credito";
      const res = await api.patch<Order>(`/orders/${o.id}/payment`, {
        payment_method: editPayMethod,
        payment_status: isCourtesy ? "cortesia" : isCredit ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
      setEditSection(null);
    } catch { setError("Error al cambiar método de pago."); }
    finally { setSaving(false); }
  }

  async function handleCancel(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: "cancelado", cancellation_reason: cancelReason });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x));
      closeEdit();
    } catch { setError("Error al cancelar la orden."); }
    finally { setSaving(false); }
  }

  async function handleCreateOrder() {
    setSaving(true); setFormError("");
    try {
      await api.post("/orders/", {
        client_id: newClientId ? parseInt(newClientId) : null,
        vehicle_id: newVehicleId ? parseInt(newVehicleId) : null,
        notes: newNotes || null,
        items: newItems.filter(i => i.custom_name.trim() || i.catalog_id).map(i => ({
          catalog_id: i.catalog_id ?? null,
          custom_name: i.catalog_id ? null : (i.custom_name.trim() || null),
          unit_price: parseFloat(i.unit_price) || 0,
          quantity: i.quantity || 1,
        })),
      });
      setNewDlg(false);
      setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]);
      loadOrders();
    } catch (err: unknown) {
      setFormError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al crear la orden.");
    } finally { setSaving(false); }
  }

  async function handlePay() {
    if (!payOrder) return;
    setSaving(true);
    try {
      const isCourtesy = payMethod === "cortesia";
      const isCredit = payMethod === "credito";
      const res = await api.patch<Order>(`/orders/${payOrder.id}/payment`, {
        payment_method: payMethod,
        payment_status: isCourtesy ? "cortesia" : isCredit ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(prev => prev.map(o => o.id === payOrder.id ? res.data : o));
      setPayDlg(false);
    } catch { setError("Error al registrar el pago."); }
    finally { setSaving(false); }
  }

  async function handleRemoveItem(order: Order, itemId: number) {
    try {
      const res = await api.delete<Order>(`/orders/${order.id}/items/${itemId}`);
      setOrders(prev => prev.map(o => o.id === order.id ? res.data : o));
    } catch { setError("Error al eliminar ítem."); }
  }

  const change = payOrder ? Math.max(0, (parseFloat(tendered) || 0) - Number(payOrder.total)) : 0;

  // ── Render ────────────────────────────────────────────────────────────────

  const SCOPES: { key: Scope; label: string }[] = [
    { key: "today", label: "Hoy" },
    { key: "date", label: "Por fecha" },
    { key: "history", label: "Historial" },
  ];
  const FILTERS: { key: Filter; label: string }[] = [
    { key: "all", label: "Todos" },
    { key: "active", label: "En proceso" },
    { key: "done", label: "Terminados" },
    { key: "paid", label: "Pagados" },
    { key: "pending_pay", label: "Pendientes de cobro" },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Servicios</h1>
          <p className="text-sm text-slate-500">Estado, cobros y cancelaciones en una sola vista.</p>
        </div>
        <Button onClick={() => { setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]); setFormError(""); setNewDlg(true); }}>
          <Plus className="h-4 w-4 mr-1" /> Nueva orden
        </Button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-400 hover:text-red-600 ml-2"><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Scope tabs */}
      <div className="flex flex-wrap gap-2">
        {SCOPES.map(s => (
          <button key={s.key} onClick={() => setScope(s.key)}
            className={`px-4 py-2 rounded-full text-sm font-bold border transition-all ${scope === s.key ? "bg-slate-900 text-white border-transparent" : "bg-white border-slate-200 text-slate-700 hover:border-slate-400"}`}>
            {s.label}
          </button>
        ))}
      </div>

      {scope === "date" && (
        <div className="flex items-center gap-3">
          <input type="date" className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium"
            value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
        </div>
      )}

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${filter === f.key ? "bg-red-600 text-white border-transparent" : "bg-white border-slate-200 text-slate-600 hover:border-slate-400"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Sticky search bar */}
      <div className="sticky top-3 z-20">
        <div className="bg-white/95 backdrop-blur border border-blue-100 rounded-2xl px-3 py-2.5 shadow-md flex items-center gap-2">
          <Search className="h-4 w-4 text-slate-400 shrink-0" />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por folio, placa, modelo, color, cliente o lavador… (/ para enfocar)"
            className="flex-1 text-sm bg-transparent outline-none font-medium text-slate-800 placeholder:text-slate-400"
          />
          <span className="text-xs font-black bg-slate-900 text-white rounded-full px-3 py-1 shrink-0">
            {filtered.length} auto{filtered.length !== 1 ? "s" : ""}
          </span>
          {search && (
            <button onClick={() => setSearch("")} className="text-slate-400 hover:text-slate-600">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Orders list */}
      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <ShoppingBag className="h-12 w-12 mb-3 opacity-30" />
          <p className="text-sm">{search ? "No hay resultados para esa búsqueda." : "No hay órdenes."}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(o => {
            const v = getVehicle(o.vehicle_id);
            const washerNames = o.washers.map(w => opName(w.user_id)).join(", ");
            const isOpen = expanded === o.id;
            const inEditMode = editOrder === o.id;
            const isCancelled = o.status === "cancelado";
            const isClosed = isPaid(o);

            // Which jump links to show
            const showLavadores = !isCancelled && !isClosed;
            const showMonto = !isClosed && !isCancelled;
            const showEstado = !isCancelled;
            const showMetodoPago = isClosed && !isCancelled;
            const showCancelar = !isCancelled && !isClosed;
            const hasEditOptions = showLavadores || showMonto || showEstado || showMetodoPago || showCancelar;

            return (
              <article key={o.id} className={`bg-white border rounded-2xl shadow-sm overflow-hidden ${isOpen ? "border-blue-200 ring-2 ring-blue-100" : "border-slate-100"}`}>

                {/* Card header */}
                <div
                  className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors select-none"
                  onClick={() => toggleExpanded(o.id)}
                >
                  {/* Vehicle + meta */}
                  <div className="flex-1 min-w-0">
                    <div className="font-black text-slate-900 text-base leading-tight truncate mb-1.5">
                      {folio(o)} · {v ? `${v.brand ?? ""} ${v.model ?? ""}`.trim() || "Vehículo" : "Vehículo"}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1" style={{ fontSize: ".82rem" }}>
                      {v?.plate && (
                        <span className="font-mono font-black bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-xs">{v.plate}</span>
                      )}
                      {v?.color && <span className="text-slate-400">{v.color}</span>}
                      {washerNames
                        ? <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-semibold text-xs">{washerNames}</span>
                        : <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-semibold text-xs">Sin asignar</span>}
                      {clientName(o.client_id) && <span className="text-slate-400">{clientName(o.client_id)}</span>}
                    </div>
                  </div>

                  {/* Badges + total */}
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${STATUS_COLORS[o.status] ?? "bg-slate-100 text-slate-600"}`}>
                        {STATUS_LABELS[o.status] ?? o.status}
                      </span>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${PAY_COLORS[o.payment_status] ?? "bg-slate-100 text-slate-600"}`}>
                        {PAY_LABELS[o.payment_status] ?? o.payment_status}
                      </span>
                    </div>
                    <span className="font-black text-slate-900 text-xl leading-none">{fmt(o.total)}</span>
                  </div>

                  {/* Cobrar / status chip */}
                  {canCharge(o) && (
                    <button
                      className="shrink-0 font-black text-white text-sm px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 transition-colors whitespace-nowrap"
                      onClick={e => { e.stopPropagation(); setPayOrder(o); setPayMethod("efectivo"); setTendered(""); setPayDlg(true); }}
                    >
                      Cobrar
                    </button>
                  )}
                  {isClosed && !isCancelled && (
                    <span className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full bg-slate-100 text-slate-500">Cerrado</span>
                  )}
                  {isCancelled && (
                    <span className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full bg-red-100 text-red-700">Cancelado</span>
                  )}

                  <span className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-slate-100 text-slate-400">
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </span>
                </div>

                {/* Expanded panel */}
                {isOpen && (
                  <div className="border-t border-slate-100 px-5 py-4 space-y-4" onClick={e => e.stopPropagation()}>

                    {/* Quick action bar */}
                    <div className="flex items-center justify-between gap-2 flex-wrap bg-slate-50 rounded-xl px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {!isCancelled && STATUS_NEXT[o.status] && (
                          <button
                            onClick={() => advanceStatus(o)}
                            className="px-4 py-2 rounded-full bg-emerald-600 text-white text-sm font-bold hover:bg-emerald-700 transition-colors"
                          >
                            {STATUS_NEXT[o.status].label}
                          </button>
                        )}
                        {isClosed && !isCancelled && (
                          <span className="text-sm text-slate-400 font-medium">Servicio cerrado</span>
                        )}
                        {isCancelled && (
                          <span className="text-sm text-red-500 font-medium">Orden cancelada</span>
                        )}
                      </div>
                      <button
                        onClick={() => inEditMode ? closeEdit() : openEdit(o)}
                        className={`px-4 py-2 rounded-full text-sm font-bold transition-colors ${inEditMode ? "bg-blue-600 text-white hover:bg-blue-700" : "bg-slate-900 text-white hover:bg-slate-700"}`}
                      >
                        {inEditMode ? "Cerrar edición" : "Editar"}
                      </button>
                    </div>

                    {/* Service items */}
                    <div className="rounded-xl bg-slate-50 p-4">
                      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">Servicio</h3>
                      {o.items.length === 0 ? (
                        <p className="text-sm text-slate-400">Sin renglones de servicio.</p>
                      ) : (
                        <div className="space-y-2">
                          {o.items.map(item => (
                            <div key={item.id} className="flex items-center justify-between bg-white border border-slate-100 rounded-xl px-4 py-2.5">
                              <div>
                                <p className="text-sm font-semibold text-slate-800">
                                  {item.custom_name ?? services.find(s => s.id === item.catalog_id)?.name ?? `Servicio #${item.catalog_id}`}
                                </p>
                                <p className="text-xs text-slate-400">Cant: {item.quantity}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-sm font-bold text-blue-700">{fmt(item.unit_price)}</span>
                                {!isClosed && !isCancelled && (
                                  <button onClick={() => handleRemoveItem(o, item.id)} className="text-slate-300 hover:text-red-500 transition-colors">
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                          <div className="text-right text-sm font-black text-slate-900 pr-1 pt-1">
                            Total: {fmt(o.total)}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* ── Edit mode ── */}
                    {inEditMode && (
                      <div className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-white p-4 space-y-3">
                        {/* Guide */}
                        <div>
                          <h3 className="text-sm font-black text-slate-900 mb-0.5">Modo de edición</h3>
                          <p className="text-xs text-slate-500 mb-3">Selecciona qué deseas modificar.</p>
                          {hasEditOptions ? (
                            <div className="flex flex-wrap gap-2">
                              {showLavadores && (
                                <button onClick={() => toggleSection("lavadores")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${editSection === "lavadores" ? "bg-blue-600 text-white border-transparent" : "bg-white border-blue-200 text-blue-700 hover:border-blue-400"}`}>
                                  Lavadores
                                </button>
                              )}
                              {showMonto && (
                                <button onClick={() => toggleSection("monto")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${editSection === "monto" ? "bg-blue-600 text-white border-transparent" : "bg-white border-blue-200 text-blue-700 hover:border-blue-400"}`}>
                                  Monto
                                </button>
                              )}
                              {showEstado && (
                                <button onClick={() => toggleSection("estado")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${editSection === "estado" ? "bg-blue-600 text-white border-transparent" : "bg-white border-blue-200 text-blue-700 hover:border-blue-400"}`}>
                                  Estado
                                </button>
                              )}
                              {showMetodoPago && (
                                <button onClick={() => toggleSection("pago")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${editSection === "pago" ? "bg-blue-600 text-white border-transparent" : "bg-white border-blue-200 text-blue-700 hover:border-blue-400"}`}>
                                  Método de pago
                                </button>
                              )}
                              {showCancelar && (
                                <button onClick={() => toggleSection("cancelar")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${editSection === "cancelar" ? "bg-red-600 text-white border-transparent" : "bg-white border-red-200 text-red-600 hover:border-red-400"}`}>
                                  Cancelar
                                </button>
                              )}
                            </div>
                          ) : (
                            <p className="text-sm text-slate-400">No hay opciones de edición disponibles.</p>
                          )}
                        </div>

                        {/* Lavadores section */}
                        {editSection === "lavadores" && showLavadores && (
                          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                            <div>
                              <h4 className="text-sm font-bold text-slate-800">Lavadores</h4>
                              <p className="text-xs text-slate-400">Actual: {washerNames || "Sin asignar"}</p>
                            </div>
                            {operators.length === 0 ? (
                              <p className="text-sm text-slate-400">No hay operadores activos.</p>
                            ) : (
                              <div className="grid grid-cols-2 gap-2">
                                {operators.map(op => (
                                  <label key={op.id}
                                    className={`flex items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${editWasherIds.has(op.id) ? "bg-blue-50 border-blue-300" : "bg-slate-50 border-slate-200 hover:border-slate-300"}`}>
                                    <input type="checkbox" className="accent-blue-600" checked={editWasherIds.has(op.id)}
                                      onChange={e => setEditWasherIds(prev => {
                                        const next = new Set(prev);
                                        e.target.checked ? next.add(op.id) : next.delete(op.id);
                                        return next;
                                      })} />
                                    <div>
                                      <div className="text-sm font-semibold text-slate-800">{op.name}</div>
                                      <div className="text-xs text-slate-400">{op.commission_percentage}% comisión</div>
                                    </div>
                                  </label>
                                ))}
                              </div>
                            )}
                            <div className="flex justify-end">
                              <Button size="sm" onClick={() => handleEditWashers(o)} disabled={saving || editWasherIds.size === 0}>
                                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Guardar
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Monto section */}
                        {editSection === "monto" && showMonto && (
                          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                            <div>
                              <h4 className="text-sm font-bold text-slate-800">Monto del vehículo</h4>
                              <p className="text-xs text-slate-400">Actual: {fmt(o.total)}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-500">Nuevo monto</label>
                                <input type="number" min="0" step="0.01" className={inp} value={editTotal}
                                  onChange={e => setEditTotal(e.target.value)} />
                              </div>
                              <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-500">Motivo</label>
                                <input className={inp} value={editReason} onChange={e => setEditReason(e.target.value)}
                                  placeholder="Razón del ajuste" />
                              </div>
                            </div>
                            <div className="flex justify-end">
                              <Button size="sm" onClick={() => handleEditTotal(o)} disabled={saving || !editTotal.trim()}>
                                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Guardar
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Estado section */}
                        {editSection === "estado" && showEstado && (
                          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                            <h4 className="text-sm font-bold text-slate-800">Cambiar estado</h4>
                            <div className="flex gap-2 flex-wrap items-end">
                              <div className="flex-1 min-w-0">
                                <select className={inp} value={editStatus} onChange={e => setEditStatus(e.target.value)}>
                                  {Object.entries(STATUS_LABELS).filter(([k]) => k !== "cancelado").map(([k, v]) => (
                                    <option key={k} value={k}>{v}</option>
                                  ))}
                                </select>
                              </div>
                              <Button size="sm" onClick={() => handleEditStatus(o)} disabled={saving}>
                                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Actualizar
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Método de pago section */}
                        {editSection === "pago" && showMetodoPago && (
                          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                            <div>
                              <h4 className="text-sm font-bold text-slate-800">Cambiar método de pago</h4>
                              <p className="text-xs text-slate-400">
                                Actual: {PAY_METHOD_LABELS[o.payment_method ?? ""] ?? o.payment_method ?? "—"}
                              </p>
                            </div>
                            <div className="flex gap-2 flex-wrap items-end">
                              <div className="flex-1 min-w-0">
                                <select className={inp} value={editPayMethod} onChange={e => setEditPayMethod(e.target.value)}>
                                  {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                                </select>
                              </div>
                              <Button size="sm" onClick={() => handleEditPayMethod(o)} disabled={saving}>
                                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Guardar
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Cancelar section */}
                        {editSection === "cancelar" && showCancelar && (
                          <div className="bg-white rounded-xl border border-red-200 p-4 space-y-3">
                            <h4 className="text-sm font-bold text-red-700">Cancelar orden #{o.id}</h4>
                            <div className="space-y-1">
                              <label className="text-xs font-semibold text-slate-500">
                                Motivo <span className="text-red-500">*</span>
                              </label>
                              <input
                                className={`${inp} border-red-200 focus:ring-red-400`}
                                value={cancelReason}
                                onChange={e => setCancelReason(e.target.value)}
                                placeholder="Describe el motivo de la cancelación"
                              />
                            </div>
                            <div className="flex justify-end">
                              <Button size="sm" variant="destructive"
                                onClick={() => handleCancel(o)} disabled={saving || !cancelReason.trim()}>
                                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Cancelar orden
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Washers summary (when NOT in edit mode) */}
                    {!inEditMode && o.washers.length > 0 && (
                      <div className="rounded-xl bg-slate-50 px-4 py-3">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Lavadores</h3>
                        <div className="flex flex-wrap gap-2">
                          {o.washers.map(w => (
                            <div key={w.id} className="flex items-center gap-2 bg-white border border-slate-100 rounded-full px-3 py-1.5 text-sm">
                              <span className="font-semibold text-slate-800">{opName(w.user_id)}</span>
                              <span className="text-slate-400">{w.commission_percent}% = {fmt(w.commission_amount)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Notes / domicilio */}
                    {(o.notes || o.is_domicilio) && (
                      <div className="flex flex-wrap gap-3 text-sm text-slate-500">
                        {o.notes && <span>Nota: {o.notes}</span>}
                        {o.is_domicilio && o.delivery_address && (
                          <span className="text-blue-500">📍 {o.delivery_address}</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {/* ── Payment dialog ── */}
      <Dialog open={payDlg} onOpenChange={o => { if (!o) setPayDlg(false); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Cobrar servicio</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Vehicle + total card */}
            {payOrder && (
              <div className="flex items-start justify-between gap-4 bg-slate-900 text-white rounded-2xl p-4">
                <div>
                  <div className="text-xs opacity-60 uppercase tracking-wide font-semibold mb-0.5">Vehículo</div>
                  <div className="font-bold text-sm">
                    {getVehicle(payOrder.vehicle_id)
                      ? `${getVehicle(payOrder.vehicle_id)?.brand ?? ""} ${getVehicle(payOrder.vehicle_id)?.model ?? ""}`.trim() || "Vehículo"
                      : "Vehículo"}
                  </div>
                  <div className="text-xs opacity-50 mt-0.5">
                    {folio(payOrder)} · {clientName(payOrder.client_id) || "Cliente general"}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs opacity-60 uppercase tracking-wide font-semibold mb-0.5">Total</div>
                  <div className="font-black text-2xl leading-none">{fmt(payOrder.total)}</div>
                </div>
              </div>
            )}

            {/* Payment method */}
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Forma de pago</label>
              <select className={inp} value={payMethod} onChange={e => { setPayMethod(e.target.value); setTendered(""); }}>
                {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            {/* Cash change helper */}
            {payMethod === "efectivo" && (
              <div className="rounded-xl bg-sky-50 border border-sky-200 p-4 space-y-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-slate-700">Efectivo recibido</label>
                  <input
                    type="number" min="0" step="0.01" className={inp}
                    value={tendered} onChange={e => setTendered(e.target.value)}
                    placeholder="Ej. 500" autoFocus
                  />
                </div>
                <div className="flex items-center justify-between bg-slate-900 text-white rounded-xl px-4 py-3">
                  <span className="text-xs font-semibold opacity-60 uppercase tracking-wide">Cambio a dar</span>
                  <span className="text-xl font-black">{fmt(change)}</span>
                </div>
              </div>
            )}

            {payMethod === "credito" && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm">
                <p className="font-bold text-amber-800">Se registrará como crédito.</p>
                <p className="text-amber-700 text-xs mt-1">No entra a caja. Se carga al saldo de cartera del cliente.</p>
              </div>
            )}

            {payMethod === "cortesia" && (
              <div className="rounded-xl bg-sky-50 border border-sky-200 px-4 py-3 text-sm">
                <p className="font-bold text-sky-800">Servicio cerrado como cortesía.</p>
                <p className="text-sky-700 text-xs mt-1">Sin ingreso a caja. Se conserva la comisión del lavador.</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayDlg(false)} disabled={saving}>Cancelar</Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handlePay} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Registrar cobro
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
                <select className={inp} value={newClientId} onChange={e => { setNewClientId(e.target.value); setNewVehicleId(""); }}>
                  <option value="">Sin cliente</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-700">Vehículo</label>
                <select className={inp} value={newVehicleId} onChange={e => setNewVehicleId(e.target.value)}>
                  <option value="">Sin vehículo</option>
                  {vehicles
                    .filter(v => !newClientId || !v.client_id || v.client_id === parseInt(newClientId))
                    .map(v => (
                      <option key={v.id} value={v.id}>{[v.plate, v.brand, v.model].filter(Boolean).join(" ")}</option>
                    ))}
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-700">Notas</label>
              <input className={inp} value={newNotes} onChange={e => setNewNotes(e.target.value)} placeholder="Opcional" />
            </div>
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
                    <select className={inp} value={item.catalog_id ?? ""} onChange={e => {
                      const svc = services.find(s => s.id === parseInt(e.target.value));
                      setNewItems(prev => prev.map((it, i) => i === idx
                        ? { ...it, catalog_id: svc?.id ?? null, custom_name: "", unit_price: svc?.base_price ?? it.unit_price }
                        : it));
                    }}>
                      <option value="">Personalizado</option>
                      {services.map(s => <option key={s.id} value={s.id}>{s.name} — {fmt(s.base_price)}</option>)}
                    </select>
                  </div>
                  {!item.catalog_id && (
                    <div className="col-span-3 space-y-1">
                      <label className="text-xs text-slate-500">Nombre</label>
                      <input className={inp} value={item.custom_name} placeholder="Descripción"
                        onChange={e => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, custom_name: e.target.value } : it))} />
                    </div>
                  )}
                  <div className={`${item.catalog_id ? "col-span-6" : "col-span-3"} space-y-1`}>
                    <label className="text-xs text-slate-500">Precio</label>
                    <input type="number" min="0" step="0.01" className={inp} value={item.unit_price} placeholder="0.00"
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
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Crear orden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
