import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración inicial (Centrado para móviles)
st.set_page_config(page_title="Tablero QRQC", layout="centered")

# ==========================================
# 1. CONFIGURACIÓN DE ENLACES DEFINITIVOS
# ==========================================
url_ingresos = "https://docs.google.com/spreadsheets/d/1xw4aqqpf6pWDa9LQSmS3ztLiF82n-ZQ0NqY3QRVTTFg/edit"
url_actualizaciones = "https://docs.google.com/spreadsheets/d/13HGJpk8SJo1nN2asMVMuS_EXhqYq4vtcMslvUEMdQw0/edit"
url_base_form_actualizacion = "https://docs.google.com/forms/d/e/1FAIpQLSfppxJI7lPOKbFQZwsDzTBYdv4hWq3QN9ImKCkAvmVCLV0wDw/viewform?entry.1541179458="
url_form_nuevo = "https://docs.google.com/forms/d/e/1FAIpQLSe9AHzNLjUkg3tdfbsUopdc8_YldXLk4YbGXYaeNKyWA198vQ/viewform"

# ==========================================
# 2. CONEXIÓN Y LECTURA DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
df_ingresos = conn.read(spreadsheet=url_ingresos, ttl=300)
df_actualizaciones = conn.read(spreadsheet=url_actualizaciones, ttl=300)

# Limpieza de nombres de columnas (quita espacios invisibles)
df_ingresos.columns = df_ingresos.columns.str.strip()
df_actualizaciones.columns = df_actualizaciones.columns.str.strip()

# Asegurarse de que exista la columna principal para no dar error
if 'N° DE TICKET' in df_ingresos.columns:
    df_ingresos = df_ingresos.dropna(subset=['N° DE TICKET'])
    df_ingresos['N° DE TICKET'] = df_ingresos['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()
else:
    st.error("🚨 Error: No se encontró la columna 'N° DE TICKET' en la hoja de ingresos.")
    st.stop()

# ==========================================
# 3. PROCESAMIENTO Y CRUCE DE DATOS
# ==========================================
if not df_actualizaciones.empty and 'N° DE TICKET' in df_actualizaciones.columns:
    df_actualizaciones = df_actualizaciones.dropna(subset=['N° DE TICKET'])
    df_actualizaciones['N° DE TICKET'] = df_actualizaciones['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_actualizaciones['Marca temporal'] = pd.to_datetime(df_actualizaciones['Marca temporal'], errors='coerce')
    
    # Quedarse solo con la última actualización de cada ticket
    df_ultimas_act = df_actualizaciones.sort_values('Marca temporal').drop_duplicates(subset='N° DE TICKET', keep='last')
    
    # Cruzar datos
    df_master = pd.merge(df_ingresos, df_ultimas_act, on='N° DE TICKET', how='left')
    df_master['TIPO DE ENTRADA'] = df_master['TIPO DE ENTRADA'].fillna('Pendiente (Sin revisión)')
else:
    df_master = df_ingresos.copy()
    df_master['TIPO DE ENTRADA'] = 'Pendiente (Sin revisión)'

# --- Escudo protector: Crear columnas si no existen ---
# NOTA: Cambia 'QUIEN CARGA' por tu nombre real de columna (ej. 'LEGAJO') si es necesario
columnas_seguras = ['AREA RESPONSABLE', 'PERSONA RESPONSABLE', 'PLAN DE ACCION', 'FECHA DE REVISION', 'AREA', 'QUIEN CARGA', 'DESCRIPCION DE FALLA']
for col in columnas_seguras:
    if col not in df_master.columns:
        df_master[col] = '' # Las crea vacías para evitar KeyError

# Unificar el nombre de la fecha
if 'Marca temporal_x' in df_master.columns:
    df_master.rename(columns={'Marca temporal_x': 'FECHA INGRESO'}, inplace=True)
elif 'Marca temporal' in df_master.columns:
    df_master.rename(columns={'Marca temporal': 'FECHA INGRESO'}, inplace=True)
elif 'FECHA INGRESO' not in df_master.columns:
    df_master['FECHA INGRESO'] = ''

# Crear el link dinámico
df_master['LINK_ACCION'] = url_base_form_actualizacion + df_master['N° DE TICKET']

# ==========================================
# 4. INTERFAZ VISUAL OPTIMIZADA
# ==========================================

st.title("🏭 Tablero QRQC")

# --- BOTONES PRINCIPALES ---
st.link_button("➕ INGRESE UN NUEVO TICKET", url_form_nuevo, use_container_width=True)

st.divider()

if st.button("🔄 Actualizar Datos Ahora", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.divider()

# --- BLOQUE 1: PENDIENTES ---
df_pendientes = df_master[df_master['TIPO DE ENTRADA'] == 'Pendiente (Sin revisión)'].copy()

st.error("⚠️ **PENDIENTES DE ACEPTACIÓN**")

if not df_pendientes.empty:
    # ⚠️ RECUERDA: Si tu columna no se llama 'QUIEN CARGA', cámbialo aquí abajo por su nombre real
    columnas_pendientes = ['FECHA INGRESO', 'AREA', 'QUIEN CARGA', 'LINK_ACCION']
    
    st.dataframe(
        df_pendientes[columnas_pendientes], 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "FECHA INGRESO": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
            "AREA": st.column_config.TextColumn("Área", width="small"),
            "QUIEN CARGA": st.column_config.TextColumn("Quien carga", width="medium"),
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="✏️ Asignar")
        }
    )
else:
    st.success("No hay tickets pendientes.")

st.divider()

# --- BLOQUE 2: ACTIVOS (EN CURSO) ---
estados_cierre = ['Cerrado', 'CERRADO', 'cerrado', 'CIERRE', 'Cierre', 'cierre']
df_activos = df_master[~df_master['TIPO DE ENTRADA'].isin(['Pendiente (Sin revisión)'] + estados_cierre)].copy()

st.info("📋 **LISTADO DE PROBLEMAS EN CURSO**")

if not df_activos.empty:
    # Se eliminó la persona responsable de la lista visual
    columnas_activos = [
        'N° DE TICKET', 
        'FECHA INGRESO', 
        'AREA RESPONSABLE', 
        'DESCRIPCION DE FALLA', 
        'PLAN DE ACCION', 
        'FECHA DE REVISION', 
        'LINK_ACCION'
    ]
        
    st.dataframe(
        df_activos[columnas_activos], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "N° DE TICKET": st.column_config.TextColumn("Ticket", width="small"),
            "FECHA INGRESO": st.column_config.DatetimeColumn("Marca temporal", format="DD/MM/YYYY"),
            "AREA RESPONSABLE": st.column_config.TextColumn("Área Responsable", width="medium"),
            "DESCRIPCION DE FALLA": st.column_config.TextColumn("Problema / Falla", width="large"),
            "PLAN DE ACCION": st.column_config.TextColumn("Plan de Acción", width="large"),
            "FECHA DE REVISION": st.column_config.TextColumn("Fecha de Revisión", width="medium"),
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="🔄 Editar / Actualizar")
        }
    )
else:
    st.write("No hay problemas en curso.")

st.divider()

# --- BLOQUE 3: HISTORIAL DE CERRADOS ---
df_cerrados = df_master[df_master['TIPO DE ENTRADA'].isin(estados_cierre)].copy()

with st.expander("✅ VER HISTORIAL DE CERRADOS"):
    if not df_cerrados.empty:
        columnas_cerrados = ['N° DE TICKET', 'FECHA INGRESO', 'DESCRIPCION DE FALLA', 'AREA RESPONSABLE', 'PLAN DE ACCION']
        st.dataframe(
            df_cerrados[columnas_cerrados], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "N° DE TICKET": st.column_config.TextColumn("Ticket", width="small"),
                "FECHA INGRESO": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
                "DESCRIPCION DE FALLA": st.column_config.TextColumn("Falla", width="large"),
                "AREA RESPONSABLE": st.column_config.TextColumn("Área", width="small"),
                "PLAN DE ACCION": st.column_config.TextColumn("Solución Final", width="large")
            }
        )
    else:
        st.write("Aún no hay problemas cerrados.")
