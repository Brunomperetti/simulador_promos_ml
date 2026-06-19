"""Utilidades de limpieza y normalización para el simulador."""

from __future__ import annotations

import re
import unicodedata
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
