import { useState, useEffect, useCallback } from "react";
import { Search, Plus, Pencil, Trash2, Loader2, Car, Zap, Users, UserPlus, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogFooter,
  DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface Client {
  id: number;
  name: string;
  phone: string;
}

interface Vehicle {
  id: number;
  client_id: number | null;
  brand: string;
  model: string;
  year: number | null;
  color: string | null;
  plates: string | null;
  notes: string | null;
  is_active: boolean;
}

interface VehicleForm {
  client_id: string;
  brand: string;
  model: string;
  year: string;
  color: string;
  plates: string;
  notes: string;
  is_active: boolean;
}

interface ClientForm {
  name: string;
  phone: string;
  email: string;
}

type CreateMode = "select" | "rapida" | "existente" | "nuevo";

function emptyForm(): VehicleForm {
  return { client_id: "", brand: "", model: "", year: "", color: "", plates: "", notes: "", is_active: true };
}

function emptyClientForm(): ClientForm {
  return { name: "", phone: "", email: "" };
}

function formFromVehicle(v: Vehicle): VehicleForm {
  return {
    client_id: v.client_id != null ? String(v.client_id) : "",
    brand:     v.brand,
    model:     v.model,
    year:      v.year != null ? String(v.year) : "",
    color:     v.color ?? "",
    plates:    v.plates ?? "",
    notes:     v.notes ?? "",
    is_active: v.is_active,
  };
}

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-slate-700">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Vehicles({ branch = "local" }: { branch?: string }) {
  const [vehicles, setVehicles]   = useState<Vehicle[]>([]);
  const [clients, setClients]     = useState<Client[]>([]);
  const [loading, setLoading]     = useState(false);
  const [query, setQuery]         = useState("");
  const [error, setError]         = useState("");

  const [dialogOpen, setDialogOpen]     = useState(false);
  const [editTarget, setEditTarget]     = useState<Vehicle | null>(null);
  const [form, setForm]                 = useState<VehicleForm>(emptyForm());
  const [saving, setSaving]             = useState(false);
  const [formError, setFormError]       = useState("");

  // Create wizard
  const [createMode, setCreateMode]     = useState<CreateMode>("select");
  const [clientForm, setClientForm]     = useState<ClientForm>(emptyClientForm());
  const [clientSearch, setClientSearch] = useState("");

  const [deleteTarget, setDeleteTarget] = useState<Vehicle | null>(null);
  const [deleting, setDeleting]         = useState(false);

  /* ── Client name lookup ── */

  const clientMap = new Map(clients.map(c => [c.id, c.name]));

  /* ── Fetch ── */

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [vRes, cRes] = await Promise.all([
        api.get<Vehicle[]>("/vehicles/", { params: { branch } }),
        api.get<Client[]>("/clients/", { params: { branch } }),
      ]);
      setVehicles(vRes.data);
      setClients(cRes.data);
    } catch {
      setError("Error al cargar vehículos.");
    } finally {
      setLoading(false);
    }
  }, [branch]);

  useEffect(() => { load(); }, [load]);

  /* ── Dialog helpers ── */

  function openCreate() {
    setEditTarget(null);
    setForm(emptyForm());
    setClientForm(emptyClientForm());
    setClientSearch("");
    setCreateMode("select");
    setFormError("");
    setDialogOpen(true);
  }

  function openEdit(v: Vehicle) {
    setEditTarget(v);
    setForm(formFromVehicle(v));
    setFormError("");
    setDialogOpen(true);
  }

  function set(field: keyof VehicleForm, value: string | boolean) {
    setForm(f => ({ ...f, [field]: value }));
  }

  function setClient(field: keyof ClientForm, value: string) {
    setClientForm(f => ({ ...f, [field]: value }));
  }

  /* ── Save ── */

  async function handleSave() {
    if (!form.brand.trim() || !form.model.trim()) {
      setFormError("Marca y modelo son obligatorios.");
      return;
    }

    setSaving(true);
    setFormError("");

    try {
      let clientId: number | null = null;

      if (editTarget || createMode === "existente") {
        clientId = form.client_id ? Number(form.client_id) : null;
      } else if (createMode === "nuevo") {
        if (!clientForm.name.trim() || !clientForm.phone.trim()) {
          setFormError("Nombre y teléfono del cliente son obligatorios.");
          setSaving(false);
          return;
        }
        const cRes = await api.post<Client>("/clients/", {
          name:  clientForm.name.trim(),
          phone: clientForm.phone.trim(),
          email: clientForm.email.trim() || null,
          branch,
        });
        clientId = cRes.data.id;
      }

      const payload = {
        client_id: clientId,
        branch,
        brand:     form.brand.trim(),
        model:     form.model.trim(),
        year:      form.year ? Number(form.year) : null,
        color:     form.color.trim() || null,
        plates:    form.plates.trim() || null,
        notes:     form.notes.trim() || null,
        is_active: form.is_active,
      };

      if (editTarget) {
        await api.put(`/vehicles/${editTarget.id}`, payload);
      } else {
        await api.post("/vehicles/", payload);
      }

      setDialogOpen(false);
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Error al guardar.");
    } finally {
      setSaving(false);
    }
  }

  /* ── Delete ── */

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/vehicles/${deleteTarget.id}`);
      setDeleteTarget(null);
      load();
    } catch {
      setError("Error al eliminar el vehículo.");
      setDeleting(false);
    }
  }

  /* ── Filter ── */

  const filtered = vehicles.filter(v => {
    const q = query.toLowerCase();
    const clientName = (v.client_id != null ? (clientMap.get(v.client_id) ?? "") : "").toLowerCase();
    return (
      v.brand.toLowerCase().includes(q) ||
      v.model.toLowerCase().includes(q) ||
      (v.plates ?? "").toLowerCase().includes(q) ||
      clientName.includes(q)
    );
  });

  function vehicleLabel(v: Vehicle) {
    const parts = [v.brand, v.model];
    if (v.year) parts.push(String(v.year));
    return parts.join(" ");
  }

  const filteredClients = clients.filter(c =>
    clientSearch === "" ||
    c.name.toLowerCase().includes(clientSearch.toLowerCase()) ||
    c.phone.includes(clientSearch)
  );

  /* ── Render ── */

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Vehículos</h1>
          <p className="text-sm text-slate-500">{vehicles.length} vehículo(s) registrado(s)</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" />
          Nuevo vehículo
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          className="w-full rounded-md border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          placeholder="Buscar por marca, placas o cliente…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Car className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">{query ? "Sin resultados" : "No hay vehículos registrados"}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                <th className="px-4 py-3 text-left">Vehículo</th>
                <th className="px-4 py-3 text-left">Placas</th>
                <th className="px-4 py-3 text-left">Color</th>
                <th className="px-4 py-3 text-left">Cliente</th>
                <th className="px-4 py-3 text-left">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(v => (
                <tr key={v.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{vehicleLabel(v)}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">{v.plates ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-500 capitalize">{v.color ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-600">{v.client_id ? (clientMap.get(v.client_id) ?? "—") : "Sin cliente"}</td>
                  <td className="px-4 py-3">
                    <Badge variant={v.is_active ? "success" : "secondary"}>
                      {v.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(v)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                        onClick={() => setDeleteTarget(v)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={o => { if (!o) setDialogOpen(false); }}>
        <DialogContent className="max-w-md">

          {editTarget ? (
            /* ──────────────── Edit mode ──────────────── */
            <>
              <DialogHeader>
                <DialogTitle>Editar vehículo</DialogTitle>
              </DialogHeader>

              <div className="space-y-4">
                {formError && (
                  <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{formError}</div>
                )}

                <Field label="Cliente (opcional)">
                  <select
                    className={inputCls}
                    value={form.client_id}
                    onChange={e => set("client_id", e.target.value)}
                  >
                    <option value="">Sin cliente</option>
                    {clients.map(c => (
                      <option key={c.id} value={c.id}>{c.name} — {c.phone}</option>
                    ))}
                  </select>
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Marca" required>
                    <input className={inputCls} value={form.brand} onChange={e => set("brand", e.target.value)} placeholder="Toyota" />
                  </Field>
                  <Field label="Modelo" required>
                    <input className={inputCls} value={form.model} onChange={e => set("model", e.target.value)} placeholder="Corolla" />
                  </Field>
                  <Field label="Año">
                    <input className={inputCls} type="number" min={1950} max={2100} value={form.year} onChange={e => set("year", e.target.value)} placeholder="2022" />
                  </Field>
                  <Field label="Color">
                    <input className={inputCls} value={form.color} onChange={e => set("color", e.target.value)} placeholder="Blanco" />
                  </Field>
                </div>

                <Field label="Placas">
                  <input className={inputCls} value={form.plates} onChange={e => set("plates", e.target.value.toUpperCase())} placeholder="ABC-123" />
                </Field>

                <Field label="Notas">
                  <textarea rows={2} className={`${inputCls} resize-none`} value={form.notes} onChange={e => set("notes", e.target.value)} placeholder="Observaciones opcionales" />
                </Field>

                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.is_active} onChange={e => set("is_active", e.target.checked)} />
                  Vehículo activo
                </label>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancelar</Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Guardar cambios
                </Button>
              </DialogFooter>
            </>

          ) : createMode === "select" ? (
            /* ──────────────── Mode selection ──────────────── */
            <>
              <DialogHeader>
                <DialogTitle>Nuevo vehículo</DialogTitle>
                <DialogDescription>Elige cómo registrar el vehículo</DialogDescription>
              </DialogHeader>

              <div className="grid gap-3 py-2">
                <button
                  className="flex items-start gap-4 rounded-lg border border-slate-200 p-4 text-left hover:border-slate-900 hover:bg-slate-50 transition-colors"
                  onClick={() => setCreateMode("rapida")}
                >
                  <div className="mt-0.5 shrink-0 rounded-md bg-slate-100 p-2">
                    <Zap className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Alta rápida</p>
                    <p className="text-sm text-slate-500">Solo datos del vehículo, sin cliente</p>
                  </div>
                </button>

                <button
                  className="flex items-start gap-4 rounded-lg border border-slate-200 p-4 text-left hover:border-slate-900 hover:bg-slate-50 transition-colors"
                  onClick={() => { setClientSearch(""); setCreateMode("existente"); }}
                >
                  <div className="mt-0.5 shrink-0 rounded-md bg-slate-100 p-2">
                    <Users className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Cliente existente</p>
                    <p className="text-sm text-slate-500">Vincular con un cliente ya registrado</p>
                  </div>
                </button>

                <button
                  className="flex items-start gap-4 rounded-lg border border-slate-200 p-4 text-left hover:border-slate-900 hover:bg-slate-50 transition-colors"
                  onClick={() => setCreateMode("nuevo")}
                >
                  <div className="mt-0.5 shrink-0 rounded-md bg-slate-100 p-2">
                    <UserPlus className="h-5 w-5 text-slate-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Cliente nuevo</p>
                    <p className="text-sm text-slate-500">Registrar cliente y vehículo al mismo tiempo</p>
                  </div>
                </button>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
              </DialogFooter>
            </>

          ) : (
            /* ──────────────── Create form (rapida / existente / nuevo) ──────────────── */
            <>
              <DialogHeader>
                <DialogTitle>
                  <div className="flex items-center gap-2">
                    <button
                      className="rounded p-0.5 hover:bg-slate-100 transition-colors"
                      onClick={() => { setCreateMode("select"); setFormError(""); }}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    {createMode === "rapida" ? "Alta rápida" : createMode === "existente" ? "Cliente existente" : "Cliente nuevo"}
                  </div>
                </DialogTitle>
              </DialogHeader>

              <div className="space-y-4">
                {formError && (
                  <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{formError}</div>
                )}

                {/* ── Client existente: search list ── */}
                {createMode === "existente" && (
                  <div className="space-y-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                      <input
                        className="w-full rounded-md border border-slate-200 pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                        placeholder="Buscar cliente por nombre o teléfono…"
                        value={clientSearch}
                        onChange={e => setClientSearch(e.target.value)}
                      />
                    </div>
                    <div className="max-h-36 overflow-y-auto rounded-md border border-slate-200 divide-y divide-slate-100">
                      {filteredClients.length === 0 ? (
                        <p className="px-3 py-4 text-center text-sm text-slate-400">Sin resultados</p>
                      ) : filteredClients.map(c => (
                        <button
                          key={c.id}
                          className={`w-full px-3 py-2 text-left text-sm transition-colors ${form.client_id === String(c.id) ? "bg-slate-900 text-white" : "hover:bg-slate-50"}`}
                          onClick={() => set("client_id", String(c.id))}
                        >
                          <span className="font-medium">{c.name}</span>
                          <span className={`ml-2 text-xs ${form.client_id === String(c.id) ? "text-slate-300" : "text-slate-400"}`}>{c.phone}</span>
                        </button>
                      ))}
                    </div>
                    {form.client_id && (
                      <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded px-2 py-1">
                        Seleccionado: <strong>{clients.find(c => String(c.id) === form.client_id)?.name}</strong>
                      </p>
                    )}
                  </div>
                )}

                {/* ── Cliente nuevo: name/phone/email fields ── */}
                {createMode === "nuevo" && (
                  <div className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Datos del cliente</p>
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Nombre" required>
                        <input className={inputCls} value={clientForm.name} onChange={e => setClient("name", e.target.value)} placeholder="Juan García" />
                      </Field>
                      <Field label="Teléfono" required>
                        <input className={inputCls} value={clientForm.phone} onChange={e => setClient("phone", e.target.value)} placeholder="55 1234 5678" />
                      </Field>
                    </div>
                    <Field label="Correo (opcional)">
                      <input className={inputCls} type="email" value={clientForm.email} onChange={e => setClient("email", e.target.value)} placeholder="juan@email.com" />
                    </Field>
                  </div>
                )}

                {(createMode === "existente" || createMode === "nuevo") && (
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Datos del vehículo</p>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Marca" required>
                    <input className={inputCls} value={form.brand} onChange={e => set("brand", e.target.value)} placeholder="Toyota" />
                  </Field>
                  <Field label="Modelo" required>
                    <input className={inputCls} value={form.model} onChange={e => set("model", e.target.value)} placeholder="Corolla" />
                  </Field>
                  <Field label="Año">
                    <input className={inputCls} type="number" min={1950} max={2100} value={form.year} onChange={e => set("year", e.target.value)} placeholder="2022" />
                  </Field>
                  <Field label="Color">
                    <input className={inputCls} value={form.color} onChange={e => set("color", e.target.value)} placeholder="Blanco" />
                  </Field>
                </div>

                <Field label="Placas">
                  <input className={inputCls} value={form.plates} onChange={e => set("plates", e.target.value.toUpperCase())} placeholder="ABC-123" />
                </Field>

                <Field label="Notas">
                  <textarea rows={2} className={`${inputCls} resize-none`} value={form.notes} onChange={e => set("notes", e.target.value)} placeholder="Observaciones opcionales" />
                </Field>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancelar</Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Crear vehículo
                </Button>
              </DialogFooter>
            </>
          )}

        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={o => { if (!o) setDeleteTarget(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminar vehículo</DialogTitle>
            <DialogDescription>
              ¿Eliminar <strong>{deleteTarget ? vehicleLabel(deleteTarget) : ""}</strong>?
              Esta acción no se puede deshacer.
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
