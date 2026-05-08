import { useState, useEffect, useRef, useCallback } from "react";
import {
  X, Send, Loader2, MessageSquare, Paperclip, MapPin,
  FileText, Download, Users, ArrowLeft, Lock,
} from "lucide-react";
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
  branch: string;
  attachment_url: string | null;
  attachment_type: string | null;
  attachment_name: string | null;
  created_at: string;
}

interface DmMsg {
  id: number;
  sender_id: number;
  sender_name: string;
  sender_role: string;
  content: string;
  attachment_url: string | null;
  attachment_type: string | null;
  attachment_name: string | null;
  created_at: string;
}

interface Contact {
  id: number;
  name: string;
  role: string;
  branch: string;
  unread: number;
}

interface PendingAttachment {
  url: string;
  type: string;
  name: string;
}

type ChatTab = "group" | "direct";

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

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin", supervisor: "Supervisor", cashier: "Cajero", operator: "Lavador",
};

/* ─── Attachment renderer ─────────────────────────────────────────────────── */

function AttachmentView({ url, type, name, isMe }: {
  url: string; type: string; name: string; isMe: boolean;
}) {
  if (type === "image") {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer">
        <img src={url} alt={name} className="max-w-[220px] max-h-[200px] rounded-xl object-cover cursor-pointer hover:opacity-90 transition-opacity" />
      </a>
    );
  }
  if (type === "video") return <video src={url} controls className="max-w-[220px] rounded-xl" />;
  if (type === "audio") return <audio src={url} controls className="max-w-[220px]" />;
  if (type === "location") {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer"
        className={cn("flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
          isMe ? "bg-slate-700 hover:bg-slate-600 text-white" : "bg-slate-200 hover:bg-slate-300 text-slate-800")}>
        <MapPin className="h-4 w-4 shrink-0" />
        <span>Ver ubicación</span>
      </a>
    );
  }
  return (
    <a href={url} download={name} target="_blank" rel="noopener noreferrer"
      className={cn("flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
        isMe ? "bg-slate-700 hover:bg-slate-600 text-white" : "bg-slate-200 hover:bg-slate-300 text-slate-800")}>
      <FileText className="h-4 w-4 shrink-0" />
      <span className="truncate max-w-[150px]">{name}</span>
      <Download className="h-3 w-3 shrink-0 ml-auto" />
    </a>
  );
}

/* ─── Message bubble (shared by group + DM) ──────────────────────────────── */

function Bubble({ isMe, showName, senderName, senderRole, content, attachUrl, attachType, attachName, time }: {
  isMe: boolean; showName: boolean; senderName: string; senderRole: string;
  content: string; attachUrl?: string | null; attachType?: string | null; attachName?: string | null;
  time: string;
}) {
  return (
    <div className={cn("flex gap-2", isMe ? "flex-row-reverse" : "flex-row")}>
      <div className="shrink-0 w-7 mt-1">
        {showName && (
          <div className={cn("w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold",
            ROLE_COLOR[senderRole] ?? "bg-slate-200 text-slate-600")}>
            {avatar(senderName)}
          </div>
        )}
      </div>
      <div className={cn("flex flex-col max-w-[75%]", isMe ? "items-end" : "items-start")}>
        {showName && (
          <p className="text-[11px] font-semibold text-slate-500 mb-0.5 px-1">
            {isMe ? "Tú" : senderName}
          </p>
        )}
        {content && (
          <div className={cn("px-3 py-2 rounded-2xl text-sm leading-relaxed",
            isMe ? "bg-slate-900 text-white rounded-tr-sm" : "bg-slate-100 text-slate-800 rounded-tl-sm",
            attachUrl ? "mb-1" : "")}>
            {content}
          </div>
        )}
        {attachUrl && attachType && (
          <AttachmentView url={attachUrl} type={attachType} name={attachName || "archivo"} isMe={isMe} />
        )}
        <p className="text-[10px] text-slate-400 mt-0.5 px-1">{time}</p>
      </div>
    </div>
  );
}

/* ─── Input bar (shared) ─────────────────────────────────────────────────── */

function InputBar({ onSend, sending, uploading, locating, pending, onClearPending, onFileChange, onLocation, inputRef }: {
  onSend: () => void; sending: boolean; uploading: boolean; locating: boolean;
  pending: PendingAttachment | null; onClearPending: () => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onLocation: () => void; inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleSend() {
    if ((!text.trim() && !pending) || sending) return;
    onSend();
    setText("");
  }

  // Expose text via ref so parent can read it
  useEffect(() => {
    if (inputRef.current) (inputRef.current as any)._value = text;
  }, [text, inputRef]);

  const canSend = (text.trim().length > 0 || !!pending) && !sending;

  return (
    <div>
      {pending && (
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-t border-slate-100">
          {pending.type === "image"
            ? <img src={pending.url} alt="" className="h-10 w-10 rounded object-cover shrink-0" />
            : pending.type === "location"
            ? <MapPin className="h-5 w-5 text-slate-400 shrink-0" />
            : <FileText className="h-5 w-5 text-slate-400 shrink-0" />}
          <span className="text-xs text-slate-600 truncate flex-1">{pending.name}</span>
          <button onClick={onClearPending} className="text-slate-400 hover:text-slate-600 shrink-0">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <div className="border-t border-slate-100 px-3 py-3 flex gap-1.5 items-center">
        <input ref={fileInputRef} type="file" className="hidden"
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip"
          onChange={onFileChange} />
        <button onClick={() => fileInputRef.current?.click()} disabled={uploading || sending}
          title="Adjuntar archivo"
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors disabled:opacity-40">
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
        </button>
        <button onClick={onLocation} disabled={locating || sending}
          title="Compartir ubicación"
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors disabled:opacity-40">
          {locating ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPin className="h-4 w-4" />}
        </button>
        <input ref={inputRef}
          className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[16px] md:text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors"
          placeholder="Escribe un mensaje…"
          value={text} onChange={e => setText(e.target.value)}
          onKeyDown={handleKey} maxLength={2000} disabled={sending} />
        <button onClick={handleSend} disabled={!canSend}
          className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition-colors disabled:opacity-40">
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function TeamChat({ open, onClose, branch = "local" }: {
  open: boolean; onClose: () => void; branch?: string;
}) {
  const { user } = useAuth();
  const [tab, setTab]     = useState<ChatTab>("group");

  // Group chat state
  const [msgs, setMsgs]   = useState<Msg[]>([]);
  const groupLastId       = useRef<number | null>(null);
  const groupBottomRef    = useRef<HTMLDivElement>(null);
  const groupInputRef     = useRef<HTMLInputElement>(null);

  // Direct chat state
  const [contacts, setContacts]             = useState<Contact[]>([]);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [dmMsgs, setDmMsgs]                 = useState<DmMsg[]>([]);
  const dmLastId                             = useRef<number | null>(null);
  const dmBottomRef                          = useRef<HTMLDivElement>(null);
  const dmInputRef                           = useRef<HTMLInputElement>(null);

  // Shared state
  const [sending, setSending]   = useState(false);
  const [uploading, setUploading] = useState(false);
  const [locating, setLocating]   = useState(false);
  const [pending, setPending]     = useState<PendingAttachment | null>(null);

  /* ── Blur on close (iOS zoom-out) ── */
  useEffect(() => {
    if (!open) { groupInputRef.current?.blur(); dmInputRef.current?.blur(); }
  }, [open]);

  /* ══════════════════════ GROUP CHAT ══════════════════════ */

  const loadGroup = useCallback(async (br: string) => {
    try {
      const res = await api.get<Msg[]>("/team-chat/", { params: { limit: 60, branch: br } });
      setMsgs(res.data);
      groupLastId.current = res.data.length ? res.data[res.data.length - 1].id : 0;
    } catch { /* ignore */ }
  }, []);

  const pollGroup = useCallback(async (br: string) => {
    if (groupLastId.current === null) return;
    try {
      const res = await api.get<Msg[]>("/team-chat/", { params: { since_id: groupLastId.current, branch: br } });
      if (res.data.length) {
        setMsgs(prev => [...prev, ...res.data]);
        groupLastId.current = res.data[res.data.length - 1].id;
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!open || tab !== "group") return;
    setMsgs([]); groupLastId.current = null;
    loadGroup(branch);
    groupInputRef.current?.focus();
    const id = setInterval(() => pollGroup(branch), 3000);
    return () => clearInterval(id);
  }, [open, tab, branch, loadGroup, pollGroup]);

  useEffect(() => { groupBottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function sendGroup() {
    const content = (groupInputRef.current as any)?._value?.trim() ?? "";
    if ((!content && !pending) || sending) return;
    setSending(true);
    const att = pending; setPending(null);
    try {
      const res = await api.post<Msg>("/team-chat/", {
        content, branch,
        attachment_url: att?.url ?? null,
        attachment_type: att?.type ?? null,
        attachment_name: att?.name ?? null,
      });
      setMsgs(prev => [...prev, res.data]);
      groupLastId.current = res.data.id;
    } catch { if (att) setPending(att); }
    finally { setSending(false); groupInputRef.current?.focus(); }
  }

  /* ══════════════════════ CONTACTS ══════════════════════ */

  const loadContacts = useCallback(async () => {
    try {
      const res = await api.get<Contact[]>("/direct-chat/contacts");
      setContacts(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!open || tab !== "direct") return;
    loadContacts();
    if (!selectedContact) {
      const id = setInterval(loadContacts, 5000);
      return () => clearInterval(id);
    }
  }, [open, tab, selectedContact, loadContacts]);

  /* ══════════════════════ DIRECT MESSAGES ══════════════════════ */

  const loadDm = useCallback(async (contactId: number) => {
    try {
      const res = await api.get<DmMsg[]>(`/direct-chat/${contactId}`, { params: { limit: 60 } });
      setDmMsgs(res.data);
      dmLastId.current = res.data.length ? res.data[res.data.length - 1].id : 0;
      // Refresh contacts to clear unread
      setContacts(prev => prev.map(c => c.id === contactId ? { ...c, unread: 0 } : c));
    } catch { /* ignore */ }
  }, []);

  const pollDm = useCallback(async (contactId: number) => {
    if (dmLastId.current === null) return;
    try {
      const res = await api.get<DmMsg[]>(`/direct-chat/${contactId}`, { params: { since_id: dmLastId.current } });
      if (res.data.length) {
        setDmMsgs(prev => [...prev, ...res.data]);
        dmLastId.current = res.data[res.data.length - 1].id;
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!open || tab !== "direct" || !selectedContact) return;
    setDmMsgs([]); dmLastId.current = null;
    loadDm(selectedContact.id);
    dmInputRef.current?.focus();
    const id = setInterval(() => pollDm(selectedContact.id), 3000);
    return () => clearInterval(id);
  }, [open, tab, selectedContact, loadDm, pollDm]);

  useEffect(() => { dmBottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [dmMsgs]);

  async function sendDm() {
    if (!selectedContact) return;
    const content = (dmInputRef.current as any)?._value?.trim() ?? "";
    if ((!content && !pending) || sending) return;
    setSending(true);
    const att = pending; setPending(null);
    try {
      const res = await api.post<DmMsg>(`/direct-chat/${selectedContact.id}`, {
        content,
        attachment_url: att?.url ?? null,
        attachment_type: att?.type ?? null,
        attachment_name: att?.name ?? null,
      });
      setDmMsgs(prev => [...prev, res.data]);
      dmLastId.current = res.data.id;
    } catch { if (att) setPending(att); }
    finally { setSending(false); dmInputRef.current?.focus(); }
  }

  /* ══════════════════════ SHARED HELPERS ══════════════════════ */

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
    } finally { setUploading(false); }
  }

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

  function switchTab(t: ChatTab) {
    setTab(t);
    setPending(null);
    if (t === "group") setSelectedContact(null);
  }

  const totalUnread = contacts.reduce((s, c) => s + c.unread, 0);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end pointer-events-none">
      <div className="absolute inset-0 bg-black/20 pointer-events-auto" onClick={onClose} />

      <div className="relative pointer-events-auto flex flex-col w-full md:w-96 h-full bg-white shadow-2xl border-l border-slate-200">

        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
          {tab === "direct" && selectedContact ? (
            <button onClick={() => setSelectedContact(null)}
              className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors shrink-0">
              <ArrowLeft className="h-4 w-4" />
            </button>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
              {tab === "direct" ? <Lock className="h-4 w-4 text-white" /> : <MessageSquare className="h-4 w-4 text-white" />}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-slate-900 truncate">
              {tab === "direct" && selectedContact ? selectedContact.name : "Chat del equipo"}
            </p>
            <p className="text-xs text-slate-400 capitalize">
              {tab === "direct" && selectedContact
                ? `${ROLE_LABEL[selectedContact.role] ?? selectedContact.role} · ${selectedContact.branch}`
                : branch}
            </p>
          </div>
          <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-100">
          <button
            onClick={() => switchTab("group")}
            className={cn("flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors",
              tab === "group" ? "text-slate-900 border-b-2 border-slate-900" : "text-slate-400 hover:text-slate-600")}>
            <MessageSquare className="h-3.5 w-3.5" />
            Grupo
          </button>
          <button
            onClick={() => switchTab("direct")}
            className={cn("flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors",
              tab === "direct" ? "text-slate-900 border-b-2 border-slate-900" : "text-slate-400 hover:text-slate-600")}>
            <Users className="h-3.5 w-3.5" />
            Mensajes
            {totalUnread > 0 && (
              <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 flex items-center justify-center px-1">
                {totalUnread > 99 ? "99+" : totalUnread}
              </span>
            )}
          </button>
        </div>

        {/* ── GROUP CHAT ── */}
        {tab === "group" && (
          <>
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
                  <Bubble key={m.id} isMe={isMe} showName={showName}
                    senderName={isMe ? "Tú" : m.user_name} senderRole={m.user_role}
                    content={m.content} attachUrl={m.attachment_url}
                    attachType={m.attachment_type} attachName={m.attachment_name}
                    time={timeLabel(m.created_at)} />
                );
              })}
              <div ref={groupBottomRef} />
            </div>
            <InputBar onSend={sendGroup} sending={sending} uploading={uploading} locating={locating}
              pending={pending} onClearPending={() => setPending(null)}
              onFileChange={handleFileChange} onLocation={handleLocation} inputRef={groupInputRef} />
          </>
        )}

        {/* ── DIRECT: CONTACT LIST ── */}
        {tab === "direct" && !selectedContact && (
          <div className="flex-1 overflow-y-auto">
            {contacts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
                <Users className="h-10 w-10 opacity-20 mb-2" />
                <p className="text-sm">Sin compañeros de equipo aún.</p>
              </div>
            ) : contacts.map(c => (
              <button key={c.id} onClick={() => setSelectedContact(c)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors border-b border-slate-50">
                <div className={cn("w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0",
                  ROLE_COLOR[c.role] ?? "bg-slate-200 text-slate-600")}>
                  {avatar(c.name)}
                </div>
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-semibold text-slate-900 truncate">{c.name}</p>
                  <p className="text-xs text-slate-400">
                    {ROLE_LABEL[c.role] ?? c.role} · <span className="capitalize">{c.branch}</span>
                  </p>
                </div>
                {c.unread > 0 && (
                  <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[20px] h-5 flex items-center justify-center px-1 shrink-0">
                    {c.unread}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* ── DIRECT: CONVERSATION ── */}
        {tab === "direct" && selectedContact && (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {dmMsgs.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-400 py-16">
                  <Lock className="h-10 w-10 opacity-20 mb-2" />
                  <p className="text-sm">Inicio de la conversación.</p>
                </div>
              )}
              {dmMsgs.map((m, i) => {
                const isMe = m.sender_id === user?.id;
                const showName = i === 0 || dmMsgs[i - 1].sender_id !== m.sender_id;
                return (
                  <Bubble key={m.id} isMe={isMe} showName={showName}
                    senderName={isMe ? "Tú" : m.sender_name} senderRole={m.sender_role}
                    content={m.content} attachUrl={m.attachment_url}
                    attachType={m.attachment_type} attachName={m.attachment_name}
                    time={timeLabel(m.created_at)} />
                );
              })}
              <div ref={dmBottomRef} />
            </div>
            <InputBar onSend={sendDm} sending={sending} uploading={uploading} locating={locating}
              pending={pending} onClearPending={() => setPending(null)}
              onFileChange={handleFileChange} onLocation={handleLocation} inputRef={dmInputRef} />
          </>
        )}
      </div>
    </div>
  );
}
