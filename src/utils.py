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


def parse_currency_amount(value: object) -> float:
    """Convierte importes en formato estadounidense o argentino a número real."""
    if pd.isna(value):
        raise ValueError("No se puede convertir un importe vacío.")

    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return float(value)

    text = str(value).strip()
    if not text:
        raise ValueError("No se puede convertir un importe vacío.")

    normalized = re.sub(r"[^\d,.-]", "", text)
    if not normalized or normalized in {"-", ",", "."}:
        raise ValueError(f"No se pudo convertir el importe: {value}")

    last_comma = normalized.rfind(",")
    last_dot = normalized.rfind(".")

    if last_comma >= 0 and last_dot >= 0:
        decimal_separator = "," if last_comma > last_dot else "."
        thousands_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(thousands_separator, "")
        normalized = normalized.replace(decimal_separator, ".")
    elif "," in normalized:
        normalized = _normalize_single_separator_amount(normalized, ",")
    elif "." in normalized:
        normalized = _normalize_single_separator_amount(normalized, ".")

    try:
        return float(Decimal(normalized))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"No se pudo convertir el importe: {value}") from exc


def _normalize_single_separator_amount(value: str, separator: str) -> str:
    """Normaliza importes con un único tipo de separador."""
    parts = value.split(separator)
    if len(parts) == 2:
        integer_part, decimal_part = parts
        if len(decimal_part) == 3 and integer_part and len(integer_part) <= 3:
            return integer_part + decimal_part
        return f"{integer_part}.{decimal_part}" if separator == "," else value

    if all(len(part) == 3 for part in parts[1:]):
        return "".join(parts)

    integer_part = "".join(parts[:-1])
    return f"{integer_part}.{parts[-1]}"


def format_currency(value: object) -> str:
    """Formatea importes con separadores de miles y dos decimales."""
    if pd.isna(value):
        return ""

    try:
        amount = parse_currency_amount(value)
    except ValueError:
        return str(value).strip()

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
