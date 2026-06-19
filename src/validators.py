"""Validaciones, alertas y métricas de la app."""

from __future__ import annotations

import pandas as pd

from src.loaders import ML_REQUIRED_COLUMNS, TN_COLUMN_ALIASES
from src.utils import first_existing_column


def find_missing_columns(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    """Devuelve las columnas requeridas que no están presentes."""
    return [column for column in required_columns if column not in df.columns]


def validate_ml_columns(df: pd.DataFrame) -> list[str]:
    """Valida columnas mínimas del archivo de Mercado Libre."""
    return find_missing_columns(df, ML_REQUIRED_COLUMNS)


def validate_tienda_nube_columns(df: pd.DataFrame) -> list[str]:
    """Valida columnas mínimas del archivo de Tienda Nube tras aplicar aliases."""
    missing = []
    for canonical, aliases in TN_COLUMN_ALIASES.items():
        if canonical not in df.columns and first_existing_column(df.columns, aliases) is None:
            missing.append(canonical)
    return missing


def is_blank(series: pd.Series) -> pd.Series:
    """Detecta valores vacíos considerando nulos y strings en blanco."""
    return series.isna() | series.astype(str).str.strip().eq("")


def build_metrics(merged_df: pd.DataFrame) -> dict[str, int]:
    """Construye las métricas principales del cruce."""
    has_match = merged_df.get("_HAS_MATCH", pd.Series(False, index=merged_df.index)).fillna(False)
    cost = merged_df.get("Costo", pd.Series(pd.NA, index=merged_df.index))
    ean = merged_df.get("Código de barras / EAN", pd.Series(pd.NA, index=merged_df.index))

    return {
        "Total publicaciones ML": int(len(merged_df)),
        "Total productos cruzados": int(has_match.sum()),
        "Total sin cruce": int((~has_match).sum()),
        "Total sin costo": int(is_blank(cost).sum()),
        "Total sin EAN": int(is_blank(ean).sum()),
    }
