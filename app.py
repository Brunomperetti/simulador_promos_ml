"""Interfaz Streamlit del simulador de promociones."""

from __future__ import annotations

import streamlit as st

from src.loaders import load_mercado_libre_excel, load_tienda_nube_csv
from src.transformers import build_display_table, merge_ml_with_tienda_nube
from src.validators import build_metrics, is_blank, validate_ml_columns, validate_tienda_nube_columns

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
metrics = build_metrics(merged_df)

metric_columns = st.columns(len(metrics))
for column, (label, value) in zip(metric_columns, metrics.items()):
    column.metric(label, value)

st.subheader("Publicaciones ML enriquecidas")
with st.container(border=True):
    st.markdown("**Filtros de la tabla principal**")
    search_col_1, search_col_2 = st.columns(2)
    sku_query = search_col_1.text_input("Buscar por SKU", placeholder="Ej: ABC123")
    title_query = search_col_2.text_input("Buscar por título/nombre", placeholder="Ej: Zapatilla")

    option_col_1, option_col_2 = st.columns(2)
    category_options = sorted(
        value for value in merged_df.get("Categorías", []).dropna().astype(str).str.strip().unique() if value
    )
    brand_options = sorted(
        value for value in merged_df.get("Marca", []).dropna().astype(str).str.strip().unique() if value
    )
    selected_category = option_col_1.selectbox("Filtrar por categoría", ["Todas"] + category_options)
    selected_brand = option_col_2.selectbox("Filtrar por marca", ["Todas"] + brand_options)

    flag_col_1, flag_col_2, flag_col_3 = st.columns(3)
    only_without_match = flag_col_1.checkbox("Ver solo productos sin cruce")
    only_without_cost = flag_col_2.checkbox("Ver solo productos sin costo")
    only_without_ean = flag_col_3.checkbox("Ver solo productos sin EAN")

filtered_df = merged_df.copy()
if sku_query:
    filtered_df = filtered_df[
        filtered_df["SKU"].fillna("").astype(str).str.contains(sku_query.strip(), case=False, na=False)
    ]
if title_query:
    title_mask = filtered_df["TITLE"].fillna("").astype(str).str.contains(title_query.strip(), case=False, na=False)
    name_mask = filtered_df["Nombre"].fillna("").astype(str).str.contains(title_query.strip(), case=False, na=False)
    filtered_df = filtered_df[title_mask | name_mask]
if selected_category != "Todas":
    filtered_df = filtered_df[filtered_df["Categorías"].fillna("").astype(str).str.strip().eq(selected_category)]
if selected_brand != "Todas":
    filtered_df = filtered_df[filtered_df["Marca"].fillna("").astype(str).str.strip().eq(selected_brand)]
if only_without_match:
    filtered_df = filtered_df[~filtered_df["_HAS_MATCH"].fillna(False)]
if only_without_cost:
    filtered_df = filtered_df[is_blank(filtered_df["Costo"])]
if only_without_ean:
    filtered_df = filtered_df[is_blank(filtered_df["Código de barras / EAN"])]

display_df = build_display_table(filtered_df)
st.caption(f"Mostrando {len(display_df)} de {len(merged_df)} publicaciones.")
st.dataframe(display_df, use_container_width=True, hide_index=True)

with st.expander("Vista previa técnica de archivos cargados"):
    st.caption("Vista técnica para revisar las primeras filas leídas sin formato ni filtros de la tabla principal.")
    st.write("Mercado Libre")
    st.dataframe(ml_df.head(20), use_container_width=True)
    st.write("Tienda Nube")
    st.dataframe(tn_df.head(20), use_container_width=True)
