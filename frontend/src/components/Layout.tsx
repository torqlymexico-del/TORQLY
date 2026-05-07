import { type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, CalendarDays, Users, Car, Wrench,
  CreditCard, Scissors, BarChart2, Bell, Bot, Plug, LogOut, Menu, X,
  ShoppingBag, Wallet, BadgeDollarSign, DollarSign, ClipboardPlus,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/",            icon: LayoutDashboard, label: "Dashboard" },
  { to: "/agenda",      icon: CalendarDays,    label: "Agenda" },
  { to: "/pos",         icon: CreditCard,      label: "POS / Cobros" },
  { to: "/clients",     icon: Users,           label: "Clientes" },
  { to: "/vehicles",    icon: Car,             label: "Vehículos" },
  { to: "/services",    icon: Wrench,          label: "Servicios" },
  { to: "/alta",          icon: ClipboardPlus,   label: "Alta de autos" },
  { to: "/orders",        icon: ShoppingBag,     label: "Órdenes" },
  { to: "/cash-sessions", icon: Wallet,          label: "Caja" },
  { to: "/credits",       icon: BadgeDollarSign, label: "Créditos" },
  { to: "/payroll",       icon: DollarSign,      label: "Nómina" },
  { to: "/commissions",   icon: Scissors,        label: "Comisiones" },
  { to: "/reports",       icon: BarChart2,       label: "Reportes" },
  { to: "/bot",         icon: Bot,             label: "Bot interno" },
  { to: "/notifications", icon: Bell,          label: "Notificaciones" },
  { to: "/integrations", icon: Plug,          label: "Integraciones" },
];

function SidebarLink({ to, icon: Icon, label }: { to: string; icon: typeof LayoutDashboard; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-slate-900 text-white"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </NavLink>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const sidebar = (
    <div className="flex h-full flex-col gap-2">
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-slate-200">
        <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white text-sm font-bold">T</div>
        <div>
          <p className="text-sm font-semibold text-slate-900 leading-none">Torqly</p>
          <p className="text-xs text-slate-400">El Garagillo</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-2 overflow-y-auto">
        {nav.map((item) => (
          <SidebarLink key={item.to} {...item} />
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
          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={handleLogout} title="Cerrar sesión">
            <LogOut className="h-4 w-4" />
          </Button>
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
          <aside className="relative z-50 w-56 bg-white h-full shadow-xl">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar mobile */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-white">
          <Button variant="ghost" size="icon" onClick={() => setOpen(!open)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <span className="font-semibold text-slate-900">Torqly</span>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
