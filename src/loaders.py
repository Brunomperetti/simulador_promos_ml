"""Lectura de archivos de Mercado Libre y Tienda Nube."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd

from src.utils import clean_dataframe, compact_column_name, first_existing_column

ML_SHEET_NAME = "Promociones"
ML_REQUIRED_COLUMNS = ["SKU", "TITLE", "ORIGINAL_PRICE", "DISCOUNT_PERCENTAGE", "FINAL_PRICE", "ACTION"]
ML_SKU_ALIASES = ["SKU", "SELLER_SKU", "SELLER SKU", "Código SKU", "Codigo SKU"]

TN_COLUMN_ALIASES = {
    "SKU": ["SKU", "Código SKU", "Codigo SKU", "Identificador", "Variante SKU"],
    "Costo": ["Costo", "Cost", "Precio de costo", "Precio costo"],
    "Código de barras / EAN": [
        "Código de barras / EAN",
        "Codigo de barras / EAN",
        "Código de barras",
        "Codigo de barras",
        "EAN",
        "Barcode",
    ],
    "Nombre": ["Nombre", "Name", "Producto", "Nombre del producto"],
    "Categorías": ["Categorías", "Categorias", "Categoría", "Categoria", "Categories"],
    "Marca": ["Marca", "Brand"],
}


def _read_upload_bytes(file: BinaryIO | BytesIO) -> bytes:
    if hasattr(file, "getvalue"):
        return file.getvalue()
    return file.read()


def _deduplicate_columns(columns: list[object]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for column in columns:
        name = str(column).strip()
        if not name or name.lower().startswith("unnamed"):
            name = "columna_sin_nombre"
        count = seen.get(name, 0)
        seen[name] = count + 1
        result.append(name if count == 0 else f"{name}_{count + 1}")
    return result


def detect_ml_header_row(raw_df: pd.DataFrame) -> int:
    """Encuentra la fila de encabezados en la hoja Promociones."""
    required_compact = {compact_column_name(column) for column in ML_REQUIRED_COLUMNS if column != "SKU"}
    sku_aliases = {compact_column_name(alias) for alias in ML_SKU_ALIASES}

    best_row = 0
    best_score = -1
    for index, row in raw_df.iterrows():
        values = {compact_column_name(value) for value in row.tolist() if pd.notna(value)}
        score = len(required_compact.intersection(values))
        if values.intersection(sku_aliases):
            score += 1
        if score > best_score:
            best_score = score
            best_row = int(index)
        if score >= 4:
            return int(index)

    return best_row


def load_mercado_libre_excel(file: BinaryIO | BytesIO) -> pd.DataFrame:
    """Lee el Excel de Mercado Libre desde la hoja Promociones detectando encabezados."""
    content = _read_upload_bytes(file)
    raw_df = pd.read_excel(BytesIO(content), sheet_name=ML_SHEET_NAME, header=None, dtype=object)
    header_row = detect_ml_header_row(raw_df)

    df = raw_df.iloc[header_row + 1 :].copy()
    df.columns = _deduplicate_columns(raw_df.iloc[header_row].tolist())
    df = clean_dataframe(df)

    sku_column = first_existing_column(df.columns, ML_SKU_ALIASES)
    if sku_column and sku_column != "SKU":
        df = df.rename(columns={sku_column: "SKU"})
    return df


def load_tienda_nube_csv(file: BinaryIO | BytesIO) -> pd.DataFrame:
    """Lee el CSV de Tienda Nube con detección de separador y aliases de columnas."""
    content = _read_upload_bytes(file)
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(BytesIO(content), sep=None, engine="python", encoding=encoding, dtype=object)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError("No se pudo leer el CSV de Tienda Nube con codificación UTF-8 o Latin-1.") from last_error

    df = clean_dataframe(df)
    rename_map = {}
    for canonical, aliases in TN_COLUMN_ALIASES.items():
        found = first_existing_column(df.columns, aliases)
        if found and found != canonical:
            rename_map[found] = canonical
    return df.rename(columns=rename_map)
