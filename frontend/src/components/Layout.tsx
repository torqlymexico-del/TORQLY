import { type ReactNode } from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Users, Car, Wrench, Wallet, BarChart2, Bot,
  Plug, LogOut, Menu, X, ShoppingBag, BadgeDollarSign, DollarSign,
  Scissors, MapPin, Bell, Building2, Home, Bike,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

// ─── Branch definitions ───────────────────────────────────────────────────────

type Branch = "local" | "domicilios" | "arrendadoras";

const BRANCHES: { key: Branch; label: string; icon: typeof Home; color: string; activeColor: string }[] = [
  { key: "local",        label: "Local",       icon: Home,      color: "text-slate-500", activeColor: "bg-slate-900 text-white" },
  { key: "domicilios",   label: "Domicilios",  icon: Bike,      color: "text-slate-500", activeColor: "bg-blue-600 text-white" },
  { key: "arrendadoras", label: "Arrendadoras",icon: Building2, color: "text-slate-500", activeColor: "bg-violet-600 text-white" },
];

const NAV: Record<Branch, { to: string; icon: typeof LayoutDashboard; label: string }[]> = {
  local: [
    { to: "/",              icon: LayoutDashboard, label: "Dashboard" },
    { to: "/orders",        icon: ShoppingBag,     label: "Órdenes" },
    { to: "/cash-sessions", icon: Wallet,          label: "Caja" },
    { to: "/clients",       icon: Users,           label: "Clientes" },
    { to: "/vehicles",      icon: Car,             label: "Vehículos" },
    { to: "/services",      icon: Wrench,          label: "Catálogo" },
    { to: "/commissions",   icon: Scissors,        label: "Comisiones" },
    { to: "/credits",       icon: BadgeDollarSign, label: "Créditos" },
    { to: "/payroll",       icon: DollarSign,      label: "Nómina" },
    { to: "/reports",       icon: BarChart2,       label: "Reportes" },
    { to: "/notifications", icon: Bell,            label: "Notificaciones" },
    { to: "/integrations",  icon: Plug,            label: "Integraciones" },
  ],
  domicilios: [
    { to: "/domicilios",              icon: LayoutDashboard, label: "Dashboard" },
    { to: "/domicilios/orders",       icon: ShoppingBag,     label: "Órdenes" },
    { to: "/domicilios/cash-sessions",icon: Wallet,          label: "Caja" },
    { to: "/domicilios/clients",      icon: Users,           label: "Clientes" },
    { to: "/domicilios/vehicles",     icon: Car,             label: "Vehículos" },
    { to: "/domicilios/zones",        icon: MapPin,          label: "Zonas" },
    { to: "/domicilios/commissions",  icon: Scissors,        label: "Comisiones" },
    { to: "/domicilios/bot",          icon: Bot,             label: "Bot / Auto." },
  ],
  arrendadoras: [
    { to: "/arrendadoras", icon: LayoutDashboard, label: "Dashboard" },
  ],
};

const BRANCH_ROOT: Record<Branch, string> = {
  local:        "/",
  domicilios:   "/domicilios",
  arrendadoras: "/arrendadoras",
};

function getBranchFromPath(pathname: string): Branch {
  if (pathname.startsWith("/domicilios"))   return "domicilios";
  if (pathname.startsWith("/arrendadoras")) return "arrendadoras";
  return "local";
}

// ─── Sidebar link ─────────────────────────────────────────────────────────────

function SidebarLink({ to, icon: Icon, label, branch }: {
  to: string; icon: typeof LayoutDashboard; label: string; branch: Branch;
}) {
  const activeClass = {
    local:        "bg-slate-900 text-white",
    domicilios:   "bg-blue-600 text-white",
    arrendadoras: "bg-violet-600 text-white",
  }[branch];

  return (
    <NavLink
      to={to}
      end={to === "/" || to === "/domicilios" || to === "/arrendadoras"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive ? activeClass : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </NavLink>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const currentBranch = getBranchFromPath(location.pathname);
  const navItems = NAV[currentBranch];

  const branchAccent = {
    local:        "border-slate-200",
    domicilios:   "border-blue-200",
    arrendadoras: "border-violet-200",
  }[currentBranch];

  function switchBranch(branch: Branch) {
    navigate(BRANCH_ROOT[branch]);
    setOpen(false);
  }

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const sidebar = (
    <div className="flex h-full flex-col">

      {/* Branch switcher */}
      <div className="px-3 pt-4 pb-3 border-b border-slate-100">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-1 mb-2">Rama</p>
        <div className="space-y-1">
          {BRANCHES.map(b => {
            const Icon = b.icon;
            const isActive = currentBranch === b.key;
            const disabled = b.key === "arrendadoras";
            return (
              <button
                key={b.key}
                onClick={() => !disabled && switchBranch(b.key)}
                disabled={disabled}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all",
                  isActive ? b.activeColor : "text-slate-500 hover:bg-slate-100 hover:text-slate-800",
                  disabled && "opacity-40 cursor-not-allowed",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {b.label}
                {disabled && (
                  <span className="ml-auto text-[10px] font-bold bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded">
                    Pronto
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Logo + branch name */}
      <div className={cn("flex items-center gap-2 px-4 py-3 border-b", branchAccent)}>
        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0",
          currentBranch === "local" ? "bg-slate-900" : currentBranch === "domicilios" ? "bg-blue-600" : "bg-violet-600"
        )}>T</div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-slate-900 leading-none truncate">Torqly</p>
          <p className="text-xs text-slate-400 capitalize">{currentBranch}</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-2 overflow-y-auto">
        {navItems.map(item => (
          <SidebarLink key={item.to} {...item} branch={currentBranch} />
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-slate-200 p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 text-sm font-semibold shrink-0">
            {user?.name?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">{user?.name}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
            title="Cerrar sesión"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex w-56 flex-col border-r border-slate-200 bg-white">
        {sidebar}
      </aside>

      {/* Sidebar mobile overlay */}
      {open && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div className="fixed inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="relative z-50 w-56 bg-white h-full shadow-xl overflow-y-auto">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar mobile */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-white">
          <button
            onClick={() => setOpen(!open)}
            className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="font-semibold text-slate-900">Torqly</span>
          <span className={cn(
            "ml-1 text-xs font-bold px-2 py-0.5 rounded-full",
            currentBranch === "local" ? "bg-slate-100 text-slate-600" :
            currentBranch === "domicilios" ? "bg-blue-50 text-blue-700" :
            "bg-violet-50 text-violet-700"
          )}>
            {currentBranch}
          </span>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
