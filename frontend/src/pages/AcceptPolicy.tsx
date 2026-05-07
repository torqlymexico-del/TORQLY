import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";

export default function AcceptPolicy() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAccept = async () => {
    setLoading(true);
    try {
      await api.post("/auth/accept-policy");
      await refresh();
      navigate("/");
    } catch {
      setError("Error al aceptar la política. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await api.delete("/auth/session").catch(() => {});
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <Card className="w-full max-w-xl shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-lg bg-slate-900 text-white">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <CardTitle>Política de privacidad</CardTitle>
          </div>
          <CardDescription>Versión 1.0 — debes aceptarla para continuar usando el sistema.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{error}</div>
          )}

          <div className="h-64 overflow-y-auto rounded-lg border border-slate-200 p-4 text-sm text-slate-600 space-y-3 leading-relaxed">
            <div>
              <p className="font-semibold text-slate-800">1. Datos que recopilamos</p>
              <p>Recopilamos los datos que ingresas al sistema: nombre, teléfono, correo, citas, pagos, inventario y actividad. Si accedes con Google, recibimos tu nombre, correo y foto pública.</p>
            </div>
            <div>
              <p className="font-semibold text-slate-800">2. Uso de los datos</p>
              <p>Los datos se usan exclusivamente para operar el taller. No vendemos ni compartimos información con terceros, excepto con integraciones que tú mismo configures.</p>
            </div>
            <div>
              <p className="font-semibold text-slate-800">3. Almacenamiento y seguridad</p>
              <p>La información se almacena en base de datos protegida. Las contraseñas se cifran con bcrypt, las credenciales externas con AES-256. El acceso está restringido por JWT y roles.</p>
            </div>
            <div>
              <p className="font-semibold text-slate-800">4. Retención</p>
              <p>Los datos se conservan mientras la cuenta esté activa. Puedes solicitar su eliminación contactando al administrador.</p>
            </div>
            <div>
              <p className="font-semibold text-slate-800">5. Tus derechos</p>
              <p>Tienes derecho a acceder, corregir o eliminar tu información personal. Contacta al administrador del sistema para ejercerlos.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <Button className="flex-1" onClick={handleAccept} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Acepto la política
            </Button>
            <Button variant="outline" onClick={handleLogout} disabled={loading}>
              Cerrar sesión
            </Button>
          </div>
          <p className="text-xs text-slate-400 text-center">Al aceptar confirmas que leíste y entendiste esta política.</p>
        </CardContent>
      </Card>
    </div>
  );
}
