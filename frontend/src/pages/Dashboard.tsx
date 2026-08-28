import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { TrendingUp, TrendingDown, PiggyBank, Wallet } from "lucide-react";
import { api } from "../api/client";
import AccountCard from "../components/AccountCard";
import StatTile from "../components/StatTile";
import { formatCurrency, shortMonth } from "../utils/format";

const MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard.get,
  });

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

  const chartData = evolucion_mensual.map((m) => ({
    name: shortMonth(m.mes),
    Ingresos: m.ingresos,
    Gastos: m.gastos,
    Ahorro: m.ahorro,
  }));

  const pieData = gastos_por_categoria.slice(0, 8).map((c) => ({
    name: c.categoria_nombre,
    value: c.importe,
    color: c.color ?? "#94a3b8",
  }));

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString("es-ES", { month: "long", year: "numeric" })}
        </p>
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

        {/* Gastos por categoría */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Gastos por categoría</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} contentStyle={{ fontSize: 11 }} />
                <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">Sin datos este mes</p>
          )}
        </div>
      </div>

      {/* ── TOP GASTOS POR CATEGORÍA ──────────────────────────── */}
      {gastos_por_categoria.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700">Desglose por categoría</h3>
          </div>
          <div className="divide-y divide-gray-50">
            {gastos_por_categoria.map((c, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-3">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ background: c.color ?? "#94a3b8" }}
                />
                <span className="flex-1 text-sm text-gray-700">{c.categoria_nombre}</span>
                <span className="text-xs text-gray-400 w-12 text-right">{c.porcentaje}%</span>
                <div
                  className="h-1.5 rounded-full bg-gray-100 w-24 overflow-hidden"
                >
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${c.porcentaje}%`, background: c.color ?? "#94a3b8" }}
                  />
                </div>
                <span className="text-sm font-semibold text-gray-900 w-28 text-right tabular-nums">
                  {formatCurrency(c.importe)}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
