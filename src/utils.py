"""Utilidades de limpieza y normalización para el simulador."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Iterable

import pandas as pd


def normalize_column_name(column: object) -> str:
    """Devuelve un nombre de columna comparable y estable."""
    text = "" if column is None else str(column)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def compact_column_name(column: object) -> str:
    """Normaliza una columna eliminando separadores para búsquedas flexibles."""
    return re.sub(r"[^a-z0-9]+", "", normalize_column_name(column))


def normalize_sku(value: object) -> str:
    """Normaliza un SKU para cruces entre archivos de diferentes fuentes."""
    if pd.isna(value):
        return ""

    sku = str(value).strip()
    if sku.endswith(".0") and re.fullmatch(r"\d+\.0", sku):
        sku = sku[:-2]

    sku = unicodedata.normalize("NFKC", sku)
    sku = re.sub(r"\s+", "", sku)
    return sku.upper()


def format_plain_text(value: object) -> str:
    """Formatea identificadores como texto, evitando decimales y notación científica."""
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    try:
        decimal_value = Decimal(text.replace(",", "."))
    except (InvalidOperation, ValueError):
        return text[:-2] if re.fullmatch(r"\d+\.0", text) else text

    if decimal_value == decimal_value.to_integral_value():
        return str(decimal_value.quantize(Decimal("1")))
    return format(decimal_value.normalize(), "f")


def format_currency(value: object) -> str:
    """Formatea importes con separadores de miles y dos decimales."""
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if not text:
        return ""

    normalized = text
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        amount = float(normalized)
    except ValueError:
        return text

    formatted = f"$ {amount:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def add_normalized_sku(df: pd.DataFrame, source_column: str = "SKU") -> pd.DataFrame:
    """Agrega la columna técnica _SKU_NORMALIZED sin mutar el DataFrame original."""
    result = df.copy()
    result["_SKU_NORMALIZED"] = result[source_column].map(normalize_sku)
    return result


def first_existing_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    """Busca una columna por aliases flexibles."""
    compact_to_original = {compact_column_name(column): column for column in columns}
    for candidate in candidates:
        found = compact_to_original.get(compact_column_name(candidate))
        if found is not None:
            return found
    return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia columnas vacías y filas completamente vacías."""
    result = df.copy()
    result = result.dropna(axis=0, how="all").dropna(axis=1, how="all")
    result.columns = [str(column).strip() for column in result.columns]
    return result
