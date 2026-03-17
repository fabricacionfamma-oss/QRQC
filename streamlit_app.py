import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión de Problemas QRQC", layout="wide")

# 1. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

# REEMPLAZA ESTAS URLs CON LAS TUYAS (Las que copiaste del navegador)
url_ingresos = "https://docs.google.com/spreadsheets/d/1xw4aqqpf6pWDa9LQSmS3ztLiF82n-ZQ0NqY3QRVTTFg/edit"
url_actualizaciones = "https://docs.google.com/spreadsheets/d/1kYDRlp_q0DDg88vks09s2eThas_WVFrUaPNujI7AKIw/edit"

# Leer los datos
df_ingresos = conn.read(spreadsheet=url_ingresos, ttl=300)
df_actualizaciones = conn.read(spreadsheet=url_actualizaciones, ttl=300)

# Limpiar espacios en blanco de los nombres de las columnas (Para evitar KeyErrors)
df_ingresos.columns = df_ingresos.columns.str.strip()
df_actualizaciones.columns = df_actualizaciones.columns.str.strip()

# Eliminar filas vacías que Google Sheets a veces lee por error
df_ingresos = df_ingresos.dropna(subset=['N° DE TICKET'])

# 2. PROCESAMIENTO DE DATOS
# Verificar si ya hay actualizaciones cargadas
if not df_actualizaciones.empty and 'N° DE TICKET' in df_actualizaciones.columns:
    df_actualizaciones = df_actualizaciones.dropna(subset=['N° DE TICKET'])
    df_actualizaciones['Marca temporal'] = pd.to_datetime(df_actualizaciones['Marca temporal'], errors='coerce')
    
    # Quedarnos con la última actualización de cada ticket
    df_ultimas_act = df_actualizaciones.sort_values('Marca temporal').drop_duplicates(subset='N° DE TICKET', keep='last')
    
    # Unir las tablas (Merge)
    df_master = pd.merge(df_ingresos, df_ultimas_act, on='N° DE TICKET', how='left')
    
    # Rellenar los vacíos de los tickets nuevos
    df_master['TIPO DE ENTRADA'] = df_master['TIPO DE ENTRADA'].fillna('Pendiente (Sin revisión)')
else:
    # Si la planilla de actualizaciones está vacía (nadie actualizó nada aún)
    df_master = df_ingresos.copy()
    df_master['TIPO DE ENTRADA'] = 'Pendiente (Sin revisión)'
    df_master['AREA RESPONSABLE'] = ''
    df_master['PERSONA RESPONSABLE'] = ''
    df_master['PLAN DE ACCION'] = ''

# Renombrar la Marca Temporal del Ingreso para que se vea más lindo en la tabla
if 'Marca temporal_x' in df_master.columns:
    df_master.rename(columns={'Marca temporal_x': 'FECHA INGRESO'}, inplace=True)
elif 'Marca temporal' in df_master.columns:
    df_master.rename(columns={'Marca temporal': 'FECHA INGRESO'}, inplace=True)

# 3. INTERFAZ VISUAL
st.title("🏭 Tablero QRQC / Listado Único de Problemas")

# --- BLOQUE 1: PENDIENTES ---
df_pendientes = df_master[df_master['TIPO DE ENTRADA'] == 'Pendiente (Sin revisión)']
st.error("### ⚠️ PENDIENTES DE ACEPTACION")
if not df_pendientes.empty:
    columnas_pendientes = ['N° DE TICKET', 'FECHA INGRESO', 'AREA', 'QUIEN AREA INGRESA EL PROBLEMA?', 'DESCRIPCION DE FALLA']
    st.dataframe(df_pendientes[columnas_pendientes], hide_index=True, use_container_width=True)
else:
    st.success("¡Excelente! No hay tickets pendientes de revisión.")

st.divider()

# --- BLOQUE 2: ACTIVOS ---
# Filtramos para que no muestre los pendientes ni los que digan "Cerrado"
df_activos = df_master[~df_master['TIPO DE ENTRADA'].isin(['Pendiente (Sin revisión)', 'Cerrado', 'CERRADO'])]
st.info("### 📋 LISTADO DE PROBLEMAS ACTIVOS")

if not df_activos.empty:
    columnas_activos = ['N° DE TICKET', 'DESCRIPCION DE FALLA', 'AREA RESPONSABLE', 'PERSONA RESPONSABLE', 'PLAN DE ACCION', 'TIPO DE ENTRADA']
    # Solo intentamos mostrar 'FECHA DE REVISION' si ya existe en la tabla combinada
    if 'FECHA DE REVISION' in df_activos.columns:
        columnas_activos.insert(5, 'FECHA DE REVISION')
        
    st.dataframe(df_activos[columnas_activos], use_container_width=True, hide_index=True)
else:
    st.write("No hay problemas en curso en este momento.")

st.divider()

# --- BLOQUE 3: BOTONES ---
col1, col2 = st.columns(2)
# RECUERDA PONER AQUÍ LOS LINKS DE TUS GOOGLE FORMS
col1.link_button("➕ INGRESE UN NUEVO TICKET", "https://forms.google.com/...", use_container_width=True)
col2.link_button("🔄 ACTUALIZAR UN TICKET", "https://forms.google.com/...", use_container_width=True)
