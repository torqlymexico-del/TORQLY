import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Separator } from "@/components/ui/separator";
import api from "@/lib/api";

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-slate-600">{label}</label>
      {children}
    </div>
  );
}

export default function Login() {
  const { login, refresh } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return decodeURIComponent(params.get("error") ?? "");
  });

  // Login fields
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");

  // Register fields
  const [rName, setRName]           = useState("");
  const [rPhone, setRPhone]         = useState("");
  const [rPhoneConf, setRPhoneConf] = useState("");
  const [rEmail, setREmail]         = useState("");
  const [rEmailConf, setREmailConf] = useState("");
  const [rPwd, setRPwd]             = useState("");
  const [rPwdConf, setRPwdConf]     = useState("");
  const [rCode, setRCode]           = useState("");

  function switchMode(next: "login" | "register") {
    setMode(next);
    setError("");
  }

  /* ── Login ── */
  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(phone, password);
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Error al iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  /* ── Register ── */
  async function handleRegister(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (rPhone !== rPhoneConf) { setError("Los números de teléfono no coinciden."); return; }
    if (rEmail && rEmail !== rEmailConf) { setError("Los correos electrónicos no coinciden."); return; }
    if (rPwd !== rPwdConf) { setError("Las contraseñas no coinciden."); return; }
    setLoading(true);
    try {
      await api.post("/auth/register", {
        name: rName.trim(),
        phone: rPhone.trim(),
        password: rPwd,
        email: rEmail.trim() || null,
        invite_code: rCode.trim() || null,
      });
      await refresh();
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Error al crear la cuenta.");
    } finally {
      setLoading(false);
    }
  }

  const handleGoogleLogin = () => { window.location.href = "/auth/google"; };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-sm space-y-5">

        {/* Logo */}
        <div className="text-center space-y-1">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-slate-900 text-white text-xl font-bold mb-2">T</div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Torqly</h1>
          <p className="text-sm text-slate-500">Control operativo del taller</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">

          {/* Tab switcher */}
          <div className="grid grid-cols-2 border-b border-slate-100">
            {(["login", "register"] as const).map(m => (
              <button
                key={m}
                onClick={() => switchMode(m)}
                className={`py-3 text-sm font-semibold transition-colors ${
                  mode === m
                    ? "text-slate-900 border-b-2 border-slate-900 -mb-px"
                    : "text-slate-400 hover:text-slate-600"
                }`}
              >
                {m === "login" ? "Iniciar sesión" : "Registrarse"}
              </button>
            ))}
          </div>

          <div className="p-6 space-y-5">
            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">{error}</div>
            )}

            {/* ── Login form ── */}
            {mode === "login" && (
              <form onSubmit={handleLogin} className="space-y-4">
                <Field label="Teléfono">
                  <input className={inputCls} type="text" placeholder="6140000000" value={phone}
                    onChange={e => setPhone(e.target.value)} required autoComplete="username" />
                </Field>
                <Field label="Contraseña">
                  <input className={inputCls} type="password" placeholder="••••••••" value={password}
                    onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
                </Field>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Entrar al sistema
                </button>
              </form>
            )}

            {/* ── Register form ── */}
            {mode === "register" && (
              <form onSubmit={handleRegister} className="space-y-4">
                <Field label="Código de acceso">
                  <input
                    className={inputCls}
                    placeholder="Ej. TQK3X9PL"
                    value={rCode}
                    onChange={e => setRCode(e.target.value.toUpperCase())}
                    autoComplete="off"
                    maxLength={20}
                  />
                  <p className="text-[11px] text-slate-400 mt-0.5">Solicítalo a tu administrador. Solo el primer usuario puede registrarse sin código.</p>
                </Field>

                <Field label="Nombre completo">
                  <input className={inputCls} placeholder="Juan Pérez" value={rName}
                    onChange={e => setRName(e.target.value)} required />
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Teléfono">
                    <input className={inputCls} type="tel" placeholder="6140000000" value={rPhone}
                      onChange={e => setRPhone(e.target.value)} required autoComplete="tel" />
                  </Field>
                  <Field label="Confirmar teléfono">
                    <input className={inputCls} type="tel" placeholder="6140000000" value={rPhoneConf}
                      onChange={e => setRPhoneConf(e.target.value)} required autoComplete="off" />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Correo (opcional)">
                    <input className={inputCls} type="email" placeholder="tu@correo.com" value={rEmail}
                      onChange={e => setREmail(e.target.value)} autoComplete="email" />
                  </Field>
                  <Field label="Confirmar correo">
                    <input
                      className={inputCls}
                      type="email"
                      placeholder="tu@correo.com"
                      value={rEmailConf}
                      onChange={e => setREmailConf(e.target.value)}
                      disabled={!rEmail}
                      autoComplete="off"
                    />
                  </Field>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Contraseña">
                    <input className={inputCls} type="password" placeholder="Mín. 8 caracteres" value={rPwd}
                      onChange={e => setRPwd(e.target.value)} required autoComplete="new-password" />
                  </Field>
                  <Field label="Confirmar contraseña">
                    <input className={inputCls} type="password" placeholder="Repite" value={rPwdConf}
                      onChange={e => setRPwdConf(e.target.value)} required autoComplete="new-password" />
                  </Field>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Crear cuenta
                </button>
              </form>
            )}

            <div className="relative">
              <Separator />
              <span className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-2 text-xs text-slate-400">o</span>
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
                <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
              </svg>
              Continuar con Google
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400">
          Torqly / El Garagillo &mdash; Sistema de gestión
        </p>
      </div>
    </div>
  );
}
