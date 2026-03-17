
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión de Problemas QRQC", layout="wide")

# 1. CONEXIÓN REAL A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# URLs de tus planillas (Asegúrate de que sean las correctas)
url_ingresos = "https://docs.google.com/spreadsheets/d/1xw4aqqpf6pWDa9LQSmS3ztLiF82n-ZQ0NqY3QRVTTFg/edit"
url_actualizaciones = "https://docs.google.com/spreadsheets/d/1kYDRlp_q0DDg88vks09s2eThas_WVFrUaPNujI7AKIw/edit"

# Leer los datos (Streamlit los cachea automáticamente para que sea rápido)
# TTL = Time To Live (se actualiza cada 5 minutos, o 300 segundos)
df_ingresos = conn.read(spreadsheet=url_ingresos, ttl=300)
df_actualizaciones = conn.read(spreadsheet=url_actualizaciones, ttl=300)

# 2. LIMPIEZA Y CRUCE DE DATOS
# Convertir las columnas de fecha a formato datetime de Pandas para poder ordenarlas
df_actualizaciones['Marca temporal'] = pd.to_datetime(df_actualizaciones['Marca temporal'])

# Quedarnos solo con la última actualización de cada ticket
df_ultimas_act = df_actualizaciones.sort_values('Marca temporal').drop_duplicates(subset='N° DE TICKET', keep='last')

# Unir ingresos con su última actualización
df_master = pd.merge(df_ingresos, df_ultimas_act, on='N° DE TICKET', how='left')
df_master['TIPO DE ENTRADA'] = df_master['TIPO DE ENTRADA'].fillna('Pendiente (Sin revisión)')

# 3. INTERFAZ (Igual que antes)
st.title("🏭 Tablero QRQC / Listado Único de Problemas")

# PENDIENTES
df_pendientes = df_master[df_master['TIPO DE ENTRADA'] == 'Pendiente (Sin revisión)']
st.error("### ⚠️ PENDIENTES DE ACEPTACION")
if not df_pendientes.empty:
    st.dataframe(df_pendientes[['N° DE TICKET', 'Marca temporal_x', 'AREA', 'DESCRIPCION DE FALLA']], hide_index=True)
else:
    st.success("¡No hay tickets pendientes!")

st.divider()

# ACTIVOS
df_activos = df_master[~df_master['TIPO DE ENTRADA'].isin(['Pendiente (Sin revisión)', 'Cerrado'])]
st.info("### 📋 LISTADO DE PROBLEMAS ACTIVOS")
if not df_activos.empty:
    st.dataframe(df_activos[['N° DE TICKET', 'DESCRIPCION DE FALLA', 'AREA RESPONSABLE', 'PERSONA RESPONSABLE', 'PLAN DE ACCION', 'TIPO DE ENTRADA']], use_container_width=True, hide_index=True)

st.divider()

col1, col2 = st.columns(2)
col1.link_button("➕ INGRESE UN NUEVO TICKET", "TU_LINK_DEL_FORM_DE_INGRESO", use_container_width=True)
col2.link_button("🔄 ACTUALIZAR UN TICKET", "TU_LINK_DEL_FORM_DE_ACTUALIZACION", use_container_width=True)
