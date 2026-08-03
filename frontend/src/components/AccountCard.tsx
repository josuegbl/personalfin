import { Building2, Wallet, RefreshCw } from "lucide-react";
import type { AccountBalance } from "../types";
import { formatCurrency, formatDate } from "../utils/format";
import { api } from "../api/client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";

const PROVIDER_STYLES: Record<string, { bg: string; border: string; badge: string; icon: string }> = {
  BBVA: {
    bg: "bg-gradient-to-br from-blue-600 to-blue-800",
    border: "border-blue-500",
    badge: "bg-blue-900/50 text-blue-100",
    icon: "text-blue-200",
  },
  "Eurocaja Rural": {
    bg: "bg-gradient-to-br from-green-600 to-green-800",
    border: "border-green-500",
    badge: "bg-green-900/50 text-green-100",
    icon: "text-green-200",
  },
  PayPal: {
    bg: "bg-gradient-to-br from-indigo-600 to-sky-700",
    border: "border-sky-500",
    badge: "bg-sky-900/50 text-sky-100",
    icon: "text-sky-200",
  },
};

const DEFAULT_STYLE = {
  bg: "bg-gradient-to-br from-gray-600 to-gray-800",
  border: "border-gray-500",
  badge: "bg-gray-700 text-gray-200",
  icon: "text-gray-300",
};

export default function AccountCard({ data }: { data: AccountBalance }) {
  const { account, variacion_mes } = data;
  const style = PROVIDER_STYLES[account.proveedor] ?? DEFAULT_STYLE;
  const [syncing, setSyncing] = useState(false);
  const qc = useQueryClient();

  async function handleSync() {
    setSyncing(true);
    try {
      await api.accounts.sync(account.id);
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["dashboard"] });
        setSyncing(false);
      }, 2000);
    } catch {
      setSyncing(false);
    }
  }

  const isPayPal = account.tipo === "paypal";

  return (
    <div className={clsx("rounded-2xl p-5 text-white shadow-lg border", style.bg, style.border)}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className={clsx("p-2 rounded-lg bg-white/10", style.icon)}>
            {isPayPal ? <Wallet size={18} /> : <Building2 size={18} />}
          </div>
          <div>
            <p className="font-semibold text-sm">{account.alias}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <p className="text-xs opacity-70">{account.proveedor}</p>
              {account.propietario && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-white/15 font-medium">
                  {account.propietario}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          title="Sincronizar cuenta"
          className="p-1.5 rounded-lg hover:bg-white/10 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Balance */}
      <div className="mb-3">
        <p className="text-xs opacity-60 mb-0.5">Saldo actual</p>
        <p className="text-2xl font-bold tabular-nums">
          {formatCurrency(account.saldo_actual, account.moneda)}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs">
        <span className={clsx("px-2 py-0.5 rounded-full font-medium", style.badge)}>
          {account.tipo === "paypal" ? "PayPal" : account.iban ? `····${account.iban.slice(-4)}` : "Cuenta"}
        </span>
        <div className="flex items-center gap-1 opacity-60">
          {account.ultima_sync ? (
            <span>Sync {formatDate(account.ultima_sync)}</span>
          ) : (
            <span>Sin sincronizar</span>
          )}
        </div>
      </div>

      {/* Monthly variation */}
      {variacion_mes !== 0 && (
        <div className={clsx("mt-2 text-xs font-medium", variacion_mes > 0 ? "text-green-300" : "text-red-300")}>
          {variacion_mes > 0 ? "+" : ""}
          {formatCurrency(variacion_mes)} este mes
        </div>
      )}
    </div>
  );
}
