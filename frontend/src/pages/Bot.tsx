import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Loader2, Bot as BotIcon, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";

/* ─── Types ─────────────────────────────────────────────────────────── */

interface BotMessage {
  id: number;
  command: string;
  response: string;
  intent: string;
  status: string;
  created_at: string;
}

/* ─── Helpers ────────────────────────────────────────────────────────── */

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

const SUGGESTIONS = [
  "¿Cuántas citas hay hoy?",
  "¿Cuáles son las ventas de hoy?",
  "Muestra el corte de caja",
  "¿Qué servicios están pendientes?",
  "Servicios en proceso",
  "Comisiones de hoy",
];

/* ─── Component ──────────────────────────────────────────────────────── */

export default function Bot() {
  const [history, setHistory]   = useState<BotMessage[]>([]);
  const [command, setCommand]   = useState("");
  const [sending, setSending]   = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const bottomRef               = useRef<HTMLDivElement>(null);
  const inputRef                = useRef<HTMLInputElement>(null);

  /* ── Load history ── */

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<BotMessage[]>("/bot/history", { params: { limit: 50 } });
      setHistory(res.data.reverse());
    } catch {
      // history not critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  /* ── Send command ── */

  async function send(cmd?: string) {
    const text = (cmd ?? command).trim();
    if (!text || sending) return;
    setCommand("");
    setSending(true);
    setError("");
    try {
      const res = await api.post<BotMessage>("/bot/command", { command: text });
      setHistory(prev => [...prev, res.data]);
    } catch {
      setError("Error al ejecutar el comando.");
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  /* ── Render ── */

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Bot interno</h1>
          <p className="text-sm text-slate-500">Consulta información del taller en lenguaje natural</p>
        </div>
        <div className="shrink-0 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 inline-block" />
          IA activa
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
          </div>
        ) : history.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-4">
            <BotIcon className="h-12 w-12 opacity-30" />
            <p className="text-sm">Escribe un comando para comenzar</p>
            <div className="flex flex-wrap justify-center gap-2 max-w-md">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-slate-400 hover:text-slate-900 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          history.map(msg => (
            <div key={msg.id} className="space-y-2">
              {/* User command */}
              <div className="flex justify-end gap-2">
                <div className="max-w-lg">
                  <div className="rounded-2xl rounded-tr-sm bg-slate-900 text-white px-4 py-2.5 text-sm">
                    {msg.command}
                  </div>
                  <p className="text-xs text-slate-400 text-right mt-1">{formatTime(msg.created_at)}</p>
                </div>
                <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="h-4 w-4 text-slate-600" />
                </div>
              </div>

              {/* Bot response */}
              <div className="flex gap-2">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                  msg.status === "success" ? "bg-emerald-100" : "bg-red-100"
                }`}>
                  <BotIcon className={`h-4 w-4 ${msg.status === "success" ? "text-emerald-600" : "text-red-500"}`} />
                </div>
                <div className="max-w-lg">
                  <div className={`rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm whitespace-pre-wrap ${
                    msg.status === "success"
                      ? "bg-slate-100 text-slate-800"
                      : "bg-red-50 text-red-800 border border-red-100"
                  }`}>
                    {msg.response}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}

        {sending && (
          <div className="flex gap-2">
            <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
              <BotIcon className="h-4 w-4 text-slate-400" />
            </div>
            <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2.5">
              <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 pt-4">
        {/* Quick suggestions (only shown when there's history) */}
        {history.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {SUGGESTIONS.slice(0, 3).map(s => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={sending}
                className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:border-slate-400 hover:text-slate-800 transition-colors disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="flex-1 rounded-lg border border-slate-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
            placeholder="Escribe un comando… Ej: ¿Cuáles son las ventas de hoy?"
            value={command}
            onChange={e => setCommand(e.target.value)}
            onKeyDown={onKey}
            disabled={sending}
          />
          <Button onClick={() => send()} disabled={!command.trim() || sending} size="icon" className="h-10 w-10">
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
