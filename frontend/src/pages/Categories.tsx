import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import type { Category, CategoryCreate } from "../types";

const CATEGORY_TYPES = [
  { value: "gasto", label: "Gasto" },
  { value: "ingreso", label: "Ingreso" },
  { value: "transferencia", label: "Transferencia" },
  { value: "neutral", label: "Neutral" },
] as const;

const TYPE_STYLES = {
  gasto: "bg-rose-50 text-rose-700 ring-rose-600/10",
  ingreso: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
  transferencia: "bg-amber-50 text-amber-700 ring-amber-600/10",
  neutral: "bg-slate-100 text-slate-600 ring-slate-500/10",
};

const INITIAL_CATEGORY: CategoryCreate = {
  nombre: "",
  color: "#64748b",
  padre_id: null,
  naturaleza: "gasto",
  incluida_en_analisis: true,
};

type CategoryRowProps = {
  category: Category;
  isSubcategory?: boolean;
  isExpanded?: boolean;
  subcategoryCount?: number;
  isDeleting: boolean;
  isRenaming: boolean;
  onDelete: (id: number, nombre: string) => void;
  onRename: (id: number, nombre: string) => void;
  onToggle?: () => void;
};

function CategoryRow({
  category,
  isSubcategory = false,
  isExpanded = false,
  subcategoryCount = 0,
  isDeleting,
  isRenaming,
  onDelete,
  onRename,
  onToggle,
}: CategoryRowProps) {
  const typeLabel = CATEGORY_TYPES.find((type) => type.value === category.naturaleza)?.label;

  return (
    <div className={`grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_130px_150px_104px] sm:items-center sm:px-5 ${isSubcategory ? "bg-slate-50/70" : "hover:bg-slate-50"}`}>
      <div className="min-w-0">
        {onToggle ? (
          <button
            onClick={onToggle}
            className="flex w-full items-center gap-2 text-left text-sm font-semibold text-slate-800"
            aria-expanded={isExpanded}
          >
            <ChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${isExpanded ? "" : "-rotate-90"}`} />
            <span className="truncate">{category.nombre}</span>
            {subcategoryCount > 0 && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">{subcategoryCount}</span>}
          </button>
        ) : (
          <p className="pl-6 text-sm font-medium text-slate-700">{category.nombre}</p>
        )}
      </div>
      <span className={`w-fit rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset ${TYPE_STYLES[category.naturaleza]}`}>
        {typeLabel}
      </span>
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="h-3.5 w-3.5 rounded-full ring-1 ring-black/10" style={{ backgroundColor: category.color ?? "#cbd5e1" }} />
        {category.color ?? "Sin color"}
      </div>
      <div className="flex justify-end">
        <button
          onClick={() => onRename(category.id, category.nombre)}
          disabled={isRenaming}
          title="Cambiar nombre"
          aria-label={`Cambiar nombre de ${category.nombre}`}
          className="rounded-md p-2 text-slate-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-30"
        >
          <Pencil size={16} />
        </button>
        <button
          onClick={() => onDelete(category.id, category.nombre)}
          disabled={!category.se_puede_eliminar || isDeleting}
          title={category.se_puede_eliminar ? "Eliminar categoría" : "No se puede eliminar: tiene movimientos o subcategorías"}
          aria-label={`Eliminar ${category.nombre}`}
          className="rounded-md p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}

export default function Categories() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CategoryCreate>(INITIAL_CATEGORY);
  const [error, setError] = useState<string | null>(null);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [editedName, setEditedName] = useState("");
  const [expandedCategories, setExpandedCategories] = useState<Set<number>>(new Set());
  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories.list,
  });

  const createCategory = useMutation({
    mutationFn: api.categories.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setForm(INITIAL_CATEGORY);
      setError(null);
      setShowForm(false);
    },
    onError: () => setError("No se pudo crear la categoría. Revisa que el nombre sea único."),
  });

  const deleteCategory = useMutation({
    mutationFn: api.categories.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setError(null);
    },
    onError: () => setError("No se pudo eliminar la categoría porque tiene movimientos o subcategorías."),
  });

  const renameCategory = useMutation({
    mutationFn: ({ id, nombre }: { id: number; nombre: string }) => api.categories.update(id, { nombre }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["forecast"] });
      setEditingCategory(null);
      setEditedName("");
      setError(null);
    },
    onError: () => setError("No se pudo cambiar el nombre. Debe ser único y no estar vacío."),
  });

  const parentCategories = categories?.filter((category) => category.padre_id === null) ?? [];
  const subcategoriesByParent = new Map<number, Category[]>();
  categories?.forEach((category) => {
    if (category.padre_id !== null) {
      const subcategories = subcategoriesByParent.get(category.padre_id) ?? [];
      subcategories.push(category);
      subcategoriesByParent.set(category.padre_id, subcategories);
    }
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nombre = form.nombre.trim();
    if (!nombre) {
      setError("Escribe un nombre para la categoría.");
      return;
    }
    createCategory.mutate({ ...form, nombre, color: form.color || null });
  }

  function handleDelete(id: number, nombre: string) {
    if (window.confirm(`¿Eliminar la categoría "${nombre}"?`)) {
      deleteCategory.mutate(id);
    }
  }

  function startRename(category: Category) {
    setEditingCategory(category);
    setEditedName(category.nombre);
    setError(null);
  }

  function submitRename(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nombre = editedName.trim();
    if (!editingCategory || !nombre) {
      setError("Escribe un nombre para la categoría.");
      return;
    }
    renameCategory.mutate({ id: editingCategory.id, nombre });
  }

  function toggleSubcategories(categoryId: number) {
    setExpandedCategories((expanded) => {
      const next = new Set(expanded);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  }

  return (
    <div className="max-w-5xl mx-auto p-5 sm:p-6 space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Categorías</h2>
          <p className="mt-1 text-sm text-slate-500">Organiza los movimientos con categorías propias.</p>
        </div>
        <button
          onClick={() => { setError(null); setShowForm((visible) => !visible); }}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 transition-colors"
        >
          <Plus size={16} />
          Nueva categoría
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[minmax(0,1fr)_150px_170px_48px_auto] sm:items-end">
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Nombre
            <input
              autoFocus
              value={form.nombre}
              onChange={(event) => setForm({ ...form, nombre: event.target.value })}
              placeholder="Ej. Mascotas"
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-200"
            />
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Tipo
            <select
              value={form.naturaleza}
              onChange={(event) => setForm({ ...form, naturaleza: event.target.value as CategoryCreate["naturaleza"] })}
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-200"
            >
              {CATEGORY_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Categoría padre
            <select
              value={form.padre_id ?? ""}
              onChange={(event) => setForm({ ...form, padre_id: event.target.value ? Number(event.target.value) : null })}
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-200"
            >
              <option value="">Sin categoría padre</option>
              {parentCategories.map((category) => <option key={category.id} value={category.id}>{category.nombre}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-sm font-medium text-slate-700">
            Color
            <input
              type="color"
              value={form.color ?? "#64748b"}
              onChange={(event) => setForm({ ...form, color: event.target.value })}
              className="h-10 w-12 cursor-pointer rounded-md border border-slate-300 bg-white p-1"
            />
          </label>
          <button
            type="submit"
            disabled={createCategory.isPending}
            className="h-10 rounded-md bg-slate-900 px-4 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            Guardar
          </button>
        </form>
      )}

      {editingCategory && (
        <form onSubmit={submitRename} className="flex flex-wrap items-end gap-3 border border-blue-200 bg-blue-50 p-4">
          <label className="grid flex-1 gap-1.5 text-sm font-medium text-slate-700">
            Cambiar nombre
            <input
              autoFocus
              value={editedName}
              onChange={(event) => setEditedName(event.target.value)}
              className="h-10 rounded-md border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            />
          </label>
          <button
            type="button"
            onClick={() => setEditingCategory(null)}
            className="h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 hover:bg-slate-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={renameCategory.isPending}
            className="h-10 rounded-md bg-blue-600 px-4 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Guardar nombre
          </button>
        </form>
      )}

      {error && <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

      <section className="overflow-hidden border border-slate-200 bg-white">
        <div className="hidden grid-cols-[minmax(0,1fr)_130px_150px_104px] border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:grid">
          <span>Categoría</span>
          <span>Tipo</span>
          <span>Color</span>
          <span className="text-right">Acción</span>
        </div>

        {isLoading ? (
          <p className="px-5 py-10 text-center text-sm text-slate-400">Cargando categorías...</p>
        ) : !categories?.length ? (
          <p className="px-5 py-10 text-center text-sm text-slate-400">Todavía no hay categorías.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {parentCategories.map((category) => {
              const subcategories = subcategoriesByParent.get(category.id) ?? [];
              const isExpanded = expandedCategories.has(category.id);

              return (
                <li key={category.id}>
                  <CategoryRow
                    category={category}
                    isExpanded={isExpanded}
                    subcategoryCount={subcategories.length}
                    isDeleting={deleteCategory.isPending}
                    isRenaming={renameCategory.isPending}
                    onDelete={handleDelete}
                    onRename={(id, nombre) => startRename(categories.find((item) => item.id === id) ?? { ...category, nombre })}
                    onToggle={subcategories.length > 0 ? () => toggleSubcategories(category.id) : undefined}
                  />
                  {isExpanded && subcategories.length > 0 && (
                    <ul className="border-t border-slate-100 divide-y divide-slate-100">
                      {subcategories.map((subcategory) => (
                        <li key={subcategory.id}>
                          <CategoryRow
                            category={subcategory}
                            isSubcategory
                            isDeleting={deleteCategory.isPending}
                            isRenaming={renameCategory.isPending}
                            onDelete={handleDelete}
                            onRename={(id, nombre) => startRename(categories.find((item) => item.id === id) ?? { ...subcategory, nombre })}
                          />
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
