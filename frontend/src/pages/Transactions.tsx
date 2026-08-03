import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, Search } from "lucide-react";
import { api } from "../api/client";
import { formatCurrency, formatDate } from "../utils/format";
import clsx from "clsx";

export default function Transactions() {
  const [search, setSearch] = useState("");
  const [accountId, setAccountId] = useState<number | undefined>();
  const [page, setPage] = useState(1);

  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: api.accounts.list });
  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions", accountId, search, page],
    queryFn: () =>
      api.transactions.list({
        account_id: accountId,
        comercio: search || undefined,
        page,
        page_size: 50,
      }),
  });

  return (
    <div className="p-6 space-y-4 max-w-5xl mx-auto">
      <h2 className="text-xl font-bold text-gray-900">Movimientos</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar comercio…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={accountId ?? ""}
          onChange={(e) => { setAccountId(e.target.value ? Number(e.target.value) : undefined); setPage(1); }}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todas las cuentas</option>
          {accounts?.map((a) => (
            <option key={a.id} value={a.id}>{a.alias}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Cargando movimientos…</div>
        ) : !transactions?.length ? (
          <div className="p-8 text-center text-gray-400 text-sm">Sin movimientos</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Fecha</th>
                <th className="px-4 py-3 text-left">Concepto</th>
                <th className="px-4 py-3 text-left">Cuenta</th>
                <th className="px-4 py-3 text-left">Categoría</th>
                <th className="px-4 py-3 text-right">Importe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {transactions.map((t) => {
                const isGasto = t.importe < 0;
                const account = accounts?.find((a) => a.id === t.account_id);
                return (
                  <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(t.fecha)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={clsx("p-1 rounded-full", isGasto ? "bg-red-50 text-red-500" : "bg-green-50 text-green-600")}>
                          {isGasto ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                        </span>
                        <div>
                          <p className="text-gray-900 font-medium truncate max-w-xs">
                            {t.comercio || t.concepto_original}
                          </p>
                          {t.recurrente && (
                            <span className="text-xs text-purple-500 font-medium">Recurrente</span>
                          )}
                          {t.origen === "paypal" && (
                            <span className="ml-1 text-xs text-sky-500 font-medium">PayPal</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{account?.alias ?? "—"}</td>
                    <td className="px-4 py-3">
                      {t.categoria ? (
                        <span
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
                          style={{ background: t.categoria.color ?? "#94a3b8" }}
                        >
                          {t.categoria.icono} {t.categoria.nombre}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Sin categoría</span>
                      )}
                    </td>
                    <td className={clsx("px-4 py-3 text-right font-semibold tabular-nums", isGasto ? "text-red-600" : "text-green-600")}>
                      {isGasto ? "" : "+"}
                      {formatCurrency(t.importe)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>{transactions?.length ?? 0} movimientos</span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="px-3 py-1.5 font-medium">Página {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={(transactions?.length ?? 0) < 50}
            className="px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
}
