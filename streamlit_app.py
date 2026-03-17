import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración inicial de la página
st.set_page_config(page_title="Tablero QRQC", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN DE ENLACES DEFINITIVOS
# ==========================================
url_ingresos = "https://docs.google.com/spreadsheets/d/1xw4aqqpf6pWDa9LQSmS3ztLiF82n-ZQ0NqY3QRVTTFg/edit"
url_actualizaciones = "https://docs.google.com/spreadsheets/d/1kYDRlp_q0DDg88vks09s2eThas_WVFrUaPNujI7AKIw/edit"

# Link base de tu Formulario de Actualización (con el Entry ID precargado)
url_base_form_actualizacion = "https://docs.google.com/forms/d/e/1FAIpQLSfppxJI7lPOKbFQZwsDzTBYdv4hWq3QN9ImKCkAvmVCLV0wDw/viewform?entry.1541179458="

# Link de tu Formulario de Ingreso Nuevo
url_form_nuevo = "https://docs.google.com/forms/d/e/1FAIpQLSe9AHzNLjUkg3tdfbsUopdc8_YldXLk4YbGXYaeNKyWA198vQ/viewform"

# ==========================================
# 2. CONEXIÓN Y LECTURA DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# Leemos los datos (se actualizan solos cada 300 segundos)
df_ingresos = conn.read(spreadsheet=url_ingresos, ttl=300)
df_actualizaciones = conn.read(spreadsheet=url_actualizaciones, ttl=300)

# Limpiamos espacios en blanco de los nombres de columnas
df_ingresos.columns = df_ingresos.columns.str.strip()
df_actualizaciones.columns = df_actualizaciones.columns.str.strip()

# Eliminamos filas vacías que no tengan N° de Ticket en ingresos
df_ingresos = df_ingresos.dropna(subset=['N° DE TICKET'])

# ==========================================
# 3. PROCESAMIENTO Y CRUCE DE DATOS (EL MOTOR)
# ==========================================
# ESTANDARIZAR LOS TICKETS EN INGRESOS (Convertir a texto puro sin decimales)
df_ingresos['N° DE TICKET'] = df_ingresos['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()

if not df_actualizaciones.empty and 'N° DE TICKET' in df_actualizaciones.columns:
    df_actualizaciones = df_actualizaciones.dropna(subset=['N° DE TICKET'])
    
    # ESTANDARIZAR LOS TICKETS EN ACTUALIZACIONES (Convertir a texto puro sin decimales)
    df_actualizaciones['N° DE TICKET'] = df_actualizaciones['N° DE TICKET'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    # Convertimos la fecha para ordenar correctamente
    df_actualizaciones['Marca temporal'] = pd.to_datetime(df_actualizaciones['Marca temporal'], errors='coerce')
    
    # Nos quedamos SOLO con la última actualización de cada ticket
    df_ultimas_act = df_actualizaciones.sort_values('Marca temporal').drop_duplicates(subset='N° DE TICKET', keep='last')
    
    # Unimos las tablas: Ingresos + Su última actualización
    df_master = pd.merge(df_ingresos, df_ultimas_act, on='N° DE TICKET', how='left')
    
    # Si un ticket no tiene actualización, le ponemos estado Pendiente
    df_master['TIPO DE ENTRADA'] = df_master['TIPO DE ENTRADA'].fillna('Pendiente (Sin revisión)')
else:
    # Si nadie actualizó nada aún, todos son nuevos/pendientes
    df_master = df_ingresos.copy()
    df_master['TIPO DE ENTRADA'] = 'Pendiente (Sin revisión)'
    df_master['AREA RESPONSABLE'] = ''
    df_master['PERSONA RESPONSABLE'] = ''
    df_master['PLAN DE ACCION'] = ''

# Mejoramos el nombre de la fecha de ingreso
if 'Marca temporal_x' in df_master.columns:
    df_master.rename(columns={'Marca temporal_x': 'FECHA INGRESO'}, inplace=True)
elif 'Marca temporal' in df_master.columns:
    df_master.rename(columns={'Marca temporal': 'FECHA INGRESO'}, inplace=True)

# Generamos la columna con el Link dinámico para TODAS las filas
df_master['LINK_ACCION'] = url_base_form_actualizacion + df_master['N° DE TICKET']

# ==========================================
# 4. INTERFAZ VISUAL DEL TABLERO
# ==========================================

# Dividimos la parte superior en dos columnas: una para el título y otra para el botón
col_titulo, col_boton = st.columns([3, 1])

with col_titulo:
    st.title("🏭 Tablero QRQC / Listado Único de Problemas")

with col_boton:
    st.write("") # Un pequeño espacio en blanco para alinear el botón verticalmente
    if st.button("🔄 Actualizar Datos Ahora", type="primary", use_container_width=True):
        st.cache_data.clear() # Borra la memoria caché de Streamlit
        st.rerun() # Recarga la página instantáneamente

# --- BLOQUE 1: PENDIENTES ---
df_pendientes = df_master[df_master['TIPO DE ENTRADA'] == 'Pendiente (Sin revisión)'].copy()
st.error("### ⚠️ PENDIENTES DE ACEPTACION")

if not df_pendientes.empty:
    columnas_pendientes = ['N° DE TICKET', 'FECHA INGRESO', 'AREA', 'QUIEN AREA INGRESA EL PROBLEMA?', 'DESCRIPCION DE FALLA', 'LINK_ACCION']
    
    st.dataframe(
        df_pendientes[columnas_pendientes], 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="✏️ Aceptar / Asignar")
        }
    )
else:
    st.success("¡Excelente! No hay tickets pendientes de revisión.")

st.divider()

# --- BLOQUE 2: ACTIVOS ---
df_activos = df_master[~df_master['TIPO DE ENTRADA'].isin(['Pendiente (Sin revisión)', 'Cerrado', 'CERRADO', 'cerrado'])].copy()
st.info("### 📋 LISTADO DE PROBLEMAS ACTIVOS")

if not df_activos.empty:
    columnas_activos = ['N° DE TICKET', 'DESCRIPCION DE FALLA', 'AREA RESPONSABLE', 'PERSONA RESPONSABLE', 'PLAN DE ACCION', 'TIPO DE ENTRADA', 'LINK_ACCION']
    
    if 'FECHA DE REVISION' in df_activos.columns:
        columnas_activos.insert(5, 'FECHA DE REVISION')
        
    st.dataframe(
        df_activos[columnas_activos], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "LINK_ACCION": st.column_config.LinkColumn("Acción", display_text="🔄 Actualizar / Cerrar")
        }
    )
else:
    st.write("No hay problemas en curso en este momento.")

st.divider()

# --- BLOQUE 3: BOTÓN DE NUEVO TICKET ---
st.markdown("### 📝 CARGA DE NUEVOS PROBLEMAS")
st.link_button("➕ INGRESE UN NUEVO TICKET", url_form_nuevo, use_container_width=True)

st.divider()

# --- BLOQUE 4: HISTORIAL DE CERRADOS ---
df_cerrados = df_master[df_master['TIPO DE ENTRADA'].isin(['Cerrado', 'CERRADO', 'cerrado'])].copy()

with st.expander("✅ VER HISTORIAL DE PROBLEMAS CERRADOS"):
    if not df_cerrados.empty:
        columnas_cerrados = ['N° DE TICKET', 'FECHA INGRESO', 'DESCRIPCION DE FALLA', 'AREA RESPONSABLE', 'PERSONA RESPONSABLE', 'PLAN DE ACCION']
        st.dataframe(df_cerrados[columnas_cerrados], use_container_width=True, hide_index=True)
    else:
        st.write("Aún no hay problemas cerrados.")
