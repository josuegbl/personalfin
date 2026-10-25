import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronDown, ChevronLeft, ChevronRight, Lock, Plus, Trash2, TrendingUp, X, Pencil } from "lucide-react";
import clsx from "clsx";
import { api } from "../api/client";
import { formatCurrency, formatLocaleNumberInput, parseLocaleNumberInput } from "../utils/format";
import type { Category, ForecastData } from "../types";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

type ForecastMode = "forecast" | "balance";

function nextMonth(year: number, month: number): [number, number] {
  return month === 12 ? [year + 1, 1] : [year, month + 1];
}

function prevMonth(year: number, month: number): [number, number] {
  return month === 1 ? [year - 1, 12] : [year, month - 1];
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

function ExpenseEditPanel({
  children,
  saving,
  onCancel,
  onConfirm,
  disabled = false,
}: {
  children: React.ReactNode;
  saving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="mb-2 rounded-xl border border-blue-100 bg-blue-50/40 p-3 space-y-3">
      {children}
      <div className="flex gap-2 justify-end">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Cancelar
        </button>
        <button
          onClick={onConfirm}
          disabled={disabled || saving}
          className={CONFIRM_BUTTON_CLASS}
        >
          {saving ? "Guardando…" : "Confirmar"}
        </button>
      </div>
    </div>
  );
}

const MONTH_ABBREVS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const CONFIRM_BUTTON_CLASS = "px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors";

type TierDraft = { importe: string; meses: number[] | null };
type CatDraft = { nombre: string; importe_planificado: string };
type PlanValueKey = "cuenta_personal_a" | "cuenta_personal_b" | "ingresos_persona_a" | "ingresos_persona_b";

type FixedDraft = { id: number; categoria: string; nombre: string; tiers: TierDraft[] };
type EditDraft = { concepto: string; tiers: TierDraft[] };

function parseAmount(s: string): number {
  return parseLocaleNumberInput(s);
}

function formatAmountEsInput(value: string): string {
  return formatLocaleNumberInput(value);
}

type MoneyInputProps = {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
};

function MoneyInput({ value, onValueChange, placeholder, autoFocus, className }: MoneyInputProps) {
  return (
    <div className={clsx("relative", className)}>
      <input
        type="text"
        inputMode="decimal"
        value={value}
        placeholder={placeholder}
        autoFocus={autoFocus}
        onChange={(event) => onValueChange(event.target.value)}
        onBlur={(event) => onValueChange(formatAmountEsInput(event.target.value))}
        className="w-full pl-3 pr-10 py-1.5 text-sm text-right border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums bg-white"
      />
      <span
        aria-hidden="true"
        className="absolute inset-y-0 right-0 flex items-center px-2 text-gray-500 text-xs pointer-events-none select-none border-l border-gray-200 bg-gray-50 rounded-r-lg"
      >
        €
      </span>
    </div>
  );
}

function PlannedAmountRow({
  label,
  value,
  editing,
  editValue,
  deleteConfirmation,
  saving,
  onStartEdit,
  onEditValueChange,
  onConfirmEdit,
  onCancelEdit,
  onRequestDelete,
  onConfirmDelete,
  onCancelDelete,
}: {
  label: string;
  value: string;
  editing: boolean;
  editValue: string;
  deleteConfirmation: boolean;
  saving: boolean;
  onStartEdit: () => void;
  onEditValueChange: (value: string) => void;
  onConfirmEdit: () => void;
  onCancelEdit: () => void;
  onRequestDelete: () => void;
  onConfirmDelete: () => void;
  onCancelDelete: () => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 py-1.5">
        <span className="text-sm text-gray-700 flex-1 min-w-0 truncate">{label}</span>
        <span className="text-sm tabular-nums text-gray-800 shrink-0">
          {formatCurrency(parseAmount(value))}
        </span>
        {!editing && (
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={onStartEdit}
              title={`Editar ${label}`}
              aria-label={`Editar ${label}`}
              className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-300 hover:text-blue-500 transition-colors"
            >
              <Pencil size={14} />
            </button>
            {deleteConfirmation ? (
              <>
                <button
                  onClick={onConfirmDelete}
                  disabled={saving}
                  className="px-2 py-1 text-xs rounded-md bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
                >
                  {saving ? "Borrando…" : "Borrar"}
                </button>
                <button
                  onClick={onCancelDelete}
                  disabled={saving}
                  className="px-2 py-1 text-xs rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                >
                  No
                </button>
              </>
            ) : (
              <button
                onClick={onRequestDelete}
                title={`Eliminar ${label}`}
                aria-label={`Eliminar ${label}`}
                className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        )}
      </div>
      {editing && (
        <ExpenseEditPanel
          saving={saving}
          onCancel={onCancelEdit}
          onConfirm={onConfirmEdit}
        >
          <MoneyInput value={editValue} onValueChange={onEditValueChange} autoFocus />
        </ExpenseEditPanel>
      )}
    </div>
  );
}

function getTierForMonth(tiers: TierDraft[], month: number): TierDraft | null {
  const specific = tiers.find(t => t.meses !== null && t.meses.includes(month));
  if (specific) return specific;
  return tiers.find(t => t.meses === null) ?? null;
}

interface PlanTabProps {
  data: ForecastData;
  year: number;
  month: number;
}

function PlanTab({ data, year, month }: PlanTabProps) {
  const qc = useQueryClient();
  const { data: allCategories } = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories.list,
  });
  const [ingresosPersonaA, setIngresosPersonaA] = useState(String(data.ingresos_persona_a));
  const [ingresosPersonaB, setIngresosPersonaB] = useState(String(data.ingresos_persona_b));
  const [personalPersonaA, setPersonalPersonaA] = useState(String(data.cuenta_personal_a));
  const [personalPersonaB, setPersonalPersonaB] = useState(String(data.cuenta_personal_b));
  const [categorias, setCategorias] = useState<CatDraft[]>(
    data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: String(g.importe_planificado) }))
  );
  const [fijos, setFijos] = useState<FixedDraft[]>(
    data.gastos_fijos_por_categoria.flatMap((group) =>
      group.subcategorias
        .filter((g) => g.id !== undefined)
        .map((g) => ({
          id: g.id!,
          categoria: group.categoria,
          nombre: g.nombre,
          tiers: (g.tiers ?? []).map((t) => ({ importe: String(t.importe), meses: t.meses ?? null })),
        }))
    )
  );
  const [saving, setSaving] = useState(false);
  const [showNewFijo, setShowNewFijo] = useState(false);
  const [newFijoCategoria, setNewFijoCategoria] = useState("");
  const [newFijoSubcategoria, setNewFijoSubcategoria] = useState("");
  const [newFijoTiers, setNewFijoTiers] = useState<TierDraft[]>([{ importe: "", meses: null }]);
  const [addingFijo, setAddingFijo] = useState(false);
  const [showNewVariable, setShowNewVariable] = useState(false);
  const [newVariableCategoria, setNewVariableCategoria] = useState("");
  const [newVariableAmount, setNewVariableAmount] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [editingFijoId, setEditingFijoId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>({ concepto: "", tiers: [] });
  const [savingEdit, setSavingEdit] = useState(false);
  const [editingPlanLine, setEditingPlanLine] = useState<string | null>(null);
  const [planLineDraft, setPlanLineDraft] = useState("");
  const [confirmDeletePlanLine, setConfirmDeletePlanLine] = useState<string | null>(null);
  const [savingPlanLine, setSavingPlanLine] = useState(false);

  useEffect(() => {
    setIngresosPersonaA(String(data.ingresos_persona_a));
    setIngresosPersonaB(String(data.ingresos_persona_b));
    setPersonalPersonaA(String(data.cuenta_personal_a));
    setPersonalPersonaB(String(data.cuenta_personal_b));
    setCategorias(data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: String(g.importe_planificado) })));
    setFijos(data.gastos_fijos_por_categoria.flatMap((group) =>
      group.subcategorias
        .filter((g) => g.id !== undefined)
        .map((g) => ({
          id: g.id!,
          categoria: group.categoria,
          nombre: g.nombre,
          tiers: (g.tiers ?? []).map((t) => ({ importe: String(t.importe), meses: t.meses ?? null })),
        }))
    ));
    setEditingFijoId(null);
    setEditingPlanLine(null);
    setConfirmDeletePlanLine(null);
    setNewFijoCategoria(parentCategoryOptions[0] ?? "");
    setShowNewVariable(false);
    setNewVariableCategoria(parentCategoryOptions[0] ?? "");
    setNewVariableAmount("");
  }, [data, year, month]);

  const totalPersonal = parseAmount(personalPersonaA) + parseAmount(personalPersonaB);
  const ingresosNomina = parseAmount(ingresosPersonaA) + parseAmount(ingresosPersonaB);
  const totalFijos = fijos.reduce((s, f) => {
    const tier = getTierForMonth(f.tiers, month);
    return s + (tier ? parseAmount(tier.importe) : 0);
  }, 0);
  const totalVariables = categorias.reduce((s, c) => s + parseAmount(c.importe_planificado), 0);
  const ahorro = ingresosNomina - totalPersonal - totalFijos - totalVariables;
  const fixedCategoriesForMonth = Array.from(new Set(
    fijos.map((expense) => expense.categoria)
  )).sort((first, second) => first.localeCompare(second, "es"));
  const parentCategories = allCategories
    ?.filter((category) => category.padre_id === null)
    .sort((first, second) => first.nombre.localeCompare(second.nombre, "es")) ?? [];
  const parentCategoryOptions = parentCategories.map((category) => category.nombre);

  function subcategoriesFor(parentName: string): Category[] {
    const parent = parentCategories.find((category) => category.nombre === parentName);
    if (!parent) return [];
    return allCategories
      ?.filter((category) => category.padre_id === parent.id)
      .sort((first, second) => first.nombre.localeCompare(second.nombre, "es")) ?? [];
  }

  const newFijoSubcategoryOptions = subcategoriesFor(newFijoCategoria);

  useEffect(() => {
    const defaultCategory = parentCategoryOptions[0] ?? "";
    if (!parentCategoryOptions.includes(newFijoCategoria)) {
      setNewFijoCategoria(defaultCategory);
    }
    const subcategories = subcategoriesFor(newFijoCategoria || defaultCategory);
    if (!subcategories.some((category) => category.nombre === newFijoSubcategoria)) {
      setNewFijoSubcategoria(subcategories[0]?.nombre ?? "");
    }
    if (!allCategories?.some((category) => category.nombre === newVariableCategoria)) {
      setNewVariableCategoria(defaultCategory);
    }
  }, [allCategories, newFijoCategoria, newFijoSubcategoria]);


  async function handleAddVariableCategory() {
    const category = newVariableCategoria.trim();
    if (!category) return;
    const amount = String(parseAmount(newVariableAmount));
    const existingIdx = categorias.findIndex((c) => c.nombre === category);
    const nextCategories = existingIdx >= 0
      ? categorias.map((item, index) => index === existingIdx ? { ...item, importe_planificado: amount } : item)
      : [...categorias, { nombre: category, importe_planificado: amount }];
    await handleSave(nextCategories);
    setCategorias(nextCategories);
    setShowNewVariable(false);
    setNewVariableCategoria(parentCategoryOptions[0] ?? "");
    setNewVariableAmount("");
  }

  async function handleDeleteFijo(id: number) {
    await api.recurringExpenses.delete(id);
    setFijos((prev) => prev.filter((f) => f.id !== id));
    await handleSave();
    setConfirmDeleteId(null);
  }

  function startEditFijo(fijo: FixedDraft) {
    setEditingFijoId(fijo.id);
    setEditingPlanLine(null);
    setEditDraft({ concepto: fijo.nombre, tiers: fijo.tiers.map(t => ({ ...t })) });
    setConfirmDeleteId(null);
    setShowNewFijo(false);
  }

  function setPlanFieldValue(key: PlanValueKey, value: string) {
    switch (key) {
      case "ingresos_persona_a": setIngresosPersonaA(value); break;
      case "ingresos_persona_b": setIngresosPersonaB(value); break;
      case "cuenta_personal_a": setPersonalPersonaA(value); break;
      case "cuenta_personal_b": setPersonalPersonaB(value); break;
    }
  }

  function startEditPlanLine(key: string, value: string) {
    setEditingPlanLine(key);
    setPlanLineDraft(value);
    setConfirmDeletePlanLine(null);
    setEditingFijoId(null);
    setConfirmDeleteId(null);
    setShowNewFijo(false);
    setShowNewVariable(false);
  }

  async function handleSavePlanLine(key: string) {
    setSavingPlanLine(true);
    try {
      const value = String(parseAmount(planLineDraft));
      if (key.startsWith("variable:")) {
        const categoryName = key.slice("variable:".length);
        const nextCategories = categorias.map((category) => category.nombre === categoryName
          ? { ...category, importe_planificado: value }
          : category
        );
        await handleSave(nextCategories);
        setCategorias(nextCategories);
      } else {
        const field = key.slice("plan:".length) as PlanValueKey;
        await handleSave(categorias, { [field]: parseAmount(planLineDraft) }, [field]);
        setPlanFieldValue(field, value);
      }
      setEditingPlanLine(null);
    } finally {
      setSavingPlanLine(false);
    }
  }

  async function handleDeletePlanLine(key: string) {
    setSavingPlanLine(true);
    try {
      if (key.startsWith("variable:")) {
        const categoryName = key.slice("variable:".length);
        const nextCategories = categorias.filter((category) => category.nombre !== categoryName);
        await handleSave(nextCategories);
        setCategorias(nextCategories);
      } else {
        const field = key.slice("plan:".length) as PlanValueKey;
        await handleSave(categorias, { [field]: 0 }, [field]);
        setPlanFieldValue(field, "0");
      }
      setConfirmDeletePlanLine(null);
    } finally {
      setSavingPlanLine(false);
    }
  }

  // --- Edit tier helpers ---

  function updateEditTierImporte(i: number, val: string) {
    setEditDraft(p => ({ ...p, tiers: p.tiers.map((t, j) => j === i ? { ...t, importe: val } : t) }));
  }

  function updateEditTierMeses(i: number, meses: number[] | null) {
    setEditDraft(p => ({ ...p, tiers: p.tiers.map((t, j) => j === i ? { ...t, meses } : t) }));
  }

  function toggleEditTierMes(tierIdx: number, m: number) {
    setEditDraft(p => {
      const tiers = p.tiers.map((t, i) => {
        if (i !== tierIdx) return t;
        const cur = t.meses ?? [];
        const next = cur.includes(m) ? cur.filter(x => x !== m) : [...cur, m];
        return { ...t, meses: next.length === 0 ? null : next.sort((a, b) => a - b) };
      });
      return { ...p, tiers };
    });
  }

  function removeEditTier(i: number) {
    setEditDraft(p => ({ ...p, tiers: p.tiers.filter((_, j) => j !== i) }));
  }

  function addEditTier() {
    setEditDraft(p => ({ ...p, tiers: [...p.tiers, { importe: "", meses: null }] }));
  }

  // --- New fijo tier helpers ---

  function updateNewFijoTierImporte(i: number, val: string) {
    setNewFijoTiers(p => p.map((t, j) => j === i ? { ...t, importe: val } : t));
  }

  function updateNewFijoTierMeses(i: number, meses: number[] | null) {
    setNewFijoTiers(p => p.map((t, j) => j === i ? { ...t, meses } : t));
  }

  function toggleNewFijoTierMes(tierIdx: number, m: number) {
    setNewFijoTiers(p => p.map((t, i) => {
      if (i !== tierIdx) return t;
      const cur = t.meses ?? [];
      const next = cur.includes(m) ? cur.filter(x => x !== m) : [...cur, m];
      return { ...t, meses: next.length === 0 ? null : next.sort((a, b) => a - b) };
    }));
  }

  function removeNewFijoTier(i: number) {
    setNewFijoTiers(p => p.filter((_, j) => j !== i));
  }

  function addNewFijoTier() {
    setNewFijoTiers(p => [...p, { importe: "", meses: null }]);
  }

  async function handleSaveEditFijo() {
    if (editingFijoId === null) return;
    const current = fijos.find((f) => f.id === editingFijoId);
    if (!current) return;
    setSavingEdit(true);
    try {
      const updated = await api.recurringExpenses.update(editingFijoId, {
        categoria: current.categoria,
        concepto: editDraft.concepto.trim(),
        tiers: editDraft.tiers.map(t => ({ importe: parseAmount(t.importe), meses: t.meses })),
      });
      setFijos(prev =>
        prev
          .map(f => f.id === editingFijoId
            ? {
                ...f,
                categoria: updated.categoria ?? f.categoria,
                nombre: updated.concepto,
                tiers: updated.tiers.map(t => ({ importe: String(t.importe), meses: t.meses ?? null })),
              }
            : f
          )
          .filter(f => {
            if (f.id !== editingFijoId) return true;
            return getTierForMonth(f.tiers, month) !== null;
          })
      );
      setEditingFijoId(null);
      await handleSave();
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleAddFijo() {
    if (!newFijoCategoria || !newFijoSubcategoria) return;
    setAddingFijo(true);
    try {
      const created = await api.recurringExpenses.create({
        categoria: newFijoCategoria,
        concepto: newFijoSubcategoria,
        tiers: newFijoTiers.map(t => ({ importe: parseAmount(t.importe), meses: t.meses })),
      });
      const tierDrafts = created.tiers.map(t => ({ importe: String(t.importe), meses: t.meses ?? null }));
      setFijos(prev => [...prev, {
        id: created.id,
        categoria: created.categoria ?? newFijoCategoria,
        nombre: created.concepto,
        tiers: tierDrafts,
      }]);
      await handleSave();
      setNewFijoCategoria(parentCategoryOptions[0] ?? "");
      setNewFijoSubcategoria("");
      setNewFijoTiers([{ importe: "", meses: null }]);
      setShowNewFijo(false);
    } finally {
      setAddingFijo(false);
    }
  }

  async function handleSave(
    categoriesToSave = categorias,
    valueOverrides: Partial<Record<PlanValueKey, number>> = {},
    fieldsToPropagate: PlanValueKey[] = [],
  ) {
    setSaving(true);
    try {
      await api.forecast.save(year, month, {
        cuenta_personal_a: valueOverrides.cuenta_personal_a ?? parseAmount(personalPersonaA),
        cuenta_personal_b: valueOverrides.cuenta_personal_b ?? parseAmount(personalPersonaB),
        ingresos_persona_a: valueOverrides.ingresos_persona_a ?? parseAmount(ingresosPersonaA),
        ingresos_persona_b: valueOverrides.ingresos_persona_b ?? parseAmount(ingresosPersonaB),
        categorias: categoriesToSave.map((c) => ({ nombre: c.nombre, importe_planificado: parseAmount(c.importe_planificado) })),
        ...(fieldsToPropagate.length > 0 && { propagar_campos: fieldsToPropagate }),
      });
      await qc.invalidateQueries({ queryKey: ["forecast"] });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Ingresos */}
      <Card>
        <SectionHeader title="Ingresos" />
        <div className="space-y-2">
          {[
            { key: "ingresos_persona_a" as const, label: "Persona A", value: ingresosPersonaA },
            { key: "ingresos_persona_b" as const, label: "Persona B", value: ingresosPersonaB },
          ].map(({ key, label, value }) => {
            const lineKey = `plan:${key}`;
            return (
              <PlannedAmountRow
                key={key}
                label={label}
                value={value}
                editing={editingPlanLine === lineKey}
                editValue={planLineDraft}
                deleteConfirmation={confirmDeletePlanLine === lineKey}
                saving={savingPlanLine}
                onStartEdit={() => startEditPlanLine(lineKey, value)}
                onEditValueChange={setPlanLineDraft}
                onConfirmEdit={() => handleSavePlanLine(lineKey)}
                onCancelEdit={() => setEditingPlanLine(null)}
                onRequestDelete={() => setConfirmDeletePlanLine(lineKey)}
                onConfirmDelete={() => handleDeletePlanLine(lineKey)}
                onCancelDelete={() => setConfirmDeletePlanLine(null)}
              />
            );
          })}
        </div>
      </Card>

      {/* Ingresos personales */}
      <Card>
        <SectionHeader title="Ingresos personales" />
        <div className="space-y-2">
          {[
            { key: "cuenta_personal_a" as const, label: "Persona A", value: personalPersonaA },
            { key: "cuenta_personal_b" as const, label: "Persona B", value: personalPersonaB },
          ].map(({ key, label, value }) => {
            const lineKey = `plan:${key}`;
            return (
              <PlannedAmountRow
                key={key}
                label={label}
                value={value}
                editing={editingPlanLine === lineKey}
                editValue={planLineDraft}
                deleteConfirmation={confirmDeletePlanLine === lineKey}
                saving={savingPlanLine}
                onStartEdit={() => startEditPlanLine(lineKey, value)}
                onEditValueChange={setPlanLineDraft}
                onConfirmEdit={() => handleSavePlanLine(lineKey)}
                onCancelEdit={() => setEditingPlanLine(null)}
                onRequestDelete={() => setConfirmDeletePlanLine(lineKey)}
                onConfirmDelete={() => handleDeletePlanLine(lineKey)}
                onCancelDelete={() => setConfirmDeletePlanLine(null)}
              />
            );
          })}
        </div>
      </Card>

      {/* Fixed expenses */}
      <Card>
        <SectionHeader title={`Gastos fijos del mes (${fijos.length})`} />
        <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
          {fixedCategoriesForMonth.map((categoryName) => {
            const items = fijos.filter((expense) => expense.categoria === categoryName);
            return (
              <div key={categoryName} className="rounded-lg border border-gray-100 p-3">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{categoryName}</h4>
                {items.map((item) => {
            const currentTier = getTierForMonth(item.tiers, month);
            return (
              <div key={item.id}>
                {/* Read-only row */}
                <div className="flex items-center gap-2 py-1.5">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-gray-700 truncate">{item.nombre}</span>
                      {item.tiers.length > 1 && (
                        <span className="text-xs bg-blue-50 text-blue-500 px-1.5 py-0.5 rounded-full shrink-0">
                          {item.tiers.length} tramos
                        </span>
                      )}
                    </div>
                    {currentTier !== null && currentTier.meses !== null && (
                      <span className="text-xs text-gray-400">
                        {currentTier.meses.map((m) => MONTH_ABBREVS[m - 1]).join(", ")}
                      </span>
                    )}
                  </div>
                  <span className="text-sm tabular-nums text-gray-800 shrink-0">
                    {formatCurrency(parseAmount(currentTier?.importe ?? "0"))}
                  </span>
                  {editingFijoId !== item.id && (
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => startEditFijo(item)}
                        className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-300 hover:text-blue-500 transition-colors"
                      >
                        <Pencil size={14} />
                      </button>
                      {confirmDeleteId === item.id ? (
                        <>
                          <button
                            onClick={() => handleDeleteFijo(item.id)}
                            className="px-2 py-1 text-xs rounded-md bg-red-500 text-white hover:bg-red-600 transition-colors"
                          >
                            Borrar
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="px-2 py-1 text-xs rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
                          >
                            No
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setConfirmDeleteId(item.id)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Inline edit panel */}
                {editingFijoId === item.id && (
                  <ExpenseEditPanel
                    saving={savingEdit}
                    onCancel={() => setEditingFijoId(null)}
                    onConfirm={handleSaveEditFijo}
                    disabled={!editDraft.concepto.trim()}
                  >
                    <select
                      value={editDraft.concepto}
                      onChange={(e) => setEditDraft((p) => ({ ...p, concepto: e.target.value }))}
                      className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    >
                      {subcategoriesFor(item.categoria).map((subcategory) => (
                        <option key={subcategory.id} value={subcategory.nombre}>{subcategory.nombre}</option>
                      ))}
                    </select>

                    {/* Tier list */}
                    {editDraft.tiers.map((tier, ti) => (
                      <div
                        key={ti}
                        className={clsx(
                          "space-y-2",
                          ti > 0 && "pt-2 border-t border-blue-100"
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500 font-medium shrink-0">
                            {editDraft.tiers.length > 1 ? `Tramo ${ti + 1}` : "Importe"}
                          </span>
                          <MoneyInput
                            value={tier.importe}
                            onValueChange={(value) => updateEditTierImporte(ti, value)}
                            className="flex-1"
                          />
                          {editDraft.tiers.length > 1 && (
                            <button
                              onClick={() => removeEditTier(ti)}
                              className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400 transition-colors shrink-0"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>

                        <div className="flex gap-2">
                          <button
                            onClick={() => updateEditTierMeses(ti, null)}
                            className={clsx(
                              "px-3 py-1 text-xs rounded-full border transition-colors",
                              tier.meses === null
                                ? "bg-blue-600 text-white border-blue-600"
                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                            )}
                          >
                            Todos los meses
                          </button>
                          <button
                            onClick={() => updateEditTierMeses(ti, tier.meses ?? [])}
                            className={clsx(
                              "px-3 py-1 text-xs rounded-full border transition-colors",
                              tier.meses !== null
                                ? "bg-blue-600 text-white border-blue-600"
                                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                            )}
                          >
                            Meses concretos
                          </button>
                        </div>

                        {tier.meses !== null && (
                          <div className="grid grid-cols-6 gap-1">
                            {MONTH_ABBREVS.map((abbr, i) => {
                              const m = i + 1;
                              const selected = tier.meses!.includes(m);
                              return (
                                <button
                                  key={m}
                                  onClick={() => toggleEditTierMes(ti, m)}
                                  className={clsx(
                                    "py-1 text-xs rounded-md font-medium transition-colors",
                                    selected ? "bg-blue-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300"
                                  )}
                                >
                                  {abbr}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ))}

                    <button
                      onClick={addEditTier}
                      className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 transition-colors"
                    >
                      <Plus size={12} />
                      Añadir tramo
                    </button>

                  </ExpenseEditPanel>
                )}
              </div>
            );
          })}
              </div>
            );
          })}
        </div>

        {/* Add fixed expense form */}
        {showNewFijo ? (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
            <select
              value={newFijoCategoria}
              onChange={(e) => {
                const category = e.target.value;
                setNewFijoCategoria(category);
                setNewFijoSubcategoria(subcategoriesFor(category)[0]?.nombre ?? "");
              }}
              className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {parentCategoryOptions.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>

            <select
              value={newFijoSubcategoria}
              onChange={(e) => setNewFijoSubcategoria(e.target.value)}
              disabled={newFijoSubcategoryOptions.length === 0}
              className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            >
              {newFijoSubcategoryOptions.length === 0 ? (
                <option>Sin subcategorías disponibles</option>
              ) : newFijoSubcategoryOptions.map((subcategory) => (
                <option key={subcategory.id} value={subcategory.nombre}>{subcategory.nombre}</option>
              ))}
            </select>

            {/* Tier list */}
            {newFijoTiers.map((tier, ti) => (
              <div
                key={ti}
                className={clsx(
                  "space-y-2",
                  ti > 0 && "pt-2 border-t border-gray-100"
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 font-medium shrink-0">
                    {newFijoTiers.length > 1 ? `Tramo ${ti + 1}` : "Importe"}
                  </span>
                  <MoneyInput
                    value={tier.importe}
                    onValueChange={(value) => updateNewFijoTierImporte(ti, value)}
                    placeholder="0"
                    className="flex-1"
                  />
                  {newFijoTiers.length > 1 && (
                    <button
                      onClick={() => removeNewFijoTier(ti)}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400 transition-colors shrink-0"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => updateNewFijoTierMeses(ti, null)}
                    className={clsx(
                      "px-3 py-1 text-xs rounded-full border transition-colors",
                      tier.meses === null
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                    )}
                  >
                    Todos los meses
                  </button>
                  <button
                    onClick={() => updateNewFijoTierMeses(ti, tier.meses ?? [])}
                    className={clsx(
                      "px-3 py-1 text-xs rounded-full border transition-colors",
                      tier.meses !== null
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                    )}
                  >
                    Meses concretos
                  </button>
                </div>

                {tier.meses !== null && (
                  <div className="grid grid-cols-6 gap-1">
                    {MONTH_ABBREVS.map((abbr, i) => {
                      const m = i + 1;
                      const selected = tier.meses!.includes(m);
                      return (
                        <button
                          key={m}
                          onClick={() => toggleNewFijoTierMes(ti, m)}
                          className={clsx(
                            "py-1 text-xs rounded-md font-medium transition-colors",
                            selected ? "bg-blue-600 text-white" : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300"
                          )}
                        >
                          {abbr}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}

            <button
              onClick={addNewFijoTier}
              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 transition-colors"
            >
              <Plus size={12} />
              Añadir tramo
            </button>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowNewFijo(false);
                  setNewFijoCategoria(parentCategoryOptions[0] ?? "");
                  setNewFijoSubcategoria("");
                  setNewFijoTiers([{ importe: "", meses: null }]);
                }}
                className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddFijo}
                disabled={!newFijoCategoria || !newFijoSubcategoria || addingFijo}
                className={clsx("flex items-center gap-1.5", CONFIRM_BUTTON_CLASS)}
              >
                <Plus size={14} />
                {addingFijo ? "Guardando…" : "Confirmar"}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => {
              setShowNewFijo(true);
              setEditingFijoId(null);
              setEditingPlanLine(null);
            }}
            className="mt-3 pt-3 border-t border-gray-100 w-full flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-700 transition-colors"
          >
            <Plus size={13} />
            Añadir gasto fijo
          </button>
        )}

        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-3">
          <span className="text-sm font-semibold text-gray-900">Total fijos</span>
          <span className="text-sm font-bold text-red-500 tabular-nums">{formatCurrency(totalFijos)}</span>
        </div>
      </Card>

      {/* Variable budgets */}
      <Card>
        <SectionHeader title="Gastos variables" />
        <div className="space-y-2">
          {categorias.map((cat) => {
            const lineKey = `variable:${cat.nombre}`;
            return (
              <PlannedAmountRow
                key={cat.nombre}
                label={cat.nombre}
                value={cat.importe_planificado}
                editing={editingPlanLine === lineKey}
                editValue={planLineDraft}
                deleteConfirmation={confirmDeletePlanLine === lineKey}
                saving={savingPlanLine}
                onStartEdit={() => startEditPlanLine(lineKey, cat.importe_planificado)}
                onEditValueChange={setPlanLineDraft}
                onConfirmEdit={() => handleSavePlanLine(lineKey)}
                onCancelEdit={() => setEditingPlanLine(null)}
                onRequestDelete={() => setConfirmDeletePlanLine(lineKey)}
                onConfirmDelete={() => handleDeletePlanLine(lineKey)}
                onCancelDelete={() => setConfirmDeletePlanLine(null)}
              />
            );
          })}
        </div>

        {showNewVariable ? (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            <select
              value={newVariableCategoria}
              onChange={(e) => setNewVariableCategoria(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {parentCategories.map((category) => (
                <optgroup key={category.id} label={category.nombre}>
                  <option value={category.nombre}>{category.nombre}</option>
                  {subcategoriesFor(category.nombre).map((subcategory) => (
                    <option key={subcategory.id} value={subcategory.nombre}>{subcategory.nombre}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            <MoneyInput
              value={newVariableAmount}
              onValueChange={setNewVariableAmount}
              placeholder="0"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowNewVariable(false);
                  setNewVariableCategoria(parentCategoryOptions[0] ?? "");
                  setNewVariableAmount("");
                }}
                className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddVariableCategory}
                disabled={saving}
                className={clsx("flex items-center gap-1.5", CONFIRM_BUTTON_CLASS)}
              >
                <Plus size={14} />
                {saving ? "Guardando…" : "Confirmar"}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => {
              setShowNewVariable(true);
              setEditingFijoId(null);
              setEditingPlanLine(null);
            }}
            className="mt-3 pt-3 border-t border-gray-100 w-full flex items-center gap-1.5 text-xs text-blue-500 hover:text-blue-700 transition-colors"
          >
            <Plus size={13} />
            Añadir gasto variable
          </button>
        )}

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
            <span className="text-gray-600">Nóminas</span>
            <span className="font-medium text-green-600 tabular-nums">{formatCurrency(ingresosNomina)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Ingresos personales</span>
            <span className="font-medium text-gray-800 tabular-nums">− {formatCurrency(totalPersonal)}</span>
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

    </div>
  );
}

interface ExecRowProps {
  label: string;
  plan: number;
  real: number;
  differenceDirection?: "plan-minus-real" | "real-minus-plan";
  bold?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
}

function ExecRow({ label, plan, real, differenceDirection = "plan-minus-real", bold = false, expanded = false, onToggle }: ExecRowProps) {
  const diff = differenceDirection === "real-minus-plan" ? real - plan : plan - real;
  const diffColor = diff === 0 ? "text-gray-400" : diff > 0 ? "text-green-600" : "text-red-500";

  return (
    <tr className={clsx("border-b border-gray-50", bold && "bg-gray-50")}>
      <td className={clsx("py-2.5 px-4 text-sm", bold ? "font-semibold text-gray-900" : "text-gray-700")}>
        {onToggle ? (
          <button onClick={onToggle} className="flex items-center gap-1.5 hover:text-blue-600">
            <ChevronDown size={15} className={clsx("transition-transform", !expanded && "-rotate-90")} />
            {label}
          </button>
        ) : label}
      </td>
      <td className="py-2.5 px-4 text-sm text-right tabular-nums text-gray-800 hidden sm:table-cell">
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

interface ExecDetailRowProps {
  label: string;
  plan?: number;
  real?: number;
  differenceDirection?: "plan-minus-real" | "real-minus-plan";
}

function ExecDetailRow({ label, plan, real, differenceDirection = "plan-minus-real" }: ExecDetailRowProps) {
  const diff = plan !== undefined && real !== undefined
    ? differenceDirection === "real-minus-plan" ? real - plan : plan - real
    : undefined;
  const diffColor = diff === undefined || diff === 0
    ? "text-gray-400"
    : diff > 0
      ? "text-green-600"
      : "text-red-500";

  return (
    <tr className="border-b border-gray-50 bg-gray-50/70">
      <td className="py-2 px-4 pl-10 text-sm text-gray-600">{label}</td>
      <td className="py-2 px-4 text-right text-sm tabular-nums text-gray-700 hidden sm:table-cell">
        {plan === undefined ? "" : formatCurrency(plan)}
      </td>
      <td className="py-2 px-4 text-right text-sm tabular-nums text-gray-700">
        {real === undefined ? "" : formatCurrency(real)}
      </td>
      <td className={clsx("py-2 px-4 text-right text-sm tabular-nums font-medium", diffColor)}>
        {diff === undefined ? "" : diff === 0 ? "—" : `${diff > 0 ? "+" : ""}${formatCurrency(diff)}`}
      </td>
    </tr>
  );
}

interface ExecTabProps {
  data: ForecastData;
}

function ExecTab({ data }: ExecTabProps) {
  const [showIncomeDetail, setShowIncomeDetail] = useState(false);
  const [showFixedDetail, setShowFixedDetail] = useState(false);
  const [showVariableDetail, setShowVariableDetail] = useState(false);

  const totalGastosPlan = (
    data.total_cuentas_personales_plan
    + data.total_gastos_fijos_plan
    + data.total_gastos_variables_plan
  );
  const gastosFijosReales = data.gastos_fijos.reduce(
    (total, expense) => total + expense.importe_real,
    0,
  );
  const gastosVariablesReales = data.gastos_reales_por_categoria.reduce(
    (total, category) => total + category.importe_real,
    0,
  );

  const fixedExpenses = data.gastos_fijos.filter(
    (expense) => expense.importe_planificado > 0 || expense.importe_real > 0,
  );
  return (
    <div className="space-y-5">
      {/* Summary table */}
      <Card>
        <SectionHeader title="Resumen del mes" />
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                {["Concepto", "Planificado", "Real", "Diferencia"].map((h) => (
                  <th
                    key={h}
                    className={clsx(
                      "pb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide",
                      h === "Concepto" ? "text-left px-4" : "text-right px-4",
                      h === "Planificado" && "hidden sm:table-cell"
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
                plan={data.ingresos_persona_a + data.ingresos_persona_b}
                real={data.ingresos_reales}
                differenceDirection="real-minus-plan"
                expanded={showIncomeDetail}
                onToggle={() => setShowIncomeDetail((visible) => !visible)}
              />
              {showIncomeDetail && (
                <>
                  <ExecDetailRow
                    label="Nóminas"
                    plan={data.ingresos_persona_a + data.ingresos_persona_b}
                    real={data.ingresos_nomina}
                    differenceDirection="real-minus-plan"
                  />
                  {data.ingresos_otros !== 0 && (
                    <ExecDetailRow
                      label="Ingresos extraordinarios"
                      real={data.ingresos_otros}
                    />
                  )}
                </>
              )}
              <ExecRow
                label="Asignaciones personales"
                plan={data.total_cuentas_personales_plan}
                real={data.total_cuentas_personales_plan}
              />
              <ExecRow
                label="Gastos fijos"
                plan={data.total_gastos_fijos_plan}
                real={gastosFijosReales}
                expanded={showFixedDetail}
                onToggle={() => setShowFixedDetail((visible) => !visible)}
              />
              {showFixedDetail && (
                fixedExpenses.length > 0 ? fixedExpenses.map((expense) => (
                  <ExecDetailRow
                    key={expense.id ?? `${expense.categoria}-${expense.nombre}`}
                    label={expense.nombre}
                    plan={expense.importe_planificado}
                    real={expense.importe_real}
                  />
                )) : (
                  <ExecDetailRow label="Sin gastos fijos planificados" />
                )
              )}
              <ExecRow
                label="Gastos variables"
                plan={data.total_gastos_variables_plan}
                real={gastosVariablesReales}
                expanded={showVariableDetail}
                onToggle={() => setShowVariableDetail((visible) => !visible)}
              />
              {showVariableDetail && (
                data.gastos_reales_por_categoria.length > 0 ? data.gastos_reales_por_categoria.map((category) => (
                  <ExecDetailRow
                    key={category.nombre}
                    label={category.nombre}
                    real={category.importe_real}
                  />
                )) : (
                  <ExecDetailRow label="Sin gastos variables registrados" />
                )
              )}
              <ExecRow
                label="Total gastos"
                plan={totalGastosPlan}
                real={data.total_gastos_reales}
                bold
              />
              <ExecRow
                label="Ahorro"
                plan={data.ahorro_estimado}
                real={data.ahorro_real}
                differenceDirection="real-minus-plan"
                bold
              />
            </tbody>
          </table>
        </div>
      </Card>

      {data.gastos_reales_por_categoria.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          <TrendingUp size={32} className="mx-auto mb-2 opacity-30" />
          Sin transacciones para este mes
        </div>
      )}
    </div>
  );
}

export default function Forecast({ mode }: { mode: ForecastMode }) {
  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;
  const [year, setYear] = useState(currentYear);
  const [month, setMonth] = useState(currentMonth);
  const [initialMonthResolved, setInitialMonthResolved] = useState(false);
  const [forecastMinYear, setForecastMinYear] = useState(currentYear);
  const [forecastMinMonth, setForecastMinMonth] = useState(currentMonth);
  const [balanceMaxYear, setBalanceMaxYear] = useState(currentYear);
  const [balanceMaxMonth, setBalanceMaxMonth] = useState(currentMonth);
  const [confirmingClose, setConfirmingClose] = useState(false);
  const [closing, setClosing] = useState(false);
  const [closeError, setCloseError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["forecast", year, month],
    queryFn: () => api.forecast.get(year, month),
  });

  useEffect(() => {
    if (isLoading || !data || initialMonthResolved || year !== currentYear || month !== currentMonth) return;

    setInitialMonthResolved(true);
    if (mode === "forecast" && data.balance_cerrado) {
      const [nextYear, nextMonthNumber] = nextMonth(currentYear, currentMonth);
      setYear(nextYear);
      setMonth(nextMonthNumber);
      setForecastMinYear(nextYear);
      setForecastMinMonth(nextMonthNumber);
    } else if (mode === "forecast") {
      setForecastMinYear(currentYear);
      setForecastMinMonth(currentMonth);
    } else if (!data.balance_cerrado) {
      const [previousYear, previousMonthNumber] = prevMonth(currentYear, currentMonth);
      setYear(previousYear);
      setMonth(previousMonthNumber);
      setBalanceMaxYear(currentYear);
      setBalanceMaxMonth(currentMonth);
    } else {
      setBalanceMaxYear(currentYear);
      setBalanceMaxMonth(currentMonth);
    }
  }, [currentMonth, currentYear, data, initialMonthResolved, isLoading, mode, month, year]);

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

  async function handleCloseMonth() {
    setClosing(true);
    setCloseError(null);
    try {
      await api.forecast.close(year, month);
      await queryClient.invalidateQueries({ queryKey: ["forecast", year, month] });
      setConfirmingClose(false);
    } catch (error) {
      setCloseError(error instanceof Error ? error.message : "No se pudo cerrar el mes");
    } finally {
      setClosing(false);
    }
  }

  const isFirstForecastMonth =
    mode === "forecast" && year === forecastMinYear && month === forecastMinMonth;
  const isLastBalanceMonth =
    mode === "balance" && year === balanceMaxYear && month === balanceMaxMonth;
  const isPastMonth = year < currentYear || (year === currentYear && month < currentMonth);
  const canCloseMonth = mode === "balance" && isPastMonth && !data?.balance_cerrado;

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {mode === "forecast" ? "Previsión mensual" : "Balance mensual"}
          </h2>
          <p className="text-sm text-gray-500 mt-0.5 hidden sm:block">
            {mode === "forecast" ? "Planifica el presupuesto" : "Consulta el resultado del mes cerrado"}
          </p>
        </div>

        {/* Month selector */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handlePrev}
            disabled={isFirstForecastMonth}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm font-semibold text-gray-800 min-w-[110px] text-center">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={handleNext}
            disabled={isLastBalanceMonth}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      {/* Content */}
      {mode === "forecast" ? (
        <PlanTab
          data={data}
          year={year}
          month={month}
        />
      ) : (
        data.balance_cerrado ? (
          <ExecTab data={data} />
        ) : (
          <div className="space-y-4 py-12 text-center">
            <p className="text-sm text-gray-500">Este mes todavía no está cerrado.</p>
            {canCloseMonth && data.plan_guardado && (
              <div className="max-w-md mx-auto rounded-lg border border-amber-200 bg-amber-50 p-4 text-left space-y-3">
                <p className="text-sm text-amber-900">
                  El cierre congela la planificación. Los importes reales seguirán calculándose desde los movimientos y su categoría actual.
                </p>
                {closeError && <p role="alert" className="text-sm text-red-600">{closeError}</p>}
                {confirmingClose ? (
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => { setConfirmingClose(false); setCloseError(null); }}
                      disabled={closing}
                      className="flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 disabled:opacity-50"
                    >
                      <X size={15} />Cancelar
                    </button>
                    <button
                      onClick={handleCloseMonth}
                      disabled={closing}
                      className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                    >
                      <Check size={15} />{closing ? "Cerrando…" : "Confirmar cierre"}
                    </button>
                  </div>
                ) : (
                  <div className="flex justify-end">
                    <button
                      onClick={() => setConfirmingClose(true)}
                      className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white"
                    >
                      <Lock size={15} />Cerrar mes
                    </button>
                  </div>
                )}
              </div>
            )}
            {canCloseMonth && !data.plan_guardado && (
              <p className="text-sm text-amber-700">Guarda la planificación antes de cerrar este mes.</p>
            )}
          </div>
        )
      )}
    </div>
  );
}
