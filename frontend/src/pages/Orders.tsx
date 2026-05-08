import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  Loader2, Plus, ShoppingBag, ChevronDown, ChevronUp, Trash2,
  Search, X, Users, Wrench, DollarSign, RotateCcw, XCircle,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter, DialogTitle,
} from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client { id: number; name: string; }
interface Vehicle { id: number; plate: string | null; brand: string | null; model: string | null; color: string | null; client_id?: number | null; }
interface ServiceCatalog { id: number; name: string; base_price: string; }
interface Operator { id: number; name: string; commission_percentage: string; }
interface OrderItem { id: number; catalog_id: number | null; custom_name: string | null; unit_price: string; quantity: number; }
interface OrderWasher { id: number; user_id: number; commission_percent: string; commission_amount: string; is_paid: boolean; }
interface Order {
  id: number; client_id: number | null; vehicle_id: number | null;
  service_date: string | null; daily_sequence: number | null;
  subtotal: string; discount_amount: string; total: string;
  status: string; payment_status: string; payment_method: string | null;
  is_domicilio: boolean; delivery_address: string | null; notes: string | null;
  items: OrderItem[]; washers: OrderWasher[];
}

// ─── Design tokens ────────────────────────────────────────────────────────────

const S: Record<string, { label: string; pill: string; border: string; advance?: { label: string; value: string; btn: string } }> = {
  en_cola:    { label: "En cola",   pill: "bg-amber-100 text-amber-800",    border: "border-l-amber-400",
                advance: { label: "Iniciar",  value: "en_proceso", btn: "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-200" } },
  en_proceso: { label: "Lavando",   pill: "bg-blue-100 text-blue-800",      border: "border-l-blue-500",
                advance: { label: "Listo",    value: "listo",      btn: "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-200" } },
  listo:      { label: "Listo",     pill: "bg-emerald-100 text-emerald-800", border: "border-l-emerald-500",
                advance: { label: "Entregar", value: "entregado",  btn: "bg-slate-700 hover:bg-slate-800 text-white shadow-slate-300" } },
  entregado:  { label: "Entregado", pill: "bg-slate-100 text-slate-600",    border: "border-l-slate-300" },
  cancelado:  { label: "Cancelado", pill: "bg-red-100 text-red-700",        border: "border-l-red-400" },
};
const P: Record<string, { label: string; pill: string }> = {
  pendiente: { label: "Pendiente", pill: "bg-orange-100 text-orange-800" },
  pagado:    { label: "Pagado",    pill: "bg-emerald-100 text-emerald-800" },
  parcial:   { label: "Parcial",   pill: "bg-blue-100 text-blue-800" },
  credito:   { label: "Crédito",   pill: "bg-violet-100 text-violet-800" },
  cortesia:  { label: "Cortesía",  pill: "bg-sky-100 text-sky-800" },
};
const PAY_METHODS = [
  { value: "efectivo",      label: "Efectivo" },
  { value: "tarjeta",       label: "Tarjeta" },
  { value: "transferencia", label: "Transferencia" },
  { value: "deposito",      label: "Depósito" },
  { value: "credito",       label: "Crédito — cartera" },
  { value: "cortesia",      label: "Cortesía" },
];
const PAY_METHOD_LABELS: Record<string, string> = Object.fromEntries(PAY_METHODS.map(m => [m.value, m.label]));

type Scope  = "today" | "date" | "history";
type Filter = "all" | "active" | "done" | "paid" | "pending_pay";
type NewItemRow = { catalog_id: number | null; custom_name: string; unit_price: string; quantity: number };

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmt(v: string | number | null | undefined) {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function norm(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s#]/g, " ").replace(/\s+/g, " ").trim();
}

const field = "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow placeholder:text-slate-400";

// ─── Component ────────────────────────────────────────────────────────────────

export default function Orders() {
  const [orders,    setOrders]    = useState<Order[]>([]);
  const [clients,   setClients]   = useState<Client[]>([]);
  const [vehicles,  setVehicles]  = useState<Vehicle[]>([]);
  const [services,  setServices]  = useState<ServiceCatalog[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [globalErr, setGlobalErr] = useState("");

  const [scope,        setScope]        = useState<Scope>("today");
  const [filter,       setFilter]       = useState<Filter>("all");
  const [selectedDate, setSelectedDate] = useState(todayStr());
  const [search,       setSearch]       = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  // Edit mode state
  const [editId,        setEditId]        = useState<number | null>(null);
  const [editSection,   setEditSection]   = useState<string | null>(null);
  const [editWashers,   setEditWashers]   = useState<Set<number>>(new Set());
  const [editTotal,     setEditTotal]     = useState("");
  const [editStatus,    setEditStatus]    = useState("");
  const [editPayMethod, setEditPayMethod] = useState("");
  const [editReason,    setEditReason]    = useState("");
  const [cancelReason,  setCancelReason]  = useState("");
  const [saving,        setSaving]        = useState(false);

  // New order dialog
  const [newDlg,       setNewDlg]       = useState(false);
  const [newClientId,  setNewClientId]  = useState("");
  const [newVehicleId, setNewVehicleId] = useState("");
  const [newNotes,     setNewNotes]     = useState("");
  const [newItems,     setNewItems]     = useState<NewItemRow[]>([]);
  const [newErr,       setNewErr]       = useState("");

  // Payment dialog
  const [payDlg,    setPayDlg]    = useState(false);
  const [payOrder,  setPayOrder]  = useState<Order | null>(null);
  const [payMethod, setPayMethod] = useState("efectivo");
  const [tendered,  setTendered]  = useState("");

  // ── Data loading ──────────────────────────────────────────────────────────

  const loadOrders = useCallback(async () => {
    setLoading(true); setGlobalErr("");
    try {
      const p: Record<string, string> = {};
      const td = todayStr();
      if (scope === "today") { p.date_from = td; p.date_to = td; }
      else if (scope === "date") { p.date_from = selectedDate; p.date_to = selectedDate; }
      setOrders((await api.get<Order[]>("/orders/", { params: p })).data);
    } catch { setGlobalErr("No se pudieron cargar las órdenes."); }
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
    const fn = (e: KeyboardEvent) => {
      if (e.key === "/" && !["INPUT","TEXTAREA","SELECT"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault(); searchRef.current?.focus(); searchRef.current?.select();
      }
    };
    document.addEventListener("keydown", fn);
    return () => document.removeEventListener("keydown", fn);
  }, []);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const clientName  = (id: number | null) => clients.find(c => c.id === id)?.name ?? "";
  const getVehicle  = (id: number | null) => vehicles.find(v => v.id === id);
  const opName      = (id: number) => operators.find(o => o.id === id)?.name ?? `#${id}`;
  const vehicleLabel = (v?: Vehicle | null) => v ? `${v.brand ?? ""} ${v.model ?? ""}`.trim() || "Vehículo" : "Vehículo";

  function folio(o: Order) {
    if (!o.daily_sequence) return `#${o.id}`;
    const d = o.service_date ? o.service_date.slice(5).replace("-", "/") : "";
    return d ? `${d} · #${String(o.daily_sequence).padStart(3, "0")}` : `#${String(o.daily_sequence).padStart(3, "0")}`;
  }

  function idx(o: Order) {
    const v = getVehicle(o.vehicle_id);
    return norm([folio(o), String(o.id), clientName(o.client_id), v?.plate ?? "", v?.brand ?? "", v?.model ?? "", v?.color ?? "",
      o.washers.map(w => opName(w.user_id)).join(" "), S[o.status]?.label ?? "", P[o.payment_status]?.label ?? ""].join(" "));
  }

  const filtered = useMemo(() => {
    let list = [...orders];
    if (filter === "active")      list = list.filter(o => ["en_cola","en_proceso","listo"].includes(o.status));
    else if (filter === "done")   list = list.filter(o => o.status === "entregado");
    else if (filter === "paid")   list = list.filter(o => o.payment_status === "pagado");
    else if (filter === "pending_pay") list = list.filter(o => o.payment_status === "pendiente" && o.status !== "cancelado");
    const q = norm(search);
    if (q) list = list.filter(o => idx(o).includes(q));
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, filter, search, clients, vehicles, operators]);

  const isPaid    = (o: Order) => ["pagado","credito","cortesia"].includes(o.payment_status);
  const canCharge = (o: Order) => o.status !== "cancelado" && !isPaid(o);

  // ── Edit mode ─────────────────────────────────────────────────────────────

  function openEdit(o: Order) {
    setEditId(o.id); setEditSection(null);
    setEditWashers(new Set(o.washers.map(w => w.user_id)));
    setEditTotal(Number(o.total).toFixed(2)); setEditStatus(o.status);
    setEditPayMethod(o.payment_method ?? "efectivo");
    setEditReason(""); setCancelReason("");
  }
  function closeEdit() { setEditId(null); setEditSection(null); }
  function pickSection(name: string) {
    setEditSection(p => p === name ? null : name); setEditReason(""); setCancelReason("");
  }
  function toggleCard(id: number) {
    setExpanded(p => { closeEdit(); return p === id ? null : id; });
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async function advance(o: Order) {
    const n = S[o.status]?.advance; if (!n) return;
    try { setOrders(p => p.map(x => x.id === o.id ? { ...x, status: n.value } : x));
          const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: n.value });
          setOrders(p => p.map(x => x.id === o.id ? res.data : x));
    } catch { setGlobalErr("Error al actualizar estado."); loadOrders(); }
  }

  async function saveWashers(o: Order) {
    if (editWashers.size === 0) { setGlobalErr("Selecciona al menos un lavador."); return; }
    setSaving(true);
    try {
      const res = await api.put<Order>(`/orders/${o.id}/washers`, {
        washers: Array.from(editWashers).map(uid => ({
          user_id: uid,
          commission_percent: parseFloat(operators.find(op => op.id === uid)?.commission_percentage ?? "0") || 0,
        })),
      });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setGlobalErr("Error al asignar lavadores."); } finally { setSaving(false); }
  }

  async function saveTotal(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/total`, { total: parseFloat(editTotal), reason: editReason || null });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setGlobalErr("Error al actualizar el monto."); } finally { setSaving(false); }
  }

  async function saveStatus(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: editStatus });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setGlobalErr("Error al actualizar estado."); } finally { setSaving(false); }
  }

  async function savePayMethod(o: Order) {
    setSaving(true);
    try {
      const isC = editPayMethod === "cortesia", isK = editPayMethod === "credito";
      const res = await api.patch<Order>(`/orders/${o.id}/payment`, {
        payment_method: editPayMethod,
        payment_status: isC ? "cortesia" : isK ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x)); setEditSection(null);
    } catch { setGlobalErr("Error al cambiar método de pago."); } finally { setSaving(false); }
  }

  async function cancelOrder(o: Order) {
    setSaving(true);
    try {
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: "cancelado", cancellation_reason: cancelReason });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x)); closeEdit();
    } catch { setGlobalErr("Error al cancelar la orden."); } finally { setSaving(false); }
  }

  async function createOrder() {
    setSaving(true); setNewErr("");
    try {
      await api.post("/orders/", {
        client_id: newClientId ? +newClientId : null,
        vehicle_id: newVehicleId ? +newVehicleId : null,
        notes: newNotes || null,
        items: newItems.filter(i => i.custom_name.trim() || i.catalog_id).map(i => ({
          catalog_id: i.catalog_id ?? null,
          custom_name: i.catalog_id ? null : (i.custom_name.trim() || null),
          unit_price: parseFloat(i.unit_price) || 0, quantity: i.quantity || 1,
        })),
      });
      setNewDlg(false); setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]);
      loadOrders();
    } catch (e: unknown) {
      setNewErr((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al crear la orden.");
    } finally { setSaving(false); }
  }

  async function pay() {
    if (!payOrder) return; setSaving(true);
    try {
      const isC = payMethod === "cortesia", isK = payMethod === "credito";
      const res = await api.patch<Order>(`/orders/${payOrder.id}/payment`, {
        payment_method: payMethod,
        payment_status: isC ? "cortesia" : isK ? "credito" : "pagado",
        discount_amount: 0,
      });
      setOrders(p => p.map(o => o.id === payOrder.id ? res.data : o)); setPayDlg(false);
    } catch { setGlobalErr("Error al registrar el pago."); } finally { setSaving(false); }
  }

  async function removeItem(order: Order, itemId: number) {
    try {
      const res = await api.delete<Order>(`/orders/${order.id}/items/${itemId}`);
      setOrders(p => p.map(o => o.id === order.id ? res.data : o));
    } catch { setGlobalErr("Error al eliminar ítem."); }
  }

  const change = payOrder ? Math.max(0, (parseFloat(tendered) || 0) - Number(payOrder.total)) : 0;

  // ── Render ────────────────────────────────────────────────────────────────

  const SCOPES: { k: Scope; l: string }[] = [
    { k: "today", l: "Hoy" }, { k: "date", l: "Por fecha" }, { k: "history", l: "Historial" },
  ];
  const FILTERS: { k: Filter; l: string }[] = [
    { k: "all", l: "Todos" }, { k: "active", l: "En proceso" }, { k: "done", l: "Terminados" },
    { k: "paid", l: "Pagados" }, { k: "pending_pay", l: "Por cobrar" },
  ];

  return (
    <div className="space-y-6 pb-16">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight leading-none">Servicios</h1>
          <p className="text-sm text-slate-400 mt-1">Gestiona estado, cobros y detalles de cada vehículo.</p>
        </div>
        <button
          onClick={() => { setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]); setNewErr(""); setNewDlg(true); }}
          className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-slate-900 text-white text-sm font-bold shadow-md hover:bg-slate-800 hover:shadow-lg active:scale-95 transition-all"
        >
          <Plus className="h-4 w-4" /> Nueva orden
        </button>
      </div>

      {/* Error */}
      {globalErr && (
        <div className="flex items-center justify-between gap-3 bg-red-50 border border-red-200 text-red-700 rounded-2xl px-5 py-3 text-sm font-medium">
          <span>{globalErr}</span>
          <button onClick={() => setGlobalErr("")}><X className="h-4 w-4 text-red-400 hover:text-red-600 transition-colors" /></button>
        </div>
      )}

      {/* ── Scope tabs ──────────────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-2xl w-fit">
        {SCOPES.map(s => (
          <button key={s.k} onClick={() => setScope(s.k)}
            className={`px-5 py-2 rounded-xl text-sm font-bold transition-all ${scope === s.k ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
            {s.l}
          </button>
        ))}
      </div>

      {scope === "date" && (
        <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)}
          className="rounded-2xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm" />
      )}

      {/* ── Filter pills ────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map(f => (
          <button key={f.k} onClick={() => setFilter(f.k)}
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all ${filter === f.k ? "bg-slate-900 text-white shadow-sm" : "bg-white border border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-800"}`}>
            {f.l}
          </button>
        ))}
      </div>

      {/* ── Search ──────────────────────────────────────────────────────────── */}
      <div className="sticky top-2 z-20">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-lg px-5 py-3.5 flex items-center gap-3">
          <Search className="h-5 w-5 text-slate-300 shrink-0" />
          <input ref={searchRef} type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por folio, placa, modelo, color, cliente o lavador…"
            className="flex-1 bg-transparent text-sm font-medium text-slate-700 placeholder:text-slate-300 outline-none" />
          {search && <button onClick={() => setSearch("")}><X className="h-4 w-4 text-slate-300 hover:text-slate-500 transition-colors" /></button>}
          <span className="shrink-0 text-xs font-black bg-slate-900 text-white px-3 py-1.5 rounded-full">
            {filtered.length} auto{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* ── Orders ──────────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex flex-col items-center gap-3 py-28 text-slate-300">
          <Loader2 className="h-9 w-9 animate-spin" />
          <span className="text-sm">Cargando…</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-28 text-slate-400">
          <div className="w-20 h-20 rounded-3xl bg-slate-50 border-2 border-slate-100 flex items-center justify-center">
            <ShoppingBag className="h-9 w-9 opacity-40" />
          </div>
          <p className="text-sm font-medium">{search ? "Sin resultados para esa búsqueda." : "No hay órdenes en esta vista."}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(o => {
            const v    = getVehicle(o.vehicle_id);
            const wstr = o.washers.map(w => opName(w.user_id)).join(", ");
            const isOpen     = expanded === o.id;
            const inEdit     = editId === o.id;
            const cancelled  = o.status === "cancelado";
            const closed     = isPaid(o);
            const sm         = S[o.status]  ?? { label: o.status,         pill: "bg-slate-100 text-slate-600", border: "border-l-slate-300" };
            const pm         = P[o.payment_status] ?? { label: o.payment_status, pill: "bg-slate-100 text-slate-600" };

            const showWashers = !cancelled && !closed;
            const showMonto   = !closed && !cancelled;
            const showEstado  = !cancelled;
            const showPago    = closed && !cancelled;
            const showCancel  = !cancelled && !closed;

            return (
              <article key={o.id}
                className={`bg-white rounded-3xl overflow-hidden border-l-[5px] transition-all duration-200 ${sm.border} ${
                  isOpen ? "shadow-xl border-t border-r border-b border-t-blue-100 border-r-blue-100 border-b-blue-100" : "shadow-md border-t border-r border-b border-slate-100 hover:shadow-lg"
                }`}>

                {/* ── Card header ── */}
                <div className="flex items-center gap-4 px-5 py-4 cursor-pointer select-none" onClick={() => toggleCard(o.id)}>

                  {/* Left info */}
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-400 shrink-0">{folio(o)}</span>
                      <span className="text-lg font-black text-slate-900 leading-tight truncate">{vehicleLabel(v)}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {v?.plate && (
                        <span className="font-mono font-black text-xs bg-slate-900 text-white px-2.5 py-1 rounded-lg tracking-widest">
                          {v.plate}
                        </span>
                      )}
                      {v?.color && <span className="text-xs text-slate-400 font-medium">{v.color}</span>}
                      <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full ${wstr ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>
                        <Wrench className="h-3 w-3" />{wstr || "Sin asignar"}
                      </span>
                      {clientName(o.client_id) && (
                        <span className="text-xs text-slate-400 font-medium">{clientName(o.client_id)}</span>
                      )}
                    </div>
                  </div>

                  {/* Right: badges + total + actions */}
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <div className="flex items-center gap-1.5 flex-wrap justify-end">
                      <span className={`text-xs font-bold px-3 py-1 rounded-full ${sm.pill}`}>{sm.label}</span>
                      <span className={`text-xs font-bold px-3 py-1 rounded-full ${pm.pill}`}>{pm.label}</span>
                    </div>
                    <span className="text-2xl font-black text-slate-900 tabular-nums leading-none">{fmt(o.total)}</span>
                  </div>

                  {/* CTA */}
                  <div className="shrink-0 flex flex-col items-center gap-2">
                    {canCharge(o) ? (
                      <button
                        onClick={e => { e.stopPropagation(); setPayOrder(o); setPayMethod("efectivo"); setTendered(""); setPayDlg(true); }}
                        className="px-5 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-black shadow-lg shadow-emerald-200 hover:shadow-emerald-300 active:scale-95 transition-all whitespace-nowrap"
                      >
                        Cobrar
                      </button>
                    ) : closed ? (
                      <span className="text-xs font-bold px-3 py-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 whitespace-nowrap">✓ Pagado</span>
                    ) : cancelled ? (
                      <span className="text-xs font-bold px-3 py-2 rounded-xl bg-red-50 text-red-600 border border-red-100 whitespace-nowrap">✗ Cancelado</span>
                    ) : null}
                    <span className={`flex items-center justify-center w-8 h-8 rounded-xl transition-colors ${isOpen ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-400"}`}>
                      {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </span>
                  </div>
                </div>

                {/* ── Expanded panel ── */}
                {isOpen && (
                  <div className="border-t border-slate-100" onClick={e => e.stopPropagation()}>
                    <div className="px-6 py-5 space-y-5">

                      {/* Quick actions row */}
                      <div className="flex items-center gap-3 flex-wrap">
                        {!cancelled && sm.advance && (
                          <button onClick={() => advance(o)}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-black shadow-md transition-all active:scale-95 ${sm.advance.btn}`}>
                            {sm.advance.label}
                          </button>
                        )}
                        {closed && !cancelled && (
                          <span className="text-sm text-slate-400 font-semibold">Servicio cerrado</span>
                        )}
                        {cancelled && (
                          <span className="text-sm text-red-400 font-semibold">Orden cancelada</span>
                        )}
                        <button onClick={() => inEdit ? closeEdit() : openEdit(o)}
                          className={`ml-auto flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-black shadow-sm transition-all active:scale-95 ${inEdit ? "bg-blue-600 text-white hover:bg-blue-700 shadow-blue-200" : "bg-slate-900 text-white hover:bg-slate-800"}`}>
                          {inEdit ? <X className="h-4 w-4" /> : <Wrench className="h-4 w-4" />}
                          {inEdit ? "Cerrar" : "Editar"}
                        </button>
                      </div>

                      {/* Services list */}
                      <div className="rounded-2xl border border-slate-100 overflow-hidden">
                        <div className="flex items-center gap-2.5 px-5 py-3 bg-slate-50 border-b border-slate-100">
                          <Wrench className="h-4 w-4 text-slate-400" />
                          <span className="text-xs font-black text-slate-500 uppercase tracking-widest">Servicios</span>
                        </div>
                        {o.items.length === 0 ? (
                          <p className="px-5 py-4 text-sm text-slate-400">Sin renglones de servicio.</p>
                        ) : (
                          <div>
                            {o.items.map((item, i) => (
                              <div key={item.id} className={`flex items-center justify-between px-5 py-3.5 ${i < o.items.length - 1 ? "border-b border-slate-50" : ""}`}>
                                <div>
                                  <p className="text-sm font-bold text-slate-800">
                                    {item.custom_name ?? services.find(s => s.id === item.catalog_id)?.name ?? `Servicio #${item.catalog_id}`}
                                  </p>
                                  <p className="text-xs text-slate-400 mt-0.5">Cantidad: {item.quantity}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-base font-black text-blue-600 tabular-nums">{fmt(item.unit_price)}</span>
                                  {!closed && !cancelled && (
                                    <button onClick={() => removeItem(o, item.id)}
                                      className="w-7 h-7 rounded-xl flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 transition-all">
                                      <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                            <div className="flex items-center justify-between px-5 py-3.5 bg-slate-50 border-t border-slate-100">
                              <span className="text-xs font-black text-slate-400 uppercase tracking-wider">Total</span>
                              <span className="text-lg font-black text-slate-900 tabular-nums">{fmt(o.total)}</span>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* ── Edit mode ── */}
                      {inEdit && (
                        <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
                          {/* Edit header with action pills */}
                          <div className="px-5 py-4 bg-slate-900">
                            <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Editar orden</p>
                            <div className="flex flex-wrap gap-2">
                              {([
                                showWashers && { id: "lavadores", label: "👷 Lavadores",      danger: false },
                                showMonto   && { id: "monto",     label: "💰 Monto",           danger: false },
                                showEstado  && { id: "estado",    label: "🔄 Estado",           danger: false },
                                showPago    && { id: "pago",      label: "💳 Método de pago",   danger: false },
                                showCancel  && { id: "cancelar",  label: "✕ Cancelar orden",   danger: true  },
                              ] as const).filter(Boolean).map((item) => {
                                if (!item) return null;
                                const active = editSection === item.id;
                                return (
                                  <button key={item.id} onClick={() => pickSection(item.id)}
                                    className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
                                      active
                                        ? item.danger ? "bg-red-500 text-white" : "bg-white text-slate-900 shadow-sm"
                                        : item.danger ? "bg-red-900/40 text-red-300 hover:bg-red-500 hover:text-white" : "bg-white/10 text-slate-300 hover:bg-white/20"
                                    }`}>
                                    {item.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {/* Lavadores */}
                          {editSection === "lavadores" && showWashers && (
                            <div className="px-5 py-5 space-y-4 bg-white border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-black text-slate-800">Asignar lavadores</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Actual: {wstr || "Sin asignar"}</p>
                              </div>
                              <div className="grid grid-cols-2 gap-2.5">
                                {operators.map(op => (
                                  <label key={op.id}
                                    className={`flex items-center gap-3 p-4 rounded-2xl border-2 cursor-pointer transition-all ${editWashers.has(op.id) ? "border-blue-400 bg-blue-50" : "border-slate-100 bg-slate-50 hover:border-slate-200"}`}>
                                    <input type="checkbox" className="accent-blue-600 w-4 h-4" checked={editWashers.has(op.id)}
                                      onChange={e => setEditWashers(prev => {
                                        const n = new Set(prev);
                                        e.target.checked ? n.add(op.id) : n.delete(op.id); return n;
                                      })} />
                                    <div>
                                      <p className="text-sm font-black text-slate-800">{op.name}</p>
                                      <p className="text-xs text-slate-400">{op.commission_percentage}% comisión</p>
                                    </div>
                                  </label>
                                ))}
                              </div>
                              <div className="flex justify-end">
                                <button onClick={() => saveWashers(o)} disabled={saving || editWashers.size === 0}
                                  className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-black shadow-md shadow-blue-200 disabled:opacity-40 transition-all active:scale-95">
                                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Users className="h-4 w-4" />}
                                  Guardar lavadores
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Monto */}
                          {editSection === "monto" && showMonto && (
                            <div className="px-5 py-5 space-y-4 bg-white border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-black text-slate-800">Ajustar monto</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Actual: <strong>{fmt(o.total)}</strong></p>
                              </div>
                              <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                  <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Nuevo monto</label>
                                  <input type="number" min="0" step="0.01" className={field} value={editTotal} onChange={e => setEditTotal(e.target.value)} />
                                </div>
                                <div className="space-y-1.5">
                                  <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Motivo</label>
                                  <input className={field} value={editReason} onChange={e => setEditReason(e.target.value)} placeholder="Razón del ajuste" />
                                </div>
                              </div>
                              <div className="flex justify-end">
                                <button onClick={() => saveTotal(o)} disabled={saving || !editTotal}
                                  className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-black shadow-md shadow-blue-200 disabled:opacity-40 transition-all active:scale-95">
                                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <DollarSign className="h-4 w-4" />}
                                  Guardar monto
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Estado */}
                          {editSection === "estado" && showEstado && (
                            <div className="px-5 py-5 space-y-4 bg-white border-t border-slate-100">
                              <h4 className="text-sm font-black text-slate-800">Cambiar estado</h4>
                              <div className="flex gap-3 items-center flex-wrap">
                                <select className={`${field} flex-1 min-w-0 max-w-xs`} value={editStatus} onChange={e => setEditStatus(e.target.value)}>
                                  {Object.entries(S).filter(([k]) => k !== "cancelado").map(([k, v]) => (
                                    <option key={k} value={k}>{v.label}</option>
                                  ))}
                                </select>
                                <button onClick={() => saveStatus(o)} disabled={saving}
                                  className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-black shadow-md shadow-blue-200 disabled:opacity-40 transition-all active:scale-95">
                                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                                  Actualizar
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Método pago */}
                          {editSection === "pago" && showPago && (
                            <div className="px-5 py-5 space-y-4 bg-white border-t border-slate-100">
                              <div>
                                <h4 className="text-sm font-black text-slate-800">Cambiar método de pago</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Actual: <strong>{PAY_METHOD_LABELS[o.payment_method ?? ""] ?? "—"}</strong></p>
                              </div>
                              <div className="flex gap-3 items-center flex-wrap">
                                <select className={`${field} flex-1 min-w-0 max-w-xs`} value={editPayMethod} onChange={e => setEditPayMethod(e.target.value)}>
                                  {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                                </select>
                                <button onClick={() => savePayMethod(o)} disabled={saving}
                                  className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-black shadow-md shadow-blue-200 disabled:opacity-40 transition-all active:scale-95">
                                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Guardar
                                </button>
                              </div>
                            </div>
                          )}

                          {/* Cancelar */}
                          {editSection === "cancelar" && showCancel && (
                            <div className="px-5 py-5 space-y-4 bg-red-50 border-t border-red-100">
                              <div>
                                <h4 className="text-sm font-black text-red-800">Cancelar orden #{o.id}</h4>
                                <p className="text-xs text-red-400 mt-0.5">Esta acción no se puede deshacer.</p>
                              </div>
                              <input className="w-full rounded-2xl border-2 border-red-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 transition placeholder:text-red-300"
                                value={cancelReason} onChange={e => setCancelReason(e.target.value)}
                                placeholder="Motivo de la cancelación (obligatorio)" />
                              <div className="flex justify-end">
                                <button onClick={() => cancelOrder(o)} disabled={saving || !cancelReason.trim()}
                                  className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-red-600 hover:bg-red-700 text-white text-sm font-black shadow-md shadow-red-200 disabled:opacity-40 transition-all active:scale-95">
                                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                                  Cancelar orden
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Washers summary */}
                      {!inEdit && o.washers.length > 0 && (
                        <div className="rounded-2xl border border-slate-100 overflow-hidden">
                          <div className="flex items-center gap-2.5 px-5 py-3 bg-slate-50 border-b border-slate-100">
                            <Users className="h-4 w-4 text-slate-400" />
                            <span className="text-xs font-black text-slate-500 uppercase tracking-widest">Lavadores</span>
                          </div>
                          <div className="flex flex-wrap gap-2 px-5 py-4">
                            {o.washers.map(w => (
                              <div key={w.id} className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-2xl px-4 py-2.5">
                                <span className="text-sm font-black text-blue-900">{opName(w.user_id)}</span>
                                <span className="text-xs text-blue-400 font-semibold">{w.commission_percent}% · {fmt(w.commission_amount)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Notes */}
                      {(o.notes || o.is_domicilio) && (
                        <div className="flex flex-wrap gap-2">
                          {o.notes && (
                            <span className="text-xs font-medium text-slate-500 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-2.5">📝 {o.notes}</span>
                          )}
                          {o.is_domicilio && o.delivery_address && (
                            <span className="text-xs font-medium text-blue-600 bg-blue-50 border border-blue-100 rounded-2xl px-4 py-2.5">📍 {o.delivery_address}</span>
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

      {/* ── Payment dialog ───────────────────────────────────────────────────── */}
      <Dialog open={payDlg} onOpenChange={o => { if (!o) setPayDlg(false); }}>
        <DialogContent className="max-w-sm p-0 rounded-3xl overflow-hidden border-0">
          {/* Dark vehicle card */}
          <div className="bg-gradient-to-br from-slate-950 to-slate-800 px-7 py-6">
            {payOrder && (
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-1">Cobrar servicio</p>
                  <p className="text-white font-black text-xl leading-tight">{vehicleLabel(getVehicle(payOrder.vehicle_id))}</p>
                  <p className="text-slate-400 text-xs font-medium mt-1">{folio(payOrder)} · {clientName(payOrder.client_id) || "Cliente general"}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-1">Total</p>
                  <p className="text-white font-black text-3xl tabular-nums leading-none">{fmt(payOrder.total)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Body */}
          <div className="px-7 py-6 space-y-5 bg-white">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Forma de pago</label>
              <select className={field} value={payMethod} onChange={e => { setPayMethod(e.target.value); setTendered(""); }}>
                {PAY_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            {payMethod === "efectivo" && (
              <div className="rounded-2xl bg-sky-50 border border-sky-200 p-5 space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Efectivo recibido</label>
                  <input type="number" min="0" step="0.01" className={field} value={tendered}
                    onChange={e => setTendered(e.target.value)} placeholder="Ej. 500" autoFocus />
                </div>
                <div className="flex items-center justify-between bg-slate-900 text-white rounded-2xl px-5 py-4">
                  <span className="text-xs font-bold opacity-50 uppercase tracking-widest">Cambio a dar</span>
                  <span className="text-2xl font-black tabular-nums">{fmt(change)}</span>
                </div>
              </div>
            )}
            {payMethod === "credito" && (
              <div className="rounded-2xl bg-amber-50 border border-amber-200 px-5 py-4">
                <p className="font-black text-amber-900 text-sm">Se registrará como crédito.</p>
                <p className="text-amber-700 text-xs mt-1.5">No entra a caja. Se carga al saldo del cliente.</p>
              </div>
            )}
            {payMethod === "cortesia" && (
              <div className="rounded-2xl bg-sky-50 border border-sky-200 px-5 py-4">
                <p className="font-black text-sky-900 text-sm">Servicio cerrado como cortesía.</p>
                <p className="text-sky-700 text-xs mt-1.5">Sin ingreso a caja. Se conserva la comisión del lavador.</p>
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button onClick={() => setPayDlg(false)} disabled={saving}
                className="flex-1 py-3.5 rounded-2xl border-2 border-slate-200 bg-white text-slate-700 text-sm font-black hover:bg-slate-50 transition-all">
                Cancelar
              </button>
              <button onClick={pay} disabled={saving}
                className="flex-[2] flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-black shadow-lg shadow-emerald-200 active:scale-95 transition-all disabled:opacity-50">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Registrar cobro
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── New order dialog ─────────────────────────────────────────────────── */}
      <Dialog open={newDlg} onOpenChange={o => { if (!o) setNewDlg(false); }}>
        <DialogContent className="max-w-lg rounded-3xl">
          <DialogHeader>
            <DialogTitle className="text-xl font-black text-slate-900">Nueva orden de servicio</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
            {newErr && (
              <div className="rounded-2xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 font-semibold">{newErr}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Cliente</label>
                <select className={field} value={newClientId} onChange={e => { setNewClientId(e.target.value); setNewVehicleId(""); }}>
                  <option value="">Sin cliente</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Vehículo</label>
                <select className={field} value={newVehicleId} onChange={e => setNewVehicleId(e.target.value)}>
                  <option value="">Sin vehículo</option>
                  {vehicles.filter(v => !newClientId || !v.client_id || v.client_id === +newClientId)
                    .map(v => <option key={v.id} value={v.id}>{[v.plate, v.brand, v.model].filter(Boolean).join(" ")}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Notas</label>
              <input className={field} value={newNotes} onChange={e => setNewNotes(e.target.value)} placeholder="Opcional" />
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-black text-slate-500 uppercase tracking-wider">Servicios</label>
                <button type="button"
                  onClick={() => setNewItems(p => [...p, { catalog_id: null, custom_name: "", unit_price: "", quantity: 1 }])}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700 transition-all">
                  <Plus className="h-3 w-3" /> Agregar
                </button>
              </div>
              {newItems.map((item, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-5 space-y-1.5">
                    <label className="text-xs text-slate-400 font-bold">Catálogo</label>
                    <select className={field} value={item.catalog_id ?? ""} onChange={e => {
                      const svc = services.find(s => s.id === +e.target.value);
                      setNewItems(p => p.map((it, j) => j === i ? { ...it, catalog_id: svc?.id ?? null, custom_name: "", unit_price: svc?.base_price ?? it.unit_price } : it));
                    }}>
                      <option value="">Personalizado</option>
                      {services.map(s => <option key={s.id} value={s.id}>{s.name} — {fmt(s.base_price)}</option>)}
                    </select>
                  </div>
                  {!item.catalog_id && (
                    <div className="col-span-3 space-y-1.5">
                      <label className="text-xs text-slate-400 font-bold">Nombre</label>
                      <input className={field} value={item.custom_name} placeholder="Descripción"
                        onChange={e => setNewItems(p => p.map((it, j) => j === i ? { ...it, custom_name: e.target.value } : it))} />
                    </div>
                  )}
                  <div className={`${item.catalog_id ? "col-span-6" : "col-span-3"} space-y-1.5`}>
                    <label className="text-xs text-slate-400 font-bold">Precio</label>
                    <input type="number" min="0" step="0.01" className={field} value={item.unit_price} placeholder="0.00"
                      onChange={e => setNewItems(p => p.map((it, j) => j === i ? { ...it, unit_price: e.target.value } : it))} />
                  </div>
                  <button type="button" className="col-span-1 flex justify-center pb-1 text-red-300 hover:text-red-500 transition-colors"
                    onClick={() => setNewItems(p => p.filter((_, j) => j !== i))}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter className="gap-2">
            <button onClick={() => setNewDlg(false)} disabled={saving}
              className="px-5 py-3 rounded-2xl border-2 border-slate-200 text-slate-700 text-sm font-bold hover:bg-slate-50 transition-all">
              Cancelar
            </button>
            <button onClick={createOrder} disabled={saving}
              className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-black shadow-md active:scale-95 transition-all disabled:opacity-50">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Crear orden
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
