import { useState, useEffect, useRef, useCallback } from "react";
import { X, Send, Loader2, MessageSquare, Paperclip, MapPin, FileText, Download } from "lucide-react";
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
  attachment_url: string | null;
  attachment_type: string | null;
  attachment_name: string | null;
  created_at: string;
}

interface PendingAttachment {
  url: string;
  type: string;
  name: string;
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

/* ─── Attachment renderer ─────────────────────────────────────────────────── */

function AttachmentView({ url, type, name, isMe }: {
  url: string; type: string; name: string; isMe: boolean;
}) {
  if (type === "image") {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer">
        <img
          src={url}
          alt={name}
          className="max-w-[220px] max-h-[200px] rounded-xl object-cover cursor-pointer hover:opacity-90 transition-opacity"
        />
      </a>
    );
  }
  if (type === "video") {
    return <video src={url} controls className="max-w-[220px] rounded-xl" />;
  }
  if (type === "audio") {
    return <audio src={url} controls className="max-w-[220px]" />;
  }
  if (type === "location") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
          isMe ? "bg-slate-700 hover:bg-slate-600 text-white" : "bg-slate-200 hover:bg-slate-300 text-slate-800"
        )}
      >
        <MapPin className="h-4 w-4 shrink-0" />
        <span>Ver ubicación</span>
      </a>
    );
  }
  return (
    <a
      href={url}
      download={name}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
        isMe ? "bg-slate-700 hover:bg-slate-600 text-white" : "bg-slate-200 hover:bg-slate-300 text-slate-800"
      )}
    >
      <FileText className="h-4 w-4 shrink-0" />
      <span className="truncate max-w-[150px]">{name}</span>
      <Download className="h-3 w-3 shrink-0 ml-auto" />
    </a>
  );
}

/* ─── Component ───────────────────────────────────────────────────────────── */

export default function TeamChat({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const [msgs, setMsgs]       = useState<Msg[]>([]);
  const [text, setText]       = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [locating, setLocating]   = useState(false);
  const [pending, setPending]     = useState<PendingAttachment | null>(null);
  const lastIdRef  = useRef<number | null>(null);
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Blur input when chat closes so iOS zooms back out
  useEffect(() => {
    if (!open) inputRef.current?.blur();
  }, [open]);

  /* ── Initial load ── */
  const loadInitial = useCallback(async () => {
    try {
      const res = await api.get<Msg[]>("/team-chat/", { params: { limit: 60 } });
      setMsgs(res.data);
      lastIdRef.current = res.data.length ? res.data[res.data.length - 1].id : 0;
    } catch { /* ignore */ }
  }, []);

  /* ── Polling ── */
  const poll = useCallback(async () => {
    if (lastIdRef.current === null) return;
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  /* ── File upload ── */
  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<PendingAttachment>("/team-chat/upload", form);
      setPending(res.data);
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Error al subir archivo");
    } finally {
      setUploading(false);
    }
  }

  /* ── Location ── */
  function handleLocation() {
    if (!navigator.geolocation) { alert("Tu navegador no soporta geolocalización"); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      pos => {
        const { latitude: lat, longitude: lng } = pos.coords;
        setPending({ url: `https://maps.google.com/?q=${lat},${lng}`, type: "location", name: "Ubicación" });
        setLocating(false);
      },
      () => { alert("No se pudo obtener la ubicación"); setLocating(false); },
      { timeout: 10000 },
    );
  }

  /* ── Send ── */
  async function handleSend() {
    const content = text.trim();
    if ((!content && !pending) || sending) return;
    setSending(true);
    setText("");
    const att = pending;
    setPending(null);
    try {
      const res = await api.post<Msg>("/team-chat/", {
        content,
        attachment_url: att?.url ?? null,
        attachment_type: att?.type ?? null,
        attachment_name: att?.name ?? null,
      });
      setMsgs(prev => [...prev, res.data]);
      lastIdRef.current = res.data.id;
    } catch {
      setText(content);
      if (att) setPending(att);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  const canSend = (text.trim().length > 0 || !!pending) && !sending;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end pointer-events-none">
      {/* backdrop */}
      <div className="absolute inset-0 bg-black/20 pointer-events-auto" onClick={onClose} />

      {/* panel */}
      <div className="relative pointer-events-auto flex flex-col w-full md:w-96 h-full bg-white shadow-2xl border-l border-slate-200">

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
            const hasAttachOnly = !m.content && !!m.attachment_url;
            return (
              <div key={m.id} className={cn("flex gap-2", isMe ? "flex-row-reverse" : "flex-row")}>
                {/* Avatar */}
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

                  {/* Text bubble — only rendered when there's text */}
                  {m.content && (
                    <div className={cn(
                      "px-3 py-2 rounded-2xl text-sm leading-relaxed",
                      isMe
                        ? "bg-slate-900 text-white rounded-tr-sm"
                        : "bg-slate-100 text-slate-800 rounded-tl-sm",
                      m.attachment_url ? "mb-1" : ""
                    )}>
                      {m.content}
                    </div>
                  )}

                  {/* Attachment */}
                  {m.attachment_url && m.attachment_type && (
                    <div className={cn(hasAttachOnly && (isMe ? "rounded-tr-sm" : "rounded-tl-sm"))}>
                      <AttachmentView
                        url={m.attachment_url}
                        type={m.attachment_type}
                        name={m.attachment_name || "archivo"}
                        isMe={isMe}
                      />
                    </div>
                  )}

                  <p className="text-[10px] text-slate-400 mt-0.5 px-1">{timeLabel(m.created_at)}</p>
                </div>
              </div>
            );
          })}
          <div ref={bottomRef} />
        </div>

        {/* Pending attachment preview */}
        {pending && (
          <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-t border-slate-100">
            {pending.type === "image"
              ? <img src={pending.url} alt="" className="h-10 w-10 rounded object-cover shrink-0" />
              : pending.type === "location"
              ? <MapPin className="h-5 w-5 text-slate-400 shrink-0" />
              : <FileText className="h-5 w-5 text-slate-400 shrink-0" />
            }
            <span className="text-xs text-slate-600 truncate flex-1">{pending.name}</span>
            <button onClick={() => setPending(null)} className="text-slate-400 hover:text-slate-600 shrink-0">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-slate-100 px-3 py-3 flex gap-1.5 items-center">
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip"
            onChange={handleFileChange}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || sending}
            title="Adjuntar archivo"
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors disabled:opacity-40"
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
          </button>

          <button
            onClick={handleLocation}
            disabled={locating || sending}
            title="Compartir ubicación"
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors disabled:opacity-40"
          >
            {locating ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPin className="h-4 w-4" />}
          </button>

          <input
            ref={inputRef}
            className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[16px] md:text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors"
            placeholder="Escribe un mensaje…"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKey}
            maxLength={2000}
            disabled={sending}
          />

          <button
            onClick={handleSend}
            disabled={!canSend}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition-colors disabled:opacity-40"
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
