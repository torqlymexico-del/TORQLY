import { useState, useEffect, useCallback } from "react";
import { Plus, Trash2, Copy, Check, Users2, Loader2, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface InviteCode {
  id: number;
  code: string;
  role: string;
  label: string | null;
  is_active: boolean;
  created_by_name: string | null;
  used_by_name: string | null;
  used_at: string | null;
  created_at: string;
}

/* ─── Role config ─────────────────────────────────────────────────────────── */

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
  const [codes, setCodes]     = useState<InviteCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  // Create dialog
  const [dialogOpen, setDialogOpen] = useState(false);
  const [role, setRole]             = useState("operator");
  const [label, setLabel]           = useState("");
  const [saving, setSaving]         = useState(false);
  const [formError, setFormError]   = useState("");

  // Delete
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<InviteCode[]>("/invite-codes/");
      setCodes(res.data);
    } catch {
      setError("Error al cargar los códigos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleCreate() {
    setSaving(true); setFormError("");
    try {
      await api.post("/invite-codes/", { role, label: label.trim() || null });
      setDialogOpen(false);
      setLabel(""); setRole("operator");
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setFormError(detail ?? "Error al crear el código.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    setDeleting(id);
    try {
      await api.delete(`/invite-codes/${id}`);
      load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Error al eliminar el código.");
    } finally {
      setDeleting(null);
    }
  }

  const active = codes.filter(c => c.is_active && !c.used_at);
  const used   = codes.filter(c => c.used_at);

  const inputCls = "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors";

  return (
    <div className="space-y-6 pb-16">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Equipo</h1>
          <p className="text-sm text-slate-400 mt-0.5">Genera códigos de acceso para nuevos miembros</p>
        </div>
        <button
          onClick={() => { setDialogOpen(true); setFormError(""); }}
          className="flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nuevo código
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-7 w-7 animate-spin text-slate-300" />
        </div>
      ) : (
        <>
          {/* ── Active codes ── */}
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
                        {c.label && <span className="text-xs text-slate-400 truncate">{c.label}</span>}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Creado por {c.created_by_name ?? "—"} · {new Date(c.created_at).toLocaleDateString("es-MX")}
                      </p>
                    </div>
                    <CopyButton text={c.code} />
                    <button
                      onClick={() => handleDelete(c.id)}
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

          {/* ── Used codes ── */}
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

      {/* ── Create dialog ── */}
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
              <label className="text-xs font-medium text-slate-600">Rol</label>
              <select
                className={inputCls}
                value={role}
                onChange={e => setRole(e.target.value)}
              >
                {ROLES.map(r => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
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
              El código generado es de un solo uso. La persona que lo reciba podrá registrarse con el rol de <strong>{roleLabel(role)}</strong>.
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
    </div>
  );
}
