# Plan: Categorías con Drag & Drop para reparenting

## Contexto y restricciones

El modelo ya tiene `padre_id` con auto-referencia, pero:
- El schema `CategoryUpdate` solo permite renombrar — no hay endpoint para mover una categoría
- La UI solo tiene 2 niveles (padre → hijo), sin arrastrar
- Las categorías de sistema (`nomina`, `sin_categoria`) no deben moverse

---

## Fase 0 — Pre-requisito: saneamiento de lookups por nombre

La auditoría revela que varios componentes identifican categorías por **nombre** en lugar de por **ID**. Si se mueve una categoría (cambia `padre_id`) o se renombra, estas partes del código producen resultados silenciosamente incorrectos. Hay que corregirlas antes del drag & drop.

### Problemas encontrados

| Ubicación | Patrón problemático | Riesgo |
|-----------|---------------------|--------|
| `Forecast.tsx` `subcategoriesFor()` | `parentCategories.find(c => c.nombre === parentName)` | Un cambio de padre rompe la lista de subcategorías del picker |
| `Forecast.tsx` `handleAddVariableCategory` | `allCategories?.find(c => c.nombre === categoryName)` | Selecciona la categoría incorrecta si hay nombres similares |
| `Forecast.tsx` `groupFixedByParent` | `categoryByName.get(expense.categoria)` | Tras un rename, la categoría no se encuentra y la agrupación falla en silencio |
| `Forecast.tsx` `plannedVariableNames` | `new Set(data.gastos_variables.map(c => c.nombre))` | Deduplicación por nombre puede suprimir filas reales |
| `RecurringExpense` (toda la pila) | `categoria: string` / `concepto: string` — sin ID | Gastos fijos completamente desvinculados de la tabla de categorías |

### Correcciones requeridas (Fase 0)

**0a. Gastos fijos (recurring expenses) — migrar de nombre a ID**

Los `RecurringExpense` almacenan `categoria` y `concepto` como strings sueltos. El campo `subcategoria_id` existe en el modelo pero nunca se usa en el frontend.

- **Backend**: añadir `categoria_id: int | None` a `RecurringExpenseCreate` y `RecurringExpenseUpdate`. El endpoint de creación/edición debe aceptar el ID, resolver el nombre desde la BD, y guardar `subcategoria_id`. Mantener `categoria`/`concepto` como cadenas por compatibilidad con seed y lógica existente.
- **Frontend tipos**: añadir `categoria_id: number | null` y `subcategoria_id: number | null` a `RecurringExpenseOut`.
- **Forecast `PlanTab`**: el picker de gastos fijos debe enviar `categoria_id` (ID de la categoría hija/subcategoría) junto con los strings actuales.
- **Forecast `ExecTab` `groupFixedByParent`**: reemplazar el mapa `categoryByName` por `categoryById` usando `subcategoria_id` para agrupar.

**0b. Forecast `PlanTab` — picker de gastos variables**

- `subcategoriesFor(parentName)`: cambiar la firma a `subcategoriesFor(parentId: number)` y filtrar por `padre_id === parentId`. El componente selector debe pasar el ID del padre, no su nombre.
- `handleAddVariableCategory`: el estado del picker debe almacenar el ID de la categoría seleccionada, no el nombre. El `find` por nombre desaparece.

**0c. Forecast `ExecTab` — `plannedVariableNames`**

- Cambiar a `new Set(data.gastos_variables.map(c => c.categoria_id))` y comparar por ID en el join con datos reales. Si `categoria_id` puede ser null para algún ítem del servidor, usar el par `(categoria_id, nombre)` y priorizar el ID cuando esté disponible.

**0d. Verificar invalidaciones**

Confirmar que tras cualquier mutación que afecte categorías, todos los query keys dependientes se invalidan:

| Mutación | Query keys a invalidar |
|----------|------------------------|
| `createCategory` | `["categories"]` |
| `renameCategory` | `["categories"]`, `["transactions"]`, `["dashboard"]`, `["forecast"]` |
| `deleteCategory` | `["categories"]`, `["transactions"]`, `["dashboard"]`, `["forecast"]` |
| `reparentCategory` (nueva) | `["categories"]`, `["forecast"]` |

> El Dashboard no tiene su propio `["categories"]` query — consume nombres ya procesados por el servidor. No necesita invalidación adicional.

---

## Fase 1 — Backend: endpoint de reparenting

**1. Nuevo schema `CategoryReparent`** en `backend/app/schemas/category.py`:
```python
class CategoryReparent(BaseModel):
    padre_id: int | None  # None = pasar a nivel raíz
```

**2. Nuevo endpoint** `PATCH /categories/{id}/parent` en `backend/app/api/v1/categories.py`:

Validaciones obligatorias:
- La categoría destino existe (si `padre_id` no es `None`)
- Sin referencias circulares: una categoría no puede ser hija de uno de sus propios descendientes
- No mover una categoría que ya tiene hijos a nivel de subcategoría (mantiene jerarquía de 2 niveles máximo)
- Bloquear el movimiento de categorías de sistema (`codigo_sistema` no nulo)

---

## Fase 2 — Frontend: drag & drop con `@dnd-kit`

**Librería elegida: `@dnd-kit/core` + `@dnd-kit/sortable`**
- Moderna, accesible, ~12KB, sin dependencias
- Soporta mouse y touch nativamente

**3. Instalar dependencias:**
```bash
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

**4. Refactorizar `frontend/src/pages/Categories.tsx`:**

Estructura del drag & drop:
- `DndContext` envuelve toda la lista de categorías
- Cada `CategoryRow` se convierte en `useDraggable`
- Cada fila padre se convierte también en `useDroppable`
- Una zona "Raíz" al final para soltar y quitar la categoría padre

Comportamiento al soltar:

| Acción | Resultado |
|--------|-----------|
| Arrastrar subcategoría sobre otra categoría padre | Cambia el `padre_id` |
| Arrastrar subcategoría a zona raíz | `padre_id = null` → pasa a nivel raíz |
| Arrastrar categoría padre que tiene hijos | Solo se permite soltar en zona raíz (reorden) |
| Arrastrar categoría de sistema | Bloqueado visualmente (cursor prohibido) |

**5. Feedback visual:**
- `DragOverlay`: ghost semitransparente de la fila mientras se arrastra
- Categoría destino: borde resaltado con color azul al hacer hover con el drag
- Zona raíz: aparece solo durante el drag como área de drop

**6. Nueva mutation `reparentCategory`** en `Categories.tsx`:
```typescript
const reparentCategory = useMutation(
  ({ id, padre_id }: { id: number; padre_id: number | null }) =>
    api.categories.reparent(id, padre_id),
  {
    onSuccess: () => {
      queryClient.invalidateQueries(["categories"]);
      queryClient.invalidateQueries(["forecast"]);
    }
  }
);
```

**7. Actualizar `frontend/src/api/client.ts`:**
```typescript
reparent: (id: number, padre_id: number | null) =>
  patch<Category>(`/categories/${id}/parent`, { padre_id }),
```

---

## Casos borde y restricciones del UI

| Caso | Manejo |
|------|--------|
| Categoría de sistema (`nomina`, `sin_categoría`) | No draggable — `useDraggable` desactivado |
| Padre con hijos arrastrado sobre otro padre | Drop bloqueado, solo puede ir a zona raíz |
| Soltar en la misma posición | No-op, sin llamada al servidor |
| Error de red al reparentar | Toast de error, rollback visual (optimistic update opcional) |

---

## Archivos afectados

### Fase 0
| Archivo | Cambio |
|---------|--------|
| `backend/app/schemas/category.py` | Añadir `CategoryReparent` |
| `backend/app/schemas/recurring_expense.py` | Añadir `categoria_id` a Create/Update/Out |
| `backend/app/api/v1/recurring_expenses.py` | Aceptar y resolver `categoria_id` |
| `frontend/src/types/index.ts` | Añadir `categoria_id`/`subcategoria_id` a `RecurringExpenseOut` |
| `frontend/src/pages/Forecast.tsx` | Corregir todos los lookups por nombre |

### Fase 1
| Archivo | Cambio |
|---------|--------|
| `backend/app/schemas/category.py` | Añadir `CategoryReparent` |
| `backend/app/api/v1/categories.py` | Nuevo endpoint `PATCH /{id}/parent` |

### Fase 2
| Archivo | Cambio |
|---------|--------|
| `frontend/src/api/client.ts` | Añadir `reparent` |
| `frontend/src/pages/Categories.tsx` | Refactorizar con dnd-kit |
| `frontend/package.json` | Añadir `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` |
