import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plus, Trash2, Save, TrendingUp, Pencil } from "lucide-react";
import clsx from "clsx";
import { api } from "../api/client";
import { formatCurrency } from "../utils/format";
import type { ForecastData } from "../types";

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

const MONTH_ABBREVS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

type TierDraft = { importe: string; meses: number[] | null };
type CatDraft = { nombre: string; importe_planificado: string };
type FixedDraft = { id: number; nombre: string; tiers: TierDraft[] };
type EditDraft = { concepto: string; tiers: TierDraft[] };

function parseAmount(s: string): number {
  const n = parseFloat(s.replace(",", "."));
  return isNaN(n) ? 0 : n;
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
  onSaved: () => void;
}

function PlanTab({ data, year, month, onSaved }: PlanTabProps) {
  const qc = useQueryClient();
  const [ingresosJosue, setIngresosJosue] = useState(String(data.ingresos_josue));
  const [ingresosAdi, setIngresosAdi] = useState(String(data.ingresos_adi));
  const [ingresosExtra, setIngresosExtra] = useState(String(data.ingresos_extra));
  const [categorias, setCategorias] = useState<CatDraft[]>(
    data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: String(g.importe_planificado) }))
  );
  const [fijos, setFijos] = useState<FixedDraft[]>(
    data.gastos_fijos
      .filter((g) => g.id !== undefined)
      .map((g) => ({
        id: g.id!,
        nombre: g.nombre,
        tiers: (g.tiers ?? []).map(t => ({ importe: String(t.importe), meses: t.meses ?? null })),
      }))
  );
  const [saving, setSaving] = useState(false);
  const [newCatName, setNewCatName] = useState("");
  const [showNewFijo, setShowNewFijo] = useState(false);
  const [newFijoConcepto, setNewFijoConcepto] = useState("");
  const [newFijoTiers, setNewFijoTiers] = useState<TierDraft[]>([{ importe: "", meses: null }]);
  const [addingFijo, setAddingFijo] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [editingFijoId, setEditingFijoId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>({ concepto: "", tiers: [] });
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    setIngresosJosue(String(data.ingresos_josue));
    setIngresosAdi(String(data.ingresos_adi));
    setIngresosExtra(String(data.ingresos_extra));
    setCategorias(
      data.gastos_variables.map((g) => ({ nombre: g.nombre, importe_planificado: String(g.importe_planificado) }))
    );
    setFijos(
      data.gastos_fijos
        .filter((g) => g.id !== undefined)
        .map((g) => ({
          id: g.id!,
          nombre: g.nombre,
          tiers: (g.tiers ?? []).map(t => ({ importe: String(t.importe), meses: t.meses ?? null })),
        }))
    );
    setEditingFijoId(null);
  }, [data]);

  const totalIngresos = parseAmount(ingresosJosue) + parseAmount(ingresosAdi) + parseAmount(ingresosExtra);
  const totalFijos = fijos.reduce((s, f) => {
    const tier = getTierForMonth(f.tiers, month);
    return s + (tier ? parseAmount(tier.importe) : 0);
  }, 0);
  const totalVariables = categorias.reduce((s, c) => s + parseAmount(c.importe_planificado), 0);
  const ahorro = totalIngresos - totalFijos - totalVariables;

  function updateCatAmount(index: number, value: string) {
    setCategorias((prev) => prev.map((c, i) => (i === index ? { ...c, importe_planificado: value } : c)));
  }

  function removeCat(index: number) {
    setCategorias((prev) => prev.filter((_, i) => i !== index));
  }

  function addCat() {
    const name = newCatName.trim();
    if (!name) return;
    setCategorias((prev) => [...prev, { nombre: name, importe_planificado: "0" }]);
    setNewCatName("");
  }

  async function handleDeleteFijo(id: number) {
    await api.recurringExpenses.delete(id);
    setFijos((prev) => prev.filter((f) => f.id !== id));
    setConfirmDeleteId(null);
  }

  function startEditFijo(fijo: FixedDraft) {
    setEditingFijoId(fijo.id);
    setEditDraft({ concepto: fijo.nombre, tiers: fijo.tiers.map(t => ({ ...t })) });
    setConfirmDeleteId(null);
    setShowNewFijo(false);
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
    setSavingEdit(true);
    try {
      const updated = await api.recurringExpenses.update(editingFijoId, {
        concepto: editDraft.concepto.trim(),
        tiers: editDraft.tiers.map(t => ({ importe: parseAmount(t.importe), meses: t.meses })),
      });
      setFijos(prev =>
        prev
          .map(f => f.id === editingFijoId
            ? {
                ...f,
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
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleAddFijo() {
    const concepto = newFijoConcepto.trim();
    if (!concepto) return;
    setAddingFijo(true);
    try {
      const created = await api.recurringExpenses.create({
        concepto,
        tiers: newFijoTiers.map(t => ({ importe: parseAmount(t.importe), meses: t.meses })),
      });
      const tierDrafts = created.tiers.map(t => ({ importe: String(t.importe), meses: t.meses ?? null }));
      if (getTierForMonth(tierDrafts, month) !== null) {
        setFijos(prev => [...prev, { id: created.id, nombre: created.concepto, tiers: tierDrafts }]);
      }
      setNewFijoConcepto("");
      setNewFijoTiers([{ importe: "", meses: null }]);
      setShowNewFijo(false);
    } finally {
      setAddingFijo(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.forecast.save(year, month, {
        ingresos_josue: parseAmount(ingresosJosue),
        ingresos_adi: parseAmount(ingresosAdi),
        ingresos_extra: parseAmount(ingresosExtra),
        categorias: categorias.map((c) => ({ nombre: c.nombre, importe_planificado: parseAmount(c.importe_planificado) })),
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
                  onChange={(e) => setter(e.target.value)}
                  onBlur={(e) => setter(String(parseAmount(e.target.value)))}
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
        <SectionHeader title={`Gastos fijos del mes (${fijos.length})`} />
        <div className="space-y-1 max-h-80 overflow-y-auto pr-1">
          {fijos.map((item) => {
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
                  <div className="mb-2 rounded-xl border border-blue-100 bg-blue-50/40 p-3 space-y-3">
                    {/* Concepto */}
                    <input
                      type="text"
                      value={editDraft.concepto}
                      onChange={(e) => setEditDraft((p) => ({ ...p, concepto: e.target.value }))}
                      className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      placeholder="Concepto"
                    />

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
                          <div className="relative flex-1">
                            <input
                              type="number"
                              value={tier.importe}
                              onChange={(e) => updateEditTierImporte(ti, e.target.value)}
                              onBlur={(e) => updateEditTierImporte(ti, String(parseAmount(e.target.value)))}
                              className="w-full px-3 py-1.5 text-sm text-right border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums bg-white"
                              step="0.01"
                              min="0"
                            />
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs pointer-events-none">€</span>
                          </div>
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

                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => setEditingFijoId(null)}
                        className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        Cancelar
                      </button>
                      <button
                        onClick={handleSaveEditFijo}
                        disabled={!editDraft.concepto.trim() || savingEdit}
                        className="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
                      >
                        {savingEdit ? "Guardando…" : "Confirmar"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Add fixed expense form */}
        {showNewFijo ? (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
            <input
              type="text"
              placeholder="Concepto (ej. Netflix)"
              value={newFijoConcepto}
              onChange={(e) => setNewFijoConcepto(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

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
                  <div className="relative flex-1">
                    <input
                      type="number"
                      placeholder="0"
                      value={tier.importe}
                      onChange={(e) => updateNewFijoTierImporte(ti, e.target.value)}
                      className="w-full px-3 py-1.5 text-sm text-right border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 tabular-nums"
                      step="0.01"
                      min="0"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs pointer-events-none">€</span>
                  </div>
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
                  setNewFijoConcepto("");
                  setNewFijoTiers([{ importe: "", meses: null }]);
                }}
                className="px-3 py-1.5 text-sm rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddFijo}
                disabled={!newFijoConcepto.trim() || addingFijo}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
              >
                <Plus size={14} />
                {addingFijo ? "Añadiendo…" : "Añadir"}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => { setShowNewFijo(true); setEditingFijoId(null); }}
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
        <SectionHeader title="Gastos variables (presupuesto)" />
        <div className="space-y-2">
          {categorias.map((cat, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-sm text-gray-700 flex-1 truncate">{cat.nombre}</span>
              <div className="relative w-36">
                <input
                  type="number"
                  value={cat.importe_planificado}
                  onChange={(e) => updateCatAmount(index, e.target.value)}
                  onBlur={(e) => updateCatAmount(index, String(parseAmount(e.target.value)))}
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
        </div>
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
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-100">
                    {["Categoría", "Planificado", "Real", "Diferencia"].map((h) => (
                      <th
                        key={h}
                        className={clsx(
                          "pb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide",
                          h === "Categoría" ? "text-left px-4" : "text-right px-4",
                          h === "Planificado" && "hidden sm:table-cell"
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
            </div>
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Previsión mensual</h2>
          <p className="text-sm text-gray-500 mt-0.5 hidden sm:block">Planifica y controla el presupuesto</p>
        </div>

        {/* Month selector */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
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
