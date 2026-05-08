import { useState, useEffect, useRef, useCallback } from "react";
import { X, Send, Loader2, MessageSquare } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

/* ─── Types ──────────────────────────────────────────────────────────────── */

interface Msg {
  id: number;
  user_id: number;
  user_name: string;
  user_role: string;
  content: string;
  created_at: string;
}

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

function avatar(name: string) {
  return name?.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase() || "?";
}

function timeLabel(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

const ROLE_COLOR: Record<string, string> = {
  admin:      "bg-violet-200 text-violet-800",
  supervisor: "bg-blue-200 text-blue-800",
  cashier:    "bg-emerald-200 text-emerald-800",
  operator:   "bg-amber-200 text-amber-800",
};

/* ─── Component ───────────────────────────────────────────────────────────── */

export default function TeamChat({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const [msgs, setMsgs]       = useState<Msg[]>([]);
  const [text, setText]       = useState("");
  const [sending, setSending] = useState(false);
  const lastIdRef             = useRef(0);
  const bottomRef             = useRef<HTMLDivElement>(null);
  const inputRef              = useRef<HTMLInputElement>(null);

  /* ── Initial load ── */
  const loadInitial = useCallback(async () => {
    try {
      const res = await api.get<Msg[]>("/team-chat/", { params: { limit: 60 } });
      setMsgs(res.data);
      if (res.data.length) lastIdRef.current = res.data[res.data.length - 1].id;
    } catch { /* ignore */ }
  }, []);

  /* ── Polling for new messages ── */
  const poll = useCallback(async () => {
    if (!lastIdRef.current) return;
    try {
      const res = await api.get<Msg[]>("/team-chat/", { params: { since_id: lastIdRef.current } });
      if (res.data.length) {
        setMsgs(prev => [...prev, ...res.data]);
        lastIdRef.current = res.data[res.data.length - 1].id;
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!open) return;
    loadInitial();
    inputRef.current?.focus();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [open, loadInitial, poll]);

  /* ── Scroll to bottom on new messages ── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  /* ── Send ── */
  async function handleSend() {
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    setText("");
    try {
      const res = await api.post<Msg>("/team-chat/", { content });
      setMsgs(prev => [...prev, res.data]);
      lastIdRef.current = res.data.id;
    } catch {
      setText(content); // restore on error
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end pointer-events-none">
      {/* backdrop */}
      <div
        className="absolute inset-0 bg-black/20 pointer-events-auto"
        onClick={onClose}
      />

      {/* panel */}
      <div className="relative pointer-events-auto flex flex-col w-80 md:w-96 h-full bg-white shadow-2xl border-l border-slate-200">

        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
            <MessageSquare className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-slate-900">Chat del equipo</p>
            <p className="text-xs text-slate-400">Solo visible para tu empresa</p>
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {msgs.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
              <MessageSquare className="h-10 w-10 opacity-20 mb-2" />
              <p className="text-sm">Sé el primero en escribir algo.</p>
            </div>
          )}
          {msgs.map((m, i) => {
            const isMe = m.user_id === user?.id;
            const showName = i === 0 || msgs[i - 1].user_id !== m.user_id;
            return (
              <div key={m.id} className={cn("flex gap-2", isMe ? "flex-row-reverse" : "flex-row")}>
                {/* Avatar — only show when sender changes */}
                <div className="shrink-0 w-7 mt-1">
                  {showName && (
                    <div className={cn(
                      "w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold",
                      ROLE_COLOR[m.user_role] ?? "bg-slate-200 text-slate-600"
                    )}>
                      {avatar(m.user_name)}
                    </div>
                  )}
                </div>

                <div className={cn("flex flex-col max-w-[75%]", isMe ? "items-end" : "items-start")}>
                  {showName && (
                    <p className="text-[11px] font-semibold text-slate-500 mb-0.5 px-1">
                      {isMe ? "Tú" : m.user_name}
                    </p>
                  )}
                  <div className={cn(
                    "px-3 py-2 rounded-2xl text-sm leading-relaxed",
                    isMe
                      ? "bg-slate-900 text-white rounded-tr-sm"
                      : "bg-slate-100 text-slate-800 rounded-tl-sm"
                  )}>
                    {m.content}
                  </div>
                  <p className="text-[10px] text-slate-400 mt-0.5 px-1">{timeLabel(m.created_at)}</p>
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-100 px-3 py-3 flex gap-2 items-center">
          <input
            ref={inputRef}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors"
            placeholder="Escribe un mensaje…"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKey}
            maxLength={2000}
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={!text.trim() || sending}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition-colors disabled:opacity-40"
          >
            {sending
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
