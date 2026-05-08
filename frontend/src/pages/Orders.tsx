import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Loader2, Plus, ShoppingBag, ChevronDown, ChevronUp, Trash2,
  Search, X, Car, User2, Wrench,
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
  id: number; catalog_id: number | null; custom_name: string | null;
  unit_price: string; quantity: number;
}
interface OrderWasher {
  id: number; user_id: number; commission_percent: string;
  commission_amount: string; is_paid: boolean;
}
interface Order {
  id: number; client_id: number | null; vehicle_id: number | null;
  service_date: string | null; daily_sequence: number | null;
  subtotal: string; discount_amount: string; total: string;
  status: string; payment_status: string; payment_method: string | null;
  is_domicilio: boolean; delivery_address: string | null; notes: string | null;
  items: OrderItem[]; washers: OrderWasher[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_META: Record<string, { label: string; badge: string; strip: string }> = {
  en_cola:    { label: "En cola",    badge: "bg-amber-100 text-amber-800 ring-1 ring-amber-200",    strip: "bg-amber-400" },
  en_proceso: { label: "Lavando",    badge: "bg-blue-100 text-blue-800 ring-1 ring-blue-200",       strip: "bg-blue-500" },
  listo:      { label: "Listo",      badge: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200", strip: "bg-emerald-500" },
  entregado:  { label: "Entregado",  badge: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",    strip: "bg-slate-400" },
  cancelado:  { label: "Cancelado",  badge: "bg-red-100 text-red-700 ring-1 ring-red-200",          strip: "bg-red-400" },
};
const STATUS_NEXT: Record<string, { label: string; value: string; cls: string }> = {
  en_cola:    { label: "▶ Iniciar",  value: "en_proceso", cls: "bg-blue-600 hover:bg-blue-700 text-white" },
  en_proceso: { label: "✓ Listo",    value: "listo",      cls: "bg-emerald-600 hover:bg-emerald-700 text-white" },
  listo:      { label: "↗ Entregar", value: "entregado",  cls: "bg-slate-800 hover:bg-slate-900 text-white" },
};
const PAY_META: Record<string, { label: string; badge: string }> = {
  pendiente: { label: "Pendiente", badge: "bg-amber-50 text-amber-700 ring-1 ring-amber-200" },
  pagado:    { label: "Pagado",    badge: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" },
  parcial:   { label: "Parcial",   badge: "bg-blue-50 text-blue-700 ring-1 ring-blue-200" },
  credito:   { label: "Crédito",   badge: "bg-violet-50 text-violet-700 ring-1 ring-violet-200" },
  cortesia:  { label: "Cortesía",  badge: "bg-sky-50 text-sky-700 ring-1 ring-sky-200" },
};
const PAY_METHOD_LABELS: Record<string, string> = {
  efectivo: "Efectivo", tarjeta: "Tarjeta", transferencia: "Transferencia",
  deposito: "Depósito", credito: "Crédito", cortesia: "Cortesía",
};
const PAY_METHODS = [
  { value: "efectivo",      label: "💵 Efectivo" },
  { value: "tarjeta",       label: "💳 Tarjeta" },
  { value: "transferencia", label: "📲 Transferencia" },
  { value: "deposito",      label: "🏦 Depósito" },
  { value: "credito",       label: "📒 Crédito — cartera" },
  { value: "cortesia",      label: "🎁 Cortesía" },
];

type Scope  = "today" | "date" | "history";
type Filter = "all" | "active" | "done" | "paid" | "pending_pay";

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmt(v: string | number | null | undefined) {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function normalize(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s#]/g, " ").replace(/\s+/g, " ").trim();
}
const inp = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition";
type NewItemRow = { catalog_id: number | null; custom_name: string; unit_price: string; quantity: number };

// ─── Component ────────────────────────────────────────────────────────────────

export default function Orders() {
  const [orders,    setOrders]    = useState<Order[]>([]);
  const [clients,   setClients]   = useState<Client[]>([]);
  const [vehicles,  setVehicles]  = useState<Vehicle[]>([]);
  const [services,  setServices]  = useState<ServiceCatalog[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState("");

  const [scope,        setScope]        = useState<Scope>("today");
  const [filter,       setFilter]       = useState<Filter>("all");
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [search,       setSearch]       = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  const [expanded, setExpanded] = useState<number | null>(null);

  // Edit mode
  const [editOrder,     setEditOrder]     = useState<number | null>(null);
  const [editSection,   setEditSection]   = useState<string | null>(null);
  const [editWasherIds, setEditWasherIds] = useState<Set<number>>(new Set());
  const [editTotal,     setEditTotal]     = useState("");
  const [editStatus,    setEditStatus]    = useState("");
  const [editPayMethod, setEditPayMethod] = useState("");
  const [editReason,    setEditReason]    = useState("");
  const [cancelReason,  setCancelReason]  = useState("");

  // New order dialog
  const [newDlg,      setNewDlg]      = useState(false);
  const [newClientId, setNewClientId] = useState("");
  const [newVehicleId,setNewVehicleId]= useState("");
  const [newNotes,    setNewNotes]    = useState("");
  const [newItems,    setNewItems]    = useState<NewItemRow[]>([]);
  const [saving,      setSaving]      = useState(false);
  const [formError,   setFormError]   = useState("");

  // Payment dialog
  const [payDlg,    setPayDlg]    = useState(false);
  const [payOrder,  setPayOrder]  = useState<Order | null>(null);
  const [payMethod, setPayMethod] = useState("efectivo");
  const [tendered,  setTendered]  = useState("");

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
      const t = e.target as HTMLElement;
      if (e.key === "/" && !["INPUT","TEXTAREA","SELECT"].includes(t.tagName)) {
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
      STATUS_META[o.status]?.label ?? o.status,
      PAY_META[o.payment_status]?.label ?? o.payment_status,
    ].join(" "));
  }

  const filtered = useMemo(() => {
    let list = [...orders];
    if (filter === "active")      list = list.filter(o => ["en_cola","en_proceso","listo"].includes(o.status));
    else if (filter === "done")   list = list.filter(o => o.status === "entregado");
    else if (filter === "paid")   list = list.filter(o => o.payment_status === "pagado");
    else if (filter === "pending_pay") list = list.filter(o => o.payment_status === "pendiente" && o.status !== "cancelado");
    const q = normalize(search);
    if (q) list = list.filter(o => orderIndex(o).includes(q));
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, filter, search, clients, vehicles, operators]);

  const isPaid    = (o: Order) => ["pagado","credito","cortesia"].includes(o.payment_status);
  const canCharge = (o: Order) => o.status !== "cancelado" && !isPaid(o);

  // ── Edit mode ─────────────────────────────────────────────────────────────

  function openEdit(o: Order) {
    setEditOrder(o.id); setEditSection(null);
    setEditWasherIds(new Set(o.washers.map(w => w.user_id)));
    setEditTotal(Number(o.total).toFixed(2));
    setEditStatus(o.status); setEditPayMethod(o.payment_method ?? "efectivo");
    setEditReason(""); setCancelReason("");
  }
  function closeEdit() { setEditOrder(null); setEditSection(null); }
  function toggleSection(name: string) { setEditSection(prev => prev === name ? null : name); setEditReason(""); setCancelReason(""); }
  function toggleExpanded(id: number) {
    setExpanded(prev => { if (prev === id) { closeEdit(); return null; } closeEdit(); return id; });
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async function advanceStatus(o: Order) {
    const next = STATUS_NEXT[o.status]; if (!next) return;
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
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setError("Error al asignar lavadores."); } finally { setSaving(false); }
  }
  async function handleEditTotal(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/total`, { total: parseFloat(editTotal), reason: editReason || null });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setError("Error al actualizar el monto."); } finally { setSaving(false); }
  }
  async function handleEditStatus(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: editStatus });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setError("Error al actualizar estado."); } finally { setSaving(false); }
  }
  async function handleEditPayMethod(o: Order) {
    setSaving(true);
    try {
      const isCourtesy = editPayMethod === "cortesia"; const isCredit = editPayMethod === "credito";
      const res = await api.patch<Order>(`/orders/${o.id}/payment`, {
        payment_method: editPayMethod,
        payment_status: isCourtesy ? "cortesia" : isCredit ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setError("Error al cambiar método de pago."); } finally { setSaving(false); }
  }
  async function handleCancel(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: "cancelado", cancellation_reason: cancelReason });
      setOrders(prev => prev.map(x => x.id === o.id ? res.data : x)); closeEdit();
    } catch { setError("Error al cancelar la orden."); } finally { setSaving(false); }
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
          unit_price: parseFloat(i.unit_price) || 0, quantity: i.quantity || 1,
        })),
      });
      setNewDlg(false); setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]);
      loadOrders();
    } catch (err: unknown) {
      setFormError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al crear la orden.");
    } finally { setSaving(false); }
  }
  async function handlePay() {
    if (!payOrder) return; setSaving(true);
    try {
      const isCourtesy = payMethod === "cortesia"; const isCredit = payMethod === "credito";
      const res = await api.patch<Order>(`/orders/${payOrder.id}/payment`, {
        payment_method: payMethod,
        payment_status: isCourtesy ? "cortesia" : isCredit ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(prev => prev.map(o => o.id === payOrder.id ? res.data : o)); setPayDlg(false);
    } catch { setError("Error al registrar el pago."); } finally { setSaving(false); }
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
    { key: "today",   label: "Hoy" },
    { key: "date",    label: "Por fecha" },
    { key: "history", label: "Historial" },
  ];
  const FILTERS: { key: Filter; label: string; count?: number }[] = [
    { key: "all",         label: "Todos" },
    { key: "active",      label: "En proceso" },
    { key: "done",        label: "Terminados" },
    { key: "paid",        label: "Pagados" },
    { key: "pending_pay", label: "Por cobrar" },
  ];

  return (
    <div className="space-y-5 pb-10">

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Órdenes de servicio</h1>
          <p className="text-sm text-slate-400 mt-0.5">Estado, cobros y edición desde aquí.</p>
        </div>
        <button
          onClick={() => { setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]); setFormError(""); setNewDlg(true); }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold shadow-sm transition-all hover:shadow-md"
        >
          <Plus className="h-4 w-4" /> Nueva orden
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between gap-3 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm font-medium">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-400 hover:text-red-600 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* ── Scope tabs ──────────────────────────────────────────────────── */}
      <div className="flex gap-1.5 p-1 bg-slate-100 rounded-xl w-fit">
        {SCOPES.map(s => (
          <button key={s.key} onClick={() => setScope(s.key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-bold transition-all ${scope === s.key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
            {s.label}
          </button>
        ))}
      </div>

      {scope === "date" && (
        <input type="date" className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
      )}

      {/* ── Filter pills ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
              filter === f.key
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-white border border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700"
            }`}>
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Sticky search ───────────────────────────────────────────────── */}
      <div className="sticky top-2 z-20">
        <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 shadow-lg shadow-slate-100 flex items-center gap-3">
          <Search className="h-4 w-4 text-slate-400 shrink-0" />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar folio, placa, modelo, color, cliente, lavador…"
            className="flex-1 text-sm bg-transparent outline-none text-slate-700 placeholder:text-slate-400"
          />
          <div className="flex items-center gap-2 shrink-0">
            {search && (
              <button onClick={() => setSearch("")} className="text-slate-300 hover:text-slate-500 transition-colors">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
            <span className="text-xs font-black bg-slate-900 text-white rounded-full px-3 py-1">
              {filtered.length} auto{filtered.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      </div>

      {/* ── Orders list ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
          <p className="text-sm text-slate-400">Cargando órdenes…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-slate-400">
          <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center">
            <ShoppingBag className="h-7 w-7 opacity-40" />
          </div>
          <p className="text-sm font-medium">{search ? "Sin resultados para esa búsqueda." : "No hay órdenes en esta vista."}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(o => {
            const v          = getVehicle(o.vehicle_id);
            const wNames     = o.washers.map(w => opName(w.user_id)).join(", ");
            const isOpen     = expanded === o.id;
            const inEdit     = editOrder === o.id;
            const isCancelled = o.status === "cancelado";
            const isClosed   = isPaid(o);
            const sm         = STATUS_META[o.status] ?? { label: o.status, badge: "bg-slate-100 text-slate-600", strip: "bg-slate-300" };
            const pm         = PAY_META[o.payment_status] ?? { label: o.payment_status, badge: "bg-slate-100 text-slate-600" };

            const showLavadores = !isCancelled && !isClosed;
            const showMonto     = !isClosed && !isCancelled;
            const showEstado    = !isCancelled;
            const showPago      = isClosed && !isCancelled;
            const showCancelar  = !isCancelled && !isClosed;

            return (
              <article key={o.id}
                className={`bg-white rounded-2xl shadow-sm border overflow-hidden transition-all ${isOpen ? "border-blue-200 shadow-blue-50 shadow-md" : "border-slate-100 hover:border-slate-200 hover:shadow"}`}>

                {/* Status strip */}
                <div className={`h-1 w-full ${sm.strip}`} />

                {/* Card header */}
                <div
                  className="flex items-center gap-3 px-5 py-4 cursor-pointer select-none"
                  onClick={() => toggleExpanded(o.id)}
                >
                  {/* Left: vehicle + meta */}
                  <div className="flex-1 min-w-0 space-y-1.5">
                    {/* Folio + vehicle name */}
                    <div className="flex items-baseline gap-2 min-w-0">
                      <span className="text-xs font-bold text-slate-400 shrink-0">{folio(o)}</span>
                      <span className="font-black text-slate-900 text-base leading-tight truncate">
                        {v ? `${v.brand ?? ""} ${v.model ?? ""}`.trim() || "Vehículo" : "Vehículo"}
                      </span>
                    </div>
                    {/* Sub-row */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      {v?.plate && (
                        <span className="inline-flex items-center gap-1 font-mono text-xs font-black bg-slate-900 text-white px-2 py-0.5 rounded-md tracking-wider">
                          {v.plate}
                        </span>
                      )}
                      {v?.color && (
                        <span className="text-xs text-slate-400">{v.color}</span>
                      )}
                      {wNames ? (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                          <Wrench className="h-2.5 w-2.5" />{wNames}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-semibold bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">
                          <Wrench className="h-2.5 w-2.5" />Sin asignar
                        </span>
                      )}
                      {clientName(o.client_id) && (
                        <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                          <User2 className="h-2.5 w-2.5" />{clientName(o.client_id)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: badges + total */}
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${sm.badge}`}>
                        {sm.label}
                      </span>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${pm.badge}`}>
                        {pm.label}
                      </span>
                    </div>
                    <span className="font-black text-slate-900 text-2xl leading-none tabular-nums">
                      {fmt(o.total)}
                    </span>
                  </div>

                  {/* Cobrar / chip */}
                  {canCharge(o) ? (
                    <button
                      className="shrink-0 font-black text-white text-sm px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 active:scale-95 transition-all shadow-sm shadow-emerald-200 whitespace-nowrap"
                      onClick={e => { e.stopPropagation(); setPayOrder(o); setPayMethod("efectivo"); setTendered(""); setPayDlg(true); }}
                    >
                      Cobrar
                    </button>
                  ) : isClosed ? (
                    <span className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100">
                      ✓ Cerrado
                    </span>
                  ) : isCancelled ? (
                    <span className="shrink-0 text-xs font-bold px-3 py-1.5 rounded-full bg-red-50 text-red-600 border border-red-100">
                      ✗ Cancelado
                    </span>
                  ) : null}

                  {/* Chevron */}
                  <span className={`shrink-0 flex items-center justify-center w-8 h-8 rounded-full transition-colors ${isOpen ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-400"}`}>
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </span>
                </div>

                {/* ── Expanded panel ─────────────────────────────────── */}
                {isOpen && (
                  <div className="border-t border-slate-100 bg-slate-50/50" onClick={e => e.stopPropagation()}>
                    <div className="px-5 py-4 space-y-4">

                      {/* Quick actions */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                          {!isCancelled && STATUS_NEXT[o.status] && (
                            <button
                              onClick={() => advanceStatus(o)}
                              className={`px-4 py-2 rounded-xl text-sm font-bold transition-all shadow-sm active:scale-95 ${STATUS_NEXT[o.status].cls}`}
                            >
                              {STATUS_NEXT[o.status].label}
                            </button>
                          )}
                          {isClosed && !isCancelled && (
                            <span className="text-sm text-slate-400 font-medium">Servicio cerrado</span>
                          )}
                          {isCancelled && (
                            <span className="text-sm text-red-400 font-medium">Orden cancelada</span>
                          )}
                        </div>
                        <button
                          onClick={() => inEdit ? closeEdit() : openEdit(o)}
                          className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${inEdit ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-200" : "bg-slate-900 text-white hover:bg-slate-700 shadow-sm"}`}
                        >
                          {inEdit ? "✕ Cerrar edición" : "✎ Editar"}
                        </button>
                      </div>

                      {/* Service items */}
                      <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
                        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-50 bg-slate-50">
                          <Wrench className="h-3.5 w-3.5 text-slate-400" />
                          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide">Servicios</h3>
                        </div>
                        {o.items.length === 0 ? (
                          <p className="px-4 py-3 text-sm text-slate-400">Sin renglones de servicio.</p>
                        ) : (
                          <div className="divide-y divide-slate-50">
                            {o.items.map(item => (
                              <div key={item.id} className="flex items-center justify-between px-4 py-3">
                                <div>
                                  <p className="text-sm font-semibold text-slate-800">
                                    {item.custom_name ?? services.find(s => s.id === item.catalog_id)?.name ?? `Servicio #${item.catalog_id}`}
                                  </p>
                                  <p className="text-xs text-slate-400 mt-0.5">Cantidad: {item.quantity}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-sm font-black text-blue-700 tabular-nums">{fmt(item.unit_price)}</span>
                                  {!isClosed && !isCancelled && (
                                    <button onClick={() => handleRemoveItem(o, item.id)}
                                      className="text-slate-200 hover:text-red-400 transition-colors p-1 rounded-lg hover:bg-red-50">
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                            <div className="flex justify-between items-center px-4 py-3 bg-slate-50">
                              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Total</span>
                              <span className="text-base font-black text-slate-900 tabular-nums">{fmt(o.total)}</span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* ── Edit mode ──────────────────────────────────── */}
                      {inEdit && (
                        <div className="rounded-2xl border border-blue-100 bg-white overflow-hidden shadow-sm">
                          {/* Guide */}
                          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-4">
                            <h3 className="text-sm font-black text-white">Modo edición</h3>
                            <p className="text-xs text-blue-200 mt-0.5">Selecciona qué deseas modificar</p>
                            <div className="flex flex-wrap gap-2 mt-3">
                              {showLavadores && (
                                <button onClick={() => toggleSection("lavadores")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all ${editSection === "lavadores" ? "bg-white text-blue-700 shadow" : "bg-white/20 text-white hover:bg-white/30"}`}>
                                  👷 Lavadores
                                </button>
                              )}
                              {showMonto && (
                                <button onClick={() => toggleSection("monto")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all ${editSection === "monto" ? "bg-white text-blue-700 shadow" : "bg-white/20 text-white hover:bg-white/30"}`}>
                                  💰 Monto
                                </button>
                              )}
                              {showEstado && (
                                <button onClick={() => toggleSection("estado")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all ${editSection === "estado" ? "bg-white text-blue-700 shadow" : "bg-white/20 text-white hover:bg-white/30"}`}>
                                  🔄 Estado
                                </button>
                              )}
                              {showPago && (
                                <button onClick={() => toggleSection("pago")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all ${editSection === "pago" ? "bg-white text-blue-700 shadow" : "bg-white/20 text-white hover:bg-white/30"}`}>
                                  💳 Método de pago
                                </button>
                              )}
                              {showCancelar && (
                                <button onClick={() => toggleSection("cancelar")}
                                  className={`text-xs font-bold px-3 py-1.5 rounded-full transition-all ${editSection === "cancelar" ? "bg-red-500 text-white shadow" : "bg-white/20 text-white hover:bg-red-400/80"}`}>
                                  ✕ Cancelar
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Sections */}
                          {editSection === "lavadores" && showLavadores && (
                            <div className="px-5 py-4 space-y-4 border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Asignar lavadores</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Actual: {wNames || "Sin asignar"}</p>
                              </div>
                              {operators.length === 0 ? (
                                <p className="text-sm text-slate-400 py-2">No hay operadores activos.</p>
                              ) : (
                                <div className="grid grid-cols-2 gap-2">
                                  {operators.map(op => (
                                    <label key={op.id}
                                      className={`flex items-center gap-3 p-3.5 rounded-xl border-2 cursor-pointer transition-all ${editWasherIds.has(op.id) ? "border-blue-400 bg-blue-50" : "border-slate-100 bg-slate-50 hover:border-slate-200"}`}>
                                      <input type="checkbox" className="accent-blue-600 w-4 h-4" checked={editWasherIds.has(op.id)}
                                        onChange={e => setEditWasherIds(prev => {
                                          const next = new Set(prev);
                                          e.target.checked ? next.add(op.id) : next.delete(op.id); return next;
                                        })} />
                                      <div>
                                        <div className="text-sm font-bold text-slate-800">{op.name}</div>
                                        <div className="text-xs text-slate-400">{op.commission_percentage}% comisión</div>
                                      </div>
                                    </label>
                                  ))}
                                </div>
                              )}
                              <div className="flex justify-end pt-1">
                                <button onClick={() => handleEditWashers(o)} disabled={saving || editWasherIds.size === 0}
                                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold disabled:opacity-50 transition-all">
                                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}Guardar lavadores
                                </button>
                              </div>
                            </div>
                          )}

                          {editSection === "monto" && showMonto && (
                            <div className="px-5 py-4 space-y-4 border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Ajustar monto</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Actual: <strong>{fmt(o.total)}</strong></p>
                              </div>
                              <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Nuevo monto</label>
                                  <input type="number" min="0" step="0.01" className={inp} value={editTotal}
                                    onChange={e => setEditTotal(e.target.value)} />
                                </div>
                                <div className="space-y-1.5">
                                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Motivo</label>
                                  <input className={inp} value={editReason} onChange={e => setEditReason(e.target.value)}
                                    placeholder="Razón del ajuste" />
                                </div>
                              </div>
                              <div className="flex justify-end">
                                <button onClick={() => handleEditTotal(o)} disabled={saving || !editTotal.trim()}
                                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold disabled:opacity-50 transition-all">
                                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}Guardar monto
                                </button>
                              </div>
                            </div>
                          )}

                          {editSection === "estado" && showEstado && (
                            <div className="px-5 py-4 space-y-4 border-t border-slate-100">
                              <h4 className="text-sm font-bold text-slate-800">Cambiar estado</h4>
                              <div className="flex gap-2 flex-wrap items-center">
                                <select className={`${inp} max-w-xs`} value={editStatus} onChange={e => setEditStatus(e.target.value)}>
                                  {Object.entries(STATUS_META).filter(([k]) => k !== "cancelado").map(([k, v]) => (
                                    <option key={k} value={k}>{v.label}</option>
                                  ))}
                                </select>
                                <button onClick={() => handleEditStatus(o)} disabled={saving}
                                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold disabled:opacity-50 transition-all">
                                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}Actualizar
                                </button>
                              </div>
                            </div>
                          )}

                          {editSection === "pago" && showPago && (
                            <div className="px-5 py-4 space-y-4 border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Cambiar método de pago</h4>
                                <p className="text-xs text-slate-400 mt-0.5">
                                  Actual: <strong>{PAY_METHOD_LABELS[o.payment_method ?? ""] ?? o.payment_method ?? "—"}</strong>
                                </p>
                              </div>
                              <div className="flex gap-2 flex-wrap items-center">
                                <select className={`${inp} flex-1 min-w-0 max-w-xs`} value={editPayMethod}
                                  onChange={e => setEditPayMethod(e.target.value)}>
                                  {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                                </select>
                                <button onClick={() => handleEditPayMethod(o)} disabled={saving}
                                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold disabled:opacity-50 transition-all">
                                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}Guardar
                                </button>
                              </div>
                            </div>
                          )}

                          {editSection === "cancelar" && showCancelar && (
                            <div className="px-5 py-4 space-y-4 border-t border-red-100 bg-red-50/50">
                              <div>
                                <h4 className="text-sm font-bold text-red-700">Cancelar orden #{o.id}</h4>
                                <p className="text-xs text-red-400 mt-0.5">Esta acción no se puede deshacer.</p>
                              </div>
                              <input
                                className="w-full rounded-xl border border-red-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 transition"
                                value={cancelReason} onChange={e => setCancelReason(e.target.value)}
                                placeholder="Motivo de la cancelación (obligatorio)" />
                              <div className="flex justify-end">
                                <button onClick={() => handleCancel(o)} disabled={saving || !cancelReason.trim()}
                                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-bold disabled:opacity-50 transition-all">
                                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}Cancelar orden
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Washers summary (non-edit) */}
                      {!inEdit && o.washers.length > 0 && (
                        <div className="bg-white rounded-xl border border-slate-100 overflow-hidden">
                          <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 border-b border-slate-50">
                            <User2 className="h-3.5 w-3.5 text-slate-400" />
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide">Lavadores</h3>
                          </div>
                          <div className="flex flex-wrap gap-2 px-4 py-3">
                            {o.washers.map(w => (
                              <div key={w.id} className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-full px-3 py-1.5">
                                <span className="text-sm font-bold text-blue-800">{opName(w.user_id)}</span>
                                <span className="text-xs text-blue-400">{w.commission_percent}% · {fmt(w.commission_amount)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Notes / domicilio */}
                      {(o.notes || o.is_domicilio) && (
                        <div className="flex flex-wrap gap-3 text-sm px-1">
                          {o.notes && (
                            <span className="text-slate-500 bg-white border border-slate-100 rounded-lg px-3 py-1.5 text-xs">
                              📝 {o.notes}
                            </span>
                          )}
                          {o.is_domicilio && o.delivery_address && (
                            <span className="text-blue-600 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5 text-xs font-medium">
                              📍 {o.delivery_address}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {/* ── Payment dialog ───────────────────────────────────────────────── */}
      <Dialog open={payDlg} onOpenChange={o => { if (!o) setPayDlg(false); }}>
        <DialogContent className="max-w-sm p-0 overflow-hidden rounded-2xl">
          {/* Dark header */}
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 px-6 py-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Cobrar servicio</div>
                {payOrder && (
                  <>
                    <div className="text-white font-bold text-base leading-tight">
                      {getVehicle(payOrder.vehicle_id)
                        ? `${getVehicle(payOrder.vehicle_id)?.brand ?? ""} ${getVehicle(payOrder.vehicle_id)?.model ?? ""}`.trim() || "Vehículo"
                        : "Vehículo"}
                    </div>
                    <div className="text-slate-400 text-xs mt-1">
                      {folio(payOrder)} · {clientName(payOrder.client_id) || "Cliente general"}
                    </div>
                  </>
                )}
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Total</div>
                <div className="text-white font-black text-3xl tabular-nums leading-none">{fmt(payOrder?.total)}</div>
              </div>
            </div>
          </div>

          {/* Body */}
          <div className="px-6 py-5 space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Forma de pago</label>
              <select className={inp} value={payMethod}
                onChange={e => { setPayMethod(e.target.value); setTendered(""); }}>
                {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            {payMethod === "efectivo" && (
              <div className="rounded-xl bg-sky-50 border border-sky-200 p-4 space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Efectivo recibido</label>
                  <input type="number" min="0" step="0.01" className={inp}
                    value={tendered} onChange={e => setTendered(e.target.value)}
                    placeholder="Ej. 500" autoFocus />
                </div>
                <div className="flex items-center justify-between bg-slate-900 text-white rounded-xl px-4 py-3">
                  <span className="text-xs font-semibold opacity-60 uppercase tracking-wide">Cambio a dar</span>
                  <span className="text-xl font-black tabular-nums">{fmt(change)}</span>
                </div>
              </div>
            )}
            {payMethod === "credito" && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
                <p className="font-bold text-amber-800 text-sm">Se registrará como crédito.</p>
                <p className="text-amber-700 text-xs mt-1">No entra a caja. Se carga al saldo de cartera del cliente.</p>
              </div>
            )}
            {payMethod === "cortesia" && (
              <div className="rounded-xl bg-sky-50 border border-sky-200 px-4 py-3">
                <p className="font-bold text-sky-800 text-sm">Servicio cerrado como cortesía.</p>
                <p className="text-sky-700 text-xs mt-1">Sin ingreso a caja. Se conserva la comisión del lavador.</p>
              </div>
            )}

            <div className="flex gap-2 pt-1">
              <button onClick={() => setPayDlg(false)} disabled={saving}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-sm font-bold hover:bg-slate-50 transition-all">
                Cancelar
              </button>
              <button onClick={handlePay} disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-black shadow-sm shadow-emerald-200 transition-all active:scale-95 disabled:opacity-50">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Registrar cobro
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── New order dialog ─────────────────────────────────────────────── */}
      <Dialog open={newDlg} onOpenChange={o => { if (!o) setNewDlg(false); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center">
                <Car className="h-3.5 w-3.5 text-white" />
              </div>
              Nueva orden de servicio
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
            {formError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700 font-medium">{formError}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Cliente</label>
                <select className={inp} value={newClientId}
                  onChange={e => { setNewClientId(e.target.value); setNewVehicleId(""); }}>
                  <option value="">Sin cliente</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Vehículo</label>
                <select className={inp} value={newVehicleId} onChange={e => setNewVehicleId(e.target.value)}>
                  <option value="">Sin vehículo</option>
                  {vehicles.filter(v => !newClientId || !v.client_id || v.client_id === parseInt(newClientId))
                    .map(v => <option key={v.id} value={v.id}>{[v.plate, v.brand, v.model].filter(Boolean).join(" ")}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Notas</label>
              <input className={inp} value={newNotes} onChange={e => setNewNotes(e.target.value)} placeholder="Opcional" />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Servicios</label>
                <button type="button"
                  onClick={() => setNewItems(prev => [...prev, { catalog_id: null, custom_name: "", unit_price: "", quantity: 1 }])}
                  className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-all">
                  <Plus className="h-3 w-3" /> Agregar
                </button>
              </div>
              {newItems.map((item, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-5 space-y-1">
                    <label className="text-xs text-slate-400">Catálogo</label>
                    <select className={inp} value={item.catalog_id ?? ""} onChange={e => {
                      const svc = services.find(s => s.id === parseInt(e.target.value));
                      setNewItems(prev => prev.map((it, i) => i === idx
                        ? { ...it, catalog_id: svc?.id ?? null, custom_name: "", unit_price: svc?.base_price ?? it.unit_price } : it));
                    }}>
                      <option value="">Personalizado</option>
                      {services.map(s => <option key={s.id} value={s.id}>{s.name} — {fmt(s.base_price)}</option>)}
                    </select>
                  </div>
                  {!item.catalog_id && (
                    <div className="col-span-3 space-y-1">
                      <label className="text-xs text-slate-400">Nombre</label>
                      <input className={inp} value={item.custom_name} placeholder="Descripción"
                        onChange={e => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, custom_name: e.target.value } : it))} />
                    </div>
                  )}
                  <div className={`${item.catalog_id ? "col-span-6" : "col-span-3"} space-y-1`}>
                    <label className="text-xs text-slate-400">Precio</label>
                    <input type="number" min="0" step="0.01" className={inp} value={item.unit_price} placeholder="0.00"
                      onChange={e => setNewItems(prev => prev.map((it, i) => i === idx ? { ...it, unit_price: e.target.value } : it))} />
                  </div>
                  <button type="button" className="col-span-1 flex justify-center pb-2 text-red-300 hover:text-red-500 transition-colors"
                    onClick={() => setNewItems(prev => prev.filter((_, i) => i !== idx))}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewDlg(false)} disabled={saving}>Cancelar</Button>
            <Button className="bg-slate-900 hover:bg-slate-800" onClick={handleCreateOrder} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Crear orden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
