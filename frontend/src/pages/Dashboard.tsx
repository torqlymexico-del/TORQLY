import { useEffect, useState } from "react";
import { DollarSign, CalendarCheck, Wrench, Users, Bell, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import api, { type DashboardData, type Appointment } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function StatCard({ title, value, icon: Icon, description, color = "slate" }: {
  title: string; value: string | number; icon: typeof DollarSign;
  description?: string; color?: string;
}) {
  const colors: Record<string, string> = {
    slate:  "bg-slate-100 text-slate-700",
    green:  "bg-emerald-100 text-emerald-700",
    blue:   "bg-blue-100 text-blue-700",
    orange: "bg-orange-100 text-orange-700",
    purple: "bg-purple-100 text-purple-700",
  };
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm text-slate-500">{title}</p>
            <p className="text-2xl font-bold text-slate-900">{value}</p>
            {description && <p className="text-xs text-slate-400">{description}</p>}
          </div>
          <div className={`p-3 rounded-xl ${colors[color] ?? colors.slate}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function statusBadge(status: string) {
  const map: Record<string, "default" | "success" | "warning" | "destructive" | "secondary"> = {
    pendiente:  "warning",
    en_proceso: "default",
    terminado:  "success",
    cancelado:  "destructive",
    pagado:     "secondary",
  };
  const labels: Record<string, string> = {
    pendiente: "Pendiente", en_proceso: "En proceso",
    terminado: "Terminado", cancelado: "Cancelado", pagado: "Pagado",
  };
  return <Badge variant={map[status] ?? "secondary"}>{labels[status] ?? status}</Badge>;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" });
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<DashboardData>("/dashboard/summary")
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  const appointments: Appointment[] = data?.recent_appointments ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Bienvenido, {user?.name}. Aquí está el resumen de hoy.</p>
      </div>

      {/* Stats */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}><CardContent className="p-5 h-24 animate-pulse bg-slate-100 rounded-xl" /></Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Ventas hoy"
            value={`$${(data?.today_revenue ?? 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })}`}
            icon={DollarSign}
            color="green"
          />
          <StatCard
            title="Citas hoy"
            value={data?.today_appointments ?? 0}
            icon={CalendarCheck}
            color="blue"
          />
          <StatCard
            title="Servicios pendientes"
            value={data?.pending_services ?? 0}
            icon={Wrench}
            color="orange"
          />
          <StatCard
            title="Operadores activos"
            value={data?.active_operators ?? 0}
            icon={Users}
            color="purple"
          />
        </div>
      )}

      {/* Alerts row */}
      {!loading && ((data?.low_stock_count ?? 0) > 0 || (data?.unread_notifications ?? 0) > 0) && (
        <div className="flex flex-wrap gap-3">
          {(data?.unread_notifications ?? 0) > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700">
              <Bell className="h-4 w-4" />
              {data?.unread_notifications} notificación(es) sin leer
            </div>
          )}
          {(data?.low_stock_count ?? 0) > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              <TrendingUp className="h-4 w-4" />
              {data?.low_stock_count} producto(s) con stock bajo
            </div>
          )}
        </div>
      )}

      {/* Citas recientes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Citas recientes</CardTitle>
          <CardDescription>Últimas citas del día</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 text-center text-slate-400 text-sm">Cargando...</div>
          ) : appointments.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-sm">No hay citas registradas hoy.</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {appointments.map((apt) => (
                <div key={apt.id} className="flex items-center justify-between px-6 py-3 hover:bg-slate-50 transition-colors">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {apt.client?.name ?? "Sin cliente"} — {apt.service_catalog?.name ?? "Sin servicio"}
                    </p>
                    <p className="text-xs text-slate-400">
                      {formatDate(apt.scheduled_start)}{apt.operator ? ` · ${apt.operator.name}` : ""}
                    </p>
                  </div>
                  <div className="ml-4 shrink-0">{statusBadge(apt.status)}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
