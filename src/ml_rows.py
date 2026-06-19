"""Detección de publicaciones reales de Mercado Libre."""

from __future__ import annotations

import unicodedata

import pandas as pd

INSTRUCTIVE_SUBSTRINGS = (
    "no modifiques esta columna",
    "precio final",
    "final_price",
    "discount_percentage",
    "original_price",
)
INSTRUCTIVE_EXACT_VALUES = {"sku", "titulo", "title", "item_id", "action"}


def _clean_text(value: object) -> str:
    """Normaliza texto para comparaciones robustas."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


def is_blank_value(value: object) -> bool:
    """Indica si un valor debe considerarse vacío."""
    return _clean_text(value) in {"", "nan", "none", "nat"}


def row_has_instructive_text(row: pd.Series) -> bool:
    """Detecta filas técnicas o instructivas de la plantilla de Mercado Libre."""
    columns_to_check = [
        "ITEM_ID",
        "SKU",
        "TITLE",
        "ORIGINAL_PRICE",
        "DISCOUNT_PERCENTAGE",
        "FINAL_PRICE",
        "ACTION",
    ]
    for column in columns_to_check:
        text = _clean_text(row.get(column))
        if not text:
            continue
        if text in INSTRUCTIVE_EXACT_VALUES:
            return True
        if any(marker in text for marker in INSTRUCTIVE_SUBSTRINGS):
            return True
    return False


def is_real_ml_publication(row: pd.Series) -> bool:
    """Determina si una fila representa una publicación editable real de Mercado Libre."""
    if row_has_instructive_text(row):
        return False

    item_id = row.get("ITEM_ID")
    title = row.get("TITLE")
    sku = row.get("SKU")
    has_item_id = not is_blank_value(item_id)
    has_title_and_sku = not is_blank_value(title) and not is_blank_value(sku)
    return has_item_id or has_title_and_sku


def filter_real_ml_publications(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve solo las filas que son publicaciones reales de Mercado Libre."""
    if df.empty:
        return df.copy()
    mask = df.apply(is_real_ml_publication, axis=1)
    return df.loc[mask].copy()
