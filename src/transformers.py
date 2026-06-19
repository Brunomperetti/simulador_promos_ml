"""Transformaciones para cruzar promociones de Mercado Libre con Tienda Nube."""

from __future__ import annotations

import pandas as pd

from src.loaders import ML_REQUIRED_COLUMNS, TN_COLUMN_ALIASES
from src.utils import add_normalized_sku

OUTPUT_COLUMNS = [
    "SKU",
    "TITLE",
    "ORIGINAL_PRICE",
    "DISCOUNT_PERCENTAGE",
    "FINAL_PRICE",
    "ACTION",
    "Costo",
    "Código de barras / EAN",
    "Nombre",
    "Categorías",
    "Marca",
]
SORT_COLUMNS = ["Categorías", "Marca", "SKU"]


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def merge_ml_with_tienda_nube(ml_df: pd.DataFrame, tn_df: pd.DataFrame) -> pd.DataFrame:
    """Cruza Mercado Libre con Tienda Nube por SKU normalizado."""
    ml_prepared = _ensure_columns(ml_df, ML_REQUIRED_COLUMNS)
    tn_prepared = _ensure_columns(tn_df, list(TN_COLUMN_ALIASES.keys()))

    ml_prepared = add_normalized_sku(ml_prepared, "SKU")
    tn_prepared = add_normalized_sku(tn_prepared, "SKU")
    tn_prepared = tn_prepared.drop_duplicates(subset=["_SKU_NORMALIZED"], keep="first")

    enrichment_columns = ["_SKU_NORMALIZED", "Costo", "Código de barras / EAN", "Nombre", "Categorías", "Marca"]
    merged = ml_prepared.merge(tn_prepared[enrichment_columns], on="_SKU_NORMALIZED", how="left")
    merged["_HAS_MATCH"] = merged["Nombre"].notna() | merged["Costo"].notna() | merged["Código de barras / EAN"].notna()
    return merged


def build_display_table(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona y ordena las columnas visibles en la app."""
    table = _ensure_columns(merged_df, OUTPUT_COLUMNS)[OUTPUT_COLUMNS].copy()
    table = table.sort_values(SORT_COLUMNS, na_position="last", kind="stable")
    return table.reset_index(drop=True)
