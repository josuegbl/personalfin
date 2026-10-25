# Plan de recuperación de la API

## Estado actual

La API se alineó con el esquema normalizado de PostgreSQL. Como el release de las migraciones `0024`/`0025` no estaba disponible y Alembic tenía revisiones duplicadas, se probó y aplicó una baseline raíz nueva. La historia anterior se conserva, sin cambios, en `backend/alembic/`; el script location activo ahora es `backend/alembic_baseline/`.

## Fases de actuación

### Fase 0: Reconciliar el historial de migraciones

**Diagnóstico inicial:** No era posible reproducir desde el workspace el esquema registrado por la base. Faltaban las migraciones locales `0024` y `0025`; había dos migraciones distintas `0021`, ambas descendientes de `0020`.

**Alternativa aplicada:** Como el release exacto no apareció en Git, imágenes ni WSL, se creó una baseline estática del esquema verificado. Se tomó un backup, se probó la baseline en una DB vacía y un clon restaurado, y solo entonces se estampó la DB actual. No se cambiaron ni se ejecutaron las migraciones antiguas.

**Estado:** completada. Las futuras migraciones se encadenan desde `bcd5f4f582de`.

**Resultado de ejecución (2026-10-25): baseline nueva aplicada.**

- Backup custom-format creado fuera del repo en `%TEMP%\bankfinances-phase0-20261025-080936.dump` (99.081 bytes). `pg_restore --list` lo reconoce y el SHA-256 de la copia coincide con el origen: `45ebe6a371e03e98da0233cb71b99bcb64e621e304a0985c14fa305bbd8aca0b`.
- Base `bankfinances`, PostgreSQL 16.15: `alembic_version = 0025`. `recurring_expenses` no tiene `categoria`; contiene `subcategoria_id` y sus FK. `forecast_category_budgets` no tiene `categoria_nombre`; contiene `categoria_id`, su FK y la unicidad `(forecast_id, categoria_id)`.
- Datos asociados: 43 gastos recurrentes, 6 con `subcategoria_id IS NULL`; 18 presupuestos, ninguno con `categoria_id IS NULL`. Los seis registros requieren revisión antes de decidir cualquier backfill.
- Evidencia sobre `0021`: existe `categories.codigo_sistema`, pero `forecast_plans` conserva `ingresos_josue`, `ingresos_adi`, `cuenta_personal_josue`, `cuenta_personal_adi`, `ingresos_planificados_josue` e `ingresos_planificados_adi`. Esto indica que el esquema refleja la variante de `0021` de `codigo_sistema`, no el renombrado a propietarios neutrales.
- Antes del rebaseline, Alembic no podía resolver `0025`, detectaba IDs `0021` duplicados y las ramas/imágenes locales solo llegaban hasta `0023`.
- Búsqueda adicional (2026-10-25): el `origin/main` publicado más reciente termina en `0023`; `origin/test` y `personalfin/main` son anteriores; no hay tags Git publicados. La copia nativa `/home/josue/BankFinances` y la imagen local también terminan en `0023`, y no hay archivos `0024`/`0025` sueltos bajo `/home/josue`.
- No se recuperó el artefacto original `0024`/`0025`; se eligió la alternativa de baseline nueva en vez de inventar su contenido. La revisión anterior de la DB se sustituyó solo después de backup y validación de un clon.

### Fase 1: Corregir el bloqueo de arranque

**Error:** El modelo [recurring_expense.py](../backend/app/models/recurring_expense.py) todavía mapea `categoria`; el seed de [main.py](../backend/app/main.py) consulta ese modelo durante el startup. Como la columna fue eliminada en `0022`, PostgreSQL devuelve `UndefinedColumn` y FastAPI no llega a servir endpoints.

**Mitigación:** Adoptar `subcategoria_id` y la relación con `Category` como fuente persistida. Derivar la categoría padre desde la subcategoría para las respuestas de API. Adaptar los datos seed para resolver categoría padre y concepto a IDs existentes; identificar explícitamente las filas sin asociación válida antes de asignarlas. No volver a crear la columna de texto como parche.

### Fase 2: Alinear Forecast con el esquema por IDs

**Error:** [forecast.py](../backend/app/models/forecast.py) y los handlers de [api/v1/forecast.py](../backend/app/api/v1/forecast.py) siguen usando `categoria_nombre`, que `0022` reemplaza por `categoria_id` en `forecast_category_budgets`. Además, el ORM espera columnas neutrales (`ingresos_persona_a/b` y `cuenta_personal_a/b`), pero la DB inspeccionada conserva los nombres Josué/Adi. Una vez recuperado el arranque, Forecast puede fallar por cualquiera de esas discrepancias.

**Mitigación aplicada:** Se mapearon los atributos semánticos del ORM a las columnas físicas Josué/Adi existentes y los presupuestos a `categoria_id`, derivando etiquetas desde `Category`. La metadata se amplió con el snapshot mensual y `codigo_sistema` para reflejar el esquema completo.

### Fase 3: Corregir el renombrado de categorías

**Error:** [api/v1/categories.py](../backend/app/api/v1/categories.py) aún renombra presupuestos mediante `categoria_nombre` y gastos recurrentes mediante `categoria`, columnas de texto incompatibles con el esquema de `0022`.

**Mitigación:** Actualizar el nombre en `Category` y dejar que las asociaciones por ID reflejen el cambio. Definir y probar el comportamiento para gastos recurrentes sin `subcategoria_id`, y para renombres de categorías padre y subcategoría.

**Dependencia:** Validar esta fase después de las fases 1 y 2, porque los handlers comparten los modelos afectados.

## Resultado de la solución

### Fases 1–3 completadas en el backend

- `RecurringExpense` ya no mapea la columna eliminada `categoria`; expone el nombre como propiedad derivada desde `subcategoria_id` y su padre. Los endpoints y los dos paths de seed guardan IDs. El seed usa la categoría padre explícita cuando no hay una subcategoría exacta, sin crear categorías nuevas; las seis filas iniciales se resolvieron individualmente según las instrucciones del usuario.
- `ForecastPlan` conserva nombres internos neutrales, pero los mapea a las columnas físicas Josué/Adi que realmente existen. `ForecastCategoryBudget` usa `categoria_id`, relación a `Category` y los nombres de FK/unique observados en la DB.
- Forecast GET/PUT obtiene nombres desde la relación por ID y rechaza presupuestos para categorías padre inexistentes. Renombrar categorías ya no actualiza columnas de texto retiradas; los IDs mantienen las asociaciones y la subcategoría renombrada sincroniza el concepto de sus recurrentes.
- Se eliminó Mounjaro (ID 52) porque no debe ser recurrente. Comisión tarjeta (ID 32) se conservó y enlazó con la categoría existente `Comisiones` (ID 97, padre `Otros`).
- Los recurrentes Amazon (ID 48), Disney (49), HBO (50) y Office (51) se reasignaron a Amazon Prime (categoría 51), Disney+ (38), HBO Max (81) y Microsoft 365 (52). Se eliminaron las categorías antiguas Amazon/Disney/HBO/Office (IDs 106–109) después de comprobar que no tenían movimientos, presupuestos ni balances asociados y mover sus referencias recurrentes. No quedan referencias FK a esos IDs.
- La auditoría global encontró solo un concepto repetido con vigencias solapadas: Deportes (IDs 55 y 112). Para conservar el histórico, el ID 55 mantiene su fin el 31/08/2026 y el ID 112 empieza el 01/09/2026. Forecast ahora filtra recurrentes por solape de fechas con el mes consultado.
- Se tomó un backup preoperación en `%TEMP%\bankfinances-pre-recurrent-cleanup-20261025.dump`; SHA-256 `67e3a09e8a76a235bb4b1dd4ec801b0c316290e8d95fb145deadc8f6fe28e71a`.
- Antes de fusionar categorías se tomó `%TEMP%\bankfinances-pre-category-merge-20261025.dump`; SHA-256 `18c3c711c03f881b9e7f0a1b59b2b864e1f8d1ddc8b016693e8d9c3c66e1ba46`.

### Validación realizada (2026-10-25)

- En `bankfinances_phase0_staging`, restaurada desde el backup: startup y `/openapi.json` responden 200; Forecast GET y PUT pasan; el PUT persiste y recupera un presupuesto por `categoria_id`.
- En staging también pasan create/update/delete de gastos recurrentes, y renombres/restauración de categorías padre e hija con la etiqueta nueva visible en Forecast.
- `python -m compileall -q app` termina correctamente y VS Code no reporta errores en los archivos modificados.
- La API activa en `localhost:8000` responde a `/openapi.json` y Forecast GET tras hot reload. Tras la limpieza, la DB original mantiene 67 categorías, 42 recurrentes y 18 presupuestos; no quedan recurrentes sin `subcategoria_id`, referencias a las cuatro categorías eliminadas ni pares de conceptos normalizados con vigencias solapadas.
- Forecast muestra Deportes ID 55/70 € en abril y Deportes ID 112/30 € en octubre. `python -m compileall -q app` termina correctamente.

### Rebaseline aplicado

- Se creó una revisión raíz DDL estática `bcd5f4f582de` en `backend/alembic_baseline/versions/`; genera el esquema completo desde cero. Su `downgrade()` falla explícitamente para impedir que una reversión borre todas las tablas.
- Se cambió `backend/alembic.ini` para usar `script_location = alembic_baseline`. El historial previo permanece intacto en `backend/alembic/` y deja de participar en el grafo activo.
- En la DB original, `alembic stamp --purge bcd5f4f582de` actualizó únicamente `alembic_version`; no ejecutó DDL ni modificó datos.
- Resultado: `alembic current` y `alembic heads` muestran `bcd5f4f582de`; `alembic check` no encuentra diferencias.

### Fase 4: Validación y recuperación

**Resultado:** completada. En una DB vacía, `alembic upgrade head` creó el esquema; el startup/seed completó, `/openapi.json` y Forecast GET respondieron 200, y `alembic check` junto con la comparación de metadata dieron cero diferencias. En un clon restaurado, `stamp --purge` dejó `bcd5f4f582de`, preservó los recuentos y pasó `current`/`check`. El mismo stamp se aplicó después a la DB original.

## Verificación de salida

- La DB original está en `bcd5f4f582de`; `alembic current`, `alembic history --verbose` y `alembic heads` usan un único head.
- `alembic upgrade head` funciona en una DB vacía; `alembic check` y el comparador de metadata no detectan diferencias.
- `alembic check` y `python -m compileall -q app` terminan correctamente.
- FastAPI inicia sin `UndefinedColumn` y responde a `/openapi.json`.
- Se prueban Forecast GET/PUT, creación/edición/borrado de gastos recurrentes y renombrado de categorías.
- Se revisan los logs y el estado del contenedor después del despliegue.

## Riesgos y límites

- `0022` enlaza los gastos recurrentes solo cuando el padre y el concepto encuentran una subcategoría coincidente; los registros no enlazados requieren revisión antes de asignar categoría.
- El downgrade de la baseline raíz está deshabilitado. Para recuperar estado, restaurar uno de los backups completos documentados.
- No restaurar las antiguas columnas de texto solo para silenciar errores: mantendría incoherente el modelo y las operaciones de la API.
- Las migraciones antiguas se conservan como referencia, pero el camino activo parte de `bcd5f4f582de`; toda migración futura debe encadenarse desde ese head.
