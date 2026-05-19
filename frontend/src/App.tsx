import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import AcceptPolicy from "@/pages/AcceptPolicy";
import Agenda from "@/pages/Agenda";
import Pos from "@/pages/Pos";
import Clients from "@/pages/Clients";
import Vehicles from "@/pages/Vehicles";
import Services from "@/pages/Services";
import Commissions from "@/pages/Commissions";
import Reports from "@/pages/Reports";
import Bot from "@/pages/Bot";
import Notifications from "@/pages/Notifications";
import Integrations from "@/pages/Integrations";
import Orders from "@/pages/Orders";
import CashSessions from "@/pages/CashSessions";
import Credits from "@/pages/Credits";
import Accounting from "@/pages/Accounting";
import Payroll from "@/pages/Payroll";
import ServiceEntry from "@/pages/ServiceEntry";
import Team from "@/pages/Team";
// Domicilios
import DomiciliosDashboard from "@/pages/domicilios/Dashboard";
import Zones from "@/pages/domicilios/Zones";
import BotConfig from "@/pages/domicilios/BotConfig";
import { type ReactNode } from "react";

const POLICY_VERSION = "1.0";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="h-8 w-8 rounded-full border-2 border-slate-900 border-t-transparent animate-spin" />
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  if (user.privacy_policy_version !== POLICY_VERSION) return <Navigate to="/accept-policy" replace />;
  return <Layout>{children}</Layout>;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/login"         element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/accept-policy" element={<AcceptPolicy />} />

          {/* ── Local branch ── */}
          <Route path="/"              element={<Protected><Dashboard /></Protected>} />
          <Route path="/agenda"        element={<Protected><Agenda /></Protected>} />
          <Route path="/pos"           element={<Protected><Pos /></Protected>} />
          <Route path="/clients"       element={<Protected><Clients branch="local" /></Protected>} />
          <Route path="/vehicles"      element={<Protected><Vehicles branch="local" /></Protected>} />
          <Route path="/services"      element={<Protected><Services branch="local" /></Protected>} />
          <Route path="/commissions"   element={<Protected><Commissions /></Protected>} />
          <Route path="/reports"       element={<Protected><Reports /></Protected>} />
          <Route path="/bot"           element={<Protected><Bot /></Protected>} />
          <Route path="/notifications" element={<Protected><Notifications /></Protected>} />
          <Route path="/integrations"  element={<Protected><Integrations /></Protected>} />
          <Route path="/orders"        element={<Protected><Orders branch="local" /></Protected>} />
          <Route path="/cash-sessions" element={<Protected><CashSessions branch="local" /></Protected>} />
          <Route path="/credits"       element={<Protected><Credits /></Protected>} />
          <Route path="/accounting"     element={<Protected><Accounting /></Protected>} />
          <Route path="/payroll"       element={<Protected><Payroll /></Protected>} />
          <Route path="/alta"          element={<Protected><ServiceEntry branch="local" /></Protected>} />
          <Route path="/team"          element={<Protected><Team /></Protected>} />

          {/* ── Domicilios branch ── */}
          <Route path="/domicilios"              element={<Protected><DomiciliosDashboard /></Protected>} />
          <Route path="/domicilios/orders"       element={<Protected><Orders branch="domicilios" /></Protected>} />
          <Route path="/domicilios/cash-sessions"element={<Protected><CashSessions branch="domicilios" /></Protected>} />
          <Route path="/domicilios/clients"      element={<Protected><Clients branch="domicilios" /></Protected>} />
          <Route path="/domicilios/vehicles"     element={<Protected><Vehicles branch="domicilios" /></Protected>} />
          <Route path="/domicilios/services"     element={<Protected><Services branch="domicilios" /></Protected>} />
          <Route path="/domicilios/alta"         element={<Protected><ServiceEntry branch="domicilios" /></Protected>} />
          <Route path="/domicilios/zones"        element={<Protected><Zones /></Protected>} />
          <Route path="/domicilios/commissions"  element={<Protected><Commissions /></Protected>} />
          <Route path="/domicilios/bot"          element={<Protected><BotConfig /></Protected>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
