import io
import csv
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from app.services.sync.base import SourceAdapter, RawTransaction


class EurocajaAdapter(SourceAdapter):
    """
    Adaptador Eurocaja Rural basado en importación manual de CSV.
    El usuario descarga el extracto desde la web de Eurocaja y lo sube al backend.

    Formato real del CSV exportado por RuralVía (separador ';', UTF-8 con BOM):
        Fecha de ejecución;Fecha valor;Descripción;Importe;Saldo

    Las primeras filas son metadatos:
        Cuentas > Consultar > Movimientos;
        Movimientos;
        Cuenta;ES59 XXXX...;
        Fecha desde;DD-MM-YYYY;
        Fecha hasta;DD-MM-YYYY;
        Tipo de movimiento;;
        (línea vacía)
    """

    def fetch_transactions(self) -> list[RawTransaction]:
        raise NotImplementedError("Eurocaja usa importación CSV manual")

    def fetch_balance(self) -> Decimal:
        raise NotImplementedError("Eurocaja usa importación CSV manual")

    # ------------------------------------------------------------------
    # API pública para el endpoint de upload
    # ------------------------------------------------------------------

    @classmethod
    def parse_csv_upload(cls, content: str) -> tuple[list[RawTransaction], Decimal | None]:
        """
        Parsea el CSV exportado por RuralVía (Eurocaja Rural).
        Devuelve (transacciones, saldo_actual).

        El saldo se extrae de la columna 'Saldo' de la primera fila de datos
        (el CSV está en orden descendente — la primera fila es la más reciente).
        """
        # Eliminar BOM si está presente
        content = content.lstrip('﻿')

        lines = content.splitlines()

        # Saltar las filas de metadatos hasta encontrar la cabecera de columnas.
        # La cabecera empieza con "Fecha" y contiene "Importe".
        data_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("Fecha") and "Importe" in line:
                data_start = i
                break

        reader = csv.DictReader(
            io.StringIO("\n".join(lines[data_start:])),
            delimiter=";",
        )

        results: list[RawTransaction] = []
        balance: Decimal | None = None

        for row in reader:
            fecha_raw   = _get_field(
                row,
                "Fecha de ejecución", "Fecha de ejecucion",
                "Fecha Operación", "Fecha Mov", "FECHA OPERACION", "Fecha",
            )
            concepto    = _get_field(row, "Descripción", "Descripcion", "Concepto", "CONCEPTO")
            importe_raw = _get_field(row, "Importe", "IMPORTE", "Cargo/Abono")
            saldo_raw   = _get_field(row, "Saldo", "SALDO", "Disponible")

            if not fecha_raw or not importe_raw:
                continue

            try:
                fecha   = _parse_date(fecha_raw)
                importe = _parse_amount(importe_raw)
            except (ValueError, InvalidOperation):
                continue

            # La primera fila válida (más reciente) tiene el saldo actual
            if balance is None and saldo_raw:
                try:
                    balance = _parse_amount(saldo_raw)
                except (ValueError, InvalidOperation):
                    pass

            results.append(RawTransaction(
                fecha=fecha,
                importe=importe,
                concepto=(concepto or "").strip(),
            ))

        return results, balance


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_field(row: dict, *keys: str) -> str | None:
    for k in keys:
        v = row.get(k, "").strip()
        if v:
            return v
    return None


def _parse_amount(raw: str) -> Decimal:
    """
    Convierte '1.234,56   €' o '-22,44   €' a Decimal.
    Maneja espacios extras, el símbolo € y separadores españoles.
    """
    cleaned = (
        raw.strip()
        .replace("€", "")
        .replace("\xa0", "")   # non-breaking space
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
    )
    return Decimal(cleaned)


def _parse_date(raw: str) -> date:
    """
    Formatos soportados:
      - 'DD-MM-YYYY HH:MM'  (Eurocaja con hora)
      - 'DD-MM-YYYY'
      - 'DD/MM/YYYY'
      - 'YYYY-MM-DD'
    """
    raw = raw.strip()
    for fmt in ("%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {raw}")
