export type AccountType = "bank";

export interface Account {
  id: number;
  tipo: AccountType;
  proveedor: string;
  iban: string | null;
  alias: string;
  saldo_actual: number;
  moneda: string;
  propietario: string | null;
  activa: boolean;
  ultima_sync: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  nombre: string;
  icono: string | null;
  color: string | null;
  padre_id: number | null;
  naturaleza: "gasto" | "ingreso" | "transferencia" | "neutral";
  incluida_en_analisis: boolean;
  se_puede_eliminar: boolean;
}

export interface CategoryCreate {
  nombre: string;
  color: string | null;
  padre_id: number | null;
  naturaleza: "gasto" | "ingreso" | "transferencia" | "neutral";
  incluida_en_analisis: boolean;
}

export interface CategoryUpdate {
  nombre: string;
}

export interface Transaction {
  id: number;
  account_id: number;
  fecha: string;
  importe: number;
  concepto_original: string;
  comercio: string | null;
  categoria_id: number | null;
  categoria: Category | null;
  subcategoria: string | null;
  recurrente: boolean;
  origen: "bank";
  notas: string | null;
  hash: string;
  created_at: string;
}

export interface AccountBalance {
  account: Account;
  saldo: number;
  variacion_mes: number;
}

export interface MonthlySummary {
  anio: number;
  mes: number;
  ingresos: number;
  gastos: number;
  ahorro: number;
  num_transacciones: number;
}

export interface CategoryExpense {
  categoria_id: number | null;
  categoria_nombre: string;
  color: string | null;
  importe: number;
  porcentaje: number;
  num_transacciones: number;
}

export interface DashboardData {
  saldo_total: number;
  saldo_por_cuenta: AccountBalance[];
  resumen_mes_actual: MonthlySummary;
  resumen_mes_anterior: MonthlySummary;
  gastos_por_categoria: CategoryExpense[];
  evolucion_mensual: MonthlySummary[];
}

export interface UploadResult {
  imported: number;
  total_in_file: number;
  skipped_existing: number;
  balance: number;
}

export interface RecurringExpenseTierIn {
  importe: number;
  meses: number[] | null;
}

export interface RecurringExpenseTierOut {
  importe: number;
  meses: number[] | null;
}

export interface RecurringExpenseCreate {
  categoria: string;
  concepto: string;
  tiers: RecurringExpenseTierIn[];
}

export interface RecurringExpenseUpdate {
  categoria: string;
  concepto: string;
  tiers: RecurringExpenseTierIn[];
}

export interface RecurringExpenseOut {
  id: number;
  categoria: string | null;
  subcategoria_id: number | null;
  concepto: string;
  tipo: string;
  tiers: RecurringExpenseTierOut[];
}

export interface ForecastCategoryItem {
  id?: number;           // Present for gastos_fijos (RecurringExpense.id)
  categoria?: string | null;
  nombre: string;
  importe_planificado: number;
  importe_real: number;
  meses?: number[] | null; // Present for gastos_fijos; null = every month
  tiers?: RecurringExpenseTierOut[];
}

export interface FixedCategoryGroup {
  categoria: string;
  subcategorias: ForecastCategoryItem[];
}

export interface ForecastCategoryInput {
  nombre: string;
  importe_planificado: number;
}

export interface ForecastPlanUpdate {
  cuenta_personal_a: number;
  cuenta_personal_b: number;
  ingresos_planificados?: number | null;
  ingresos_persona_a: number;
  ingresos_persona_b: number;
  categorias: ForecastCategoryInput[];
}

export interface ForecastData {
  anio: number;
  mes: number;
  es_ejecucion: boolean;
  cuenta_personal_a: number;
  cuenta_personal_b: number;
  ingresos_planificados: number | null;
  ingresos_persona_a: number;
  ingresos_persona_b: number;
  ingresos_nomina: number;
  ingresos_otros: number;
  ingresos_reales: number;
  gastos_fijos: ForecastCategoryItem[];
  gastos_fijos_por_categoria: FixedCategoryGroup[];
  gastos_variables: ForecastCategoryItem[];
  gastos_reales_por_categoria: ForecastCategoryItem[];
  total_cuentas_personales_plan: number;
  total_gastos_fijos_plan: number;
  total_gastos_variables_plan: number;
  ahorro_estimado: number;
  total_gastos_reales: number;
  ahorro_real: number;
}
