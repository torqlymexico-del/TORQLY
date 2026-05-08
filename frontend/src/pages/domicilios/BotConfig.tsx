import { Bot } from "lucide-react";

export default function BotConfig() {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-4 text-slate-400">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center">
        <Bot className="h-8 w-8 text-blue-400" />
      </div>
      <div className="text-center">
        <h2 className="text-lg font-bold text-slate-700">Bot / Automatización</h2>
        <p className="text-sm mt-1 max-w-xs">
          Próximamente — el bot automatizará la recepción de pedidos, asignación de lavadores y cobros para domicilios.
        </p>
      </div>
    </div>
  );
}
