"""
Utilidades compartidas por los scripts de sync manual (BBVA, Eurocaja Rural).
"""

import sys
from pathlib import Path

import httpx


def get_account(backend_url: str, account_id: int) -> dict:
    """
    Obtiene los datos de una cuenta desde el backend.

    Args:
        backend_url: URL base del backend (ej. http://localhost:8000).
        account_id: ID de la cuenta.

    Returns:
        Diccionario con los datos de la cuenta.

    Raises:
        SystemExit: Si el backend no responde o la cuenta no existe.
    """
    try:
        resp = httpx.get(f"{backend_url}/api/v1/accounts/{account_id}", timeout=10)
    except httpx.ConnectError:
        print(f"❌ No se puede conectar al backend en {backend_url}")
        sys.exit(1)

    if resp.status_code == 404:
        print(f"❌ Cuenta {account_id} no encontrada en el backend.")
        sys.exit(1)

    if not resp.is_success:
        print(f"❌ Error del backend: {resp.status_code} {resp.text}")
        sys.exit(1)

    return resp.json()


def list_accounts_by_provider(backend_url: str, proveedor: str) -> list[dict]:
    """
    Lista las cuentas activas de un proveedor concreto.

    Args:
        backend_url: URL base del backend.
        proveedor: Nombre del proveedor (ej. "BBVA", "Eurocaja Rural").

    Returns:
        Lista de diccionarios con los datos de cada cuenta.
    """
    try:
        resp = httpx.get(f"{backend_url}/api/v1/accounts/", timeout=10)
        return [a for a in resp.json() if a.get("proveedor") == proveedor]
    except Exception:
        return []


def upload_file(
    backend_url: str,
    account_id: int,
    filename: str,
    content_bytes: bytes,
    mime_type: str = "application/octet-stream",
) -> dict:
    """
    Envía un archivo al endpoint de upload del backend.

    Args:
        backend_url: URL base del backend.
        account_id: ID de la cuenta destino.
        filename: Nombre del archivo (se usa para la detección de formato en el backend).
        content_bytes: Contenido binario del archivo.
        mime_type: MIME type del archivo.

    Returns:
        Respuesta JSON del backend con el resultado de la importación.

    Raises:
        RuntimeError: Si el backend devuelve un error.
    """
    resp = httpx.post(
        f"{backend_url}/api/v1/sync/{account_id}/upload",
        files={"file": (filename, content_bytes, mime_type)},
        timeout=60,
    )
    if not resp.is_success:
        raise RuntimeError(f"Error del backend al importar: {resp.status_code} {resp.text}")
    return resp.json()


def resolve_account_id(backend_url: str, proveedor: str, argv: list[str]) -> int:
    """
    Resuelve el account_id desde argumentos CLI, env var ACCOUNT_ID o
    autodetección si hay una sola cuenta del proveedor.

    Args:
        backend_url: URL base del backend.
        proveedor: Proveedor para la autodetección (ej. "BBVA").
        argv: Lista de argumentos de línea de comandos (sys.argv[1:]).

    Returns:
        ID de la cuenta resuelta.

    Raises:
        SystemExit: Si no se puede resolver.
    """
    import os

    if argv:
        return int(argv[0])

    if os.environ.get("ACCOUNT_ID"):
        return int(os.environ["ACCOUNT_ID"])

    accounts = list_accounts_by_provider(backend_url, proveedor)
    if not accounts:
        print(f"No se encontraron cuentas de {proveedor!r} en el backend.")
        print(f"Uso: .venv/bin/python3 scripts/sync_*_manual.py ACCOUNT_ID")
        sys.exit(1)

    if len(accounts) == 1:
        account_id = accounts[0]["id"]
        print(f"Cuenta {proveedor} encontrada: [{account_id}] {accounts[0].get('alias', '')}")
        return account_id

    print(f"Cuentas {proveedor} disponibles:")
    for a in accounts:
        print(f"  [{a['id']}] {a.get('alias', '')} — IBAN: {a.get('iban', 'N/A')}")
    return int(input("Introduce el ID de la cuenta: ").strip())
