# Plan de Desarrollo - Aplicación de Economía Familiar

## Objetivo

Desarrollar una aplicación privada para gestionar la economía familiar
mediante la sincronización automática de las cuentas bancarias (BBVA y
Eurocaja Rural) y la cuenta PayPal, proporcionando una visión clara de
ingresos, gastos, ahorro y evolución financiera.

## Alcance

La aplicación se limita a:

-   Cuentas corrientes (BBVA, Eurocaja Rural).
-   Cuenta y pagos PayPal.
-   Ingresos.
-   Gastos.
-   Gastos recurrentes.
-   Gastos puntuales.
-   Presupuestos.
-   Análisis de ahorro.

No contempla inversiones, bolsa, criptomonedas ni patrimonio.

## Preguntas que debe responder

-   ¿Cuánto dinero tenemos disponible hoy?
-   ¿Cuánto queda hasta final de mes?
-   ¿Cuál es el desfase entre los gastos previstos, el gasto real y el saldo?
-   ¿Cuánto gastamos por categoría?
-   ¿Qué gastos son recurrentes?
-   ¿Qué gastos han aumentado?
-   ¿Cuánto conseguimos ahorrar cada mes?
-   ¿Cuánto hemos pagado a través de PayPal este mes y en qué?
-   ¿Qué saldo tenemos en la cuenta PayPal ahora mismo?

------------------------------------------------------------------------

# Arquitectura

Frontend (React)

↓

FastAPI

↓

Servicios

-   Sincronización bancaria (BankAdapter)
-   Sincronización PayPal (PayPalAdapter)
-   Deduplicación de movimientos
-   Categorización
-   Recurrentes
-   Analítica
-   IA (futuro)

↓

PostgreSQL

------------------------------------------------------------------------

# Módulos

## 1. Sincronización bancaria

Objetivo:

-   Descargar movimientos automáticamente.
-   Actualizar saldos.
-   Detectar nuevos movimientos.
-   Evitar duplicados.

Primera implementación:

-   Playwright → BBVA
-   Playwright → Eurocaja Rural
-   PayPal REST API → PayPal (token OAuth 2.0, sin scraping)

Diseño mediante interfaz `SourceAdapter` para unificar bancos y PayPal:

```
SourceAdapter
├── BankAdapter (Playwright)
│   ├── BBVAAdapter
│   └── EurocajaAdapter
└── PayPalAdapter (REST API)
```

### Transferencias internas: deduplicación entre cuentas

Cuando se transfiere dinero entre cuentas propias (BBVA Josué, BBVA Adi,
Caja Rural) el movimiento aparece **en ambos lados**: como un débito en la
cuenta origen y como un crédito en la cuenta destino. Contarlos como gasto e
ingreso distorsionaría el análisis.

Algoritmo de detección:

1.  Tras cada sincronización, buscar transacciones sin emparejar cuyo
    concepto contenga el IBAN o alias de otra cuenta propia.
2.  Como segundo criterio, buscar pares `(débito, crédito)` con el mismo
    importe absoluto y fecha dentro de una ventana de 2 días hábiles.
3.  Si ambas cuentas pertenecen a la tabla `accounts` → marcar el par como
    transferencia interna.
4.  Ambas patas reciben `categoria = 'Transferencias internas'` y
    `excluir_de_gastos = true`.
5.  Quedan enlazadas mediante el campo `transfer_pair_id`.

Casos conocidos en este hogar:

| Origen | Destino | Concepto habitual |
|---|---|---|
| Caja Rural | BBVA Josué | Transferencia mensual salario |
| Caja Rural | BBVA Adi | Transferencia mensual salario |
| BBVA Adi | Caja Rural | Aportación gastos comunes |
| Cualquier cuenta | ING Ahorro | Transferencia a ahorro |

Si solo se detecta una de las dos patas (por ejemplo, el banco destino
no está sincronizado aún), la transacción se marca con
`transfer_estado = 'pendiente'` en lugar de excluirse, para revisión manual.

```sql
-- Campos adicionales en transactions
transfer_pair_id   INTEGER REFERENCES transactions(id),
transfer_estado    TEXT CHECK (transfer_estado IN ('completo', 'pendiente', NULL))
```

### PayPal: deduplicación de movimientos

Cuando se paga con PayPal usando la cuenta bancaria como fuente de
fondos, el cargo aparece **en ambos lados**: como un débito en BBVA/Eurocaja
y como un gasto en PayPal. Para no contarlo dos veces:

-   Los movimientos cuyo concepto bancario contenga "PAYPAL" se marcan
    con `origen = 'paypal_passthrough'` y se excluyen del cómputo de
    gastos; el gasto real es el registrado en PayPal.
-   Los pagos financiados desde el saldo propio de PayPal no generan
    movimiento bancario y se registran únicamente desde PayPal.
-   La tabla `transactions` incluye el campo `paypal_transaction_id` para
    enlazar ambos lados cuando corresponda.

------------------------------------------------------------------------

## 2. Base de datos

### accounts

-   id
-   tipo (`bank` | `paypal`)
-   banco / proveedor
-   iban (nullable para PayPal)
-   alias
-   saldo_actual
-   moneda (EUR por defecto)

### transactions

-   id
-   account_id
-   fecha
-   importe
-   concepto_original
-   comercio
-   categoria
-   subcategoria
-   recurrente
-   origen (`bank` | `paypal`)
-   paypal_transaction_id (nullable; enlaza el cargo bancario con su pago PayPal)
-   transfer_pair_id (nullable; enlaza las dos patas de una transferencia interna)
-   transfer_estado (`completo` | `pendiente` | null)
-   excluir_de_gastos (boolean; `true` para `paypal_passthrough` y transferencias internas completas)
-   hash

### categories

Categorías iniciales:

-   Vivienda
-   Alimentación
-   Supermercado
-   Gasolina
-   Transporte
-   Restaurantes
-   Ocio
-   Salud
-   Educación
-   Seguros
-   Impuestos
-   Nómina
-   Transferencias internas
-   Suscripciones
-   PayPal (subtotal de pagos vía PayPal; se desglosa por subcategoría)
-   Otros

------------------------------------------------------------------------

## 3. Motor de categorización

Primera versión:

Sistema basado en reglas.

Ejemplos:

-   Mercadona → Alimentación
-   Carrefour → Alimentación
-   Netflix → Suscripciones
-   Repsol → Gasolina
-   Pagos PayPal con comercio conocido → categoría del comercio (no "PayPal")
-   Pagos PayPal con comercio desconocido → solicitar categoría manual

Cuando aparezca un comercio desconocido:

-   sugerir categoría
-   permitir corrección manual
-   aprender automáticamente para futuros movimientos

------------------------------------------------------------------------

## 4. Gastos recurrentes

Detección automática de:

-   Hipoteca
-   Luz
-   Agua
-   Gas
-   Internet
-   Seguros
-   Netflix
-   Spotify
-   Colegio
-   Guardería

Mostrar:

-   gasto fijo mensual
-   próximo cobro
-   evolución

------------------------------------------------------------------------

## 5. Dashboard

Información principal:

-   Saldo conjunto (bancos + saldo PayPal)
-   Disponible real
-   Gastos pendientes
-   Ahorro previsto
-   Saldo PayPal actual (tile independiente)

Resumen mensual:

-   ingresos
-   gastos
-   ahorro

Gráficas:

-   evolución mensual
-   comparación anual
-   categorías

------------------------------------------------------------------------

## 6. Gastos por categoría

Visualización de:

-   importe mensual
-   porcentaje
-   evolución
-   comparación con meses anteriores

------------------------------------------------------------------------

## 7. Calendario financiero

Mostrar próximos pagos previstos:

-   hipoteca
-   seguros
-   suministros
-   suscripciones

Con previsión del saldo tras cada cargo.

------------------------------------------------------------------------

## 8. Forecast del mes siguiente

### Objetivo

Mostrar una previsión cerrada del mes siguiente antes de que empiece, respondiendo a:

-   ¿Cuánto vamos a ingresar?
-   ¿Qué gastos fijos tenemos ya confirmados?
-   ¿Qué gastos extraordinarios caen este mes?
-   ¿Cuánto nos quedará disponible para gastos variables y ahorro?

### Fuentes de datos

| Dato | Origen |
|---|---|
| Nóminas | Transacciones categorizadas como `Nómina` en los últimos 3 meses |
| Gastos recurrentes | Motor de recurrentes (módulo 4) |
| Gastos estacionales | Tabla `recurring_expenses` con flag `mes_activacion` |
| Saldo inicial | Suma de saldos actuales en todas las cuentas |

### Modelo de datos

```sql
-- Gastos recurrentes con mes de activación
CREATE TABLE recurring_expenses (
    id            SERIAL PRIMARY KEY,
    concepto      TEXT NOT NULL,
    importe       DECIMAL(10,2) NOT NULL,
    cuenta_id     INTEGER REFERENCES accounts(id),
    tipo          TEXT CHECK (tipo IN ('fijo', 'estacional', 'variable')),
    meses         INTEGER[],        -- meses en que aplica (1-12); NULL = todos
    dia_cobro     INTEGER,          -- día del mes estimado
    categoria     TEXT
);
```

### Cálculo del forecast

```
Ingresos previstos
  = suma de nóminas (media 3 meses)
  + ingresos extra confirmados

Gastos fijos previstos
  = gastos recurrentes activos en el mes siguiente
  + gastos estacionales que caen ese mes

Gastos variables estimados
  = media de gastos variables de los últimos 3 meses

Saldo previsto final
  = saldo actual
  + ingresos previstos
  - gastos fijos previstos
  - gastos variables estimados

Margen de ahorro
  = saldo previsto final - colchón mínimo configurado
```

### Pantalla de forecast

Estructura del panel:

```
┌─────────────────────────────────────────────────┐
│  PREVISIÓN SEPTIEMBRE 2026                       │
├──────────────────┬──────────────────────────────┤
│ Ingresos         │ Josué            1.953,79 €  │
│                  │ Adi              2.977,55 €  │
│                  │ ─────────────────────────── │
│                  │ Total            4.931,34 €  │
├──────────────────┼──────────────────────────────┤
│ Gastos fijos     │ Hipoteca           550,93 €  │
│                  │ Préstamos          948,52 €  │
│                  │ Suministros        309,00 €  │
│                  │ Suscripciones      102,74 €  │
│                  │ Salud               59,90 €  │
│                  │ Otros               480,44 € │
│                  │ ─────────────────────────── │
│                  │ Total            2.451,53 €  │
├──────────────────┼──────────────────────────────┤
│ ⚠ Extraordinario │ Seguro Toyota      471,64 €  │
│                  │ Amazon Prime        49,99 €  │
│                  │ ─────────────────────────── │
│                  │ Total              521,63 €  │
├──────────────────┼──────────────────────────────┤
│ Variables (est.) │ Media 3 meses    ~800,00 €   │
├──────────────────┼──────────────────────────────┤
│ DISPONIBLE       │                 1.158,18 €   │
└──────────────────┴──────────────────────────────┘
```

Reglas de presentación:

-   Los gastos extraordinarios (solo algunos meses del año) se destacan
    visualmente con un icono de advertencia y color diferenciado.
-   Si el disponible estimado cae por debajo del colchón mínimo configurado,
    se muestra alerta en rojo.
-   El desglose por cuenta (BBVA Josué, BBVA Adi, Caja Rural) es accesible
    desde el panel expandido.

### Gastos estacionales conocidos

Cargados como datos semilla en la base de datos:

| Concepto | Importe | Meses |
|---|---|---|
| Seguro Toyota | 471,64 € | Septiembre |
| Seguro Kia | 121,82 € | Febrero, Abril |
| Seguro Hogar | 98,12 € | Febrero, Mayo, Agosto, Noviembre |
| Seguro Vida | 121,91 € | Febrero, Mayo, Agosto, Noviembre |
| Amazon Prime | 49,99 € | Septiembre |
| Microsoft 365 | 129,99 € | Agosto |
| Mantenimiento caldera | 155,05 € | Mayo |
| Comisión tarjeta | 80,00 € | Julio |
| Comedor colegio (inicio curso) | 242,00 € | Octubre |
| Remesas | 100–200 € | Según mes |

------------------------------------------------------------------------

## 9. Buscador

Búsquedas como:

-   Amazon
-   Mercadona mayo
-   Gasolina febrero
-   Seguro coche

------------------------------------------------------------------------

## 10. IA (segunda fase)

La IA no accederá directamente a los movimientos bancarios.

Consumirá únicamente los datos estructurados de la base de datos.

Ejemplos:

-   ¿En qué gastamos más dinero este año?
-   ¿Qué categoría ha aumentado?
-   ¿Dónde podemos ahorrar?
-   Resume el último trimestre.

------------------------------------------------------------------------

# Tecnologías

Backend

-   Python
-   FastAPI
-   SQLAlchemy
-   Alembic

Persistencia

-   PostgreSQL

Automatización bancaria

-   Playwright (BBVA, Eurocaja Rural)

Integración PayPal

-   PayPal REST API v2 (OAuth 2.0 client credentials)

Planificación

-   APScheduler

Contenedores

-   Docker Compose

Frontend

-   React

------------------------------------------------------------------------

# Roadmap

## MVP

-   Base de datos
-   Sincronización BBVA
-   Sincronización Eurocaja
-   Sincronización PayPal (REST API)
-   Deduplicación movimientos banco ↔ PayPal
-   Importación incremental
-   Dashboard básico (incluye tile saldo PayPal)

## Versión 1

-   Motor de reglas
-   Categorización automática
-   Recurrentes
-   Calendario financiero

## Versión 2

-   Forecast del mes siguiente
-   Gastos estacionales (datos semilla)
-   Alertas de disponible bajo

## Versión 3

-   IA
-   Recomendaciones
-   Presupuestos

------------------------------------------------------------------------

# Principios de diseño

-   Automatización completa.
-   Cero introducción manual de movimientos.
-   Datos locales y controlados por el usuario.
-   Arquitectura desacoplada.
-   Fácil incorporación de nuevos bancos.
-   Sencillez antes que complejidad.
