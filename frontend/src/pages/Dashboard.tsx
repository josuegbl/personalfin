import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown, PiggyBank, Wallet } from "lucide-react";
import { api } from "../api/client";
import AccountCard from "../components/AccountCard";
import StatTile from "../components/StatTile";
import { formatCurrency, shortMonth } from "../utils/format";
import { isAtOrBeforeMinMonth } from "../utils/dateLimits";

const MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function shiftMonth(year: number, month: number, offset: number): [number, number] {
  const value = year * 12 + month - 1 + offset;
  return [Math.floor(value / 12), (value % 12) + 1];
}

export default function Dashboard() {
  const [year, setYear] = useState(() => new Date().getFullYear());
  const [month, setMonth] = useState(() => new Date().getMonth() + 1);
  const [categoryView, setCategoryView] = useState<"month" | "year">("month");
  const today = new Date();
  const isCurrentMonth = year === today.getFullYear() && month === today.getMonth() + 1;
  const isMinMonth = isAtOrBeforeMinMonth(year, month);
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", year, month],
    queryFn: () => api.dashboard.get(year, month),
  });

  function moveMonth(offset: number) {
    const [nextYear, nextMonth] = shiftMonth(year, month, offset);
    setYear(nextYear);
    setMonth(nextMonth);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-red-500">
        Error cargando el dashboard: {error instanceof Error ? error.message : String(error)}
      </div>
    );
  }

  const { resumen_mes_actual: mes, saldo_por_cuenta, gastos_por_categoria, evolucion_mensual } = data;

  const chartData = evolucion_mensual.map((summary) => ({
    name: `${shortMonth(summary.mes)} ${String(summary.anio).slice(-2)}`,
    Ingresos: summary.ingresos,
    Gastos: summary.gastos,
    Ahorro: summary.ahorro,
  }));

  const monthlySavings = evolucion_mensual.filter(
    (summary) => summary.anio === year
      && summary.mes <= month
      && !(isCurrentMonth && summary.mes === month),
  );
  const accumulatedYear = monthlySavings.reduce((total, summary) => total + Number(summary.ahorro), 0);
  const categoryExpenses = categoryView === "month"
    ? gastos_por_categoria
    : data.gastos_por_categoria_anual;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page header */}
      <div className="space-y-3">
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => moveMonth(-1)}
            disabled={isMinMonth}
            title="Mes anterior"
            aria-label="Mes anterior"
            className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="min-w-28 text-center text-sm font-medium capitalize text-gray-700">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={() => moveMonth(1)}
            disabled={isCurrentMonth}
            title="Mes siguiente"
            aria-label="Mes siguiente"
            className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      {/* ── SALDOS POR CUENTA ─────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Saldos por cuenta
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {saldo_por_cuenta.map((sb) => (
            <AccountCard key={sb.account.id} data={sb} />
          ))}
        </div>

        {/* Total unificado */}
        <div className="mt-3 bg-white rounded-xl border border-gray-200 px-5 py-3 flex items-center justify-between shadow-sm">
          <span className="text-sm text-gray-500 font-medium">Saldo total (todas las cuentas)</span>
          <span className="text-2xl font-bold text-gray-900 tabular-nums">
            {formatCurrency(data.saldo_total)}
          </span>
        </div>
      </section>

      {/* ── RESUMEN DEL MES ───────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Resumen del mes
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatTile
            label="Ingresos"
            value={formatCurrency(mes.ingresos)}
            color="green"
            icon={<TrendingUp size={14} />}
          />
          <StatTile
            label="Gastos"
            value={formatCurrency(mes.gastos)}
            color="red"
            icon={<TrendingDown size={14} />}
          />
          <StatTile
            label="Ahorro"
            value={formatCurrency(mes.ahorro)}
            sub={mes.ingresos > 0 ? `${((mes.ahorro / mes.ingresos) * 100).toFixed(0)}% de los ingresos` : undefined}
            color={mes.ahorro >= 0 ? "blue" : "red"}
            icon={<PiggyBank size={14} />}
          />
          <StatTile
            label="Movimientos"
            value={String(mes.num_transacciones)}
            color="gray"
            icon={<Wallet size={14} />}
          />
        </div>
      </section>

      {/* ── GRÁFICAS ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Evolución mensual */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Evolución mensual (12 meses)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barSize={10} barGap={2}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                formatter={(v: number) => formatCurrency(v)}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="Ingresos" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Gastos" fill="#f87171" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Ahorro" fill="#60a5fa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Ahorro mes a mes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col min-h-0">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Ahorro mes a mes · {year}</h3>
          {monthlySavings.length > 0 ? (
            <>
              <div className="divide-y divide-gray-100 flex-1 overflow-y-auto">
                {monthlySavings.map((summary) => (
                  <div key={`${summary.anio}-${summary.mes}`} className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-600">{MONTH_NAMES[summary.mes - 1]}</span>
                    <span className={`text-sm font-semibold tabular-nums ${summary.ahorro >= 0 ? "text-green-600" : "text-red-500"}`}>
                      {formatCurrency(summary.ahorro)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-gray-200 pt-3 flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-700">Total acumulado</span>
                <span className={`text-base font-bold tabular-nums ${accumulatedYear >= 0 ? "text-green-600" : "text-red-500"}`}>
                  {formatCurrency(accumulatedYear)}
                </span>
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">Sin datos acumulados</p>
          )}
        </div>
      </div>

      {/* ── TOP GASTOS POR CATEGORÍA ──────────────────────────── */}
      <section className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 pt-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Desglose por categoría</h3>
          <div role="tablist" aria-label="Período del desglose" className="flex gap-5">
            <button
              type="button"
              role="tab"
              aria-selected={categoryView === "month"}
              onClick={() => setCategoryView("month")}
              className={`pb-2 text-sm border-b-2 ${categoryView === "month" ? "border-blue-600 text-blue-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >
              Mes
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={categoryView === "year"}
              onClick={() => setCategoryView("year")}
              className={`pb-2 text-sm border-b-2 ${categoryView === "year" ? "border-blue-600 text-blue-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >
              Acumulado del año
            </button>
          </div>
        </div>
        {categoryExpenses.length > 0 ? (
          <div className="divide-y divide-gray-50">
            {categoryExpenses.map((category) => (
              <div key={category.categoria_id ?? category.categoria_nombre} className="flex items-center gap-3 px-5 py-3">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: category.color ?? "#94a3b8" }} />
                <span className="flex-1 min-w-0 text-sm text-gray-700 truncate">{category.categoria_nombre}</span>
                <span className="text-xs text-gray-400 w-12 text-right">{category.porcentaje}%</span>
                <div className="hidden sm:block h-1.5 rounded-full bg-gray-100 w-24 overflow-hidden">
                  <div className="h-full" style={{ width: `${category.porcentaje}%`, background: category.color ?? "#94a3b8" }} />
                </div>
                <span className="text-sm font-semibold text-gray-900 w-28 text-right tabular-nums">
                  {formatCurrency(category.importe)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-5 py-8 text-center text-sm text-gray-400">
            {categoryView === "month" ? "Sin gastos este mes" : "Sin gastos acumulados este año"}
          </p>
        )}
      </section>
    </div>
  );
}
