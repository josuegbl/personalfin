import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plus, Trash2, Save, TrendingUp } from "lucide-react";
import clsx from "clsx";
import { api } from "../api/client";
import { formatCurrency } from "../utils/format";
import type { ForecastCategoryInput, ForecastData } from "../types";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

type Tab = "plan" | "exec";

function nextMonth(year: number, month: number): [number, number] {
  return month === 12 ? [year + 1, 1] : [year, month + 1];
}

function prevMonth(year: number, month: number): [number, number] {
  return month === 1 ? [year - 1, 12] : [year, month - 1];
}

function DiffBadge({ plan, real, invertSign = false }: { plan: number; real: number; invertSign?: boolean }) {
  const diff = real - plan;
  const isGood = invertSign ? diff >= 0 : diff <= 0;
  if (diff === 0) return <span className="text-gray-400 text-xs">—</span>;
  return (
    <span className={clsx("text-xs font-medium", isGood ? "text-green-600" : "text-red-500")}>
      {diff > 0 ? "+" : ""}{formatCurrency(diff)}
    </span>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{title}</h3>
  );
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx("bg-white rounded-xl border border-gray-200 p-5 shadow-sm", className)}>
      {children}
    </div>
  );
}

interface PlanTabProps {
  data: ForecastData;
  year: number;
  month: number;
  onSaved: () => void;
}

function PlanTab({ data, year, month, onSaved }: PlanTabProps) {
  const qc = useQueryClient();
  const [ingresosJosue, setIngresosJosue] = useState(data.ingresos_josue);
  const [ingresosAdi, setIngresosAdi] = useState(data.ingresos_adi);
  const [ingresosExtra, setIngresosExtra] = useState(data.ingresos_extra);
  const [categorias, setCategorias] = useState<ForecastCategoryInput[]>(
    data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: g.importe_planificado }))
  );
  const [saving, setSaving] = useState(false);
  const [newCatName, setNewCatName] = useState("");

  useEffect(() => {
    setIngresosJosue(data.ingresos_josue);
    setIngresosAdi(data.ingresos_adi);
    setIngresosExtra(data.ingresos_extra);
    setCategorias(
      data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: g.importe_planificado }))
    );
  }, [data]);

  const totalIngresos = ingresosJosue + ingresosAdi + ingresosExtra;
  const totalFijos = data.total_gastos_fijos_plan;
  const totalVariables = categorias.reduce((s, c) => s + c.importe_planificado, 0);
  const ahorro = totalIngresos - totalFijos - totalVariables;

  function updateCatAmount(index: number, value: number) {
    setCategorias((prev) => prev.map((c, i) => (i === index ? { ...c, importe_planificado: value } : c)));
  }

  function removeCat(index: number) {
    setCategorias((prev) => prev.filter((_, i) => i !== index));
  }

  function addCat() {
    const name = newCatName.trim();
    if (!name) return;
    setCategorias((prev) => [...prev, { nombre: name, importe_planificado: 0 }]);
    setNewCatName("");
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.forecast.save(year, month, {
        ingresos_josue: ingresosJosue,
        ingresos_adi: ingresosAdi,
        ingresos_extra: ingresosExtra,
        categorias,
      });
      qc.invalidateQueries({ queryKey: ["forecast", year, month] });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Revenues */}
      <Card>
        <SectionHeader title="Ingresos" />
        <div className="space-y-2">
          {[
            { label: "Josué", value: ingresosJosue, setter: setIngresosJosue },
            { label: "Adi", value: ingresosAdi, setter: setIngresosAdi },
            { label: "Extra", value: ingresosExtra, setter: setIngresosExtra },
          ].map(({ label, value, setter }) => (
            <div key={label} className="flex items-center justify-between gap-4">
              <span className="text-sm text-gray-700 w-20">{label}</span>
              <div className="relative flex-1 max-w-48">
                <input
                  type="number"
                  value={value}
                  onChange={(e) => setter(Number(e.target.value))}
                  className="w-full px-3 py-1.5 text-sm text-right border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums"
                  step="0.01"
                  min="0"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs pointer-events-none">€</span>
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100 mt-2">
            <span className="text-sm font-semibold text-gray-900">Total ingresos</span>
            <span className="text-sm font-bold text-green-600 tabular-nums">{formatCurrency(totalIngresos)}</span>
          </div>
        </div>
      </Card>

      {/* Fixed expenses */}
      <Card>
        <SectionHeader title={`Gastos fijos del mes (${data.gastos_fijos.length})`} />
        <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
          {data.gastos_fijos.map((item) => (
            <div key={item.nombre} className="flex items-center justify-between py-1 text-sm">
              <span className="text-gray-600 truncate max-w-[60%]">{item.nombre}</span>
              <span className="text-gray-800 tabular-nums">{formatCurrency(item.importe_planificado)}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-2">
          <span className="text-sm font-semibold text-gray-900">Total fijos</span>
          <span className="text-sm font-bold text-red-500 tabular-nums">{formatCurrency(totalFijos)}</span>
        </div>
      </Card>

      {/* Variable budgets */}
      <Card>
        <SectionHeader title="Gastos variables (presupuesto)" />
        <div className="space-y-2">
          {categorias.map((cat, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-sm text-gray-700 flex-1 truncate">{cat.nombre}</span>
              <div className="relative w-36">
                <input
                  type="number"
                  value={cat.importe_planificado}
                  onChange={(e) => updateCatAmount(index, Number(e.target.value))}
                  className="w-full px-3 py-1.5 text-sm text-right border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums"
                  step="0.01"
                  min="0"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs pointer-events-none">€</span>
              </div>
              <button
                onClick={() => removeCat(index)}
                className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        {/* Add category */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
          <input
            type="text"
            placeholder="Nueva categoría..."
            value={newCatName}
            onChange={(e) => setNewCatName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCat()}
            className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={addCat}
            disabled={!newCatName.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 disabled:opacity-40 transition-colors"
          >
            <Plus size={14} />
            Añadir
          </button>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-3">
          <span className="text-sm font-semibold text-gray-900">Total variables</span>
          <span className="text-sm font-bold text-orange-500 tabular-nums">{formatCurrency(totalVariables)}</span>
        </div>
      </Card>

      {/* Summary */}
      <Card className="bg-gray-50">
        <SectionHeader title="Resumen planificado" />
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Ingresos totales</span>
            <span className="font-medium text-green-600 tabular-nums">{formatCurrency(totalIngresos)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Gastos fijos</span>
            <span className="font-medium text-gray-800 tabular-nums">− {formatCurrency(totalFijos)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Gastos variables</span>
            <span className="font-medium text-gray-800 tabular-nums">− {formatCurrency(totalVariables)}</span>
          </div>
          <div className="flex justify-between pt-2 border-t border-gray-200 font-semibold text-base">
            <span className="text-gray-900">Ahorro estimado</span>
            <span className={clsx("tabular-nums", ahorro >= 0 ? "text-blue-600" : "text-red-500")}>
              {formatCurrency(ahorro)}
            </span>
          </div>
        </div>
      </Card>

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        <Save size={16} />
        {saving ? "Guardando…" : "Guardar planificación"}
      </button>
    </div>
  );
}

interface ExecRowProps {
  label: string;
  plan: number;
  real: number;
  colorScheme?: "income" | "expense" | "saving";
  bold?: boolean;
}

function ExecRow({ label, plan, real, colorScheme = "expense", bold = false }: ExecRowProps) {
  const diff = real - plan;
  const isGood = colorScheme === "income" || colorScheme === "saving" ? diff >= 0 : diff <= 0;
  const diffColor = diff === 0 ? "text-gray-400" : isGood ? "text-green-600" : "text-red-500";

  return (
    <tr className={clsx("border-b border-gray-50", bold && "bg-gray-50")}>
      <td className={clsx("py-2.5 px-4 text-sm", bold ? "font-semibold text-gray-900" : "text-gray-700")}>
        {label}
      </td>
      <td className="py-2.5 px-4 text-sm text-right tabular-nums text-gray-800">
        {formatCurrency(plan)}
      </td>
      <td className="py-2.5 px-4 text-sm text-right tabular-nums text-gray-800">
        {formatCurrency(real)}
      </td>
      <td className={clsx("py-2.5 px-4 text-sm text-right tabular-nums font-medium", diffColor)}>
        {diff === 0 ? "—" : `${diff > 0 ? "+" : ""}${formatCurrency(diff)}`}
      </td>
    </tr>
  );
}

interface ExecTabProps {
  data: ForecastData;
}

function ExecTab({ data }: ExecTabProps) {
  const [showCatDetail, setShowCatDetail] = useState(false);

  const totalGastosPlan = data.total_gastos_fijos_plan + data.total_gastos_variables_plan;

  const realCategoryMap = new Map(
    data.gastos_reales_por_categoria.map((c) => [c.nombre, c.importe_real])
  );

  const varCategoriesWithReal = data.gastos_variables.map((v) => ({
    nombre: v.nombre,
    plan: v.importe_planificado,
    real: realCategoryMap.get(v.nombre) ?? 0,
  }));

  const unplannedCategories = data.gastos_reales_por_categoria.filter(
    (c) => !data.gastos_variables.some((v) => v.nombre === c.nombre)
  );

  return (
    <div className="space-y-5">
      {/* Summary table */}
      <Card>
        <SectionHeader title="Resumen del mes" />
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              {["Concepto", "Planificado", "Real", "Diferencia"].map((h) => (
                <th
                  key={h}
                  className={clsx(
                    "pb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide",
                    h === "Concepto" ? "text-left px-4" : "text-right px-4"
                  )}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <ExecRow
              label="Ingresos"
              plan={data.total_ingresos_plan}
              real={data.ingresos_reales}
              colorScheme="income"
            />
            <ExecRow
              label="Gastos fijos"
              plan={data.total_gastos_fijos_plan}
              real={0}
              colorScheme="expense"
            />
            <ExecRow
              label="Gastos variables"
              plan={data.total_gastos_variables_plan}
              real={data.total_gastos_reales}
              colorScheme="expense"
            />
            <ExecRow
              label="Total gastos"
              plan={totalGastosPlan}
              real={data.total_gastos_reales}
              colorScheme="expense"
              bold
            />
            <ExecRow
              label="Ahorro"
              plan={data.ahorro_estimado}
              real={data.ahorro_real}
              colorScheme="saving"
              bold
            />
          </tbody>
        </table>
      </Card>

      {/* Variable category detail */}
      {data.gastos_variables.length > 0 && (
        <Card>
          <button
            onClick={() => setShowCatDetail((v) => !v)}
            className="w-full flex items-center justify-between mb-1"
          >
            <SectionHeader title="Variables por categoría" />
            <span className="text-xs text-blue-500 hover:underline -mt-3">
              {showCatDetail ? "Ocultar" : "Ver detalle"}
            </span>
          </button>
          {showCatDetail && (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  {["Categoría", "Planificado", "Real", "Diferencia"].map((h) => (
                    <th
                      key={h}
                      className={clsx(
                        "pb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide",
                        h === "Categoría" ? "text-left px-4" : "text-right px-4"
                      )}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {varCategoriesWithReal.map((cat) => (
                  <ExecRow
                    key={cat.nombre}
                    label={cat.nombre}
                    plan={cat.plan}
                    real={cat.real}
                    colorScheme="expense"
                  />
                ))}
                {unplannedCategories.map((cat) => (
                  <ExecRow
                    key={cat.nombre}
                    label={`${cat.nombre} (sin plan)`}
                    plan={0}
                    real={cat.importe_real}
                    colorScheme="expense"
                  />
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {/* Real category breakdown */}
      {data.gastos_reales_por_categoria.length > 0 && (
        <Card>
          <SectionHeader title="Gasto real por categoría" />
          <div className="space-y-2">
            {data.gastos_reales_por_categoria.map((item) => {
              const pct = data.total_gastos_reales > 0
                ? (item.importe_real / data.total_gastos_reales) * 100
                : 0;
              return (
                <div key={item.nombre}>
                  <div className="flex items-center justify-between text-sm mb-0.5">
                    <span className="text-gray-700 truncate max-w-[55%]">{item.nombre}</span>
                    <span className="tabular-nums text-gray-800">{formatCurrency(item.importe_real)}</span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-400 rounded-full"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {data.gastos_reales_por_categoria.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          <TrendingUp size={32} className="mx-auto mb-2 opacity-30" />
          Sin transacciones para este mes
        </div>
      )}
    </div>
  );
}

export default function Forecast() {
  const today = new Date();
  const [year, setYear] = useState(() => {
    const [y] = nextMonth(today.getFullYear(), today.getMonth() + 1);
    return y;
  });
  const [month, setMonth] = useState(() => {
    const [, m] = nextMonth(today.getFullYear(), today.getMonth() + 1);
    return m;
  });
  const [activeTab, setActiveTab] = useState<Tab>("plan");

  const { data, isLoading, error } = useQuery({
    queryKey: ["forecast", year, month],
    queryFn: () => api.forecast.get(year, month),
  });

  function handlePrev() {
    const [y, m] = prevMonth(year, month);
    setYear(y);
    setMonth(m);
  }

  function handleNext() {
    const [y, m] = nextMonth(year, month);
    setYear(y);
    setMonth(m);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error || !data) {
    return <p className="p-8 text-red-500">Error cargando previsión</p>;
  }

  return (
    <div className="p-6 space-y-5 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Previsión mensual</h2>
          <p className="text-sm text-gray-500 mt-0.5">Planifica y controla el presupuesto</p>
        </div>

        {/* Month selector */}
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrev}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm font-semibold text-gray-800 min-w-[110px] text-center">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={handleNext}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex rounded-xl border border-gray-200 p-1 bg-gray-50 gap-1">
        {(["plan", "exec"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
              activeTab === tab
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            )}
          >
            {tab === "plan" ? "Planificación" : "Ejecución"}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === "plan" ? (
        <PlanTab
          data={data}
          year={year}
          month={month}
          onSaved={() => setActiveTab("exec")}
        />
      ) : (
        <ExecTab data={data} />
      )}
    </div>
  );
}
