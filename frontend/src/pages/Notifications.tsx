import { useState, useEffect, useCallback } from "react";
import { Bell, BellOff, CheckCheck, Info, CheckCircle, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface Notification {
  id: number;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

/* ─── Config ─────────────────────────────────────────────────────────── */

const TYPE_CONFIG: Record<string, {
  icon: React.ElementType;
  badge: "default" | "success" | "warning" | "destructive";
  bg: string;
  iconColor: string;
}> = {
  info:    { icon: Info,          badge: "default",     bg: "bg-blue-50 border-blue-100",   iconColor: "text-blue-500" },
  success: { icon: CheckCircle,   badge: "success",     bg: "bg-emerald-50 border-emerald-100", iconColor: "text-emerald-500" },
  warning: { icon: AlertTriangle, badge: "warning",     bg: "bg-amber-50 border-amber-100",  iconColor: "text-amber-500" },
  error:   { icon: XCircle,       badge: "destructive", bg: "bg-red-50 border-red-100",      iconColor: "text-red-500" },
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Hace un momento";
  if (mins < 60) return `Hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `Hace ${days}d`;
}

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Notifications() {
  const [items, setItems]           = useState<Notification[]>([]);
  const [loading, setLoading]       = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [error, setError]           = useState("");
  const [marking, setMarking]       = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<Notification[]>("/notifications/", {
        params: { unread_only: unreadOnly, limit: 100 },
      });
      setItems(res.data);
    } catch {
      setError("Error al cargar notificaciones.");
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => { load(); }, [load]);

  async function markRead(id: number) {
    setMarking(s => new Set(s).add(id));
    try {
      await api.post(`/notifications/${id}/read`);
      setItems(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch {
      setError("Error al marcar notificación.");
    } finally {
      setMarking(s => { const next = new Set(s); next.delete(id); return next; });
    }
  }

  async function markAllRead() {
    const unread = items.filter(n => !n.is_read);
    await Promise.all(unread.map(n => markRead(n.id)));
  }

  const unreadCount = items.filter(n => !n.is_read).length;
  const displayed   = unreadOnly ? items.filter(n => !n.is_read) : items;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notificaciones</h1>
          <p className="text-sm text-slate-500">
            {unreadCount > 0 ? `${unreadCount} sin leer` : "Todo al día"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={unreadOnly ? "default" : "outline"}
            size="sm"
            onClick={() => setUnreadOnly(v => !v)}
          >
            <BellOff className="h-4 w-4 mr-1" />
            {unreadOnly ? "Mostrar todas" : "Solo no leídas"}
          </Button>
          {unreadCount > 0 && (
            <Button variant="outline" size="sm" onClick={markAllRead}>
              <CheckCheck className="h-4 w-4 mr-1" />
              Marcar todas leídas
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : displayed.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Bell className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">{unreadOnly ? "No hay notificaciones sin leer" : "Sin notificaciones"}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {displayed.map(n => {
            const cfg = TYPE_CONFIG[n.type] ?? TYPE_CONFIG.info;
            const Icon = cfg.icon;
            const isMarking = marking.has(n.id);

            return (
              <div
                key={n.id}
                className={`flex gap-3 rounded-lg border p-4 transition-opacity ${
                  n.is_read ? "opacity-60 bg-white border-slate-100" : `${cfg.bg}`
                }`}
              >
                {/* Icon */}
                <div className="shrink-0 mt-0.5">
                  <Icon className={`h-5 w-5 ${n.is_read ? "text-slate-300" : cfg.iconColor}`} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-slate-900">{n.title}</p>
                    {!n.is_read && <Badge variant={cfg.badge}>{n.type}</Badge>}
                  </div>
                  <p className="text-sm text-slate-600 mt-0.5">{n.message}</p>
                  <p className="text-xs text-slate-400 mt-1">{timeAgo(n.created_at)}</p>
                </div>

                {/* Action */}
                {!n.is_read && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 h-8 text-xs text-slate-500 hover:text-slate-900"
                    onClick={() => markRead(n.id)}
                    disabled={isMarking}
                  >
                    {isMarking
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <CheckCheck className="h-3.5 w-3.5" />
                    }
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
