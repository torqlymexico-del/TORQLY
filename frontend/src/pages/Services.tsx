import { useState, useEffect, useCallback } from "react";
import { Search, Plus, Pencil, Trash2, Loader2, Wrench, ChevronDown, ChevronRight, Clock, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";
import { cn } from "@/lib/utils";

/* ─── Types ──────────────────────────────────────────────────────────── */

interface Family   { id: number; name: string; color_code: string; sort_order: number; is_active: boolean; }
interface Subfamily{ id: number; family_id: number; name: string; sort_order: number; is_active: boolean; }
interface Service  {
  id: number; name: string; description: string | null;
  base_price: string | number; estimated_duration_minutes: number;
  service_type: string; is_active: boolean; subfamily_id: number | null;
}
interface ServiceForm {
  name: string; description: string; base_price: string;
  estimated_duration_minutes: string; service_type: string;
  is_active: boolean; family_id: string; subfamily_id: string;
}

const SERVICE_TYPES = [
  { value: "lavado",    label: "Lavado"     },
  { value: "detallado", label: "Detallado"  },
  { value: "pulido",    label: "Pulido"     },
  { value: "ceramico",  label: "Cerámico"   },
  { value: "domicilio", label: "A domicilio"},
];

function emptyForm(): ServiceForm {
  return { name: "", description: "", base_price: "0", estimated_duration_minutes: "60", service_type: "lavado", is_active: true, family_id: "", subfamily_id: "" };
}
function formFromService(s: Service, subfamilies: Subfamily[]): ServiceForm {
  const sf = s.subfamily_id ? subfamilies.find(x => x.id === s.subfamily_id) : null;
  return {
    name: s.name, description: s.description ?? "",
    base_price: String(s.base_price), estimated_duration_minutes: String(s.estimated_duration_minutes),
    service_type: s.service_type, is_active: s.is_active,
    family_id: sf ? String(sf.family_id) : "", subfamily_id: s.subfamily_id ? String(s.subfamily_id) : "",
  };
}

const inputCls = "w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 bg-white";

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-slate-700">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function formatDuration(mins: number) {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60), m = mins % 60;
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

function fmt(v: string | number) { return `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`; }

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Services({ branch = "local" }: { branch?: string }) {
  const [families,    setFamilies]    = useState<Family[]>([]);
  const [subfamilies, setSubfamilies] = useState<Subfamily[]>([]);
  const [services,    setServices]    = useState<Service[]>([]);
  const [loading,     setLoading]     = useState(false);
  const [query,       setQuery]       = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [error,       setError]       = useState("");
  const [collapsed,   setCollapsed]   = useState<Set<string>>(new Set());

  const [dialogOpen,    setDialogOpen]    = useState(false);
  const [editTarget,    setEditTarget]    = useState<Service | null>(null);
  const [form,          setForm]          = useState<ServiceForm>(emptyForm());
  const [saving,        setSaving]        = useState(false);
  const [formError,     setFormError]     = useState("");
  const [deleteTarget,  setDeleteTarget]  = useState<Service | null>(null);
  const [deleting,      setDeleting]      = useState(false);

  /* ── Fetch ── */

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [f, sf, s] = await Promise.all([
        api.get<Family[]>("/catalog/families", { params: { branch } }),
        api.get<Subfamily[]>("/catalog/subfamilies", { params: { branch } }),
        api.get<Service[]>("/services-catalog/", { params: { branch } }),
      ]);
      setFamilies(f.data.filter(x => x.is_active).sort((a, b) => a.sort_order - b.sort_order));
      setSubfamilies(sf.data.filter(x => x.is_active).sort((a, b) => a.sort_order - b.sort_order));
      setServices(s.data);
    } catch { setError("Error al cargar datos."); }
    finally  { setLoading(false); }
  }, [branch]);

  useEffect(() => { load(); }, [load]);

  /* ── Helpers ── */

  function openCreate() { setEditTarget(null); setForm(emptyForm()); setFormError(""); setDialogOpen(true); }
  function openEdit(s: Service) { setEditTarget(s); setForm(formFromService(s, subfamilies)); setFormError(""); setDialogOpen(true); }
  function set(field: keyof ServiceForm, value: string | boolean) {
    setForm(f => { const next = { ...f, [field]: value }; if (field === "family_id") next.subfamily_id = ""; return next; });
  }

  const formSubfamilies = form.family_id ? subfamilies.filter(sf => sf.family_id === Number(form.family_id)) : subfamilies;

  async function handleSave() {
    if (!form.name.trim()) { setFormError("El nombre es obligatorio."); return; }
    const duration = Number(form.estimated_duration_minutes);
    if (!duration || duration < 15 || duration > 1440) { setFormError("La duración debe estar entre 15 y 1440 minutos."); return; }
    setSaving(true); setFormError("");
    const payload = {
      branch,
      name: form.name.trim(), description: form.description.trim() || null,
      base_price: Number(form.base_price) || 0, estimated_duration_minutes: duration,
      service_type: form.service_type, is_active: form.is_active,
      subfamily_id: form.subfamily_id ? Number(form.subfamily_id) : null,
    };
    try {
      if (editTarget) await api.put(`/services-catalog/${editTarget.id}`, payload);
      else            await api.post("/services-catalog/", payload);
      setDialogOpen(false); load();
    } catch (err: unknown) {
      setFormError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al guardar.");
    } finally { setSaving(false); }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try { await api.delete(`/services-catalog/${deleteTarget.id}`); setDeleteTarget(null); load(); }
    catch { setError("Error al eliminar."); setDeleting(false); }
  }

  function toggleCollapse(key: string) {
    setCollapsed(prev => { const n = new Set(prev); if (n.has(key)) n.delete(key); else n.add(key); return n; });
  }

  /* ── Grouping ── */

  const q = query.toLowerCase();
  const filteredServices = q
    ? services.filter(s => s.name.toLowerCase().includes(q) || (s.description ?? "").toLowerCase().includes(q))
    : services;

  const subfamilyMap = new Map(subfamilies.map(sf => [sf.id, sf]));
  type GK = number | "none";
  const grouped = new Map<GK, Map<GK, Service[]>>();
  for (const svc of filteredServices) {
    const sf = svc.subfamily_id ? subfamilyMap.get(svc.subfamily_id) : null;
    const fk: GK = sf ? sf.family_id : "none";
    const sk: GK = svc.subfamily_id ?? "none";
    if (!grouped.has(fk)) grouped.set(fk, new Map());
    const g = grouped.get(fk)!;
    if (!g.has(sk)) g.set(sk, []);
    g.get(sk)!.push(svc);
  }

  const orderedFamilyKeys: GK[] = [
    ...families.filter(f => grouped.has(f.id)).map(f => f.id as GK),
    ...(grouped.has("none") ? ["none" as GK] : []),
  ];

  const autocompleteMatches = query.length > 0
    ? services.filter(s => s.name.toLowerCase().includes(query.toLowerCase()) || (s.description ?? "").toLowerCase().includes(query.toLowerCase())).slice(0, 8)
    : [];

  /* ── Render ── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Catálogo de servicios</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {services.length} servicio{services.length !== 1 ? "s" : ""} en {families.length} familia{families.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={openCreate} className="shrink-0">
          <Plus className="h-4 w-4 mr-2" /> Nuevo servicio
        </Button>
      </div>

      {error && <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 bg-white"
          placeholder="Buscar por nombre o descripción…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setSearchFocused(true)}
          onBlur={() => setTimeout(() => setSearchFocused(false), 150)}
          autoComplete="off"
        />
        {searchFocused && autocompleteMatches.length > 0 && (
          <div className="absolute z-30 top-full mt-1 w-full bg-white rounded-lg border border-slate-200 shadow-xl overflow-hidden">
            {autocompleteMatches.map(s => (
              <button
                key={s.id}
                onMouseDown={() => { setQuery(s.name); setSearchFocused(false); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 text-left border-b border-slate-50 last:border-0"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{s.name}</p>
                  {s.description && <p className="text-xs text-slate-400 truncate">{s.description}</p>}
                </div>
                <span className="text-sm font-semibold text-slate-700 shrink-0">{fmt(s.base_price)}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-300" /></div>
      ) : filteredServices.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Wrench className="h-14 w-14 mb-4 opacity-30" />
          <p className="text-base font-medium">{query ? "Sin resultados para tu búsqueda" : "No hay servicios en el catálogo"}</p>
          {!query && <p className="text-sm mt-1">Crea el primer servicio con el botón de arriba</p>}
        </div>
      ) : (
        <div className="space-y-3">
          {orderedFamilyKeys.map(fKey => {
            const family      = fKey !== "none" ? families.find(f => f.id === fKey) : null;
            const sfMap       = grouped.get(fKey)!;
            const familyLabel = family?.name ?? "Sin familia";
            const color       = family?.color_code ?? "#94a3b8";
            const fCollapsed  = collapsed.has(`f-${fKey}`);
            const total       = Array.from(sfMap.values()).reduce((s, a) => s + a.length, 0);

            const orderedSfKeys: GK[] = [
              ...subfamilies.filter(sf => sf.family_id === fKey && sfMap.has(sf.id)).map(sf => sf.id as GK),
              ...(sfMap.has("none") ? ["none" as GK] : []),
            ];

            return (
              <div key={String(fKey)} className="rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                {/* ── Family header ── */}
                <button
                  onClick={() => toggleCollapse(`f-${fKey}`)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left transition-colors hover:brightness-95"
                  style={{ backgroundColor: `${color}18`, borderLeft: `4px solid ${color}` }}
                >
                  <div className="flex-1 flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <span className="font-bold text-slate-900 text-base">{familyLabel}</span>
                    <span
                      className="text-xs font-semibold px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: `${color}30`, color }}
                    >
                      {total}
                    </span>
                  </div>
                  {fCollapsed
                    ? <ChevronRight className="h-5 w-5 text-slate-500 shrink-0" />
                    : <ChevronDown  className="h-5 w-5 text-slate-500 shrink-0" />}
                </button>

                {/* ── Subfamilies ── */}
                {!fCollapsed && orderedSfKeys.map(sfKey => {
                  const subfamily   = sfKey !== "none" ? subfamilyMap.get(sfKey as number) : null;
                  const sfServices  = sfMap.get(sfKey)!;
                  const sfLabel     = subfamily?.name ?? "Sin subfamilia";
                  const sfCollapsed = collapsed.has(`sf-${sfKey}`);

                  return (
                    <div key={String(sfKey)} className="border-t border-slate-100">
                      {/* Subfamily sub-header */}
                      <button
                        onClick={() => toggleCollapse(`sf-${sfKey}`)}
                        className="w-full flex items-center gap-2 px-6 py-3 bg-white hover:bg-slate-50 transition-colors text-left"
                      >
                        {sfCollapsed
                          ? <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                          : <ChevronDown  className="h-4 w-4 text-slate-400 shrink-0" />}
                        <span className="text-sm font-semibold text-slate-700">{sfLabel}</span>
                        <span className="ml-auto text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full font-medium">
                          {sfServices.length}
                        </span>
                      </button>

                      {/* Service rows */}
                      {!sfCollapsed && (
                        <div className="divide-y divide-slate-100">
                          {sfServices.map(s => (
                            <div
                              key={s.id}
                              className={cn(
                                "flex items-center gap-4 px-8 py-3.5 transition-colors",
                                s.is_active ? "hover:bg-slate-50" : "opacity-60 hover:bg-slate-50"
                              )}
                            >
                              {/* Name + description */}
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold text-slate-900">{s.name}</p>
                                {s.description && (
                                  <p className="text-sm text-slate-500 mt-0.5 truncate max-w-sm">{s.description}</p>
                                )}
                              </div>

                              {/* Duration */}
                              <div className="hidden sm:flex items-center gap-1.5 text-slate-500 text-sm shrink-0">
                                <Clock className="h-3.5 w-3.5" />
                                {formatDuration(s.estimated_duration_minutes)}
                              </div>

                              {/* Type */}
                              <div className="hidden md:flex items-center gap-1.5 text-slate-500 text-sm shrink-0">
                                <Tag className="h-3.5 w-3.5" />
                                <span className="capitalize">{s.service_type}</span>
                              </div>

                              {/* Status */}
                              <Badge variant={s.is_active ? "success" : "secondary"} className="shrink-0 text-xs hidden sm:flex">
                                {s.is_active ? "Activo" : "Inactivo"}
                              </Badge>

                              {/* Price */}
                              <p className="font-bold text-lg text-slate-900 shrink-0 w-24 text-right">
                                {fmt(s.base_price)}
                              </p>

                              {/* Actions */}
                              <div className="flex items-center gap-1 shrink-0">
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500 hover:text-slate-900" onClick={() => openEdit(s)}>
                                  <Pencil className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                  variant="ghost" size="icon"
                                  className="h-8 w-8 text-slate-400 hover:text-red-600 hover:bg-red-50"
                                  onClick={() => setDeleteTarget(s)}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Create / Edit dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={o => { if (!o) setDialogOpen(false); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editTarget ? "Editar servicio" : "Nuevo servicio"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-1">
            {formError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{formError}</div>
            )}
            <Field label="Nombre" required>
              <input className={inputCls} value={form.name} onChange={e => set("name", e.target.value)} placeholder="Lavado completo" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Familia">
                <select className={inputCls} value={form.family_id} onChange={e => set("family_id", e.target.value)}>
                  <option value="">Sin familia</option>
                  {families.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </Field>
              <Field label="Subfamilia">
                <select className={inputCls} value={form.subfamily_id} onChange={e => set("subfamily_id", e.target.value)} disabled={!form.family_id}>
                  <option value="">Sin subfamilia</option>
                  {formSubfamilies.map(sf => <option key={sf.id} value={sf.id}>{sf.name}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Tipo de servicio" required>
              <select className={inputCls} value={form.service_type} onChange={e => set("service_type", e.target.value)}>
                {SERVICE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Precio base ($)">
                <input type="number" min="0" step="0.01" className={inputCls} value={form.base_price} onChange={e => set("base_price", e.target.value)} placeholder="0.00" />
              </Field>
              <Field label="Duración (min)">
                <input type="number" min="15" max="1440" step="15" className={inputCls} value={form.estimated_duration_minutes} onChange={e => set("estimated_duration_minutes", e.target.value)} placeholder="60" />
              </Field>
            </div>
            <Field label="Descripción">
              <textarea rows={2} className={cn(inputCls, "resize-none")} value={form.description} onChange={e => set("description", e.target.value)} placeholder="Detalles del servicio (opcional)" />
            </Field>
            {editTarget && (
              <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <input type="checkbox" checked={form.is_active} onChange={e => set("is_active", e.target.checked)} className="rounded" />
                <span className="text-slate-700">Servicio activo</span>
              </label>
            )}
          </div>
          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editTarget ? "Guardar cambios" : "Crear servicio"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete confirmation ── */}
      <Dialog open={!!deleteTarget} onOpenChange={o => { if (!o) setDeleteTarget(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminar servicio</DialogTitle>
            <DialogDescription>
              ¿Eliminar <strong>{deleteTarget?.name}</strong>? Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
