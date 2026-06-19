"""Interfaz Streamlit del simulador de promociones."""

from __future__ import annotations

import streamlit as st

from src.loaders import load_mercado_libre_excel, load_tienda_nube_csv
from src.transformers import build_display_table, merge_ml_with_tienda_nube
from src.validators import build_metrics, validate_ml_columns, validate_tienda_nube_columns

st.set_page_config(page_title="Simulador de Promociones ML", page_icon="📊", layout="wide")

st.title("Simulador de Promociones Mercado Libre")
st.caption("Primera versión: lectura, cruce por SKU y visualización enriquecida con Tienda Nube.")

ml_file = st.file_uploader("Excel de promociones de Mercado Libre", type=["xlsx", "xls"])
tn_file = st.file_uploader("CSV de productos de Tienda Nube", type=["csv"])

if not ml_file or not tn_file:
    st.info("Subí el Excel de Mercado Libre y el CSV de Tienda Nube para comenzar.")
    st.stop()

try:
    ml_df = load_mercado_libre_excel(ml_file)
    tn_df = load_tienda_nube_csv(tn_file)
except Exception as exc:  # Streamlit debe mostrar errores de lectura de forma amigable.
    st.error(f"No se pudieron leer los archivos: {exc}")
    st.stop()

ml_missing = validate_ml_columns(ml_df)
tn_missing = validate_tienda_nube_columns(tn_df)
if ml_missing:
    st.warning("Columnas faltantes en Mercado Libre: " + ", ".join(ml_missing))
if tn_missing:
    st.warning("Columnas faltantes en Tienda Nube: " + ", ".join(tn_missing))

merged_df = merge_ml_with_tienda_nube(ml_df, tn_df)
display_df = build_display_table(merged_df)
metrics = build_metrics(merged_df)

metric_columns = st.columns(len(metrics))
for column, (label, value) in zip(metric_columns, metrics.items()):
    column.metric(label, value)

st.subheader("Publicaciones ML enriquecidas")
st.dataframe(display_df, use_container_width=True, hide_index=True)

with st.expander("Vista previa de archivos cargados"):
    st.write("Mercado Libre")
    st.dataframe(ml_df.head(20), use_container_width=True)
    st.write("Tienda Nube")
    st.dataframe(tn_df.head(20), use_container_width=True)
