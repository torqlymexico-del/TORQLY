import { MapPin } from "lucide-react";

export default function Zones() {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-4 text-slate-400">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center">
        <MapPin className="h-8 w-8 text-blue-400" />
      </div>
      <div className="text-center">
        <h2 className="text-lg font-bold text-slate-700">Zonas de servicio</h2>
        <p className="text-sm mt-1">Próximamente — configura zonas de cobertura y tarifas por zona.</p>
      </div>
    </div>
  );
}
