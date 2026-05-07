import { useState, useEffect, useCallback } from "react";
import {
  Plus, Pencil, Trash2, Zap, CheckCircle, XCircle, AlertCircle,
  Clock, Loader2, ChevronDown, ChevronUp, Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import api from "@/lib/api";

/* ─── Types ──────────────────────────────────────────────────────────────── */

type Provider =
  | "whatsapp_meta"
  | "google_calendar"
  | "google_sheets"
  | "clickup"
  | "meta_business"
  | "custom";

interface Account {
  id: number;
  provider: Provider;
  name: string;
  description: string | null;
  status: "active" | "inactive" | "error" | "expired";
  is_default: boolean;
  suffix: string | null;
  last_connected_at: string | null;
  last_used_at: string | null;
  config: Record<string, string | null>;
  last_error: string | null;
}

/* ─── Provider metadata ──────────────────────────────────────────────────── */

interface ProviderMeta {
  label: string;
  description: string;
  color: string;
  icon: string;
  credentialFields: Field[];
  configFields: Field[];
}

interface Field {
  key: string;
  label: string;
  placeholder?: string;
  required?: boolean;
  secret?: boolean;
  textarea?: boolean;
  hint?: string;
}

const PROVIDERS: Record<Provider, ProviderMeta> = {
  whatsapp_meta: {
    label: "WhatsApp Cloud API",
    description: "Envío de mensajes y notificaciones vía WhatsApp Business.",
    color: "bg-green-100 text-green-700 border-green-200",
    icon: "💬",
    credentialFields: [
      { key: "access_token", label: "Access Token", required: true, secret: true, placeholder: "EAAGm…" },
      { key: "verify_token", label: "Verify Token", placeholder: "mi-token-secreto" },
      { key: "webhook_secret", label: "Webhook Secret", secret: true, placeholder: "opcional" },
    ],
    configFields: [
      { key: "phone_number_id", label: "Phone Number ID", required: true, placeholder: "1234567890" },
      { key: "business_account_id", label: "Business Account ID", placeholder: "opcional" },
      { key: "api_version", label: "API Version", placeholder: "v20.0" },
    ],
  },
  google_calendar: {
    label: "Google Calendar",
    description: "Sincronización de citas con Google Calendar.",
    color: "bg-blue-100 text-blue-700 border-blue-200",
    icon: "📅",
    credentialFields: [
      { key: "credentials_json", label: "Service Account JSON", secret: true, textarea: true, placeholder: '{"type":"service_account",...}', hint: "Pega el JSON de cuenta de servicio, o usa los campos OAuth abajo." },
      { key: "client_id", label: "Client ID (OAuth)", placeholder: "opcional si usas Service Account" },
      { key: "client_secret", label: "Client Secret (OAuth)", secret: true, placeholder: "opcional" },
      { key: "refresh_token", label: "Refresh Token (OAuth)", secret: true, placeholder: "opcional" },
    ],
    configFields: [
      { key: "calendar_id", label: "Calendar ID", placeholder: "primary" },
    ],
  },
  google_sheets: {
    label: "Google Sheets",
    description: "Exportación de datos a hojas de cálculo de Google.",
    color: "bg-emerald-100 text-emerald-700 border-emerald-200",
    icon: "📊",
    credentialFields: [
      { key: "credentials_json", label: "Service Account JSON", secret: true, textarea: true, placeholder: '{"type":"service_account",...}' },
      { key: "client_id", label: "Client ID (OAuth)", placeholder: "opcional" },
      { key: "client_secret", label: "Client Secret (OAuth)", secret: true, placeholder: "opcional" },
      { key: "refresh_token", label: "Refresh Token (OAuth)", secret: true, placeholder: "opcional" },
    ],
    configFields: [
      { key: "spreadsheet_id", label: "Spreadsheet ID", required: true, placeholder: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms" },
      { key: "calendar_id", label: "Calendar ID", placeholder: "primary" },
    ],
  },
  clickup: {
    label: "ClickUp",
    description: "Creación automática de tareas en ClickUp.",
    color: "bg-purple-100 text-purple-700 border-purple-200",
    icon: "✅",
    credentialFields: [
      { key: "api_token", label: "API Token", required: true, secret: true, placeholder: "pk_…" },
      { key: "webhook_secret", label: "Webhook Secret", secret: true, placeholder: "opcional" },
    ],
    configFields: [
      { key: "list_id", label: "List ID", required: true, placeholder: "901200000" },
      { key: "team_id", label: "Team ID", placeholder: "opcional" },
      { key: "space_id", label: "Space ID", placeholder: "opcional" },
      { key: "folder_id", label: "Folder ID", placeholder: "opcional" },
    ],
  },
  meta_business: {
    label: "Meta Business",
    description: "Gestión de Meta Business Suite (anuncios, páginas, Instagram).",
    color: "bg-indigo-100 text-indigo-700 border-indigo-200",
    icon: "🏢",
    credentialFields: [
      { key: "access_token", label: "Access Token", required: true, secret: true, placeholder: "EAAGm…" },
    ],
    configFields: [
      { key: "business_id", label: "Business ID", required: true, placeholder: "123456789" },
      { key: "app_id", label: "App ID", placeholder: "opcional" },
      { key: "ad_account_id", label: "Ad Account ID", placeholder: "act_123…" },
      { key: "page_id", label: "Page ID", placeholder: "opcional" },
      { key: "api_version", label: "API Version", placeholder: "v20.0" },
    ],
  },
  custom: {
    label: "Custom / Otro",
    description: "Integración personalizada con endpoint propio.",
    color: "bg-slate-100 text-slate-700 border-slate-200",
    icon: "🔗",
    credentialFields: [
      { key: "secret_value", label: "Secret / API Key", secret: true, placeholder: "sk-…" },
    ],
    configFields: [
      { key: "custom_endpoint", label: "Endpoint URL", placeholder: "https://api.ejemplo.com/webhook" },
    ],
  },
};

const PROVIDER_ORDER: Provider[] = [
  "whatsapp_meta",
  "google_calendar",
  "google_sheets",
  "clickup",
  "meta_business",
  "custom",
];

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

function statusBadge(status: Account["status"]) {
  const map = {
    active:   { label: "Activo",   cls: "bg-emerald-100 text-emerald-700", Icon: CheckCircle },
    inactive: { label: "Inactivo", cls: "bg-slate-100 text-slate-600",    Icon: XCircle },
    error:    { label: "Error",    cls: "bg-red-100 text-red-700",         Icon: AlertCircle },
    expired:  { label: "Expirado", cls: "bg-amber-100 text-amber-700",     Icon: Clock },
  };
  const { label, cls, Icon } = map[status] ?? map.inactive;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

function relativeTime(iso: string | null) {
  if (!iso) return null;
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2)  return "hace un momento";
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `hace ${hrs} h`;
  return `hace ${Math.floor(hrs / 24)} días`;
}

/* ─── Form dialog ─────────────────────────────────────────────────────────── */

function AccountForm({
  provider,
  existing,
  onSave,
  onClose,
}: {
  provider: Provider;
  existing: Account | null;
  onSave: (data: Record<string, string>) => Promise<void>;
  onClose: () => void;
}) {
  const meta = PROVIDERS[provider];
  const allFields = [...meta.credentialFields, ...meta.configFields];
  const initial: Record<string, string> = { name: existing?.name ?? "", description: existing?.description ?? "" };
  allFields.forEach(f => { initial[f.key] = ""; });

  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(key: string, value: string) {
    setForm(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave({ ...form, provider });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al guardar.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  function renderField(f: Field) {
    const val = form[f.key] ?? "";
    const hint = existing && f.secret ? `Deja en blanco para conservar el valor actual` : f.hint;
    return (
      <div key={f.key} className="space-y-1">
        <label className="block text-xs font-medium text-slate-700">
          {f.label}
          {f.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        {f.textarea ? (
          <textarea
            rows={4}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-slate-900 resize-y"
            placeholder={f.placeholder}
            value={val}
            onChange={e => set(f.key, e.target.value)}
          />
        ) : (
          <input
            type={f.secret ? "password" : "text"}
            className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
            placeholder={f.placeholder}
            value={val}
            onChange={e => set(f.key, e.target.value)}
          />
        )}
        {hint && <p className="text-xs text-slate-400">{hint}</p>}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label className="block text-xs font-medium text-slate-700">Nombre <span className="text-red-500">*</span></label>
        <input
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          placeholder={`Ej: ${meta.label} Principal`}
          value={form.name}
          onChange={e => set("name", e.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <label className="block text-xs font-medium text-slate-700">Descripción</label>
        <input
          className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
          placeholder="Opcional"
          value={form.description}
          onChange={e => set("description", e.target.value)}
        />
      </div>

      {meta.credentialFields.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Credenciales</p>
          {meta.credentialFields.map(renderField)}
        </div>
      )}

      {meta.configFields.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Configuración</p>
          {meta.configFields.map(renderField)}
        </div>
      )}

      {error && <p className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</p>}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose} disabled={saving}>Cancelar</Button>
        <Button type="submit" disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : null}
          {existing ? "Guardar cambios" : "Conectar"}
        </Button>
      </DialogFooter>
    </form>
  );
}

/* ─── Account card ───────────────────────────────────────────────────────── */

function AccountCard({
  account,
  onEdit,
  onTest,
  onDeactivate,
  onSetDefault,
}: {
  account: Account;
  onEdit: () => void;
  onTest: () => void;
  onDeactivate: () => void;
  onSetDefault: () => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.post<{ ok: boolean; message: string }>(`/integrations/accounts/${account.id}/test`);
      setTestResult(res.data);
    } catch {
      setTestResult({ ok: false, message: "Error al probar la conexión." });
    } finally {
      setTesting(false);
      onTest();
    }
  }

  return (
    <div className={`rounded-lg border bg-white p-4 space-y-3 ${account.status === "error" ? "border-red-200" : "border-slate-200"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-900 text-sm truncate">{account.name}</span>
            {account.is_default && (
              <span className="inline-flex items-center gap-0.5 text-xs text-amber-600 font-medium">
                <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                Default
              </span>
            )}
            {statusBadge(account.status)}
          </div>
          {account.description && <p className="text-xs text-slate-500 mt-0.5">{account.description}</p>}
          <div className="flex flex-wrap gap-3 mt-1 text-xs text-slate-400">
            {account.suffix && <span>Token: …{account.suffix}</span>}
            {account.last_connected_at && <span>Conectado {relativeTime(account.last_connected_at)}</span>}
            {!account.last_connected_at && <span>Nunca probado</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {!account.is_default && account.status === "active" && (
            <Button variant="ghost" size="icon" className="h-7 w-7" title="Marcar como default" onClick={onSetDefault}>
              <Star className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-7 w-7" title="Editar" onClick={onEdit}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          {account.status !== "inactive" && (
            <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500 hover:text-red-700" title="Desactivar" onClick={onDeactivate}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {account.last_error && (
        <p className="text-xs bg-red-50 text-red-700 rounded px-2 py-1 border border-red-100 break-all">
          {account.last_error}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Button size="sm" variant="outline" className="h-7 text-xs gap-1.5" onClick={handleTest} disabled={testing}>
          {testing ? <Loader2 className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
          Probar conexión
        </Button>
        {testResult && (
          <span className={`text-xs flex items-center gap-1 ${testResult.ok ? "text-emerald-600" : "text-red-600"}`}>
            {testResult.ok ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
            {testResult.message}
          </span>
        )}
      </div>
    </div>
  );
}

/* ─── Provider section ───────────────────────────────────────────────────── */

function ProviderSection({
  provider,
  accounts,
  onReload,
}: {
  provider: Provider;
  accounts: Account[];
  onReload: () => void;
}) {
  const meta = PROVIDERS[provider];
  const [open, setOpen] = useState(accounts.length > 0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [confirmDeactivate, setConfirmDeactivate] = useState<Account | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  const active = accounts.filter(a => a.status !== "inactive");

  async function handleSave(data: Record<string, string>) {
    if (editing) {
      await api.put(`/integrations/accounts/${editing.id}`, data);
    } else {
      await api.post("/integrations/accounts", { ...data, provider });
    }
    setDialogOpen(false);
    setEditing(null);
    onReload();
  }

  async function handleDeactivate() {
    if (!confirmDeactivate) return;
    setDeactivating(true);
    try {
      await api.post(`/integrations/accounts/${confirmDeactivate.id}/deactivate`);
      onReload();
    } finally {
      setDeactivating(false);
      setConfirmDeactivate(null);
    }
  }

  async function handleSetDefault(account: Account) {
    await api.post(`/integrations/accounts/${account.id}/set-default`);
    onReload();
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 transition-colors text-left"
      >
        <span className="text-2xl">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-900">{meta.label}</span>
            {active.length > 0 && (
              <span className={`text-xs font-medium border rounded-full px-2 py-0.5 ${meta.color}`}>
                {active.length} cuenta{active.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs gap-1"
            onClick={e => { e.stopPropagation(); setEditing(null); setDialogOpen(true); }}
          >
            <Plus className="h-3 w-3" />
            Conectar
          </Button>
          {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </div>
      </button>

      {/* Account list */}
      {open && (
        <div className="border-t border-slate-100 px-5 py-4 space-y-3">
          {accounts.length === 0 ? (
            <p className="text-sm text-slate-400 py-2">
              No hay cuentas configuradas.{" "}
              <button className="underline text-slate-600 hover:text-slate-900" onClick={() => { setEditing(null); setDialogOpen(true); }}>
                Conectar ahora
              </button>
            </p>
          ) : (
            accounts.map(acc => (
              <AccountCard
                key={acc.id}
                account={acc}
                onEdit={() => { setEditing(acc); setDialogOpen(true); }}
                onTest={onReload}
                onDeactivate={() => setConfirmDeactivate(acc)}
                onSetDefault={() => handleSetDefault(acc)}
              />
            ))
          )}
        </div>
      )}

      {/* Create/edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={v => { if (!v) { setDialogOpen(false); setEditing(null); } }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? `Editar ${editing.name}` : `Conectar ${meta.label}`}</DialogTitle>
          </DialogHeader>
          <AccountForm
            provider={provider}
            existing={editing}
            onSave={handleSave}
            onClose={() => { setDialogOpen(false); setEditing(null); }}
          />
        </DialogContent>
      </Dialog>

      {/* Deactivate confirm dialog */}
      <Dialog open={!!confirmDeactivate} onOpenChange={v => { if (!v) setConfirmDeactivate(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Desactivar integración</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-slate-600">
            ¿Desactivar <strong>{confirmDeactivate?.name}</strong>? Los webhooks y sincronizaciones dejarán de funcionar.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDeactivate(null)} disabled={deactivating}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDeactivate} disabled={deactivating}>
              {deactivating ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : null}
              Desactivar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ─── Main page ──────────────────────────────────────────────────────────── */

export default function Integrations() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<Account[]>("/integrations/accounts", { params: { include_inactive: true } });
      setAccounts(res.data);
    } catch {
      setError("No se pudo cargar la lista de integraciones.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const byProvider = (provider: Provider) => accounts.filter(a => a.provider === provider);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Integraciones</h1>
          <p className="text-sm text-slate-500">Conecta servicios externos: WhatsApp, Google, ClickUp y más.</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Recargar"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {loading && accounts.length === 0 ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-7 w-7 animate-spin text-slate-300" />
        </div>
      ) : (
        <div className="space-y-4">
          {PROVIDER_ORDER.map(provider => (
            <ProviderSection
              key={provider}
              provider={provider}
              accounts={byProvider(provider)}
              onReload={load}
            />
          ))}
        </div>
      )}
    </div>
  );
}
