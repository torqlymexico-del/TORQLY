import { useState, useEffect, useCallback } from "react";
import {
  Plus, Trash2, Copy, Check, Users2, Loader2, ShieldCheck,
  UserCog, Pencil, ToggleLeft, ToggleRight, AlertTriangle,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface InviteCode {
  id: number;
  code: string;
  role: string;
  branch: string;
  label: string | null;
  is_active: boolean;
  created_by_name: string | null;
  used_by_name: string | null;
  used_at: string | null;
  created_at: string;
}

interface TeamUser {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  role: string;
  branch: string;
  is_active: boolean;
  weekly_salary: string;
  commission_percentage: string;
}

type Tab = "codes" | "users";

/* ─── Config ──────────────────────────────────────────────────────────────── */

const BRANCHES = [
  { value: "local",       label: "Local" },
  { value: "domicilios",  label: "Domicilios" },
];

const ROLES: { value: string; label: string; color: string }[] = [
  { value: "admin",      label: "Administrador", color: "bg-violet-100 text-violet-700" },
  { value: "supervisor", label: "Supervisor",    color: "bg-blue-100 text-blue-700" },
  { value: "cashier",    label: "Cajero",        color: "bg-emerald-100 text-emerald-700" },
  { value: "operator",   label: "Lavador",       color: "bg-amber-100 text-amber-700" },
];

function roleLabel(role: string) {
  return ROLES.find(r => r.value === role)?.label ?? role;
}
function roleColor(role: string) {
  return ROLES.find(r => r.value === role)?.color ?? "bg-slate-100 text-slate-600";
}
function branchColor(b: string) {
  return b === "domicilios" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600";
}

/* ─── Copy button ─────────────────────────────────────────────────────────── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }
  return (
    <button
      onClick={handleCopy}
      className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
      title="Copiar código"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

/* ─── Component ───────────────────────────────────────────────────────────── */

export default function Team() {
  const { user: me } = useAuth();
  const isAdmin = me?.role === "admin";

  const [tab, setTab] = useState<Tab>("codes");

  /* ── Invite codes state ── */
  const [codes, setCodes]     = useState<InviteCode[]>([]);
  const [codesLoading, setCodesLoading] = useState(false);
  const [codesError, setCodesError]     = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [role, setRole]             = useState("operator");
  const [branch, setBranch]         = useState("local");
  const [label, setLabel]           = useState("");
  const [saving, setSaving]         = useState(false);
  const [formError, setFormError]   = useState("");
  const [deleting, setDeleting]     = useState<number | null>(null);

  /* ── Users state ── */
  const [users, setUsers]           = useState<TeamUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError]     = useState("");

  // Edit user dialog
  const [editOpen, setEditOpen]     = useState(false);
  const [editUser, setEditUser]     = useState<TeamUser | null>(null);
  const [editName, setEditName]     = useState("");
  const [editPhone, setEditPhone]   = useState("");
  const [editEmail, setEditEmail]   = useState("");
  const [editRole, setEditRole]     = useState("operator");
  const [editBranch, setEditBranch] = useState("local");
  const [editSalary, setEditSalary] = useState("");
  const [editCommission, setEditCommission] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError]   = useState("");

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<TeamUser | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  /* ── Load codes ── */
  const loadCodes = useCallback(async () => {
    setCodesLoading(true); setCodesError("");
    try {
      const res = await api.get<InviteCode[]>("/invite-codes/");
      setCodes(res.data);
    } catch {
      setCodesError("Error al cargar los códigos.");
    } finally {
      setCodesLoading(false);
    }
  }, []);

  /* ── Load users ── */
  const loadUsers = useCallback(async () => {
    setUsersLoading(true); setUsersError("");
    try {
      const res = await api.get<TeamUser[]>("/users/");
      setUsers(res.data);
    } catch {
      setUsersError("Error al cargar usuarios.");
    } finally {
      setUsersLoading(false);
    }
  }, []);

  useEffect(() => { loadCodes(); }, [loadCodes]);
  useEffect(() => { if (tab === "users") loadUsers(); }, [tab, loadUsers]);

  /* ── Invite code actions ── */
  async function handleCreate() {
    setSaving(true); setFormError("");
    try {
      await api.post("/invite-codes/", { role, branch, label: label.trim() || null });
      setDialogOpen(false);
      setLabel(""); setRole("operator"); setBranch("local");
      loadCodes();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Error al crear el código.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteCode(id: number) {
    setDeleting(id);
    try {
      await api.delete(`/invite-codes/${id}`);
      loadCodes();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setCodesError(detail ?? "Error al eliminar el código.");
    } finally {
      setDeleting(null);
    }
  }

  /* ── User actions ── */
  function openEdit(u: TeamUser) {
    setEditUser(u);
    setEditName(u.name);
    setEditPhone(u.phone ?? "");
    setEditEmail(u.email ?? "");
    setEditRole(u.role);
    setEditBranch(u.branch);
    setEditSalary(u.weekly_salary ?? "0");
    setEditCommission(u.commission_percentage ?? "0");
    setEditError("");
    setEditOpen(true);
  }

  async function handleEditSave() {
    if (!editUser) return;
    setEditSaving(true); setEditError("");
    try {
      await api.put(`/users/${editUser.id}`, {
        name: editName.trim(),
        phone: editPhone.trim(),
        email: editEmail.trim() || null,
        role: editRole,
        branch: editBranch,
        weekly_salary: parseFloat(editSalary) || 0,
        commission_percentage: parseFloat(editCommission) || 0,
      });
      setEditOpen(false);
      loadUsers();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setEditError(detail ?? "Error al guardar.");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleToggleActive(u: TeamUser) {
    try {
      await api.put(`/users/${u.id}`, { is_active: !u.is_active });
      setUsers(prev => prev.map(x => x.id === u.id ? { ...x, is_active: !u.is_active } : x));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setUsersError(detail ?? "Error al cambiar estado.");
    }
  }

  function confirmDelete(u: TeamUser) {
    setDeleteTarget(u);
    setDeleteConfirmOpen(true);
  }

  async function handleDeleteUser() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/users/${deleteTarget.id}`);
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
      loadUsers();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setUsersError(detail ?? "Error al eliminar usuario.");
      setDeleteConfirmOpen(false);
    } finally {
      setDeleteLoading(false);
    }
  }

  const active = codes.filter(c => c.is_active && !c.used_at);
  const used   = codes.filter(c => c.used_at);

  const inputCls = "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors";

  return (
    <div className="space-y-5 pb-16">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Equipo</h1>
          <p className="text-sm text-slate-400 mt-0.5">Gestión de accesos y miembros</p>
        </div>
        {tab === "codes" && (
          <button
            onClick={() => { setDialogOpen(true); setFormError(""); }}
            className="flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuevo código
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setTab("codes")}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
            tab === "codes" ? "border-slate-900 text-slate-900" : "border-transparent text-slate-400 hover:text-slate-600"
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          Códigos de acceso
        </button>
        {isAdmin && (
          <button
            onClick={() => setTab("users")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab === "users" ? "border-slate-900 text-slate-900" : "border-transparent text-slate-400 hover:text-slate-600"
            }`}
          >
            <UserCog className="h-4 w-4" />
            Usuarios
          </button>
        )}
      </div>

      {/* ══════════════ CÓDIGOS TAB ══════════════ */}
      {tab === "codes" && (
        <>
          {codesError && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{codesError}</div>
          )}

          {codesLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-7 w-7 animate-spin text-slate-300" />
            </div>
          ) : (
            <>
              {/* Active codes */}
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Disponibles ({active.length})
                </p>
                {active.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex flex-col items-center justify-center py-12 text-slate-400">
                    <ShieldCheck className="h-10 w-10 mb-2 opacity-30" />
                    <p className="text-sm">Sin códigos activos. Genera uno para invitar a tu equipo.</p>
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100">
                    {active.map(c => (
                      <div key={c.id} className="px-4 py-3 flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono font-bold text-slate-900 tracking-widest text-base">{c.code}</span>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${roleColor(c.role)}`}>
                              {roleLabel(c.role)}
                            </span>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${branchColor(c.branch)}`}>
                              {c.branch}
                            </span>
                            {c.label && <span className="text-xs text-slate-400 truncate">{c.label}</span>}
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Creado por {c.created_by_name ?? "—"} · {new Date(c.created_at).toLocaleDateString("es-MX")}
                          </p>
                        </div>
                        <CopyButton text={c.code} />
                        <button
                          onClick={() => handleDeleteCode(c.id)}
                          disabled={deleting === c.id}
                          className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                          title="Revocar código"
                        >
                          {deleting === c.id
                            ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            : <Trash2 className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Used codes */}
              {used.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Utilizados ({used.length})
                  </p>
                  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100">
                    {used.map(c => (
                      <div key={c.id} className="px-4 py-3 flex items-center gap-3 opacity-60">
                        <Users2 className="h-4 w-4 text-slate-400 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-slate-500 tracking-widest text-sm">{c.code}</span>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${roleColor(c.role)}`}>
                              {roleLabel(c.role)}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Usado por <strong className="text-slate-600">{c.used_by_name ?? "—"}</strong>
                            {c.used_at && ` · ${new Date(c.used_at).toLocaleDateString("es-MX")}`}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ══════════════ USUARIOS TAB ══════════════ */}
      {tab === "users" && (
        <>
          {usersError && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{usersError}</div>
          )}

          {usersLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-7 w-7 animate-spin text-slate-300" />
            </div>
          ) : users.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex flex-col items-center justify-center py-12 text-slate-400">
              <UserCog className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">Sin usuarios registrados.</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100">
              {users.map(u => (
                <div key={u.id} className={`px-4 py-3 flex items-center gap-3 ${!u.is_active ? "opacity-50" : ""}`}>
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${roleColor(u.role)}`}>
                    {u.name[0]?.toUpperCase() ?? "?"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-900 text-sm">{u.name}</span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${roleColor(u.role)}`}>
                        {roleLabel(u.role)}
                      </span>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${branchColor(u.branch)}`}>
                        {u.branch}
                      </span>
                      {!u.is_active && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-600">
                          Inactivo
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {u.phone ?? "Sin teléfono"}
                      {u.email && <span className="ml-2 truncate max-w-[180px] inline-block align-bottom" title={u.email}> · {u.email}</span>}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => openEdit(u)}
                      className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
                      title="Editar usuario"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    {u.id !== me?.id && (
                      <>
                        <button
                          onClick={() => handleToggleActive(u)}
                          className={`h-7 w-7 flex items-center justify-center rounded-lg transition-colors ${
                            u.is_active
                              ? "hover:bg-amber-50 text-slate-400 hover:text-amber-600"
                              : "hover:bg-emerald-50 text-slate-400 hover:text-emerald-600"
                          }`}
                          title={u.is_active ? "Desactivar usuario" : "Activar usuario"}
                        >
                          {u.is_active
                            ? <ToggleRight className="h-4 w-4" />
                            : <ToggleLeft className="h-4 w-4" />}
                        </button>
                        <button
                          onClick={() => confirmDelete(u)}
                          className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                          title="Eliminar usuario"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Create invite code dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={o => { if (!o) setDialogOpen(false); }}>
        <DialogContent className="max-w-sm rounded-2xl p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-5 pt-5 pb-4 border-b border-slate-100">
            <DialogTitle className="text-base font-semibold">Nuevo código de acceso</DialogTitle>
          </DialogHeader>

          <div className="px-5 py-4 space-y-4">
            {formError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{formError}</div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Rama</label>
              <select className={inputCls} value={branch} onChange={e => setBranch(e.target.value)}>
                {BRANCHES.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Rol</label>
              <select className={inputCls} value={role} onChange={e => setRole(e.target.value)}>
                {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Etiqueta (opcional)</label>
              <input
                className={inputCls}
                placeholder="ej. Para Juan — cajero turno mañana"
                value={label}
                onChange={e => setLabel(e.target.value)}
                maxLength={80}
              />
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-200 px-3 py-2.5 text-xs text-slate-500">
              Código de un solo uso. El destinatario se registrará como <strong>{roleLabel(role)}</strong>.
            </div>
          </div>

          <DialogFooter className="px-5 pb-5 pt-1 flex gap-2">
            <button
              onClick={() => setDialogOpen(false)}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              disabled={saving}
            >
              Cancelar
            </button>
            <button
              onClick={handleCreate}
              disabled={saving}
              className="flex-1 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Generar código
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Edit user dialog ── */}
      <Dialog open={editOpen} onOpenChange={o => { if (!o) setEditOpen(false); }}>
        <DialogContent className="max-w-sm rounded-2xl p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-5 pt-5 pb-4 border-b border-slate-100">
            <DialogTitle className="text-base font-semibold">Editar usuario</DialogTitle>
          </DialogHeader>

          <div className="px-5 py-4 space-y-3 max-h-[70vh] overflow-y-auto">
            {editError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{editError}</div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Nombre</label>
              <input className={inputCls} value={editName} onChange={e => setEditName(e.target.value)} placeholder="Nombre completo" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Teléfono</label>
              <input className={inputCls} value={editPhone} onChange={e => setEditPhone(e.target.value)} placeholder="5551234567" />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Correo (opcional)</label>
              <input className={inputCls} type="email" value={editEmail} onChange={e => setEditEmail(e.target.value)} placeholder="correo@ejemplo.com" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Rol</label>
                <select className={inputCls} value={editRole} onChange={e => setEditRole(e.target.value)}>
                  {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Rama</label>
                <select className={inputCls} value={editBranch} onChange={e => setEditBranch(e.target.value)}>
                  {BRANCHES.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">Sueldo semanal</label>
                <input
                  className={inputCls} type="number" min="0" step="0.01"
                  value={editSalary} onChange={e => setEditSalary(e.target.value)}
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-600">% Comisión</label>
                <input
                  className={inputCls} type="number" min="0" max="100" step="0.1"
                  value={editCommission} onChange={e => setEditCommission(e.target.value)}
                  placeholder="0"
                />
              </div>
            </div>
          </div>

          <DialogFooter className="px-5 pb-5 pt-1 flex gap-2">
            <button
              onClick={() => setEditOpen(false)}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              disabled={editSaving}
            >
              Cancelar
            </button>
            <button
              onClick={handleEditSave}
              disabled={editSaving}
              className="flex-1 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {editSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Guardar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Delete confirm dialog ── */}
      <Dialog open={deleteConfirmOpen} onOpenChange={o => { if (!o) setDeleteConfirmOpen(false); }}>
        <DialogContent className="max-w-sm rounded-2xl p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-5 pt-5 pb-4 border-b border-slate-100">
            <DialogTitle className="text-base font-semibold text-red-700 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Eliminar usuario
            </DialogTitle>
          </DialogHeader>
          <div className="px-5 py-4">
            <p className="text-sm text-slate-700">
              ¿Estás seguro de que quieres eliminar a <strong>{deleteTarget?.name}</strong>? Esta acción no se puede deshacer.
            </p>
            <p className="text-xs text-slate-400 mt-2">
              Si el usuario tiene órdenes o registros asociados, podrías recibir un error. En ese caso, desactívalo en lugar de eliminarlo.
            </p>
          </div>
          <DialogFooter className="px-5 pb-5 pt-1 flex gap-2">
            <button
              onClick={() => setDeleteConfirmOpen(false)}
              className="flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              disabled={deleteLoading}
            >
              Cancelar
            </button>
            <button
              onClick={handleDeleteUser}
              disabled={deleteLoading}
              className="flex-1 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {deleteLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Eliminar
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
