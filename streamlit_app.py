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

df_ingresos.columns = df_ingresos.columns.str.strip()
df_actualizaciones.columns = df_actualizaciones.columns.str.strip()
df_ingresos = df_ingresos.dropna(subset=['N° DE TICKET'])

# ==========================================
# 3. PROCESAMIENTO Y CRUCE DE DATOS
# ==========================================
df_ingresos['N° DE TICKET'] = df_ingresos['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()

if not df_actualizaciones.empty and 'N° DE TICKET' in df_actualizaciones.columns:
    df_actualizaciones = df_actualizaciones.dropna(subset=['N° DE TICKET'])
    df_actualizaciones['N° DE TICKET'] = df_actualizaciones['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_actualizaciones['Marca temporal'] = pd.to_datetime(df_actualizaciones['Marca temporal'], errors='coerce')
    df_ultimas_act = df_actualizaciones.sort_values('Marca temporal').drop_duplicates(subset='N° DE TICKET', keep='last')
    df_master = pd.merge(df_ingresos, df_ultimas_act, on='N° DE TICKET', how='left')
    df_master['TIPO DE ENTRADA'] = df_master['TIPO DE ENTRADA'].fillna('Pendiente (Sin revisión)')
else:
    df_master = df_ingresos.copy()
    df_master['TIPO DE ENTRADA'] = 'Pendiente (Sin revisión)'
    df_master['AREA RESPONSABLE'] = ''
    df_master['PERSONA RESPONSABLE'] = ''
    df_master['PLAN DE ACCION'] = ''

if 'Marca temporal_x' in df_master.columns:
    df_master.rename(columns={'Marca temporal_x': 'FECHA INGRESO'}, inplace=True)
elif 'Marca temporal' in df_master.columns:
    df_master.rename(columns={'Marca temporal': 'FECHA INGRESO'}, inplace=True)

df_master['LINK_ACCION'] = url_base_form_actualizacion + df_master['N° DE TICKET']

# ==========================================
# 4. INTERFAZ VISUAL OPTIMIZADA
# ==========================================

st.title("🏭 Tablero QRQC")

# --- BOTONES PRINCIPALES REORGANIZADOS ---
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
    columnas_pendientes = ['N° DE TICKET', 'AREA', 'DESCRIPCION DE FALLA', 'LINK_ACCION']
    
    st.dataframe(
        df_pendientes[columnas_pendientes], 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "N° DE TICKET": st.column_config.TextColumn("Ticket", width="small"),
            "AREA": st.column_config.TextColumn("Área", width="small"),
            "DESCRIPCION DE FALLA": st.column_config.TextColumn("Falla", width="large"),
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="✏️ Asignar")
        }
    )
else:
    st.success("No hay tickets pendientes.")

st.divider()

# --- BLOQUE 2: ACTIVOS ---
estados_cierre = ['Cerrado', 'CERRADO', 'cerrado', 'CIERRE', 'Cierre', 'cierre']
df_activos = df_master[~df_master['TIPO DE ENTRADA'].isin(['Pendiente (Sin revisión)'] + estados_cierre)].copy()

st.info("📋 **LISTADO DE PROBLEMAS ACTIVOS**")

if not df_activos.empty:
    # AÑADIDA 'DESCRIPCION DE FALLA' A LA LISTA DE COLUMNAS
    columnas_activos = ['N° DE TICKET', 'DESCRIPCION DE FALLA', 'PERSONA RESPONSABLE', 'TIPO DE ENTRADA', 'LINK_ACCION']
        
    st.dataframe(
        df_activos[columnas_activos], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "N° DE TICKET": st.column_config.TextColumn("Ticket", width="small"),
            "DESCRIPCION DE FALLA": st.column_config.TextColumn("Falla", width="large"), # AÑADIDA LA CONFIGURACIÓN
            "PERSONA RESPONSABLE": st.column_config.TextColumn("Responsable", width="medium"),
            "TIPO DE ENTRADA": st.column_config.TextColumn("Estado", width="small"),
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="🔄 Editar")
        }
    )
else:
    st.write("No hay problemas en curso.")

st.divider()

# --- BLOQUE 3: HISTORIAL DE CERRADOS ---
df_cerrados = df_master[df_master['TIPO DE ENTRADA'].isin(estados_cierre)].copy()

with st.expander("✅ VER HISTORIAL DE CERRADOS"):
    if not df_cerrados.empty:
        # AQUÍ YA ESTABA INCLUIDA LA FALLA
        columnas_cerrados = ['N° DE TICKET', 'DESCRIPCION DE FALLA', 'PLAN DE ACCION']
        st.dataframe(
            df_cerrados[columnas_cerrados], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "N° DE TICKET": st.column_config.TextColumn("Ticket", width="small"),
                "DESCRIPCION DE FALLA": st.column_config.TextColumn("Falla", width="large"), # Añadido el ancho para consistencia
                "PLAN DE ACCION": st.column_config.TextColumn("Solución", width="large")
            }
        )
    else:
        st.write("Aún no hay problemas cerrados.")
