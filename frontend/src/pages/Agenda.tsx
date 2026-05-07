import { useState, useEffect, useCallback } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import api from "@/lib/api";

interface AgendaAppointment {
  id: number;
  scheduled_start: string;
  status: string;
  charge_status: string;
  estimated_price: string | number | null;
  client_name: string | null;
  vehicle_label: string | null;
  service_name: string | null;
  operator_name: string | null;
}

const STATUS: Record<string, { label: string; variant: "default" | "success" | "warning" | "destructive" | "secondary" }> = {
  pendiente:  { label: "Pendiente",  variant: "warning" },
  confirmado: { label: "Confirmado", variant: "default" },
  en_proceso: { label: "En proceso", variant: "secondary" },
  terminado:  { label: "Terminado",  variant: "success" },
  cancelado:  { label: "Cancelado",  variant: "destructive" },
};

function toDateStr(d: Date) {
  return d.toISOString().slice(0, 10);
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function formatFullDate(d: Date) {
  return d.toLocaleDateString("es-MX", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}

function shiftDay(d: Date, delta: number): Date {
  const n = new Date(d);
  n.setDate(n.getDate() + delta);
  return n;
}

export default function Agenda() {
  const [date, setDate] = useState<Date>(new Date());
  const [appointments, setAppointments] = useState<AgendaAppointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [cancelTarget, setCancelTarget] = useState<AgendaAppointment | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  const fetchDay = useCallback(async (d: Date) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<AgendaAppointment[]>("/appointments/agenda/day", {
        params: { target_date: toDateStr(d) },
      });
      setAppointments(res.data);
    } catch {
      setError("Error al cargar la agenda. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDay(date); }, [date, fetchDay]);

  const handleCancel = async () => {
    if (!cancelTarget) return;
    setCancelling(true);
    try {
      await api.post(`/appointments/${cancelTarget.id}/cancel`, null, {
        params: cancelReason.trim() ? { reason: cancelReason.trim() } : {},
      });
      setCancelTarget(null);
      setCancelReason("");
      fetchDay(date);
    } catch {
      setError("Error al cancelar la cita.");
      setCancelling(false);
    }
  };

  const isToday = toDateStr(date) === toDateStr(new Date());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agenda</h1>
          <p className="text-sm text-slate-500 capitalize">{formatFullDate(date)}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setDate(d => shiftDay(d, -1))}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {!isToday && (
            <Button variant="outline" size="sm" onClick={() => setDate(new Date())}>
              Hoy
            </Button>
          )}
          <Button variant="outline" size="icon" onClick={() => setDate(d => shiftDay(d, 1))}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-slate-300" />
        </div>
      ) : appointments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <CalendarDays className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">No hay citas para este día</p>
        </div>
      ) : (
        <div className="space-y-3">
          {appointments.map((appt) => {
            const cfg = STATUS[appt.status] ?? { label: appt.status, variant: "default" as const };
            const price = appt.estimated_price != null ? Number(appt.estimated_price).toFixed(2) : null;

            return (
              <div
                key={appt.id}
                className="flex items-start gap-4 rounded-lg border border-slate-200 bg-white p-4"
              >
                {/* Time column */}
                <div className="w-14 shrink-0 text-center">
                  <p className="text-base font-bold text-slate-800">{formatTime(appt.scheduled_start)}</p>
                </div>

                {/* Main info */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900">{appt.client_name ?? "—"}</span>
                    <Badge variant={cfg.variant}>{cfg.label}</Badge>
                    {appt.charge_status === "pagado" && (
                      <Badge variant="success">Pagado</Badge>
                    )}
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5">{appt.vehicle_label ?? "—"}</p>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-400">
                    {appt.service_name && <span>{appt.service_name}</span>}
                    {appt.operator_name && <span>Operador: {appt.operator_name}</span>}
                    {price && <span>${price}</span>}
                  </div>
                </div>

                {/* Actions */}
                {appt.status !== "cancelado" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 border-red-200 text-red-600 hover:bg-red-50"
                    onClick={() => { setCancelTarget(appt); setCancelReason(""); }}
                  >
                    Cancelar
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Summary footer */}
      {!loading && appointments.length > 0 && (
        <p className="text-xs text-slate-400 text-right">
          {appointments.filter(a => a.status !== "cancelado").length} cita(s) activas ·{" "}
          {appointments.filter(a => a.charge_status === "pagado").length} pagada(s)
        </p>
      )}

      {/* Cancel dialog */}
      <Dialog
        open={!!cancelTarget}
        onOpenChange={(open) => { if (!open) { setCancelTarget(null); setCancelReason(""); } }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cancelar cita</DialogTitle>
            <DialogDescription>
              ¿Cancelar la cita de <strong>{cancelTarget?.client_name}</strong>?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Motivo (opcional)</label>
            <input
              className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              placeholder="Ej: Cliente no disponible"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCancel()}
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => { setCancelTarget(null); setCancelReason(""); }}
              disabled={cancelling}
            >
              Volver
            </Button>
            <Button variant="destructive" onClick={handleCancel} disabled={cancelling}>
              {cancelling && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirmar cancelación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
