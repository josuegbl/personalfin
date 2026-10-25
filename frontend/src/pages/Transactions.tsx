import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, Search } from "lucide-react";
import { api } from "../api/client";
import { formatCurrency, formatDate } from "../utils/format";
import clsx from "clsx";

export default function Transactions() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [accountId, setAccountId] = useState<number | undefined>();
  const [transactionType, setTransactionType] = useState<"ingresos" | "gastos" | "">("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [datePreset, setDatePreset] = useState<"" | "3m" | "6m" | "1y" | "ytd" | "custom">("");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [page, setPage] = useState(1);

  const { data: accounts } = useQuery({ queryKey: ["accounts"], queryFn: api.accounts.list });
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: api.categories.list });
  const updateCategory = useMutation({
    mutationFn: ({ id, categoria_id }: { id: number; categoria_id: number }) =>
      api.transactions.update(id, { categoria_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["forecast"] });
    },
  });

  function resolvedDateRange(): { fecha_desde?: string; fecha_hasta?: string } {
    const today = new Date();
    const formatDateInput = (date: Date) =>
      `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    if (datePreset === "3m") start.setMonth(start.getMonth() - 3);
    else if (datePreset === "6m") start.setMonth(start.getMonth() - 6);
    else if (datePreset === "1y") start.setFullYear(start.getFullYear() - 1);
    else if (datePreset === "ytd") return { fecha_desde: `${today.getFullYear()}-01-01` };
    else if (datePreset === "custom") {
      return { fecha_desde: customFrom || undefined, fecha_hasta: customTo || undefined };
    } else return {};
    return { fecha_desde: formatDateInput(start) };
  }

  const dateRange = resolvedDateRange();
  const { data: transactions, isLoading } = useQuery({
    queryKey: ["transactions", accountId, search, transactionType, categoryId, datePreset, customFrom, customTo, page],
    queryFn: () =>
      api.transactions.list({
        account_id: accountId,
        concepto: search || undefined,
        tipo: transactionType || undefined,
        categoria_id: categoryId === "" ? undefined : categoryId,
        ...dateRange,
        page,
        page_size: 50,
      }),
  });

  function clearFilters() {
    setAccountId(undefined);
    setTransactionType("");
    setCategoryId("");
    setDatePreset("");
    setCustomFrom("");
    setCustomTo("");
    setPage(1);
  }

  const selectClass = "w-full px-2 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelClass = "block text-xs font-medium text-gray-500 mb-1";

  return (
    <div className="p-6 space-y-4 max-w-6xl mx-auto">
      <h2 className="text-xl font-bold text-gray-900">Movimientos</h2>

      <div className="flex flex-col gap-4 md:flex-row md:items-start">
        <aside className="w-full shrink-0 rounded-lg border border-gray-200 bg-white p-4 space-y-4 md:w-56">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Filtros</p>
          <div>
            <label className={labelClass} htmlFor="transactions-account">Cuenta</label>
            <select
              id="transactions-account"
              value={accountId ?? ""}
              onChange={(event) => { setAccountId(event.target.value ? Number(event.target.value) : undefined); setPage(1); }}
              className={selectClass}
            >
              <option value="">Todas</option>
              {accounts?.map((account) => <option key={account.id} value={account.id}>{account.alias}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="transactions-type">Tipo</label>
            <select
              id="transactions-type"
              value={transactionType}
              onChange={(event) => { setTransactionType(event.target.value as typeof transactionType); setPage(1); }}
              className={selectClass}
            >
              <option value="">Todos</option>
              <option value="ingresos">Ingresos</option>
              <option value="gastos">Gastos</option>
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="transactions-category">Categoría</label>
            <select
              id="transactions-category"
              value={categoryId}
              onChange={(event) => { setCategoryId(event.target.value ? Number(event.target.value) : ""); setPage(1); }}
              className={selectClass}
            >
              <option value="">Todas</option>
              {categories?.map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="transactions-period">Período</label>
            <select
              id="transactions-period"
              value={datePreset}
              onChange={(event) => { setDatePreset(event.target.value as typeof datePreset); setPage(1); }}
              className={selectClass}
            >
              <option value="">Todo el historial</option>
              <option value="ytd">Este año</option>
              <option value="1y">Últimos 12 meses</option>
              <option value="6m">Últimos 6 meses</option>
              <option value="3m">Últimos 3 meses</option>
              <option value="custom">Personalizado</option>
            </select>
            {datePreset === "custom" && (
              <div className="mt-2 space-y-2">
                <input
                  type="date"
                  aria-label="Fecha desde"
                  value={customFrom}
                  onChange={(event) => { setCustomFrom(event.target.value); setPage(1); }}
                  className={selectClass}
                />
                <input
                  type="date"
                  aria-label="Fecha hasta"
                  value={customTo}
                  onChange={(event) => { setCustomTo(event.target.value); setPage(1); }}
                  className={selectClass}
                />
              </div>
            )}
          </div>
          {(accountId !== undefined || transactionType !== "" || categoryId !== "" || datePreset !== "") && (
            <button type="button" onClick={clearFilters} className="text-xs text-blue-600 hover:underline">
              Limpiar filtros
            </button>
          )}
        </aside>

        <div className="min-w-0 flex-1 space-y-4">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar concepto o comercio…"
              value={search}
              onChange={(event) => { setSearch(event.target.value); setPage(1); }}
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

      {/* Table / Card list */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Cargando movimientos…</div>
        ) : !transactions?.length ? (
          <div className="p-8 text-center text-gray-400 text-sm">Sin movimientos</div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden sm:block">
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
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-500">{account?.alias ?? "—"}</td>
                        <td className="px-4 py-3">
                          <select
                            aria-label={`Categoría de ${t.concepto_original}`}
                            value={t.categoria_id ?? ""}
                            onChange={(e) => updateCategory.mutate({ id: t.id, categoria_id: Number(e.target.value) })}
                            disabled={updateCategory.isPending && updateCategory.variables?.id === t.id}
                            className="max-w-44 px-2 py-1 text-xs border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                          >
                            {categories?.map((category) => (
                              <option key={category.id} value={category.id}>
                                {category.icono ? `${category.icono} ` : ""}{category.nombre}
                              </option>
                            ))}
                          </select>
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
            </div>

            {/* Mobile card list */}
            <div className="sm:hidden divide-y divide-gray-100">
              {transactions.map((t) => {
                const isGasto = t.importe < 0;
                const account = accounts?.find((a) => a.id === t.account_id);
                return (
                  <div key={t.id} className="flex items-start gap-3 px-4 py-3">
                    <span className={clsx("p-1 rounded-full mt-0.5 shrink-0", isGasto ? "bg-red-50 text-red-500" : "bg-green-50 text-green-600")}>
                      {isGasto ? <ArrowDownLeft size={12} /> : <ArrowUpRight size={12} />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {t.comercio || t.concepto_original}
                        </p>
                        <span className={clsx("font-semibold tabular-nums shrink-0", isGasto ? "text-red-600" : "text-green-600")}>
                          {isGasto ? "" : "+"}{formatCurrency(t.importe)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-xs text-gray-400">{formatDate(t.fecha)}</span>
                        {account && <span className="text-xs text-gray-400">{account.alias}</span>}
                        <select
                          aria-label={`Categoría de ${t.concepto_original}`}
                          value={t.categoria_id ?? ""}
                          onChange={(e) => updateCategory.mutate({ id: t.id, categoria_id: Number(e.target.value) })}
                          disabled={updateCategory.isPending && updateCategory.variables?.id === t.id}
                          className="max-w-44 px-2 py-1 text-xs border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                        >
                          {categories?.map((category) => (
                            <option key={category.id} value={category.id}>
                              {category.icono ? `${category.icono} ` : ""}{category.nombre}
                            </option>
                          ))}
                        </select>
                        {t.recurrente && <span className="text-xs text-purple-500 font-medium">Recurrente</span>}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
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
      </div>
    </div>
  );
}
