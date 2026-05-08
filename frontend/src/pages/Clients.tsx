import { useState, useEffect, useCallback } from "react";
import { Search, Plus, Pencil, Trash2, Loader2, Users } from "lucide-react";
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
  email: string | null;
  address: string | null;
  notes: string | null;
  is_active: boolean;
}

interface ClientForm {
  name: string;
  phone: string;
  email: string;
  address: string;
  notes: string;
  is_active: boolean;
}

function emptyForm(): ClientForm {
  return { name: "", phone: "", email: "", address: "", notes: "", is_active: true };
}

function formFromClient(c: Client): ClientForm {
  return {
    name: c.name,
    phone: c.phone,
    email: c.email ?? "",
    address: c.address ?? "",
    notes: c.notes ?? "",
    is_active: c.is_active,
  };
}

/* ─── Field component ────────────────────────────────────────────────── */

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

const inputCls = "w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900";

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Clients({ branch = "local" }: { branch?: string }) {
  const [clients, setClients]     = useState<Client[]>([]);
  const [loading, setLoading]     = useState(false);
  const [query, setQuery]         = useState("");
  const [error, setError]         = useState("");

  // Dialog state
  const [dialogOpen, setDialogOpen]   = useState(false);
  const [editTarget, setEditTarget]   = useState<Client | null>(null);
  const [form, setForm]               = useState<ClientForm>(emptyForm());
  const [saving, setSaving]           = useState(false);
  const [formError, setFormError]     = useState("");

  // Delete dialog
  const [deleteTarget, setDeleteTarget] = useState<Client | null>(null);
  const [deleting, setDeleting]         = useState(false);

  /* ── Fetch ── */

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<Client[]>("/clients/", { params: { branch } });
      setClients(res.data);
    } catch {
      setError("Error al cargar clientes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  /* ── Dialog helpers ── */

  function openCreate() {
    setEditTarget(null);
    setForm(emptyForm());
    setFormError("");
    setDialogOpen(true);
  }

  function openEdit(c: Client) {
    setEditTarget(c);
    setForm(formFromClient(c));
    setFormError("");
    setDialogOpen(true);
  }

  function set(field: keyof ClientForm, value: string | boolean) {
    setForm(f => ({ ...f, [field]: value }));
  }

  /* ── Save ── */

  async function handleSave() {
    if (!form.name.trim() || !form.phone.trim()) {
      setFormError("Nombre y teléfono son obligatorios.");
      return;
    }
    setSaving(true);
    setFormError("");
    const payload = {
      name:      form.name.trim(),
      phone:     form.phone.trim(),
      email:     form.email.trim() || null,
      address:   form.address.trim() || null,
      notes:     form.notes.trim() || null,
      is_active: form.is_active,
      branch,
    };
    try {
      if (editTarget) {
        await api.put(`/clients/${editTarget.id}`, payload);
      } else {
        await api.post("/clients/", payload);
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
      await api.delete(`/clients/${deleteTarget.id}`);
      setDeleteTarget(null);
      load();
    } catch {
      setError("Error al eliminar el cliente.");
      setDeleting(false);
    }
  }

  /* ── Filter ── */

  const filtered = clients.filter(c => {
    const q = query.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.phone.includes(q) ||
      (c.email ?? "").toLowerCase().includes(q)
    );
  });

  /* ── Render ── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Clientes</h1>
          <p className="text-sm text-slate-500">{clients.length} cliente(s) registrado(s)</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" />
          Nuevo cliente
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          className="w-full rounded-md border border-slate-200 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          placeholder="Buscar por nombre, teléfono o correo…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Users className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">{query ? "Sin resultados" : "No hay clientes registrados"}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-medium text-slate-500">
                <th className="px-4 py-3 text-left">Nombre</th>
                <th className="px-4 py-3 text-left">Teléfono</th>
                <th className="px-4 py-3 text-left">Correo</th>
                <th className="px-4 py-3 text-left">Estado</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(c => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{c.name}</td>
                  <td className="px-4 py-3 text-slate-600">{c.phone}</td>
                  <td className="px-4 py-3 text-slate-500">{c.email ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Badge variant={c.is_active ? "success" : "secondary"}>
                      {c.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(c)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                        onClick={() => setDeleteTarget(c)}
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
          <DialogHeader>
            <DialogTitle>{editTarget ? "Editar cliente" : "Nuevo cliente"}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {formError && (
              <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{formError}</div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nombre" required>
                <input className={inputCls} value={form.name} onChange={e => set("name", e.target.value)} placeholder="Juan Pérez" />
              </Field>
              <Field label="Teléfono" required>
                <input className={inputCls} value={form.phone} onChange={e => set("phone", e.target.value)} placeholder="5551234567" />
              </Field>
            </div>
            <Field label="Correo electrónico">
              <input className={inputCls} type="email" value={form.email} onChange={e => set("email", e.target.value)} placeholder="juan@correo.com" />
            </Field>
            <Field label="Dirección">
              <input className={inputCls} value={form.address} onChange={e => set("address", e.target.value)} placeholder="Calle, ciudad" />
            </Field>
            <Field label="Notas">
              <textarea
                rows={2}
                className={`${inputCls} resize-none`}
                value={form.notes}
                onChange={e => set("notes", e.target.value)}
                placeholder="Observaciones opcionales"
              />
            </Field>
            {editTarget && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={e => set("is_active", e.target.checked)}
                  className="rounded"
                />
                Cliente activo
              </label>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Cancelar</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editTarget ? "Guardar cambios" : "Crear cliente"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={o => { if (!o) setDeleteTarget(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminar cliente</DialogTitle>
            <DialogDescription>
              ¿Eliminar a <strong>{deleteTarget?.name}</strong>? Esta acción no se puede deshacer.
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
