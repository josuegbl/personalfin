import io
import csv
import tempfile
import os
import unicodedata
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from app.services.sync.base import SourceAdapter, RawTransaction


# ---------------------------------------------------------------------------
# Adaptador CSV (upload manual)
# ---------------------------------------------------------------------------

class BBVAAdapter(SourceAdapter):
    """
    Adaptador BBVA basado en importación manual de CSV.
    El usuario descarga el extracto desde la web de BBVA y lo sube al backend.

    Formato del CSV exportado por BBVA (separador ';'):
        Fecha;Fecha valor;Concepto;Movimiento;Disponible
    """

    def fetch_transactions(self) -> list[RawTransaction]:
        raise NotImplementedError("BBVA usa importación CSV manual")

    def fetch_balance(self) -> Decimal:
        raise NotImplementedError("BBVA usa importación CSV manual")

    @classmethod
    def parse_csv_upload(cls, content: str) -> tuple[list[RawTransaction], Decimal | None]:
        """
        Parsea el contenido del CSV exportado por BBVA.

        Args:
            content: Texto del archivo CSV.

        Returns:
            Tupla (transacciones, saldo_actual). El saldo se extrae de la
            columna 'Disponible' de la primera fila (BBVA exporta en orden
            descendente).
        """
        lines = content.splitlines()

        data_start = 0
        for i, line in enumerate(lines):
            if "Fecha" in line and ("Concepto" in line or "Movimiento" in line):
                data_start = i
                break

        reader = csv.DictReader(
            io.StringIO("\n".join(lines[data_start:])),
            delimiter=";",
        )

        results: list[RawTransaction] = []
        balance: Decimal | None = None

        for row in reader:
            fecha_raw   = _get_field(row, "Fecha", "FECHA")
            concepto    = _get_field(row, "Concepto", "CONCEPTO", "Descripción")
            importe_raw = _get_field(row, "Movimiento", "Importe", "IMPORTE", "Cargo/Abono")
            saldo_raw   = _get_field(row, "Disponible", "DISPONIBLE", "Saldo")

            if not fecha_raw or not importe_raw:
                continue

            try:
                fecha   = _parse_date(fecha_raw)
                importe = _parse_amount(importe_raw)
            except (ValueError, InvalidOperation):
                continue

            if balance is None and saldo_raw:
                try:
                    balance = _parse_amount(saldo_raw)
                except (ValueError, InvalidOperation):
                    pass

            results.append(RawTransaction(
                fecha=fecha,
                importe=importe,
                concepto=concepto or "",
            ))

        return results, balance


# ---------------------------------------------------------------------------
# Adaptador Playwright (sync automático)
# ---------------------------------------------------------------------------

class BBVAPlaywrightAdapter(SourceAdapter):
    """
    Adaptador BBVA con login automático via Playwright y descarga del Excel
    de movimientos desde web.bbva.es.

    Credenciales requeridas en backend/.env según el propietario de la cuenta:
        Cuenta A → BBVA_CUENTA_A_USER / BBVA_CUENTA_A_PASSWORD
        Cuenta B → BBVA_CUENTA_B_USER / BBVA_CUENTA_B_PASSWORD
    """

    _LOGIN_URL  = "https://www.bbva.es/nimbus/signin.html"
    _HOME_URL   = "https://www.bbva.es/personas.html"
    # BBVA bloquea headless; se requiere headless=False con Xvfb en Docker Linux
    _STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--start-maximized",
    ]
    _USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
    # propietario normalizado → prefijo de variables de entorno
    _CREDENTIAL_MAP: dict[str, str] = {
        "CUENTA_A": "BBVA_CUENTA_A",
        "CUENTA_B": "BBVA_CUENTA_B",
    }

    def fetch_transactions(self) -> list[RawTransaction]:
        raise NotImplementedError("BBVAPlaywrightAdapter usa sync() directamente")

    def fetch_balance(self) -> Decimal:
        raise NotImplementedError("BBVAPlaywrightAdapter usa sync() directamente")

    def sync(self) -> int:
        """
        Abre Chromium en modo headless, descarga el Excel de movimientos de la
        cuenta y lo importa en una única sesión de navegador.

        Returns:
            Número de transacciones nuevas importadas.
        """
        user, password = self._resolve_credentials()

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ImportError(
                "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"
            ) from exc

        with sync_playwright() as p:
            # headless=False es necesario: BBVA bloquea todos los modos headless.
            # En Docker/Linux sin display, ejecuta con Xvfb (ver Dockerfile).
            try:
                browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=300, args=self._STEALTH_ARGS)
            except Exception:
                browser = p.chromium.launch(headless=False, slow_mo=300, args=self._STEALTH_ARGS)
            ctx = browser.new_context(
                user_agent=self._USER_AGENT,
                locale="es-ES",
                accept_downloads=True,
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = ctx.new_page()
            try:
                self._login(page, user, password)
                xlsx_bytes = self._download_movements_excel(page)
            finally:
                browser.close()

        transactions, balance = parse_bbva_excel(xlsx_bytes)
        return self._persist(transactions, balance)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_credentials(self) -> tuple[str, str]:
        """
        Mapea account.propietario al par de credenciales correspondiente.

        Returns:
            Tupla (usuario, contraseña).

        Raises:
            ValueError: Si las variables de entorno no están configuradas.
        """
        propietario_raw = self.account.propietario or ""
        normalized = "".join(
            c for c in unicodedata.normalize("NFD", propietario_raw.upper())
            if unicodedata.category(c) != "Mn"
        )
        prefix = self._CREDENTIAL_MAP.get(normalized, "BBVA_CUENTA_A")

        user     = os.environ.get(f"{prefix}_USER", "")
        password = os.environ.get(f"{prefix}_PASSWORD", "")

        if not user or not password:
            raise ValueError(
                f"Credenciales BBVA no configuradas para propietario={propietario_raw!r}. "
                f"Define {prefix}_USER y {prefix}_PASSWORD en backend/.env"
            )
        return user, password

    def _login(self, page, user: str, password: str) -> None:
        """
        Navega al login de BBVA y rellena las credenciales automáticamente.

        Requiere headless=False (BBVA bloquea todos los modos headless).
        """
        page.goto(self._LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_000)

        for sel in ("input[placeholder='Usuario']", "input[name='user']", "input[type='text']"):
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.fill(sel, user)
                    break
            except Exception:
                pass

        for sel in ("input[placeholder='Clave de acceso']", "input[name='password']", "input[type='password']"):
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.fill(sel, password)
                    break
            except Exception:
                pass

        for sel in ("button:has-text('Iniciar sesión')", "button[type='submit']",
                    "[class*='c-button--secondary']:has-text('Iniciar sesión')"):
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.click(sel)
                    break
            except Exception:
                pass

        page.wait_for_url("**/web.bbva.es/**", timeout=40_000)
        _wait_spa(page)

    def _download_movements_excel(self, page) -> bytes:
        """
        Navega a la cuenta correcta (por IBAN), entra en la pestaña de
        movimientos y descarga el Excel.

        Returns:
            Contenido binario del archivo .xlsx descargado.

        Raises:
            ValueError: Si la cuenta no tiene IBAN configurado.
            RuntimeError: Si no se encuentra la tarjeta de la cuenta en el portal.
        """
        iban = (self.account.iban or "").replace(" ", "").upper()
        if not iban:
            raise ValueError(
                f"La cuenta {self.account.alias!r} no tiene IBAN — configúralo antes de hacer sync automático"
            )

        _click_account_by_iban(page, iban)

        page.locator("[aria-label*='movimientos']").first.click()
        _wait_spa(page, timeout=10_000)

        with page.expect_download(timeout=30_000) as dl_info:
            page.locator("[class*='c-icon-download']").first.click()

        dl = dl_info.value
        tmp = tempfile.mktemp(suffix=".xlsx")
        dl.save_as(tmp)
        try:
            with open(tmp, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Parser Excel (reutilizable: Playwright y upload manual de .xlsx)
# ---------------------------------------------------------------------------

def parse_bbva_excel(content: bytes) -> tuple[list[RawTransaction], Decimal | None]:
    """
    Parsea el Excel descargado desde el portal BBVA (hoja 'Informe BBVA').

    Estructura de columnas (fila 5 = cabecera, datos desde fila 6):
        B: F.Valor  C: Fecha  D: Concepto  E: Movimiento
        F: Importe  G: Divisa  H: Disponible  J: Observaciones

    Args:
        content: Bytes del archivo .xlsx.

    Returns:
        Tupla (transacciones, saldo_actual).
        El saldo se extrae de la primera fila de datos (más reciente).

    Raises:
        ImportError: Si openpyxl no está instalado.
        KeyError: Si el Excel no contiene la hoja esperada.
    """
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "openpyxl es necesario para el Excel de BBVA. Instala con: pip install openpyxl"
        ) from exc

    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb["Informe BBVA"]

    results: list[RawTransaction] = []
    balance: Decimal | None = None
    header_found = False

    for row in ws.iter_rows(values_only=True):
        if not header_found:
            if row[1] == "F.Valor":
                header_found = True
            continue

        fecha_raw  = row[2]              # C: Fecha operación
        concepto   = (row[3] or "").strip()  # D: Concepto
        movimiento = (row[4] or "").strip()  # E: Movimiento
        importe    = row[5]              # F: Importe (ya es float en el Excel)
        disponible = row[7]              # H: Disponible
        obs        = (row[9] or "").strip()  # J: Observaciones

        if fecha_raw is None or importe is None:
            continue

        fecha = _parse_excel_date(fecha_raw)
        if fecha is None:
            continue

        # Primera fila válida → saldo actual
        if balance is None and disponible is not None:
            try:
                balance = Decimal(str(disponible))
            except Exception:
                pass

        # concepto_original: Concepto + Movimiento cuando aporta info adicional
        parts = [concepto]
        if movimiento and movimiento.upper() != concepto.upper():
            parts.append(movimiento)
        concepto_original = " | ".join(p for p in parts if p)

        # comercio: Observaciones suele contener el nombre del comercio completo
        comercio = obs if obs and obs.upper() != movimiento.upper() else None

        results.append(RawTransaction(
            fecha=fecha,
            importe=Decimal(str(importe)),
            concepto=concepto_original,
            comercio=comercio,
        ))

    return results, balance


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def _wait_spa(page, timeout: int = 20_000) -> None:
    """Espera a que la SPA de web.bbva.es termine de renderizar."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(2_000)


def _click_account_by_iban(page, iban: str) -> None:
    """
    Localiza en el dashboard la tarjeta de cuenta que contiene el IBAN y hace
    clic. Prueba el IBAN completo y, como fallback, los últimos 4 dígitos.

    Args:
        page: Página de Playwright (ya en web.bbva.es).
        iban: IBAN normalizado (sin espacios, mayúsculas).

    Raises:
        RuntimeError: Si no se encuentra ninguna tarjeta con ese IBAN.
    """
    for text in (iban, iban[-4:]):
        for sel in (
            f"[class*='product-list']:has-text('{text}')",
            f"[class*='product']:has-text('{text}')",
        ):
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3_000):
                    el.click()
                    _wait_spa(page, timeout=8_000)
                    return
            except Exception:
                pass

    raise RuntimeError(
        f"No se encontró la tarjeta de cuenta con IBAN {iban!r} en el dashboard de BBVA. "
        "Comprueba que el IBAN guardado en la base de datos coincide con el mostrado en la web."
    )


def _parse_excel_date(raw) -> date | None:
    """Convierte fechas del Excel (string o datetime) a date."""
    if raw is None:
        return None
    if isinstance(raw, str):
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None
    if hasattr(raw, "date"):
        return raw.date()
    return None


def _get_field(row: dict, *keys: str) -> str | None:
    for k in keys:
        v = row.get(k, "").strip()
        if v:
            return v
    return None


def _parse_amount(raw: str) -> Decimal:
    cleaned = (
        raw.strip()
        .replace("€", "").replace("\xa0", "")
        .replace(" ", "").replace(".", "").replace(",", ".")
    )
    return Decimal(cleaned)


def _parse_date(raw: str) -> date:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {raw}")
