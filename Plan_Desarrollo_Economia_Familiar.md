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
-   excluir_de_gastos (boolean; `true` para movimientos `paypal_passthrough`)
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

## 8. Buscador

Búsquedas como:

-   Amazon
-   Mercadona mayo
-   Gasolina febrero
-   Seguro coche

------------------------------------------------------------------------

## 9. IA (segunda fase)

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

-   IA
-   Recomendaciones
-   Presupuestos
-   Alertas

------------------------------------------------------------------------

# Principios de diseño

-   Automatización completa.
-   Cero introducción manual de movimientos.
-   Datos locales y controlados por el usuario.
-   Arquitectura desacoplada.
-   Fácil incorporación de nuevos bancos.
-   Sencillez antes que complejidad.
