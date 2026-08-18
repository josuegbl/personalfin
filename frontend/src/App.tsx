import { Routes, Route, NavLink } from "react-router-dom";
import { LayoutDashboard, ArrowLeftRight, Tag, RefreshCw, TrendingUp } from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Categories from "./pages/Categories";
import Forecast from "./pages/Forecast";
import { api } from "./api/client";
import { useState } from "react";

export default function App() {
  const [syncing, setSyncing] = useState(false);

  async function handleSyncAll() {
    setSyncing(true);
    try {
      await api.accounts.syncAll();
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-56 bg-gray-900 text-white flex-col">
        <div className="p-5 border-b border-gray-700">
          <h1 className="text-lg font-bold tracking-tight">💰 BankFinances</h1>
          <p className="text-xs text-gray-400 mt-0.5">Economía familiar</p>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          <NavItem to="/" icon={<LayoutDashboard size={16} />} label="Dashboard" />
          <NavItem to="/transactions" icon={<ArrowLeftRight size={16} />} label="Movimientos" />
          <NavItem to="/categories" icon={<Tag size={16} />} label="Categorías" />
          <NavItem to="/forecast" icon={<TrendingUp size={16} />} label="Previsión" />
        </nav>

        <div className="p-3 border-t border-gray-700">
          <button
            onClick={handleSyncAll}
            disabled={syncing}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Sincronizando…" : "Sincronizar todo"}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto pb-16 md:pb-0">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/forecast" element={<Forecast />} />
        </Routes>
      </main>

      {/* Bottom nav — mobile only */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-gray-900 border-t border-gray-700 flex">
        <NavItem to="/" icon={<LayoutDashboard size={20} />} label="Dashboard" mobile />
        <NavItem to="/transactions" icon={<ArrowLeftRight size={20} />} label="Movimientos" mobile />
        <NavItem to="/categories" icon={<Tag size={20} />} label="Categorías" mobile />
        <NavItem to="/forecast" icon={<TrendingUp size={20} />} label="Previsión" mobile />
        <button
          onClick={handleSyncAll}
          disabled={syncing}
          className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs text-gray-300 hover:text-white disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={20} className={syncing ? "animate-spin" : ""} />
          Sync
        </button>
      </nav>
    </div>
  );
}

function NavItem({
  to,
  icon,
  label,
  mobile = false,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  mobile?: boolean;
}) {
  if (mobile) {
    return (
      <NavLink
        to={to}
        end
        className={({ isActive }) =>
          `flex-1 flex flex-col items-center justify-center py-2 gap-0.5 text-xs transition-colors ${
            isActive ? "text-blue-400" : "text-gray-300 hover:text-white"
          }`
        }
      >
        {icon}
        {label}
      </NavLink>
    );
  }

  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
          isActive ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-700 hover:text-white"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
