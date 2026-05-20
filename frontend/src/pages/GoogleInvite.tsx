import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors";

export default function GoogleInvite() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const params = new URLSearchParams(window.location.search);
  const email = params.get("email") ?? "";
  const name  = params.get("name")  ?? "Usuario";

  const [code, setCode]       = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  useEffect(() => {
    document.title = "Torqly — Activar cuenta";
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) { setError("Ingresa tu código de acceso."); return; }
    setError(""); setLoading(true);
    try {
      await api.post("/auth/google-complete", { invite_code: code.trim() });
      await refresh();
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Error al verificar el código.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-sm space-y-5">

        {/* Logo */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-slate-900 text-white text-xl font-bold mb-2">T</div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Torqly</h1>
          <p className="text-sm text-slate-500">Activar cuenta nueva</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">

          {/* Google account info */}
          <div className="px-6 pt-5 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-700 font-semibold text-sm shrink-0">
                {name[0]?.toUpperCase() ?? "G"}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
                {email && <p className="text-xs text-slate-400 truncate">{email}</p>}
              </div>
            </div>
            <p className="mt-3 text-sm text-slate-600">
              Tu cuenta de Google no está registrada en ninguna empresa. Ingresa el código de acceso que te proporcionó tu administrador para activarla.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{error}</div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Código de acceso</label>
              <input
                className={inputCls}
                placeholder="Ej. TQK3X9PL"
                value={code}
                onChange={e => setCode(e.target.value.toUpperCase())}
                autoComplete="off"
                maxLength={20}
                autoFocus
              />
              <p className="text-[11px] text-slate-400">Solicítalo a tu administrador si no lo tienes.</p>
            </div>

            <button
              type="submit"
              disabled={loading || !code.trim()}
              className="w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Activar cuenta
            </button>

            <button
              type="button"
              onClick={() => navigate("/login")}
              className="w-full text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Cancelar — volver al inicio de sesión
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400">
          Torqly / El Garagillo &mdash; Sistema de gestión
        </p>
      </div>
    </div>
  );
}
