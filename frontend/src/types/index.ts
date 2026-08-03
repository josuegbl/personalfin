export type AccountType = "bank" | "paypal";

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
  origen: "bank" | "paypal";
  paypal_transaction_id: string | null;
  excluir_de_gastos: boolean;
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
