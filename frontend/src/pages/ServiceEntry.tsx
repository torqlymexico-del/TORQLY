import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Check, ChevronRight, Search, X, Zap, UserCheck, UserPlus } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type VehicleType = "sedan" | "suv" | "camioneta" | "van" | "moto" | "otro";
const VEHICLE_TYPES: { value: VehicleType; label: string }[] = [
  { value: "sedan", label: "Sedán" },
  { value: "suv",   label: "SUV" },
  { value: "camioneta", label: "Camioneta / Pickup" },
  { value: "van",   label: "Van / Minivan" },
  { value: "moto",  label: "Motocicleta" },
  { value: "otro",  label: "Otro" },
];

interface Client { id: number; name: string; phone: string; }
interface Vehicle { id: number; client_id: number | null; brand: string; model: string; type: string | null; color: string | null; plates: string | null; year: number | null; }
interface ServiceItem { id: number; name: string; base_price: string; description: string | null; is_active: boolean; subfamily_id: number | null; }
interface Family { id: number; name: string; color_code: string; sort_order: number; is_active: boolean; }
interface Subfamily { id: number; family_id: number; name: string; sort_order: number; is_active: boolean; }
interface Operator { id: number; name: string; commission_percentage: string; }
interface CartItem { catalog_id: number; name: string; unit_price: number; quantity: number; }

type Mode = "quick" | "existing" | "new";
type VehicleSub = "select" | "new";

// ─── Autocomplete data ─────────────────────────────────────────────────────────

const CAR_BRANDS = [
  "Acura","Alfa Romeo","Audi","BMW","Buick","Cadillac","Chevrolet","Chrysler",
  "Citroën","Dodge","Ferrari","Fiat","Ford","GMC","Honda","Hyundai","Infiniti",
  "Isuzu","Jaguar","Jeep","Kia","Land Rover","Lexus","Lincoln","Maserati",
  "Mazda","Mercedes-Benz","Mini","Mitsubishi","Nissan","Peugeot","Porsche",
  "Ram","Renault","Seat","Subaru","Suzuki","Tesla","Toyota","Volkswagen","Volvo",
];

const CAR_COLORS_PRESET = [
  { label: "Blanco",      hex: "#f8fafc", dark: false },
  { label: "Negro",       hex: "#0f172a", dark: true  },
  { label: "Gris",        hex: "#94a3b8", dark: false },
  { label: "Plata",       hex: "#cbd5e1", dark: false },
  { label: "Rojo",        hex: "#ef4444", dark: true  },
  { label: "Azul",        hex: "#3b82f6", dark: true  },
  { label: "Azul marino", hex: "#1e3a5f", dark: true  },
  { label: "Verde",       hex: "#16a34a", dark: true  },
  { label: "Café",        hex: "#92400e", dark: true  },
  { label: "Beige",       hex: "#d4b483", dark: false },
  { label: "Amarillo",    hex: "#eab308", dark: false },
  { label: "Naranja",     hex: "#f97316", dark: true  },
  { label: "Dorado",      hex: "#b45309", dark: true  },
  { label: "Morado",      hex: "#7c3aed", dark: true  },
];

const _cy = new Date().getFullYear();
const RECENT_YEARS = Array.from({ length: 14 }, (_, i) => String(_cy - i));

// ─── AutocompleteInput ─────────────────────────────────────────────────────────

function highlightMatch(text: string, query: string) {
  if (!query.trim()) return <span>{text}</span>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <span>{text}</span>;
  return (
    <span>
      {text.slice(0, idx)}
      <span className="font-bold text-slate-900">{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </span>
  );
}

interface AcProps {
  value: string;
  onChange: (v: string) => void;
  suggestions: string[];
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  id?: string;
}

function AutocompleteInput({ value, onChange, suggestions, placeholder, className, autoFocus, id }: AcProps) {
  const [open, setOpen] = useState(false);
  const filtered = value.length >= 1
    ? suggestions.filter(s => s.toLowerCase().includes(value.toLowerCase())).slice(0, 9)
    : [];
  return (
    <div className="relative">
      <input
        id={id}
        className={className}
        value={value}
        autoComplete="off"
        autoFocus={autoFocus}
        placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && filtered.length > 0 && (
        <div className="absolute z-30 top-full mt-0.5 w-full bg-white rounded-md border border-slate-200 shadow-lg max-h-52 overflow-y-auto">
          {filtered.map(s => (
            <button
              key={s}
              type="button"
              onMouseDown={() => { onChange(s); setOpen(false); }}
              className="w-full text-left px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              {highlightMatch(s, value)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const STEPS = ["Modo", "Cliente", "Servicios", "Lavadores", "Confirmar"];

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:opacity-60";
const labelCls = "block text-sm font-medium text-slate-700 mb-1";

function fmt(v: string | number) {
  return Number(v).toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ServiceEntry({ branch = "local" }: { branch?: string }) {
  const navigate = useNavigate();

  const [clients, setClients] = useState<Client[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);
  const [subfamilies, setSubfamilies] = useState<Subfamily[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [activeFamilyId, setActiveFamilyId] = useState<number | null>(null);

  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<Mode | null>(null);

  // Step 2
  const [clientId, setClientId] = useState<number | null>(null);
  const [clientSearch, setClientSearch] = useState("");
  const [vehicleSub, setVehicleSub] = useState<VehicleSub>("select");
  const [vehicleId, setVehicleId] = useState<number | null>(null);
  const [newClientName, setNewClientName] = useState("");
  const [newClientPhone, setNewClientPhone] = useState("");
  const [newClientEmail, setNewClientEmail] = useState("");
  const [vBrand, setVBrand] = useState("");
  const [vModel, setVModel] = useState("");
  const [vType, setVType] = useState<VehicleType>("sedan");
  const [vColor, setVColor] = useState("");
  const [vPlates, setVPlates] = useState("");
  const [vYear, setVYear] = useState("");

  // Step 3
  const [cart, setCart] = useState<CartItem[]>([]);
  const [svcSearch, setSvcSearch] = useState("");

  // Step 4
  const [washers, setWashers] = useState<{ user_id: number; name: string; commission_percent: number }[]>([]);
  const [orderNotes, setOrderNotes] = useState("");

  // Submit
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    const p = { branch };
    Promise.all([
      api.get<Client[]>("/clients/", { params: p }),
      api.get<Vehicle[]>("/vehicles/", { params: p }),
      api.get<ServiceItem[]>("/services-catalog/", { params: p }),
      api.get<Family[]>("/catalog/families", { params: p }),
      api.get<Subfamily[]>("/catalog/subfamilies", { params: p }),
      api.get<Operator[]>("/payroll/operators"),
    ]).then(([c, v, s, f, sf, o]) => {
      setClients(c.data);
      setVehicles(v.data);
      setServices(s.data.filter((x: ServiceItem) => x.is_active));
      setFamilies(f.data.filter((x: Family) => x.is_active).sort((a: Family, b: Family) => a.sort_order - b.sort_order));
      setSubfamilies(sf.data.filter((x: Subfamily) => x.is_active).sort((a: Subfamily, b: Subfamily) => a.sort_order - b.sort_order));
      setOperators(o.data);
    }).catch(() => {});
  }, [branch]);

  // ─── Validation ────────────────────────────────────────────────────────────

  function step2Valid(): boolean {
    if (mode === "quick") {
      if (clientId && vehicleSub === "select") return !!vehicleId;
      return vBrand.trim().length > 0 && vModel.trim().length > 0 && vColor.trim().length > 0;
    }
    if (mode === "existing") {
      if (!clientId) return false;
      if (vehicleSub === "select") return !!vehicleId;
      return vBrand.trim().length > 0 && vModel.trim().length > 0 && vColor.trim().length > 0;
    }
    if (mode === "new") {
      return (
        newClientName.trim().length >= 2 &&
        newClientPhone.trim().length >= 7 &&
        vBrand.trim().length > 0 &&
        vModel.trim().length > 0 &&
        vColor.trim().length > 0
      );
    }
    return false;
  }

  // ─── Navigation ────────────────────────────────────────────────────────────

  function selectMode(m: Mode) {
    setMode(m);
    setClientId(null); setClientSearch(""); setVehicleSub("select"); setVehicleId(null);
    setNewClientName(""); setNewClientPhone(""); setNewClientEmail("");
    setVBrand(""); setVModel(""); setVType("sedan"); setVColor(""); setVPlates(""); setVYear("");
    setStep(2);
  }

  // ─── Cart helpers ──────────────────────────────────────────────────────────

  function addToCart(svc: ServiceItem) {
    setCart(prev => {
      if (prev.find(i => i.catalog_id === svc.id)) return prev;
      return [...prev, { catalog_id: svc.id, name: svc.name, unit_price: Number(svc.base_price), quantity: 1 }];
    });
  }

  function removeFromCart(catalog_id: number) {
    setCart(prev => prev.filter(i => i.catalog_id !== catalog_id));
  }

  // ─── Washer helpers ────────────────────────────────────────────────────────

  function toggleWasher(op: Operator) {
    const id = op.id;
    if (washers.find(w => w.user_id === id)) {
      setWashers(prev => prev.filter(w => w.user_id !== id));
    } else if (washers.length < 2) {
      setWashers(prev => [...prev, { user_id: id, name: op.name, commission_percent: Number(op.commission_percentage) }]);
    }
  }

  // ─── Submit ────────────────────────────────────────────────────────────────

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      let finalClientId: number | null = clientId;
      let finalVehicleId: number | null = vehicleId;

      if (mode === "new") {
        const { data } = await api.post("/clients/", {
          name: newClientName.trim(),
          phone: newClientPhone.trim(),
          email: newClientEmail.trim() || null,
          branch,
        });
        finalClientId = data.id;
      }

      // Create vehicle whenever brand is filled (client_id can be null in quick mode)
      if (vBrand.trim().length > 0) {
        const { data } = await api.post("/vehicles/", {
          client_id: finalClientId,
          branch,
          brand: vBrand.trim(),
          model: vModel.trim(),
          type: vType,
          color: vColor.trim() || null,
          plates: vPlates.trim() || null,
          year: vYear ? parseInt(vYear) : null,
        });
        finalVehicleId = data.id;
      }

      const { data: order } = await api.post("/orders/", {
        client_id: finalClientId,
        vehicle_id: finalVehicleId,
        branch,
        items: cart.map(i => ({ catalog_id: i.catalog_id, unit_price: i.unit_price, quantity: i.quantity })),
        notes: orderNotes.trim() || null,
      });

      if (washers.length > 0) {
        await api.put(`/orders/${order.id}/washers`, {
          washers: washers.map(w => ({ user_id: w.user_id, commission_percent: w.commission_percent })),
        });
      }

      navigate(branch === "domicilios" ? "/domicilios/orders" : "/orders");
    } catch (e: any) {
      setSubmitError(e?.response?.data?.detail ?? "Error al crear la orden");
    } finally {
      setSubmitting(false);
    }
  }

  // ─── Derived ───────────────────────────────────────────────────────────────

  const filteredClients = clients.filter(c =>
    c.name.toLowerCase().includes(clientSearch.toLowerCase()) || c.phone.includes(clientSearch)
  );
  const clientVehicles = clientId ? vehicles.filter(v => v.client_id === clientId) : [];
  // (filteredServices is now computed inside renderStep3 to support family grouping)
  const cartTotal = cart.reduce((sum, i) => sum + i.unit_price * i.quantity, 0);

  // ─── Steps ─────────────────────────────────────────────────────────────────

  function StepIndicator() {
    return (
      <div className="flex items-center gap-1 mb-6 flex-wrap">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = n < step;
          const active = n === step;
          return (
            <div key={label} className="flex items-center">
              <div className={cn(
                "flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold border-2 transition-colors",
                done ? "bg-slate-900 border-slate-900 text-white"
                     : active ? "border-slate-900 text-slate-900 bg-white"
                     : "border-slate-300 text-slate-400 bg-white"
              )}>
                {done ? <Check className="h-3.5 w-3.5" /> : n}
              </div>
              <span className={cn("ml-1 text-xs hidden sm:inline", active ? "text-slate-900 font-medium" : "text-slate-400")}>
                {label}
              </span>
              {i < STEPS.length - 1 && <ChevronRight className="h-4 w-4 text-slate-300 mx-1" />}
            </div>
          );
        })}
      </div>
    );
  }

  function renderStep1() {
    const cards = [
      { mode: "quick" as Mode, icon: Zap,       title: "Alta rápida",       desc: "Sin registrar cliente. Ingresa el auto directo.", color: "#f59e0b" },
      { mode: "existing" as Mode, icon: UserCheck, title: "Cliente existente", desc: "Busca un cliente ya registrado en el sistema.",  color: "#3b82f6" },
      { mode: "new" as Mode,      icon: UserPlus,  title: "Cliente nuevo",     desc: "Registra un nuevo cliente y su vehículo.",        color: "#10b981" },
    ];
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cards.map(({ mode: m, icon: Icon, title, desc, color }) => (
          <button
            key={m}
            onClick={() => selectMode(m)}
            className="flex flex-col items-center gap-4 rounded-xl border-2 border-slate-200 p-6 hover:border-slate-300 transition-all group text-left"
            style={{ ["--accent" as string]: color }}
          >
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all"
              style={{ backgroundColor: `${color}18`, color }}
            >
              <Icon className="h-7 w-7" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-slate-900 text-base">{title}</p>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">{desc}</p>
            </div>
            <div
              className="mt-auto w-full rounded-lg py-2 text-xs font-semibold text-center transition-colors"
              style={{ backgroundColor: `${color}15`, color }}
            >
              Seleccionar
            </div>
          </button>
        ))}
      </div>
    );
  }

  function renderStep2() {
    const selectedClientObj = clientId ? clients.find(c => c.id === clientId) : null;

    const modeConfig = {
      quick:    { icon: Zap,       label: "Alta rápida",       color: "#f59e0b" },
      existing: { icon: UserCheck, label: "Cliente existente", color: "#3b82f6" },
      new:      { icon: UserPlus,  label: "Cliente nuevo",     color: "#10b981" },
    } as const;
    const mc = mode ? modeConfig[mode] : null;

    function VehiclePicker({ required }: { required: boolean }) {
      const label = required ? "Vehículo *" : "Vehículo (opcional)";
      return (
        <div>
          <label className={labelCls}>{label}</label>
          <div className="flex gap-2 mb-3">
            {(["select", "new"] as VehicleSub[]).map(sub => (
              <button
                key={sub}
                onClick={() => {
                  setVehicleSub(sub);
                  setVehicleId(null);
                  setVBrand(""); setVModel(""); setVType("sedan"); setVColor(""); setVPlates(""); setVYear("");
                }}
                className={cn(
                  "flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors",
                  vehicleSub === sub
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-200 text-slate-600 hover:border-slate-400"
                )}
              >
                {sub === "select" ? "Vehículo existente" : "Nuevo vehículo"}
              </button>
            ))}
          </div>
          {vehicleSub === "select" && (
            clientVehicles.length === 0
              ? <p className="text-sm text-slate-400 text-center py-4 rounded-md border border-dashed border-slate-200">
                  Sin vehículos registrados.{" "}
                  <button className="text-slate-700 underline" onClick={() => setVehicleSub("new")}>Agregar uno</button>
                </p>
              : <div className="space-y-2">
                  {clientVehicles.map(v => {
                    const detail = [v.plates, v.color, v.year ? String(v.year) : null].filter(Boolean).join(" · ");
                    return (
                      <button
                        key={v.id}
                        onClick={() => setVehicleId(vehicleId === v.id ? null : v.id)}
                        className={cn(
                          "w-full flex items-center justify-between rounded-md border px-3 py-2 text-sm transition-colors",
                          vehicleId === v.id
                            ? "border-slate-900 bg-slate-900 text-white"
                            : "border-slate-200 hover:border-slate-400"
                        )}
                      >
                        <span className="font-medium">{v.brand} {v.model}</span>
                        <span className={cn("text-xs", vehicleId === v.id ? "text-slate-300" : "text-slate-400")}>
                          {detail || "—"}
                        </span>
                      </button>
                    );
                  })}
                </div>
          )}
        </div>
      );
    }

    // Suggestions derived from existing vehicle history
    const dbBrands = [...new Set(vehicles.map(v => v.brand).filter(Boolean))];
    const allBrandSuggestions = [...new Set([...CAR_BRANDS, ...dbBrands])].sort((a, b) =>
      a.localeCompare(b, "es", { sensitivity: "base" })
    );
    const modelSuggestions = vBrand.trim()
      ? [...new Set(vehicles.filter(v => v.brand.toLowerCase() === vBrand.toLowerCase()).map(v => v.model).filter(Boolean))]
      : [...new Set(vehicles.map(v => v.model).filter(Boolean))];
    const colorSuggestions = [
      ...CAR_COLORS_PRESET.map(c => c.label),
      ...new Set(vehicles.map(v => v.color).filter(Boolean) as string[]),
    ].filter((v, i, a) => a.findIndex(x => x.toLowerCase() === v.toLowerCase()) === i);

    function NewVehicleFields({ optional }: { optional: boolean }) {
      return (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="h-px flex-1 bg-slate-100" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Vehículo{optional ? " (opcional)" : ""}
            </span>
            <div className="h-px flex-1 bg-slate-100" />
          </div>
          <div className="grid grid-cols-2 gap-3">

            {/* Marca */}
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Marca{!optional ? " *" : ""}</label>
              <AutocompleteInput
                className={inputCls}
                value={vBrand}
                onChange={v => { setVBrand(v); setVModel(""); }}
                suggestions={allBrandSuggestions}
                placeholder="Toyota"
              />
            </div>

            {/* Modelo */}
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Modelo{!optional ? " *" : ""}</label>
              <AutocompleteInput
                className={inputCls}
                value={vModel}
                onChange={setVModel}
                suggestions={modelSuggestions}
                placeholder="Corolla"
              />
            </div>

            {/* Tipo */}
            <div className="col-span-2">
              <label className="text-xs text-slate-500 mb-1 block">Tipo de vehículo</label>
              <div className="grid grid-cols-3 gap-1.5">
                {VEHICLE_TYPES.map(t => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setVType(t.value)}
                    className={cn(
                      "rounded-md border px-2 py-1.5 text-xs font-medium transition-colors text-center",
                      vType === t.value
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 text-slate-600 hover:border-slate-400"
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Color */}
            <div className="col-span-2">
              <label className="text-xs text-slate-500 mb-1 block">Color{!optional ? " *" : ""}</label>
              <AutocompleteInput
                className={inputCls}
                value={vColor}
                onChange={setVColor}
                suggestions={colorSuggestions}
                placeholder="Blanco"
              />
              {/* Color swatches */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {CAR_COLORS_PRESET.map(c => (
                  <button
                    key={c.label}
                    type="button"
                    title={c.label}
                    onClick={() => setVColor(c.label)}
                    className={cn(
                      "flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-all",
                      vColor.toLowerCase() === c.label.toLowerCase()
                        ? "border-slate-900 ring-2 ring-slate-900 ring-offset-1"
                        : "border-slate-200 hover:border-slate-400"
                    )}
                  >
                    <span className="w-3 h-3 rounded-full shrink-0 border border-slate-300/60" style={{ backgroundColor: c.hex }} />
                    <span className="text-slate-700">{c.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Placas */}
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Placas</label>
              <input
                className={inputCls}
                value={vPlates}
                onChange={e => setVPlates(e.target.value.toUpperCase())}
                placeholder="ABC-123"
              />
            </div>

            {/* Año */}
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Año</label>
              <input
                className={inputCls}
                inputMode="numeric"
                maxLength={4}
                value={vYear}
                onChange={e => setVYear(e.target.value.replace(/\D/g, ""))}
                placeholder={String(_cy)}
              />
              <div className="flex flex-wrap gap-1 mt-1.5">
                {RECENT_YEARS.slice(0, 8).map(y => (
                  <button
                    key={y}
                    type="button"
                    onClick={() => setVYear(vYear === y ? "" : y)}
                    className={cn(
                      "rounded border px-1.5 py-0.5 text-xs transition-colors",
                      vYear === y
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 text-slate-500 hover:border-slate-400"
                    )}
                  >
                    {y}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>
      );
    }

    return (
      <div className="space-y-5">

        {/* Mode badge */}
        {mc && (
          <div className="flex items-center justify-between">
            <span
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full"
              style={{ backgroundColor: `${mc.color}18`, color: mc.color }}
            >
              <mc.icon className="h-3.5 w-3.5" />
              {mc.label}
            </span>
            <button
              onClick={() => setStep(1)}
              className="text-xs text-slate-400 hover:text-slate-700 underline underline-offset-2 transition-colors"
            >
              Cambiar modo
            </button>
          </div>
        )}

        {/* ── MODO: CLIENTE EXISTENTE ─────────────────────────────── */}
        {mode === "existing" && (
          <>
            <div>
              <label className={labelCls}>Cliente *</label>
              {selectedClientObj ? (
                <div className="flex items-center gap-2 rounded-md border border-slate-900 bg-slate-900 text-white px-3 py-2.5 text-sm">
                  <UserCheck className="h-4 w-4 shrink-0" />
                  <span className="flex-1 font-medium">{selectedClientObj.name}</span>
                  <span className="text-slate-300 text-xs mr-1">{selectedClientObj.phone}</span>
                  <button
                    onClick={() => { setClientId(null); setClientSearch(""); setVehicleId(null); setVehicleSub("select"); }}
                    className="text-slate-400 hover:text-white transition-colors"
                    title="Cambiar cliente"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <>
                  <div className="relative mb-2">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      autoFocus
                      className={inputCls + " pl-9"}
                      placeholder="Buscar por nombre o teléfono…"
                      value={clientSearch}
                      onChange={e => { setClientSearch(e.target.value); setClientId(null); }}
                    />
                  </div>
                  <div className="max-h-48 overflow-y-auto rounded-md border border-slate-200 divide-y">
                    {filteredClients.length === 0
                      ? <p className="p-3 text-sm text-slate-400 text-center">
                          {clientSearch ? "Sin resultados" : "Escribe para buscar un cliente…"}
                        </p>
                      : filteredClients.slice(0, 20).map(c => (
                          <button
                            key={c.id}
                            onClick={() => { setClientId(c.id); setVehicleSub("select"); setVehicleId(null); }}
                            className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-slate-50 transition-colors"
                          >
                            <span className="font-medium text-slate-800">{c.name}</span>
                            <span className="text-xs text-slate-400">{c.phone}</span>
                          </button>
                        ))
                    }
                  </div>
                </>
              )}
            </div>

            {clientId && VehiclePicker({ required: true })}
            {clientId && vehicleSub === "new" && NewVehicleFields({ optional: false })}
          </>
        )}

        {/* ── MODO: CLIENTE NUEVO ─────────────────────────────────── */}
        {mode === "new" && (
          <>
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-px flex-1 bg-slate-100" />
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Datos del cliente</span>
                <div className="h-px flex-1 bg-slate-100" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Nombre *</label>
                  <input
                    autoFocus
                    className={inputCls}
                    value={newClientName}
                    onChange={e => setNewClientName(e.target.value)}
                    placeholder="Nombre completo"
                  />
                  {newClientName.length > 0 && newClientName.trim().length < 2 && (
                    <p className="text-xs text-red-500 mt-1">Mínimo 2 caracteres</p>
                  )}
                </div>
                <div>
                  <label className={labelCls}>Teléfono *</label>
                  <input
                    className={inputCls}
                    value={newClientPhone}
                    onChange={e => setNewClientPhone(e.target.value)}
                    placeholder="612-123-4567"
                  />
                  {newClientPhone.length > 0 && newClientPhone.trim().length < 7 && (
                    <p className="text-xs text-red-500 mt-1">Mínimo 7 dígitos</p>
                  )}
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Correo electrónico</label>
                  <input
                    className={inputCls}
                    type="email"
                    value={newClientEmail}
                    onChange={e => setNewClientEmail(e.target.value)}
                    placeholder="cliente@correo.com"
                  />
                </div>
              </div>
            </div>
            {NewVehicleFields({ optional: false })}
          </>
        )}

        {/* ── MODO: ALTA RÁPIDA ───────────────────────────────────── */}
        {mode === "quick" && (
          <>
            <div>
              <label className={labelCls}>Cliente (opcional)</label>
              {selectedClientObj ? (
                <div className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2.5 text-sm">
                  <Check className="h-4 w-4 text-green-600 shrink-0" />
                  <span className="flex-1 font-medium text-slate-800">{selectedClientObj.name}</span>
                  <span className="text-xs text-slate-400 mr-1">{selectedClientObj.phone}</span>
                  <button
                    onClick={() => { setClientId(null); setClientSearch(""); setVehicleId(null); setVehicleSub("select"); }}
                    className="text-slate-300 hover:text-slate-600 transition-colors"
                    title="Quitar cliente"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div>
                  <div className="relative mb-1">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                    <input
                      className={inputCls + " pl-9"}
                      placeholder="Buscar cliente existente…"
                      value={clientSearch}
                      onChange={e => setClientSearch(e.target.value)}
                    />
                  </div>
                  {clientSearch && filteredClients.length > 0 && (
                    <div className="max-h-32 overflow-y-auto rounded-md border border-slate-200 divide-y">
                      {filteredClients.slice(0, 8).map(c => (
                        <button
                          key={c.id}
                          onClick={() => { setClientId(c.id); setClientSearch(""); setVehicleSub("select"); setVehicleId(null); }}
                          className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-slate-50"
                        >
                          <span className="font-medium text-slate-800">{c.name}</span>
                          <span className="text-xs text-slate-400">{c.phone}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  {clientSearch && filteredClients.length === 0 && (
                    <p className="text-xs text-slate-400 mt-1 px-1">Sin resultados</p>
                  )}
                </div>
              )}
            </div>

            {/* Con cliente seleccionado: elegir entre vehículo existente o nuevo */}
            {clientId && VehiclePicker({ required: false })}
            {clientId && vehicleSub === "new" && NewVehicleFields({ optional: false })}

            {/* Sin cliente: campos de vehículo requeridos */}
            {!clientId && NewVehicleFields({ optional: false })}
          </>
        )}

      </div>
    );
  }

  function renderStep3() {
    const sfMap = new Map(subfamilies.map(sf => [sf.id, sf]));

    const visibleServices = svcSearch.trim()
      ? services.filter(s => s.name.toLowerCase().includes(svcSearch.toLowerCase()))
      : activeFamilyId
        ? services.filter(s => {
            const sf = s.subfamily_id ? sfMap.get(s.subfamily_id) : null;
            return sf ? sf.family_id === activeFamilyId : false;
          })
        : services;

    type GKey = number | "none";
    const bySf = new Map<GKey, ServiceItem[]>();
    for (const svc of visibleServices) {
      const key: GKey = svc.subfamily_id ?? "none";
      if (!bySf.has(key)) bySf.set(key, []);
      bySf.get(key)!.push(svc);
    }
    const orderedSfKeys: GKey[] = [
      ...subfamilies.filter(sf => bySf.has(sf.id)).map(sf => sf.id as GKey),
      ...(bySf.has("none") ? ["none" as GKey] : []),
    ];

    return (
      <div className="space-y-3">

        {/* ── Barra de búsqueda ──────────────────────────────────────── */}
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400 pointer-events-none" />
          <input
            className="w-full rounded-lg border-2 border-slate-200 pl-9 pr-4 py-2.5 text-sm font-medium focus:outline-none focus:border-slate-900 transition-colors"
            placeholder="Buscar servicio…"
            value={svcSearch}
            autoComplete="off"
            onChange={e => { setSvcSearch(e.target.value); if (e.target.value) setActiveFamilyId(null); }}
          />
          {svcSearch && (
            <button
              onClick={() => setSvcSearch("")}
              className="absolute right-3 top-3 text-slate-300 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* ── Filtro de familias ─────────────────────────────────────── */}
        {!svcSearch && families.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveFamilyId(null)}
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-semibold border-2 transition-all",
                activeFamilyId === null
                  ? "bg-slate-900 border-slate-900 text-white shadow-sm"
                  : "border-slate-200 text-slate-500 hover:border-slate-400 hover:text-slate-800"
              )}
            >
              Todos
            </button>
            {families.map(f => {
              const isActive = activeFamilyId === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => setActiveFamilyId(isActive ? null : f.id)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold border-2 transition-all"
                  style={isActive
                    ? { backgroundColor: f.color_code, borderColor: f.color_code, color: "#fff", boxShadow: `0 2px 8px ${f.color_code}55` }
                    : { borderColor: "#e2e8f0", color: "#475569" }
                  }
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: isActive ? "rgba(255,255,255,0.6)" : f.color_code }}
                  />
                  {f.name}
                </button>
              );
            })}
          </div>
        )}

        {/* ── Lista de servicios ─────────────────────────────────────── */}
        <div className="space-y-2">
          {orderedSfKeys.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-12">Sin resultados</p>
          )}
          {orderedSfKeys.map(sfKey => {
            const subfamily = sfKey !== "none" ? sfMap.get(sfKey as number) : null;
            const sfServices = bySf.get(sfKey)!;
            const parentFamily = subfamily ? families.find(f => f.id === subfamily.family_id) : null;
            const familyColor = parentFamily?.color_code ?? "#334155";

            return (
              <div key={String(sfKey)} className="space-y-1.5">
                {subfamily?.name && (
                  <div className="flex items-center gap-2 pt-2 px-1">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: familyColor }} />
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">{subfamily.name}</span>
                  </div>
                )}

                {sfServices.map(svc => {
                  const inCart = !!cart.find(i => i.catalog_id === svc.id);
                  return (
                    <button
                      key={svc.id}
                      className="w-full flex items-center justify-between px-4 py-3.5 rounded-xl border-2 text-left transition-all hover:shadow-sm"
                      style={inCart
                        ? { borderColor: familyColor, backgroundColor: familyColor + "12" }
                        : { borderColor: "#e2e8f0", backgroundColor: "#fff" }
                      }
                      onClick={() => inCart ? removeFromCart(svc.id) : addToCart(svc)}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-base text-slate-900 leading-snug">{svc.name}</p>
                        {svc.description && (
                          <p className="text-xs text-slate-400 mt-0.5 leading-snug">{svc.description}</p>
                        )}
                      </div>
                      <div className="ml-4 shrink-0 flex items-center gap-3">
                        <p className="text-lg font-bold" style={{ color: familyColor }}>{fmt(svc.base_price)}</p>
                        <div
                          className="w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all shrink-0"
                          style={inCart
                            ? { backgroundColor: familyColor, borderColor: familyColor }
                            : { borderColor: "#cbd5e1" }
                          }
                        >
                          {inCart && <Check className="h-3.5 w-3.5 text-white" />}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* ── Total ─────────────────────────────────────────────────── */}
        {cart.length > 0 && (
          <div className="flex items-center justify-between rounded-xl bg-slate-900 text-white px-5 py-3.5">
            <span className="text-sm text-slate-400">
              {cart.length} servicio{cart.length !== 1 ? "s" : ""} seleccionado{cart.length !== 1 ? "s" : ""}
            </span>
            <span className="text-xl font-bold">{fmt(cartTotal)}</span>
          </div>
        )}
      </div>
    );
  }

  function renderStep4() {
    const washerColors = ["#6366f1", "#10b981"]; // indigo para el 1°, emerald para el 2°

    return (
      <div className="space-y-4">

        {/* ── Lavadores ─────────────────────────────────────────────── */}
        <p className="text-sm text-slate-500">
          Selecciona hasta <strong>2 lavadores</strong> (opcional).
        </p>

        {operators.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-10 border-2 border-dashed border-slate-200 rounded-xl">
            Sin operadores registrados
          </p>
        ) : (
          <div className="space-y-2.5">
            {operators.map(op => {
              const washerIdx = washers.findIndex(w => w.user_id === op.id);
              const selected = washerIdx !== -1;
              const maxed = !selected && washers.length >= 2;
              const accentColor = selected ? washerColors[washerIdx] ?? washerColors[0] : null;

              return (
                <button
                  key={op.id}
                  onClick={() => toggleWasher(op)}
                  disabled={maxed}
                  className={cn(
                    "w-full flex items-center gap-4 rounded-xl border-2 px-5 py-4 text-left transition-all",
                    selected  ? "shadow-md"
                    : maxed   ? "border-slate-100 bg-slate-50 text-slate-400 cursor-not-allowed opacity-50"
                              : "border-slate-200 hover:border-slate-300 hover:shadow-sm bg-white"
                  )}
                  style={selected && accentColor ? {
                    borderColor: accentColor,
                    backgroundColor: accentColor + "10",
                  } : {}}
                >
                  {/* Avatar */}
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold shrink-0 transition-all"
                    style={selected && accentColor
                      ? { backgroundColor: accentColor, color: "#fff" }
                      : { backgroundColor: "#f1f5f9", color: "#64748b" }
                    }
                  >
                    {op.name[0].toUpperCase()}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      "font-bold text-base leading-tight",
                      selected ? "text-slate-900" : maxed ? "text-slate-400" : "text-slate-800"
                    )}>
                      {op.name}
                    </p>
                    <p className="text-sm mt-0.5" style={{ color: selected && accentColor ? accentColor : "#94a3b8" }}>
                      Comisión: <strong>{Number(op.commission_percentage)}%</strong>
                    </p>
                  </div>

                  {/* Estado */}
                  {selected ? (
                    <div
                      className="flex items-center gap-1.5 shrink-0 rounded-full px-3 py-1.5 text-xs font-bold"
                      style={{ backgroundColor: accentColor!, color: "#fff" }}
                    >
                      <Check className="h-3.5 w-3.5" />
                      {washerIdx === 0 ? "Principal" : "Asistente"}
                    </div>
                  ) : maxed ? (
                    <span className="text-xs text-slate-400 shrink-0">Límite</span>
                  ) : (
                    <div className="w-8 h-8 rounded-full border-2 border-slate-200 shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Resumen lavadores */}
        {washers.length > 0 && (
          <div className="flex items-center gap-3 rounded-xl px-4 py-3 border-2" style={{ borderColor: washerColors[0] + "40", backgroundColor: washerColors[0] + "08" }}>
            <div className="flex -space-x-2">
              {washers.map((w, i) => (
                <div
                  key={w.user_id}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white border-2 border-white"
                  style={{ backgroundColor: washerColors[i] ?? washerColors[0] }}
                >
                  {w.name[0].toUpperCase()}
                </div>
              ))}
            </div>
            <p className="text-sm font-semibold text-slate-700">
              {washers.map(w => w.name).join(" + ")}
            </p>
          </div>
        )}

        {/* Notas */}
        <div>
          <label className={labelCls}>Notas de la orden (opcional)</label>
          <textarea
            className={inputCls + " resize-none"}
            rows={2}
            value={orderNotes}
            onChange={e => setOrderNotes(e.target.value)}
            placeholder="Observaciones, instrucciones especiales…"
          />
        </div>
      </div>
    );
  }

  function renderStep5() {
    const selectedClient = clientId ? clients.find(c => c.id === clientId) : null;
    const selectedVehicle = vehicleId ? vehicles.find(v => v.id === vehicleId) : null;

    const summaryRows = [
      {
        label: "Cliente",
        value: mode === "new"
          ? `${newClientName} · ${newClientPhone} (nuevo)`
          : selectedClient
          ? `${selectedClient.name} · ${selectedClient.phone}`
          : "Sin cliente (alta rápida)",
      },
      {
        label: "Vehículo",
        value: selectedVehicle
          ? `${selectedVehicle.brand} ${selectedVehicle.model}${selectedVehicle.type ? ` · ${selectedVehicle.type}` : ""}${selectedVehicle.plates ? ` · ${selectedVehicle.plates}` : ""}`
          : vBrand
          ? `${vBrand} ${vModel} · ${VEHICLE_TYPES.find(t => t.value === vType)?.label ?? vType}${vColor ? ` · ${vColor}` : ""}${vPlates ? ` · ${vPlates}` : ""} (nuevo)`
          : "Sin vehículo",
      },
      {
        label: "Lavadores",
        value: washers.length === 0
          ? "Sin asignar"
          : washers.map(w => `${w.name} (${w.commission_percent}%)`).join(", "),
      },
    ];

    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 bg-slate-900 text-white">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-0.5">Resumen de la orden</p>
            <p className="text-2xl font-bold">{fmt(cartTotal)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{cart.reduce((s, i) => s + i.quantity, 0)} servicio{cart.reduce((s, i) => s + i.quantity, 0) !== 1 ? "s" : ""}</p>
          </div>

          {summaryRows.map(row => (
            <div key={row.label} className="px-4 py-3 border-t border-slate-100">
              <p className="text-xs text-slate-400 mb-0.5 font-medium uppercase tracking-wide">{row.label}</p>
              <p className="text-sm font-medium text-slate-900">{row.value}</p>
            </div>
          ))}

          <div className="px-4 py-3 border-t border-slate-100">
            <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wide">Servicios</p>
            <div className="space-y-1.5">
              {cart.map(i => (
                <div key={i.catalog_id} className="flex justify-between items-center text-sm">
                  <span className="text-slate-700 truncate max-w-xs">{i.name}{i.quantity > 1 ? ` ×${i.quantity}` : ""}</span>
                  <span className="font-semibold text-slate-900 ml-3 shrink-0">{fmt(i.unit_price * i.quantity)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {submitError && (
          <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex items-start gap-2">
            <X className="h-4 w-4 shrink-0 mt-0.5" />
            {submitError}
          </div>
        )}
      </div>
    );
  }

  // ─── Main render ───────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto pb-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-900">Alta de vehículo</h1>
        <p className="text-sm text-slate-500 mt-0.5">Registra una nueva orden de servicio</p>
      </div>

      <StepIndicator />

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
        {step === 5 && renderStep5()}
      </div>

      {/* ── Barra de navegación sticky ──────────────────────────────────── */}
      {step >= 2 && (
        <div className="sticky bottom-0 z-10 mt-4 bg-slate-50 pb-2">
          <div className="flex gap-3 bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3">
            <Button
              variant="outline"
              className="flex-1 h-11"
              onClick={() => setStep(s => s - 1)}
            >
              Atrás
            </Button>
            {step <= 4 ? (
              <Button
                className="flex-2 h-11 px-8"
                onClick={() => setStep(s => s + 1)}
                disabled={step === 2 ? !step2Valid() : step === 3 ? cart.length === 0 : false}
              >
                Siguiente
              </Button>
            ) : (
              <Button
                className="flex-2 h-11 px-8 bg-emerald-600 hover:bg-emerald-700"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? "Creando orden…" : "Confirmar y crear orden"}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
