import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Loader2, Plus, ShoppingBag, ChevronRight, ChevronLeft, ChevronDown,
  ChevronUp, Trash2, Search, X, Users, Check,
} from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import api from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Client       { id: number; name: string; }
interface Vehicle      { id: number; plate: string | null; brand: string | null; model: string | null; color: string | null; client_id?: number | null; }
interface ServiceCatalog { id: number; name: string; base_price: string; }
interface Operator     { id: number; name: string; commission_percentage: string; }
interface OrderItem    { id: number; catalog_id: number | null; custom_name: string | null; unit_price: string; quantity: number; }
interface OrderWasher  { id: number; user_id: number; commission_percent: string; commission_amount: string; is_paid: boolean; }
interface Order {
  id: number; client_id: number | null; vehicle_id: number | null;
  service_date: string | null; daily_sequence: number | null;
  subtotal: string; discount_amount: string; discount_reason: string | null; total: string;
  status: string; payment_status: string; payment_method: string | null;
  is_domicilio: boolean; delivery_address: string | null; notes: string | null;
  items: OrderItem[]; washers: OrderWasher[];
}

// ─── Design tokens ────────────────────────────────────────────────────────────

const S: Record<string, { label: string; pill: string; dot: string; advance?: { label: string; value: string } }> = {
  en_cola:    { label: "En cola",   pill: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",      dot: "bg-amber-400",
                advance: { label: "Iniciar lavado", value: "en_proceso" } },
  en_proceso: { label: "Lavando",   pill: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",         dot: "bg-blue-500",
                advance: { label: "Marcar listo",   value: "listo" } },
  listo:      { label: "Listo",     pill: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200", dot: "bg-emerald-500",
                advance: { label: "Entregar",        value: "entregado" } },
  entregado:  { label: "Entregado", pill: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",     dot: "bg-slate-400" },
  cancelado:  { label: "Cancelado", pill: "bg-red-50 text-red-600 ring-1 ring-red-200",            dot: "bg-red-400" },
};

const P: Record<string, { label: string; color: string }> = {
  pendiente: { label: "Por cobrar", color: "text-orange-500" },
  pagado:    { label: "Pagado",     color: "text-emerald-600" },
  parcial:   { label: "Parcial",    color: "text-blue-600" },
  credito:   { label: "Crédito",    color: "text-violet-600" },
  cortesia:  { label: "Cortesía",   color: "text-sky-600" },
};

const PAY_METHODS = [
  { value: "efectivo",      label: "Efectivo" },
  { value: "tarjeta",       label: "Tarjeta" },
  { value: "transferencia", label: "Transferencia" },
  { value: "deposito",      label: "Depósito" },
  { value: "credito",       label: "Crédito — cartera" },
  { value: "cortesia",      label: "Cortesía" },
];
const PAY_LABELS: Record<string, string> = Object.fromEntries(PAY_METHODS.map(m => [m.value, m.label]));

const STATUSES = [
  { value: "en_cola",    label: "En cola" },
  { value: "en_proceso", label: "En proceso" },
  { value: "listo",      label: "Listo" },
  { value: "entregado",  label: "Entregado" },
];

type Scope        = "today" | "date" | "history";
type Filter       = "all" | "active" | "done" | "paid" | "pending_pay";
type ManageAction = "lavadores" | "estado" | "monto" | "reembolso" | "metodo_pago" | "cancelar" | "add_item";

function todayStr() { return new Date().toISOString().slice(0, 10); }
function fmt(v: string | number | null | undefined) {
  if (v == null) return "—";
  return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function norm(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\w\s#]/g, " ").replace(/\s+/g, " ").trim();
}

const inp  = "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-shadow placeholder:text-slate-400";
const primaryBtn = "w-full py-3 rounded-xl bg-blue-500 hover:bg-blue-600 active:scale-[0.98] text-white font-semibold text-sm transition-all disabled:opacity-50";
const dangerBtn  = "w-full py-3 rounded-xl bg-red-500 hover:bg-red-600 active:scale-[0.98] text-white font-semibold text-sm transition-all disabled:opacity-50";

// ─── Component ────────────────────────────────────────────────────────────────

export default function Orders({ branch = "local" }: { branch?: string }) {

  // ── Data ──────────────────────────────────────────────────────────────────
  const [orders,    setOrders]    = useState<Order[]>([]);
  const [clients,   setClients]   = useState<Client[]>([]);
  const [vehicles,  setVehicles]  = useState<Vehicle[]>([]);
  const [services,  setServices]  = useState<ServiceCatalog[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [globalErr, setGlobalErr] = useState("");
  const [saving,    setSaving]    = useState(false);

  // ── View ──────────────────────────────────────────────────────────────────
  const [scope,    setScope]    = useState<Scope>("today");
  const [dateFrom, setDateFrom] = useState(todayStr());
  const [dateTo,   setDateTo]   = useState(todayStr());
  const [filter,   setFilter]   = useState<Filter>("all");
  const [search,   setSearch]   = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  // ── New order ─────────────────────────────────────────────────────────────
  const [newDlg,       setNewDlg]       = useState(false);
  const [newClientId,  setNewClientId]  = useState("");
  const [newVehicleId, setNewVehicleId] = useState("");
  const [newNotes,     setNewNotes]     = useState("");
  const [newIsDom,     setNewIsDom]     = useState(false);
  const [newAddr,      setNewAddr]      = useState("");
  const [newItems,     setNewItems]     = useState<{ catalog_id: number | null; custom_name: string; unit_price: string; quantity: number }[]>([]);
  const [newErr,       setNewErr]       = useState("");

  // ── Pay dialog ────────────────────────────────────────────────────────────
  const [payDlg,         setPayDlg]         = useState(false);
  const [payOrder,       setPayOrder]       = useState<Order | null>(null);
  const [payMethod,      setPayMethod]      = useState("efectivo");
  const [payStatus,      setPayStatus]      = useState("pagado");
  const [payDiscount,    setPayDiscount]    = useState("0");
  const [payDiscReason,  setPayDiscReason]  = useState("");
  const [tendered,       setTendered]       = useState("");

  // ── Manage modal ──────────────────────────────────────────────────────────
  const [manageDlg,    setManageDlg]    = useState(false);
  const [manageOrder,  setManageOrder]  = useState<Order | null>(null);
  const [manageAction, setManageAction] = useState<ManageAction | null>(null);
  const [manageErr,    setManageErr]    = useState("");
  // per-action state
  const [mWasherIds,     setMWasherIds]     = useState<Set<number>>(new Set());
  const [mCommissions,   setMCommissions]   = useState<Record<number, string>>({});
  const [mEditStatus,    setMEditStatus]    = useState("");
  const [mEditTotal,     setMEditTotal]     = useState("");
  const [mDiscount,      setMDiscount]      = useState("0");
  const [mDiscReason,    setMDiscReason]    = useState("");
  const [mPayMethod,     setMPayMethod]     = useState("efectivo");
  const [mPayStatus,     setMPayStatus]     = useState("pagado");
  const [mCancelReason,  setMCancelReason]  = useState("");
  const [mItem,          setMItem]          = useState({ catalog_id: "", custom_name: "", unit_price: "", quantity: "1" });

  // ── Helpers ───────────────────────────────────────────────────────────────
  const getVehicle  = useCallback((id: number | null) => vehicles.find(v => v.id === id),   [vehicles]);
  const getClient   = useCallback((id: number | null) => clients.find(c => c.id === id),    [clients]);
  const opName      = useCallback((uid: number | null) => uid == null ? "Sin asignar" : (operators.find(o => o.id === uid)?.name ?? `Lavador ${uid}`), [operators]);
  const catalogName = useCallback((id: number | null) => services.find(s => s.id === id)?.name ?? "Servicio",  [services]);

  function vehicleLabel(v: Vehicle | undefined) {
    if (!v) return "Sin vehículo";
    return [v.brand, v.model, v.color].filter(Boolean).join(" ") || "Vehículo";
  }
  function folio(o: Order) {
    return o.daily_sequence != null ? `#${String(o.daily_sequence).padStart(3, "0")}` : `#${o.id}`;
  }
  function isPaid(o: Order) {
    return ["pagado", "parcial", "credito", "cortesia"].includes(o.payment_status);
  }

  // ── Load data ─────────────────────────────────────────────────────────────
  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { branch };
      if (scope === "today")   { params.date_from = todayStr(); params.date_to = todayStr(); }
      else if (scope === "date") { params.date_from = dateFrom; params.date_to = dateTo; }
      else                     { params.limit = "200"; }
      setOrders((await api.get<Order[]>("/orders/", { params })).data);
    } catch { setGlobalErr("Error al cargar órdenes."); }
    setLoading(false);
  }, [scope, dateFrom, dateTo]);

  useEffect(() => { loadOrders(); }, [loadOrders]);

  useEffect(() => {
    Promise.all([
      api.get<Client[]>("/clients/"),
      api.get<Vehicle[]>("/vehicles/"),
      api.get<ServiceCatalog[]>("/service-catalog/"),
      api.get<Operator[]>("/users/?role=operator"),
    ]).then(([c, v, s, o]) => {
      setClients(c.data); setVehicles(v.data); setServices(s.data); setOperators(o.data);
    }).catch(() => {});
  }, []);

  // ── Filtered list ─────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    let list = orders;
    if (filter === "active")       list = list.filter(o => ["en_cola","en_proceso"].includes(o.status));
    else if (filter === "done")    list = list.filter(o => ["listo","entregado"].includes(o.status));
    else if (filter === "paid")    list = list.filter(o => isPaid(o));
    else if (filter === "pending_pay") list = list.filter(o => !isPaid(o) && o.status !== "cancelado");
    if (search) {
      const q = norm(search);
      list = list.filter(o => {
        const v = getVehicle(o.vehicle_id);
        const c = getClient(o.client_id);
        return [folio(o), v?.plate, v?.brand, v?.model, v?.color, c?.name, o.notes].some(
          f => f && norm(String(f)).includes(q),
        );
      });
    }
    return list;
  }, [orders, filter, search, getVehicle, getClient]);

  // ── Status advance ────────────────────────────────────────────────────────
  async function advance(o: Order) {
    const n = S[o.status]?.advance; if (!n) return;
    try {
      setOrders(p => p.map(x => x.id === o.id ? { ...x, status: n.value } : x));
      const res = await api.patch<Order>(`/orders/${o.id}/status`, { status: n.value });
      setOrders(p => p.map(x => x.id === o.id ? res.data : x));
    } catch { setGlobalErr("Error al actualizar estado."); loadOrders(); }
  }

  // ── Remove item (from expanded card) ─────────────────────────────────────
  async function removeItem(order: Order, itemId: number) {
    try {
      const res = await api.delete<Order>(`/orders/${order.id}/items/${itemId}`);
      setOrders(p => p.map(o => o.id === order.id ? res.data : o));
      if (manageOrder?.id === order.id) setManageOrder(res.data);
    } catch { setGlobalErr("Error al eliminar ítem."); }
  }

  // ── Pay dialog ────────────────────────────────────────────────────────────
  function openPayDialog(o: Order) {
    setPayOrder(o);
    setPayMethod(o.payment_method ?? "efectivo");
    setPayStatus("pagado");
    setPayDiscount(Number(o.discount_amount) > 0 ? o.discount_amount : "0");
    setPayDiscReason("");
    setTendered("");
    setPayDlg(true);
    setManageDlg(false);
  }

  async function submitPay() {
    if (!payOrder) return;
    setSaving(true);
    try {
      const isCourtesy = payStatus === "cortesia";
      const isCredit   = payStatus === "credito";
      const res = await api.patch<Order>(`/orders/${payOrder.id}/payment`, {
        payment_method: isCourtesy ? "cortesia" : isCredit ? "credito" : payMethod,
        payment_status: isCourtesy ? "cortesia" : isCredit ? "credito" : payStatus,
        discount_amount: parseFloat(payDiscount) || 0,
        discount_reason: payDiscReason || null,
      });
      setOrders(p => p.map(o => o.id === payOrder.id ? res.data : o));
      setPayDlg(false);
    } catch { setGlobalErr("Error al registrar el pago."); }
    setSaving(false);
  }

  const payFinal  = payOrder ? Math.max(0, Number(payOrder.total) - (parseFloat(payDiscount) || 0)) : 0;
  const payChange = Math.max(0, (parseFloat(tendered) || 0) - payFinal);

  // ── Manage modal ──────────────────────────────────────────────────────────
  function openManage(o: Order) {
    setManageOrder(o);
    setManageAction(null);
    setManageErr("");
    setManageDlg(true);
  }

  function goAction(action: ManageAction) {
    const o = manageOrder; if (!o) return;
    setManageErr("");
    if (action === "lavadores") {
      setMWasherIds(new Set(o.washers.map(w => w.user_id)));
      const comms: Record<number, string> = {};
      o.washers.forEach(w => { comms[w.user_id] = w.commission_percent; });
      setMCommissions(comms);
    } else if (action === "estado") {
      setMEditStatus(o.status);
    } else if (action === "monto") {
      setMEditTotal(o.total);
    } else if (action === "reembolso") {
      setMDiscount(Number(o.discount_amount) > 0 ? o.discount_amount : "0");
      setMDiscReason(o.discount_reason ?? "");
    } else if (action === "metodo_pago") {
      setMPayMethod(o.payment_method ?? "efectivo");
      setMPayStatus(o.payment_status);
    } else if (action === "cancelar") {
      setMCancelReason("");
    } else if (action === "add_item") {
      setMItem({ catalog_id: "", custom_name: "", unit_price: "", quantity: "1" });
    }
    setManageAction(action);
  }

  function toggleWasher(uid: number) {
    setMWasherIds(prev => {
      const next = new Set(prev);
      if (next.has(uid)) { next.delete(uid); }
      else {
        next.add(uid);
        if (!(uid in mCommissions)) {
          const op = operators.find(o => o.id === uid);
          setMCommissions(c => ({ ...c, [uid]: op?.commission_percentage ?? "0" }));
        }
      }
      return next;
    });
  }

  async function saveWashers() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.put<Order>(`/orders/${manageOrder.id}/washers`, {
        washers: Array.from(mWasherIds).map(uid => ({
          user_id: uid,
          commission_percent: parseFloat(mCommissions[uid] ?? "0") || 0,
        })),
      });
      updateManage(res.data);
    } catch { setManageErr("Error al guardar lavadores."); }
    setSaving(false);
  }

  async function saveEstado() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.patch<Order>(`/orders/${manageOrder.id}/status`, { status: mEditStatus });
      updateManage(res.data);
    } catch { setManageErr("Error al cambiar estado."); }
    setSaving(false);
  }

  async function saveTotal() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.patch<Order>(`/orders/${manageOrder.id}/total`, { total: parseFloat(mEditTotal) || 0 });
      updateManage(res.data);
    } catch { setManageErr("Error al ajustar monto."); }
    setSaving(false);
  }

  async function saveReembolso() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.patch<Order>(`/orders/${manageOrder.id}/payment`, {
        payment_method: manageOrder.payment_method,
        payment_status: manageOrder.payment_status,
        discount_amount: parseFloat(mDiscount) || 0,
        discount_reason: mDiscReason || null,
      });
      updateManage(res.data);
    } catch { setManageErr("Error al aplicar reembolso."); }
    setSaving(false);
  }

  async function saveMetodoPago() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.patch<Order>(`/orders/${manageOrder.id}/payment`, {
        payment_method: mPayMethod,
        payment_status: mPayStatus,
        discount_amount: parseFloat(manageOrder.discount_amount) || 0,
        discount_reason: manageOrder.discount_reason || null,
      });
      updateManage(res.data);
    } catch { setManageErr("Error al cambiar método de pago."); }
    setSaving(false);
  }

  async function saveCancelar() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const res = await api.patch<Order>(`/orders/${manageOrder.id}/status`, {
        status: "cancelado",
        cancellation_reason: mCancelReason || null,
      });
      setOrders(p => p.map(o => o.id === manageOrder.id ? res.data : o));
      setManageDlg(false);
    } catch { setManageErr("Error al cancelar la orden."); }
    setSaving(false);
  }

  async function saveAddItem() {
    if (!manageOrder) return;
    setSaving(true); setManageErr("");
    try {
      const catId = mItem.catalog_id ? parseInt(mItem.catalog_id) : null;
      const res = await api.post<Order>(`/orders/${manageOrder.id}/items`, {
        catalog_id:  catId,
        custom_name: catId ? null : mItem.custom_name || null,
        unit_price:  parseFloat(mItem.unit_price) || 0,
        quantity:    parseInt(mItem.quantity) || 1,
      });
      updateManage(res.data);
    } catch { setManageErr("Error al agregar servicio."); }
    setSaving(false);
  }

  function updateManage(updated: Order) {
    setOrders(p => p.map(o => o.id === updated.id ? updated : o));
    setManageOrder(updated);
    setManageAction(null);
  }

  // ── New order ─────────────────────────────────────────────────────────────
  async function submitNew() {
    setNewErr("");
    if (!newItems.length) { setNewErr("Agrega al menos un servicio."); return; }
    setSaving(true);
    try {
      const res = await api.post<Order>("/orders/", {
        client_id:        newClientId  ? parseInt(newClientId)  : null,
        vehicle_id:       newVehicleId ? parseInt(newVehicleId) : null,
        items:            newItems.map(i => ({
          catalog_id:  i.catalog_id,
          custom_name: i.catalog_id ? null : i.custom_name || null,
          unit_price:  parseFloat(i.unit_price) || 0,
          quantity:    i.quantity,
        })),
        is_domicilio:     branch === "domicilios" ? true : newIsDom,
        delivery_address: newIsDom ? newAddr : null,
        notes:            newNotes || null,
      });
      setOrders(p => [res.data, ...p]);
      setNewDlg(false);
    } catch { setNewErr("Error al crear la orden."); }
    setSaving(false);
  }

  const filteredVehicles = useMemo(
    () => newClientId ? vehicles.filter(v => v.client_id === parseInt(newClientId)) : vehicles,
    [vehicles, newClientId],
  );

  // ── Render ────────────────────────────────────────────────────────────────
  const SCOPES:  { k: Scope;  l: string }[] = [{ k:"today",l:"Hoy" },{ k:"date",l:"Por fecha" },{ k:"history",l:"Historial" }];
  const FILTERS: { k: Filter; l: string }[] = [
    { k:"all",l:"Todos" },{ k:"active",l:"Activos" },{ k:"done",l:"Terminados" },
    { k:"paid",l:"Pagados" },{ k:"pending_pay",l:"Por cobrar" },
  ];

  return (
    <div className="space-y-4 pb-16">

      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Servicios</h1>
          <p className="text-sm text-slate-400">Gestiona estado, cobros y detalles.</p>
        </div>
        <button
          onClick={() => { setNewClientId(""); setNewVehicleId(""); setNewNotes(""); setNewItems([]); setNewIsDom(false); setNewAddr(""); setNewErr(""); setNewDlg(true); }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold shadow-sm active:scale-95 transition-all"
        >
          <Plus className="h-4 w-4" /> Nueva
        </button>
      </div>

      {/* Error banner */}
      {globalErr && (
        <div className="flex items-center justify-between gap-3 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">
          <span>{globalErr}</span>
          <button onClick={() => setGlobalErr("")}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Scope tabs */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-xl w-fit">
        {SCOPES.map(s => (
          <button key={s.k} onClick={() => setScope(s.k)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${scope === s.k ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
            {s.l}
          </button>
        ))}
      </div>

      {/* Date pickers */}
      {scope === "date" && (
        <div className="flex items-center gap-3">
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className={inp + " w-auto"} />
          <span className="text-slate-400 text-sm">—</span>
          <input type="date" value={dateTo}   onChange={e => setDateTo(e.target.value)}   className={inp + " w-auto"} />
        </div>
      )}

      {/* Filter pills */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button key={f.k} onClick={() => setFilter(f.k)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${filter === f.k ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
            {f.l}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
        <input placeholder="Buscar placa, cliente, folio…" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-10 py-3 rounded-xl bg-slate-100 border-transparent text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white transition-all" />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-3.5 top-1/2 -translate-y-1/2">
            <X className="h-4 w-4 text-slate-400 hover:text-slate-600" />
          </button>
        )}
      </div>

      {/* Order list */}
      {loading ? (
        <div className="flex flex-col items-center gap-3 py-24 text-slate-300">
          <Loader2 className="h-8 w-8 animate-spin" /><span className="text-sm">Cargando…</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-24 text-slate-400">
          <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center">
            <ShoppingBag className="h-7 w-7 opacity-40" />
          </div>
          <p className="text-sm">{search ? "Sin resultados." : "No hay órdenes aquí."}</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filtered.map(o => {
            const v         = getVehicle(o.vehicle_id);
            const c         = getClient(o.client_id);
            const wstr      = o.washers.map(w => opName(w.user_id)).join(", ");
            const isOpen    = expanded === o.id;
            const cancelled = o.status === "cancelado";
            const paid      = isPaid(o);
            const sm        = S[o.status]  ?? { label: o.status, pill: "bg-slate-100 text-slate-600 ring-1 ring-slate-200", dot: "bg-slate-400" };
            const pm        = P[o.payment_status] ?? { label: o.payment_status, color: "text-slate-500" };

            return (
              <article key={o.id} className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow overflow-hidden">

                {/* Card header — tappable */}
                <div className="px-4 pt-4 pb-3 cursor-pointer select-none" onClick={() => setExpanded(p => p === o.id ? null : o.id)}>
                  <div className="flex items-start gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full mt-[5px] shrink-0 ${sm.dot}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-slate-400 font-mono">{folio(o)}</span>
                            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${sm.pill}`}>{sm.label}</span>
                            {o.is_domicilio && <span className="text-[11px] font-semibold bg-purple-50 text-purple-600 px-2 py-0.5 rounded-full">Domicilio</span>}
                          </div>
                          <p className="text-[15px] font-bold text-slate-900 mt-1 leading-snug">{vehicleLabel(v)}</p>
                          {v?.plate && (
                            <span className="inline-block text-[11px] font-mono font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md mt-0.5 tracking-widest">
                              {v.plate}
                            </span>
                          )}
                          {c && <p className="text-xs text-slate-400 mt-0.5">{c.name}</p>}
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-lg font-bold text-slate-900">{fmt(o.total)}</p>
                          <p className={`text-xs font-semibold mt-0.5 ${pm.color}`}>{pm.label}</p>
                        </div>
                      </div>
                      {wstr && (
                        <p className="text-xs text-slate-400 mt-1.5 flex items-center gap-1">
                          <Users className="h-3 w-3 shrink-0" /> {wstr}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Action row */}
                <div className="px-4 pb-4 flex items-center gap-2">
                  {sm.advance && !paid && (
                    <button onClick={() => advance(o)}
                      className="flex-1 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold active:scale-[0.98] transition-all">
                      {sm.advance.label}
                    </button>
                  )}
                  {!paid && !cancelled && (o.status === "listo" || o.status === "entregado") && (
                    <button onClick={() => openPayDialog(o)}
                      className="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-semibold active:scale-[0.98] transition-all">
                      Cobrar
                    </button>
                  )}
                  {paid && (
                    <div className="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-xl bg-emerald-50">
                      <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                        <Check className="h-3 w-3 text-white" />
                      </div>
                      <span className="text-sm font-semibold text-emerald-700 truncate">{PAY_LABELS[o.payment_method ?? ""] ?? o.payment_method ?? "Cobrado"}</span>
                    </div>
                  )}
                  {!cancelled && (
                    <button onClick={() => openManage(o)}
                      className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-sm font-semibold active:scale-[0.98] transition-all">
                      ···
                    </button>
                  )}
                  <button onClick={() => setExpanded(p => p === o.id ? null : o.id)}
                    className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 transition-colors">
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>
                </div>

                {/* Expanded items */}
                {isOpen && (
                  <div className="border-t border-slate-100 px-4 py-3">
                    {o.items.length === 0 ? (
                      <p className="text-sm text-slate-400 text-center py-2">Sin ítems</p>
                    ) : (
                      <div className="space-y-2">
                        {o.items.map(item => (
                          <div key={item.id} className="flex items-center gap-2">
                            <span className="text-sm text-slate-700 flex-1 min-w-0 truncate">
                              {item.catalog_id ? catalogName(item.catalog_id) : item.custom_name || "Servicio"}
                              {item.quantity > 1 && <span className="text-slate-400 ml-1">×{item.quantity}</span>}
                            </span>
                            <span className="text-sm font-semibold text-slate-900 shrink-0">{fmt(String(Number(item.unit_price) * item.quantity))}</span>
                            {!cancelled && !paid && (
                              <button onClick={() => removeItem(o, item.id)}
                                className="p-1 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors">
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {o.notes && (
                      <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-100 italic">{o.notes}</p>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {/* ── Manage Modal ──────────────────────────────────────────────────────── */}
      <Dialog open={manageDlg} onOpenChange={v => { if (!v) { setManageDlg(false); setManageAction(null); } }}>
        <DialogContent className="sm:max-w-sm rounded-3xl p-0 gap-0 overflow-hidden">
          {manageOrder && (() => {
            const o        = manageOrder;
            const paid     = isPaid(o);
            const cancelled = o.status === "cancelado";

            return (
              <>
                <div className="px-5 pt-5 pb-4">
                  {manageAction && (
                    <button onClick={() => { setManageAction(null); setManageErr(""); }}
                      className="flex items-center gap-1 text-blue-500 text-sm font-medium mb-3 -ml-1">
                      <ChevronLeft className="h-4 w-4" /> Atrás
                    </button>
                  )}
                  <DialogTitle className="text-[17px] font-bold text-slate-900 leading-snug">
                    {manageAction == null        ? `${folio(o)} · Gestionar`
                      : manageAction === "lavadores"  ? "Lavadores"
                      : manageAction === "estado"     ? "Cambiar estado"
                      : manageAction === "monto"      ? "Ajustar monto"
                      : manageAction === "reembolso"  ? "Reembolso / Descuento"
                      : manageAction === "metodo_pago"? "Método de pago"
                      : manageAction === "cancelar"   ? "Cancelar orden"
                      : manageAction === "add_item"   ? "Agregar servicio"
                      : ""}
                  </DialogTitle>
                  <p className="text-sm text-slate-400 mt-0.5">{vehicleLabel(getVehicle(o.vehicle_id))}</p>
                </div>

                {manageErr && (
                  <div className="mx-5 mb-1 px-4 py-3 bg-red-50 rounded-xl text-sm text-red-700">{manageErr}</div>
                )}

                <div className="px-5 pb-5 space-y-3 max-h-[70vh] overflow-y-auto">

                  {/* ── Main menu ── */}
                  {manageAction == null && (
                    <>
                      <IosGroup>
                        {!cancelled && (
                          <IosRow label="Lavadores"
                            value={o.washers.length > 0 ? o.washers.map(w => opName(w.user_id)).join(", ") : "Sin asignar"}
                            onClick={() => goAction("lavadores")} />
                        )}
                        {!cancelled && (
                          <IosRow label="Cambiar estado" value={S[o.status]?.label ?? o.status} onClick={() => goAction("estado")} />
                        )}
                        {!cancelled && (
                          <IosRow label="Agregar servicio" onClick={() => goAction("add_item")} />
                        )}
                      </IosGroup>

                      <IosGroup>
                        {!paid && !cancelled && (
                          <IosRow label="Cobrar" labelClass="font-semibold text-emerald-600" onClick={() => openPayDialog(o)} />
                        )}
                        {!cancelled && (
                          <IosRow label="Ajustar monto total" value={fmt(o.total)} onClick={() => goAction("monto")} />
                        )}
                        {paid && (
                          <IosRow label="Cambiar método de pago" value={PAY_LABELS[o.payment_method ?? ""] ?? ""} onClick={() => goAction("metodo_pago")} />
                        )}
                        {paid && (
                          <IosRow label="Reembolso / Descuento"
                            value={Number(o.discount_amount) > 0 ? `-${fmt(o.discount_amount)}` : undefined}
                            onClick={() => goAction("reembolso")} />
                        )}
                      </IosGroup>

                      {!cancelled && (
                        <IosGroup>
                          <IosRow label="Cancelar orden" labelClass="text-red-600" onClick={() => goAction("cancelar")} />
                        </IosGroup>
                      )}
                    </>
                  )}

                  {/* ── Lavadores ── */}
                  {manageAction === "lavadores" && (
                    <>
                      <IosGroup>
                        {operators.length === 0 && (
                          <p className="px-4 py-3 text-sm text-slate-400">No hay operadores registrados.</p>
                        )}
                        {operators.map(op => {
                          const sel = mWasherIds.has(op.id);
                          return (
                            <div key={op.id} className="flex items-center gap-3 px-4 py-3 bg-white">
                              <button onClick={() => toggleWasher(op.id)}
                                className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${sel ? "bg-blue-500 border-blue-500" : "border-slate-300"}`}>
                                {sel && <Check className="h-3 w-3 text-white" />}
                              </button>
                              <span className="flex-1 text-sm font-medium text-slate-800">{op.name}</span>
                              {sel && (
                                <div className="flex items-center gap-1">
                                  <input type="number" min="0" max="100" step="1"
                                    value={mCommissions[op.id] ?? op.commission_percentage}
                                    onChange={e => setMCommissions(c => ({ ...c, [op.id]: e.target.value }))}
                                    className="w-16 text-right rounded-lg border border-slate-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
                                  <span className="text-xs text-slate-400">%</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </IosGroup>
                      <button onClick={saveWashers} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Guardar"}
                      </button>
                    </>
                  )}

                  {/* ── Cambiar estado ── */}
                  {manageAction === "estado" && (
                    <>
                      <IosGroup>
                        {STATUSES.map(s => (
                          <button key={s.value} onClick={() => setMEditStatus(s.value)}
                            className="w-full px-4 py-3 flex items-center justify-between text-sm text-left bg-white hover:bg-slate-50 transition-colors">
                            <span className={mEditStatus === s.value ? "font-semibold text-blue-600" : "text-slate-700"}>{s.label}</span>
                            {mEditStatus === s.value && <Check className="h-4 w-4 text-blue-500" />}
                          </button>
                        ))}
                      </IosGroup>
                      <button onClick={saveEstado} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Guardar"}
                      </button>
                    </>
                  )}

                  {/* ── Ajustar monto ── */}
                  {manageAction === "monto" && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Total</label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                          <input type="number" min="0" step="0.01" value={mEditTotal}
                            onChange={e => setMEditTotal(e.target.value)}
                            className={inp + " pl-8"} placeholder="0.00" autoFocus />
                        </div>
                      </div>
                      <button onClick={saveTotal} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Guardar"}
                      </button>
                    </>
                  )}

                  {/* ── Reembolso ── */}
                  {manageAction === "reembolso" && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Monto a descontar</label>
                        <div className="relative">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                          <input type="number" min="0" step="0.01" value={mDiscount}
                            onChange={e => setMDiscount(e.target.value)}
                            className={inp + " pl-8"} placeholder="0.00" autoFocus />
                        </div>
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Motivo</label>
                        <input value={mDiscReason} onChange={e => setMDiscReason(e.target.value)}
                          className={inp} placeholder="Ej: error de cobro, cortesía…" />
                      </div>
                      <div className="bg-slate-50 rounded-xl px-4 py-3 text-sm space-y-1">
                        <div className="flex justify-between text-slate-500"><span>Total original</span><span>{fmt(o.subtotal)}</span></div>
                        <div className="flex justify-between text-red-600"><span>Descuento</span><span>-{fmt(mDiscount || "0")}</span></div>
                        <div className="flex justify-between font-bold text-slate-900 pt-2 border-t border-slate-200">
                          <span>Total final</span><span>{fmt(String(Number(o.subtotal) - (parseFloat(mDiscount) || 0)))}</span>
                        </div>
                      </div>
                      <button onClick={saveReembolso} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Aplicar"}
                      </button>
                    </>
                  )}

                  {/* ── Método de pago ── */}
                  {manageAction === "metodo_pago" && (
                    <>
                      <IosGroup>
                        {PAY_METHODS.map(m => (
                          <button key={m.value} onClick={() => setMPayMethod(m.value)}
                            className="w-full px-4 py-3 flex items-center justify-between text-sm text-left bg-white hover:bg-slate-50 transition-colors">
                            <span className={mPayMethod === m.value ? "font-semibold text-blue-600" : "text-slate-700"}>{m.label}</span>
                            {mPayMethod === m.value && <Check className="h-4 w-4 text-blue-500" />}
                          </button>
                        ))}
                      </IosGroup>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Estado de pago</label>
                        <select value={mPayStatus} onChange={e => setMPayStatus(e.target.value)} className={inp}>
                          <option value="pagado">Pagado</option>
                          <option value="parcial">Parcial</option>
                          <option value="credito">Crédito</option>
                          <option value="cortesia">Cortesía</option>
                        </select>
                      </div>
                      <button onClick={saveMetodoPago} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Guardar"}
                      </button>
                    </>
                  )}

                  {/* ── Cancelar ── */}
                  {manageAction === "cancelar" && (
                    <>
                      <p className="text-sm text-slate-500">Esta acción cancelará la orden permanentemente.</p>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Motivo (opcional)</label>
                        <textarea value={mCancelReason} onChange={e => setMCancelReason(e.target.value)}
                          className={inp + " resize-none"} rows={3} placeholder="Ej: cliente no se presentó, error de registro…" />
                      </div>
                      <button onClick={saveCancelar} disabled={saving} className={dangerBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Confirmar cancelación"}
                      </button>
                    </>
                  )}

                  {/* ── Agregar servicio ── */}
                  {manageAction === "add_item" && (
                    <>
                      <div>
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Del catálogo</label>
                        <select value={mItem.catalog_id} onChange={e => {
                          const s = services.find(s => s.id === parseInt(e.target.value));
                          setMItem(p => ({ ...p, catalog_id: e.target.value, unit_price: s ? s.base_price : p.unit_price }));
                        }} className={inp}>
                          <option value="">— Personalizado —</option>
                          {services.map(s => <option key={s.id} value={s.id}>{s.name} · {fmt(s.base_price)}</option>)}
                        </select>
                      </div>
                      {!mItem.catalog_id && (
                        <div>
                          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Nombre</label>
                          <input value={mItem.custom_name} onChange={e => setMItem(p => ({ ...p, custom_name: e.target.value }))}
                            className={inp} placeholder="Nombre del servicio" />
                        </div>
                      )}
                      <div className="flex gap-3">
                        <div className="flex-1">
                          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Precio</label>
                          <div className="relative">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                            <input type="number" min="0" step="0.01" value={mItem.unit_price}
                              onChange={e => setMItem(p => ({ ...p, unit_price: e.target.value }))}
                              className={inp + " pl-8"} placeholder="0.00" />
                          </div>
                        </div>
                        <div className="w-24">
                          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Cant.</label>
                          <input type="number" min="1" value={mItem.quantity}
                            onChange={e => setMItem(p => ({ ...p, quantity: e.target.value }))}
                            className={inp} placeholder="1" />
                        </div>
                      </div>
                      <button onClick={saveAddItem} disabled={saving} className={primaryBtn}>
                        {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Agregar"}
                      </button>
                    </>
                  )}

                </div>
              </>
            );
          })()}
        </DialogContent>
      </Dialog>

      {/* ── Pay Dialog ────────────────────────────────────────────────────────── */}
      <Dialog open={payDlg} onOpenChange={v => { if (!v) setPayDlg(false); }}>
        <DialogContent className="sm:max-w-sm rounded-3xl p-0 gap-0 overflow-hidden">
          {payOrder && (
            <>
              <div className="bg-slate-900 px-5 pt-5 pb-5">
                <DialogTitle className="text-lg font-bold text-white">Cobrar</DialogTitle>
                <p className="text-sm text-slate-400 mt-0.5">{vehicleLabel(getVehicle(payOrder.vehicle_id))} · {folio(payOrder)}</p>
                <p className="text-4xl font-black text-white mt-3 tabular-nums">{fmt(payFinal)}</p>
                {(parseFloat(payDiscount) || 0) > 0 && (
                  <p className="text-sm text-slate-500 line-through mt-0.5">{fmt(payOrder.total)}</p>
                )}
              </div>

              <div className="px-5 py-4 space-y-4 max-h-[65vh] overflow-y-auto">
                {/* Payment type */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Tipo</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[{ v:"pagado",l:"Normal" },{ v:"cortesia",l:"Cortesía" },{ v:"credito",l:"Crédito" }].map(t => (
                      <button key={t.v} onClick={() => setPayStatus(t.v)}
                        className={`py-2 rounded-xl text-xs font-semibold transition-all ${payStatus === t.v ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                        {t.l}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Method (only for normal payment) */}
                {payStatus === "pagado" && (
                  <IosGroup>
                    {PAY_METHODS.filter(m => !["credito","cortesia"].includes(m.value)).map(m => (
                      <button key={m.value} onClick={() => setPayMethod(m.value)}
                        className="w-full px-4 py-3 flex items-center justify-between text-sm text-left bg-white hover:bg-slate-50 transition-colors">
                        <span className={payMethod === m.value ? "font-semibold text-blue-600" : "text-slate-700"}>{m.label}</span>
                        {payMethod === m.value && <Check className="h-4 w-4 text-blue-500" />}
                      </button>
                    ))}
                  </IosGroup>
                )}

                {/* Cash change */}
                {payStatus === "pagado" && payMethod === "efectivo" && (
                  <div>
                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Con cuánto paga</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                      <input type="number" min="0" value={tendered} onChange={e => setTendered(e.target.value)}
                        className={inp + " pl-8"} placeholder="0.00" />
                    </div>
                    {payChange > 0 && (
                      <div className="mt-2 px-4 py-2.5 bg-emerald-50 rounded-xl flex items-center justify-between">
                        <span className="text-sm text-emerald-700">Cambio</span>
                        <span className="text-sm font-bold text-emerald-700">{fmt(payChange)}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Discount */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Descuento (opcional)</label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                      <input type="number" min="0" step="0.01" value={payDiscount}
                        onChange={e => setPayDiscount(e.target.value)}
                        className={inp + " pl-8"} placeholder="0.00" />
                    </div>
                    <input value={payDiscReason} onChange={e => setPayDiscReason(e.target.value)}
                      className={inp + " flex-1"} placeholder="Motivo" />
                  </div>
                </div>

                <button onClick={submitPay} disabled={saving} className={primaryBtn}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Confirmar cobro"}
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* ── New Order Dialog ──────────────────────────────────────────────────── */}
      <Dialog open={newDlg} onOpenChange={v => { if (!v) setNewDlg(false); }}>
        <DialogContent className="sm:max-w-md rounded-3xl p-0 gap-0 overflow-hidden max-h-[90vh]">
          <div className="px-5 pt-5 pb-4 border-b border-slate-100 sticky top-0 bg-white z-10">
            <DialogTitle className="text-[17px] font-bold text-slate-900">Nueva orden</DialogTitle>
          </div>
          <div className="px-5 py-4 space-y-4 overflow-y-auto">
            {newErr && <div className="px-4 py-3 bg-red-50 rounded-xl text-sm text-red-700">{newErr}</div>}

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Cliente</label>
              <select value={newClientId} onChange={e => { setNewClientId(e.target.value); setNewVehicleId(""); }} className={inp}>
                <option value="">Sin cliente</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Vehículo</label>
              <select value={newVehicleId} onChange={e => setNewVehicleId(e.target.value)} className={inp}>
                <option value="">Sin vehículo</option>
                {filteredVehicles.map(v => (
                  <option key={v.id} value={v.id}>{[v.plate, v.brand, v.model, v.color].filter(Boolean).join(" · ")}</option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Servicios</label>
                <button onClick={() => setNewItems(p => [...p, { catalog_id: null, custom_name: "", unit_price: "", quantity: 1 }])}
                  className="flex items-center gap-1 text-blue-500 text-xs font-semibold">
                  <Plus className="h-3 w-3" /> Agregar
                </button>
              </div>
              {newItems.length === 0 ? (
                <p className="text-sm text-slate-400 py-1">Sin servicios — presiona Agregar.</p>
              ) : (
                <div className="space-y-2">
                  {newItems.map((item, i) => (
                    <div key={i} className="bg-slate-50 rounded-xl p-3 space-y-2">
                      <select value={item.catalog_id ?? ""} onChange={e => {
                        const s = services.find(s => s.id === parseInt(e.target.value));
                        setNewItems(p => p.map((it, j) => j === i
                          ? { ...it, catalog_id: s?.id ?? null, custom_name: s ? "" : it.custom_name, unit_price: s ? s.base_price : it.unit_price }
                          : it));
                      }} className={inp}>
                        <option value="">— Personalizado —</option>
                        {services.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                      {!item.catalog_id && (
                        <input value={item.custom_name}
                          onChange={e => setNewItems(p => p.map((it, j) => j === i ? { ...it, custom_name: e.target.value } : it))}
                          className={inp} placeholder="Nombre del servicio" />
                      )}
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
                          <input type="number" min="0" step="0.01" value={item.unit_price}
                            onChange={e => setNewItems(p => p.map((it, j) => j === i ? { ...it, unit_price: e.target.value } : it))}
                            className={inp + " pl-8"} placeholder="0.00" />
                        </div>
                        <div className="w-20">
                          <input type="number" min="1" value={item.quantity}
                            onChange={e => setNewItems(p => p.map((it, j) => j === i ? { ...it, quantity: parseInt(e.target.value) || 1 } : it))}
                            className={inp} placeholder="1" />
                        </div>
                        <button onClick={() => setNewItems(p => p.filter((_, j) => j !== i))}
                          className="p-2.5 rounded-xl bg-red-50 hover:bg-red-100 text-red-500 transition-colors">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Notas</label>
              <textarea value={newNotes} onChange={e => setNewNotes(e.target.value)}
                className={inp + " resize-none"} rows={2} placeholder="Observaciones opcionales…" />
            </div>

            <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
              <button onClick={() => setNewIsDom(p => !p)}
                className={`w-10 h-6 rounded-full transition-colors relative ${newIsDom ? "bg-blue-500" : "bg-slate-300"}`}>
                <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-all ${newIsDom ? "left-4.5" : "left-0.5"}`} />
              </button>
              <span className="text-sm font-medium text-slate-700">Servicio a domicilio</span>
            </div>
            {newIsDom && (
              <input value={newAddr} onChange={e => setNewAddr(e.target.value)}
                className={inp} placeholder="Dirección de entrega" />
            )}

            <button onClick={submitNew} disabled={saving} className={primaryBtn}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : "Crear orden"}
            </button>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function IosGroup({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-slate-50 rounded-2xl overflow-hidden divide-y divide-slate-100">
      {children}
    </div>
  );
}

function IosRow({ label, value, labelClass, onClick }: {
  label: string; value?: string; labelClass?: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="w-full px-4 py-3.5 flex items-center justify-between gap-3 text-left bg-white hover:bg-slate-50 transition-colors">
      <span className={`text-sm font-medium ${labelClass ?? "text-slate-800"}`}>{label}</span>
      <div className="flex items-center gap-2 min-w-0 shrink-0">
        {value && <span className="text-sm text-slate-400 truncate max-w-[150px]">{value}</span>}
        <ChevronRight className="h-4 w-4 text-slate-300" />
      </div>
    </button>
  );
}
