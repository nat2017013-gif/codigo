"""
=============================================================================
  SISTEMA DE CONTROL ESTADÍSTICO DE PROCESOS  v2.0
  Molinos Santa Marta S.A.S. — Línea de Empaque de Mogolla
  Universidad del Magdalena · Facultad de Ingeniería
  Asignatura: Control Estadístico de Procesos · Grupo 5
=============================================================================
  Instalación:
      pip install streamlit pandas numpy scipy plotly openpyxl
  Ejecución:
      python -m streamlit run app_molinos.py
=============================================================================
  Estructura del proyecto (todos en la misma carpeta):
      app_molinos.py       ← este archivo (punto de entrada)
      calculos_cep.py      ← funciones estadísticas y de exportación
      interfaz_estilos.py  ← CSS, paleta de colores, componentes HTML
      visualizaciones.py   ← figuras Plotly
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
from scipy import stats
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

# ── Módulos del proyecto ──────────────────────────────────────────────────────
from interfaz_estilos import (
    CP, CR, CG, CY, CN,
    configurar_pagina, aplicar_estilos,
    render_encabezado, render_alarm, render_section_title
)
from calculos_cep import (
    LSL, USL, NOMINAL, CONTROL_CONSTANTS,
    detect_subgroups, validate_data,
    compute_spc, compute_eco, cpk_st,
    generate_sample_excel, export_excel,
)
from visualizaciones import (
    fig_histogram, fig_xbar, fig_r,
    fig_power, fig_gauge, fig_simulador_campanas,
    fig_campanas_potencia,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN E INICIALIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────
configurar_pagina()
aplicar_estilos()
render_encabezado()

# ── Logo corporativo en header: reemplaza el engranaje ⚙️ por la imagen ──────
# Inyección CSS pura sobre .corp-header-logo sin tocar interfaz_estilos.py.
import base64 as _b64, pathlib as _pl
_BASE_DIR   = _pl.Path(__file__).resolve().parent
_ASSETS_DIR = _BASE_DIR / "assets"
try:
    _logo_hdr_bytes = (_ASSETS_DIR / "logo_molinos.jfif").read_bytes()
    _logo_hdr_b64   = _b64.b64encode(_logo_hdr_bytes).decode()
    _logo_hdr_src   = f"data:image/jpeg;base64,{_logo_hdr_b64}"
    st.markdown(f"""
    <style>
    /* Oculta el emoji ⚙️ sin modificar el DOM; convierte el div en portador de imagen */
    .corp-header-logo {{
        font-size: 0 !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        width: 46px !important;
        height: 46px !important;
        overflow: hidden;
    }}
    .corp-header-logo::after {{
        content: '';
        display: block;
        width: 46px;
        height: 46px;
        border-radius: 8px;
        background-image: url('{_logo_hdr_src}');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    </style>
    """, unsafe_allow_html=True)
except Exception:
    pass   # si no existe el archivo, permanece el ⚙️ original sin error

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
st.session_state.setdefault("modo_carga", None)   # None | "excel" | "manual"
st.session_state.setdefault("df_manual_ok", False)
st.session_state.setdefault("df_manual_raw", None)
# Límites de especificación activos — persisten durante toda la sesión.
# El usuario los ajusta en page_capacidad(); el resto de la app los lee aquí.
st.session_state.setdefault("cap_lsl",     float(LSL))
st.session_state.setdefault("cap_usl",     float(USL))
st.session_state.setdefault("cap_nominal", float(NOMINAL))

# ── Selector de modo — Layout Split-Screen Corporativo ───────────────────────
if st.session_state["modo_carga"] is None:

    # ── CSS refinado: imagen única, logo embebido, espaciado limpio ───────────
    st.markdown("""
    <style>
    /* Elimina margen/padding que Streamlit agrega al widget st.image */
    [data-testid="stImage"] {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 0 !important;
    }
    [data-testid="stImage"] > img {
        border-radius: 12px;
        box-shadow: 0 6px 28px rgba(0,0,0,0.22);
        object-fit: cover;
        object-position: center;
        width: 100% !important;
        max-height: 520px;
        display: block;
    }
    /* Alineación vertical de columnas */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch;
        gap: 2rem;
    }
    /* Panel derecho */
    .split-panel {
        padding: 2rem 1.6rem 2rem 2rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .split-logo {
        max-height: 64px;
        max-width: 190px;
        object-fit: contain;
        margin-bottom: 1.2rem;
        display: block;
    }
    .split-divider {
        border: none;
        border-top: 2px solid #1B4F72;
        margin: 0 0 1.4rem 0;
        opacity: 0.15;
    }
    .split-title {
        font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        color: #1B4F72;
        line-height: 1.35;
        margin-bottom: 0.3rem;
    }
    .split-subtitle {
        font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: #5D6D7E;
        margin-bottom: 1.2rem;
    }
    .split-description {
        font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        font-size: 0.88rem;
        color: #566573;
        line-height: 1.7;
        margin-bottom: 2rem;
        border-left: 3px solid #1B4F72;
        padding-left: 0.9rem;
    }
    .split-label {
        font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #7F8C8D;
        margin-bottom: 0.75rem;
    }
    </style>
    """, unsafe_allow_html=True)

    _col_img, _col_panel = st.columns([5, 7])

    # ── Columna izquierda: UNA SOLA imagen via st.image (sin duplicado HTML) ──
    with _col_img:
        try:
            st.image(str(_ASSETS_DIR / "molino_inicio.jfif"), use_container_width=True)
        except Exception:
            st.markdown(
                '<div style="height:520px;background:#D5D8DC;border-radius:12px;'
                'display:flex;align-items:center;justify-content:center;'
                'color:#7F8C8D;font-family:\'IBM Plex Sans\',sans-serif;font-size:.9rem;">'
                'Imagen no disponible</div>',
                unsafe_allow_html=True
            )

    # ── Columna derecha: texto corporativo + botones (sin logo redundante) ──────
    with _col_panel:
        # Panel de texto: título, subtítulo, descripción, label de botones

        st.markdown("""
        <div class="split-panel">
            <hr class="split-divider">
            <div class="split-title">Sistema de Control Estadístico de Procesos (CEP)</div>
            <div class="split-subtitle">Línea de Empaque · Mogolla · Fase I — Análisis Histórico</div>
            <div class="split-description">
                Plataforma de monitoreo y análisis estadístico para la línea de empaque.<br>
                Evalúa capacidad de proceso, detecta causas especiales de variación
                y cuantifica el impacto económico del desajuste de dosificación.
            </div>
            <div class="split-label">Seleccionar método de ingreso de datos</div>
        </div>
        """, unsafe_allow_html=True)

        # Botones — lógica 100% intacta, keys sin cambios
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            if st.button("📂 Cargar Excel", type="primary", use_container_width=True,
                         help="Sube un .xlsx con columnas X1, X2, …, Xn"):
                st.session_state["modo_carga"] = "excel"
                st.rerun()
        with _mc2:
            if st.button("✍️ Ingreso Manual", type="secondary", use_container_width=True,
                         help="Escribe los datos directamente en una tabla editable"):
                st.session_state["modo_carga"] = "manual"
                st.rerun()

    st.stop()

# ── Página activa temprana (antes del router; sidebar aún no se ha renderizado) ──
_pagina_ahora = st.session_state.get("pagina", "capacidad")

# ── Botón para cambiar de modo (solo en Capacidad) ────────────────────────────
if _pagina_ahora == "capacidad":
    _modo_label = "📂 Excel" if st.session_state["modo_carga"] == "excel" else "✍️ Manual"
    if st.button(f"↩ Cambiar método de carga ({_modo_label})", key="btn_cambiar_modo"):
        st.session_state["modo_carga"]    = None
        st.session_state["df_manual_ok"]  = False
        st.session_state["df_manual_raw"] = None
        st.session_state.pop("df_excel_raw", None)
        st.rerun()

# =============================================================================
# RAMA A — EXCEL (flujo original intacto)
# =============================================================================
if st.session_state["modo_carga"] == "excel":

    uploaded = None

    if _pagina_ahora == "capacidad":
        sample_bytes = generate_sample_excel()

        if "df_excel_raw" not in st.session_state:
            st.markdown(render_alarm("info", (
                "<strong>📋 Instrucciones de uso</strong><br><br>"
                "1. Descarga la <strong>plantilla de ejemplo</strong> con el botón de abajo<br>"
                "2. Completa con los datos de pesaje de tu línea (columnas X1…Xn)<br>"
                "3. Carga el archivo Excel con el botón de abajo<br>"
                "4. El sistema calculará automáticamente CEP, capacidad, potencia y economía<br><br>"
                "<strong>Límites activos:</strong> LIE = 39.5 kg · LSE = 40.5 kg · Nominal = 40.0 kg"
            )), unsafe_allow_html=True)

        upc, dlc = st.columns([4, 1])
        with upc:
            uploaded = st.file_uploader(
                "📂 Cargar archivo Excel con datos de muestreo (.xlsx)",
                type=["xlsx", "xls"],
                key="main_xl_uploader",
                help="Columnas obligatorias: X1, X2, ..., Xn (n entre 2 y 10). Opcionales: Subgrupo, Hora."
            )
        with dlc:
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "⬇ Plantilla", sample_bytes, "plantilla_CEP.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width='stretch'
            )

        if uploaded is None and "df_excel_raw" not in st.session_state:
            st.stop()

    _proc_ok = False
    if uploaded is not None:
        try:
            df_raw = pd.read_excel(uploaded)
            _xcand = sorted(
                [c for c in df_raw.columns
                 if str(c).strip().upper().startswith("X") and str(c).strip()[1:].isdigit()],
                key=lambda c: int(str(c).strip()[1:])
            )
            if not _xcand:
                st.error("❌ No se encontraron columnas X1, X2,... en el archivo.")
                st.stop()
            df_raw[_xcand] = df_raw[_xcand].apply(pd.to_numeric, errors="coerce")
            _invalid_mask  = df_raw[_xcand].isnull().any(axis=1)
            _filas_xl      = (df_raw.index[_invalid_mask] + 2).tolist()  # +2: 1-index + encabezado
            df_raw = df_raw.dropna(subset=_xcand, how="all").reset_index(drop=True)
            df_raw = df_raw.dropna(subset=_xcand, how="any").reset_index(drop=True)
            if _filas_xl:
                _f_str = ", ".join(str(f) for f in _filas_xl[:8])
                _extra = f" (y {len(_filas_xl)-8} más)" if len(_filas_xl) > 8 else ""
                st.warning(
                    f"⚠ Se eliminaron {len(_filas_xl)} fila(s) por datos no numéricos — "
                    f"fila(s) Excel: {_f_str}{_extra}. "
                    "Verifica que todas las celdas X1…Xn contengan números válidos."
                )
            _keep  = [c for c in df_raw.columns
                      if (str(c).strip().upper().startswith("X") and str(c).strip()[1:].isdigit())
                      or str(c).lower() in ("subgrupo", "hora", "fecha", "turno", "operario")]
            df_raw = df_raw[[c for c in df_raw.columns if c in _keep]]
            if len(df_raw) < 2:
                st.warning("⚠ Se necesitan al menos 2 subgrupos completos. Revisa el archivo.")
                st.stop()
            st.session_state["df_excel_raw"] = df_raw.copy()
            n, x_cols = detect_subgroups(df_raw)
            _dyn_lsl = st.session_state["cap_lsl"]
            _dyn_usl = st.session_state["cap_usl"]
            _dyn_nom = st.session_state["cap_nominal"]
            issues   = validate_data(df_raw, x_cols, lsl=_dyn_lsl, usl=_dyn_usl)
            s        = compute_spc(df_raw, x_cols, n,
                                   lsl=_dyn_lsl, usl=_dyn_usl,
                                   nominal=_dyn_nom)
            _proc_ok = True
        except Exception as _e:
            st.error("❌ No se pudo procesar el archivo. Verifica que tenga columnas X1, X2,... con valores numéricos.")
            with st.expander("Ver detalle técnico"):
                st.code(str(_e))
            st.stop()
    elif "df_excel_raw" in st.session_state:
        try:
            df_raw = st.session_state["df_excel_raw"].copy()
            n, x_cols = detect_subgroups(df_raw)
            _dyn_lsl = st.session_state["cap_lsl"]
            _dyn_usl = st.session_state["cap_usl"]
            _dyn_nom = st.session_state["cap_nominal"]
            issues   = validate_data(df_raw, x_cols, lsl=_dyn_lsl, usl=_dyn_usl)
            s        = compute_spc(df_raw, x_cols, n,
                                   lsl=_dyn_lsl, usl=_dyn_usl,
                                   nominal=_dyn_nom)
            _proc_ok = True
        except Exception as _e:
            st.error("❌ Error al recuperar datos. Vuelve a Capacidad y sube el archivo.")
            with st.expander("Ver detalle técnico"):
                st.code(str(_e))
            st.stop()
    else:
        st.markdown(render_alarm("info",
            "Para comenzar, ve a la página <strong>Capacidad</strong> y carga un archivo Excel."
        ), unsafe_allow_html=True)
        st.stop()

    if _proc_ok:
        for iss in issues:
            st.warning(f"⚠ {iss}")
# =============================================================================
else:
    # Bloque de ingreso VISIBLE solo en Capacidad; el resto de páginas solo reconstruye s
    if _pagina_ahora == "capacidad":
        st.markdown(
            render_section_title("✍️ Ingreso Manual de Datos Históricos (Fase I)"),
            unsafe_allow_html=True,
        )

        if not st.session_state["df_manual_ok"]:
            st.markdown(render_alarm("info", (
                "<strong>📋 Instrucciones</strong><br><br>"
                "1. Configura el número de subgrupos y el tamaño de muestra <strong>n</strong><br>"
                "2. Completa todos los valores de peso en la tabla (kg)<br>"
                "3. Pulsa <strong>💾 Guardar datos iniciales</strong> para activar el análisis<br><br>"
                "<strong>Límites activos:</strong> LIE = 39.5 kg · LSE = 40.5 kg · Nominal = 40.0 kg"
            )), unsafe_allow_html=True)

        # ── Controles de estructura ───────────────────────────────────────────────
        _mc_a, _mc_b = st.columns([1, 1])
        with _mc_a:
            _man_nsg = st.number_input("Nº de subgrupos (filas)", min_value=2, max_value=100,
                                       value=20, key="man_nsg")
        with _mc_b:
            _man_n = st.number_input("Tamaño de muestra n (columnas X)", min_value=2, max_value=10,
                                     value=5, key="man_n")

        _man_xcols = [f"X{i+1}" for i in range(int(_man_n))]

        # ── Inicializar / redimensionar tabla en session_state ────────────────────
        _man_key = f"man_df_{int(_man_nsg)}_{int(_man_n)}"
        if st.session_state.get("man_table_key") != _man_key:
            _man_data = {"Subgrupo": list(range(1, int(_man_nsg)+1)),
                         "Hora":     [""] * int(_man_nsg)}
            for xc in _man_xcols:
                _man_data[xc] = [np.nan] * int(_man_nsg)
            st.session_state["man_df_edit"]   = pd.DataFrame(_man_data)
            st.session_state["man_table_key"] = _man_key
            st.session_state.pop(f"man_editor_{_man_key}", None)

        # ── Tabla editable ────────────────────────────────────────────────────────
        st.markdown(f"**Ingresa los pesos (kg) — {int(_man_nsg)} subgrupos × n={int(_man_n)}:**")
        _man_edited = st.data_editor(
            st.session_state["man_df_edit"],
            width="stretch",
            num_rows="fixed",
            column_config={
                "Subgrupo": st.column_config.NumberColumn("Subgrupo", disabled=True),
                "Hora":     st.column_config.TextColumn("Hora"),
                **{xc: st.column_config.NumberColumn(
                    xc, format="%.3f", step=0.001)
                   for xc in _man_xcols}
            },
            key=f"man_editor_{_man_key}"
        )

        # ── Botón guardar ─────────────────────────────────────────────────────────
        if st.button("💾 Guardar datos iniciales", type="primary", key="btn_man_guardar"):
            _df_check = _man_edited[_man_xcols].apply(pd.to_numeric, errors="coerce")
            _n_nulls  = _df_check.isnull().any(axis=1).sum()
            if _n_nulls > 0:
                _sg_inv = (_df_check.isnull().any(axis=1)).to_numpy().nonzero()[0] + 1
                _sg_str = ", ".join(str(i) for i in _sg_inv[:8])
                _sg_ext = f" (y {len(_sg_inv)-8} más)" if len(_sg_inv) > 8 else ""
                st.warning(
                    f"⚠ {_n_nulls} subgrupo(s) contienen datos no numéricos o vacíos: "
                    f"subgrupos {_sg_str}{_sg_ext}. "
                    "Corrige los valores antes de guardar."
                )
            elif len(_df_check.dropna()) < 2:
                st.warning("⚠ Se necesitan al menos 2 subgrupos completos.")
            else:
                _df_save = _man_edited.copy()
                for xc in _man_xcols:
                    _df_save[xc] = pd.to_numeric(_df_save[xc], errors="coerce")
                _df_save = _df_save.dropna(subset=_man_xcols, how="any").reset_index(drop=True)
                st.session_state["df_manual_raw"] = _df_save
                st.session_state["df_manual_ok"]  = True

            st.stop()

    # Datos confirmados → construir df_raw / n / x_cols / s idénticos al flujo Excel
    _proc_ok = False
    try:
        df_raw = st.session_state["df_manual_raw"].copy()
        n, x_cols = detect_subgroups(df_raw)
        _dyn_lsl = st.session_state["cap_lsl"]
        _dyn_usl = st.session_state["cap_usl"]
        _dyn_nom = st.session_state["cap_nominal"]
        issues    = validate_data(df_raw, x_cols, lsl=_dyn_lsl, usl=_dyn_usl)
        s         = compute_spc(df_raw, x_cols, n,
                                lsl=_dyn_lsl, usl=_dyn_usl,
                                nominal=_dyn_nom)
        _proc_ok  = True
    except Exception as _e:
        st.error("❌ No se pudo procesar los datos manuales. Verifica que todos los valores sean numéricos.")
        with st.expander("Ver detalle técnico"):
            st.code(str(_e))
        st.stop()

    if _proc_ok:
        for iss in issues:
            st.warning(f"⚠ {iss}")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE — parámetros económicos (persisten al cambiar de página)
# ─────────────────────────────────────────────────────────────────────────────
st.session_state.setdefault("eco_cost_kg",   25.0)
st.session_state.setdefault("eco_prod_h",    255)
st.session_state.setdefault("eco_hours_day", 16.0)
st.session_state.setdefault("eco_days_month",30)
st.session_state.setdefault("eco_lote",      200)
st.session_state.setdefault("eco_p_rechazo", 0.10)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN INLINE + KPIs — solo se ejecutan si el procesamiento fue exitoso
# ─────────────────────────────────────────────────────────────────────────────
# Protección explícita: s, n, x_cols solo existen cuando _proc_ok es True.
# (Los st.stop() en el bloque de carga ya detienen el script en caso de error,
#  pero este guard es una salvaguarda adicional ante cualquier re-run parcial.)
if not _proc_ok:
    st.stop()

# Valores silenciosos — bloque de muestreo eliminado del flujo global
n_proposed = st.session_state.get("n_proposed_val", 5)
freq_min   = st.session_state.get("freq_min_val", 20)

# KPIs globales — s está garantizado definido aquí
# (El rendering de los KPIs de Capacidad se realiza dentro de page_capacidad()
#  en el orden visual correcto. Las variables se calculan aquí para que otras
#  páginas y funciones puedan seguir referenciándolas sin cambios.)
_kpi_nominal   = st.session_state["cap_nominal"]
_kpi_over_g    = max(0.0, s["xbar_bar"] - _kpi_nominal) * 1000
_kpi_sacos_mes = (st.session_state["eco_prod_h"]
                  * st.session_state["eco_hours_day"]
                  * st.session_state["eco_days_month"])
_kpi_over_kg   = max(0.0, s["xbar_bar"] - _kpi_nominal) * _kpi_sacos_mes
_kpi_costo_mes = _kpi_over_kg * st.session_state["eco_cost_kg"]
_kpi_costo_anio= _kpi_costo_mes * 12
_kpi_sacos_ext = (_kpi_over_kg * 12 / 40) if _kpi_over_g > 0 else 0.0

cpk_color, cpk_text, cpk_badge = cpk_st(s["Cpk"])

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — NAVEGACIÓN SPA
# ─────────────────────────────────────────────────────────────────────────────

# Páginas disponibles agrupadas por fase
_PAGES = {
    "🏭 FASE I": [
        ("📊 Capacidad",      "capacidad"),
        ("📈 Cartas CEP",     "cartas_cep"),
        ("🔬 Diagnóstico",    "diagnostico"),
    ],
    "📊 FASE II": [
        ("⚡ Potencia",       "potencia"),
        ("🔴 Monitoreo",      "monitoreo"),
    ],
    "📦 MUESTREO": [
        ("📦 Planes de Muestreo", "muestreo"),
    ],
    "💰 ANÁLISIS ECONÓMICO": [
        ("💰 Análisis Económico", "eco_analisis"),
    ],
}

# Inicializar página por defecto
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "capacidad"


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN HTML — reporte completo descargable
# ─────────────────────────────────────────────────────────────────────────────

def generate_full_html_report() -> str:
    """Genera un reporte HTML completo con los resultados ya calculados en s y session_state."""
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lsl_r  = st.session_state["cap_lsl"]
    usl_r  = st.session_state["cap_usl"]
    nom_r  = st.session_state["cap_nominal"]
    xb     = s["xbar_bar"]
    sig    = s["sigma_st"]
    r_bar  = s["R_bar"]
    n_sg   = s["n"]
    k_sg   = len(s["df"])
    Cp     = s["Cp"]
    Cpl    = s["Cpl"]
    Cpu    = s["Cpu"]
    Cpk    = s["Cpk"]
    pnc_l  = s["pnc_low"]  * 100
    pnc_h  = s["pnc_high"] * 100
    pnc_t  = s["pnc_total"]* 100
    UCLx   = s["UCL_x"]
    LCLx   = s["LCL_x"]
    UCLr   = s["UCL_r"]
    LCLr   = s["LCL_r"]
    sw     = s.get("sw", {})
    sx_    = s.get("signals_x", [])
    sr_    = s.get("signals_r", [])

    over_g = max(0.0, xb - nom_r) * 1000
    und_g  = min(0.0, xb - nom_r) * 1000
    sacos_mes = (st.session_state["eco_prod_h"]
                 * st.session_state["eco_hours_day"]
                 * st.session_state["eco_days_month"])
    over_kg   = max(0.0, xb - nom_r) * sacos_mes
    costo_mes = over_kg * st.session_state["eco_cost_kg"]
    costo_anio= costo_mes * 12
    sacos_ext = (over_kg * 12 / 40) if over_g > 0 else 0.0

    # Capacidad semáforo
    def cpk_badge_txt(v):
        if v >= 1.33: return "#27AE60", "CAPAZ"
        if v >= 1.0:  return "#F39C12", "MARGINAL"
        return "#E74C3C", "INCAPAZ"
    cpk_col, cpk_lbl = cpk_badge_txt(Cpk)

    # Shapiro-Wilk
    sw_txt = ""
    if sw.get("W"):
        sw_normal = sw.get("normal", False)
        sw_txt = (f"W = {sw['W']:.5f} | p = {sw['p']:.5f} | "
                  + ("✅ Normalidad confirmada" if sw_normal else "⚠ Posible no normalidad"))

    # Alarmas CEP
    cx_ok  = "✅ Sin puntos fuera de control"    if not sx_ else f"❌ {len(sx_)} subgrupo(s) fuera de LCx"
    cr_ok  = "✅ Variabilidad bajo control"       if not sr_ else f"❌ {len(sr_)} subgrupo(s) fuera de LCr"

    # Monitoreo
    bloques = st.session_state.get("mon_bloques", [])
    mon_txt = f"{len(bloques)} bloque(s) de monitoreo registrados." if bloques else "Sin datos de monitoreo en esta sesión."

    # Plan de muestreo
    n_prop = st.session_state.get("n_proposed_val", n_sg)
    freq   = st.session_state.get("freq_min_val", 20)

    # μ* económico
    eco_lote  = st.session_state.get("eco_lote", 200)
    eco_p     = st.session_state.get("eco_p_rechazo", 0.10)
    eco_p_dec = eco_p / 100.0
    z_opt_r   = float(stats.norm.ppf(1.0 - eco_p_dec)) if eco_p_dec > 0 else 3.09
    se_lote_r = sig / float(np.sqrt(max(eco_lote, 1)))
    mu_star_r = nom_r + z_opt_r * se_lote_r
    mu_star_r = float(np.clip(mu_star_r, nom_r, max(xb, nom_r + 1e-6)))
    des_opt_g = (mu_star_r - nom_r) * 1000
    over_opt_kg = max(0.0, mu_star_r - nom_r) * sacos_mes
    costo_opt_mes = over_opt_kg * st.session_state["eco_cost_kg"]
    costo_opt_anio = costo_opt_mes * 12
    ahorro_anio = costo_anio - costo_opt_anio

    # ── CSS inline ────────────────────────────────────────────────────────────
    css = """
    body{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#F4F6F7;color:#2C3E50}
    .page{max-width:960px;margin:0 auto;padding:2rem 1.5rem}
    h1{font-size:1.5rem;color:#1B4F72;border-bottom:3px solid #1B4F72;padding-bottom:.4rem;margin-bottom:.2rem}
    h2{font-size:1.1rem;color:#1B4F72;margin:1.6rem 0 .5rem;border-left:4px solid #2E86C1;padding-left:.6rem}
    h3{font-size:.95rem;color:#2E86C1;margin:.8rem 0 .3rem}
    .sub{font-size:.75rem;color:#7F8C8D;margin-bottom:1rem}
    .kpi-row{display:flex;gap:.8rem;flex-wrap:wrap;margin:.6rem 0 1rem}
    .kpi{background:white;border-radius:8px;padding:.7rem 1rem;min-width:130px;
         box-shadow:0 1px 4px rgba(0,0,0,.1);flex:1;text-align:center}
    .kval{font-size:1.4rem;font-weight:700}
    .klbl{font-size:.7rem;color:#7F8C8D;margin-top:.2rem}
    table{width:100%;border-collapse:collapse;font-size:.82rem;margin:.5rem 0 1rem;background:white;
          border-radius:6px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
    th{background:#1B4F72;color:white;padding:.45rem .7rem;text-align:left}
    td{padding:.4rem .7rem;border-bottom:1px solid #EBF5FB}
    tr:last-child td{border:none}
    .ok{color:#27AE60;font-weight:600}
    .warn{color:#F39C12;font-weight:600}
    .bad{color:#E74C3C;font-weight:600}
    .tag{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.7rem;font-weight:700;color:white}
    footer{text-align:center;font-size:.7rem;color:#95A5A6;margin-top:2rem;padding-top:1rem;border-top:1px solid #D5DBDB}
    @media print{body{background:white}.page{padding:1rem}}
    """

    def kpi(val, lbl, color="#2E86C1"):
        return f'<div class="kpi"><div class="kval" style="color:{color}">{val}</div><div class="klbl">{lbl}</div></div>'

    def row(*cells):
        return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    def thead(*cells):
        return "<thead><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead>"

    # ── Construcción del HTML ─────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reporte CEP — Molinos Santa Marta S.A.S.</title>
<style>{css}</style>
</head>
<body>
<div class="page">

<h1>📊 Reporte CEP — Línea de Empaque de Mogolla</h1>
<p class="sub">Molinos Santa Marta S.A.S. &nbsp;·&nbsp; Generado: {ts} &nbsp;·&nbsp;
LSL = {lsl_r:.2f} kg &nbsp;·&nbsp; USL = {usl_r:.2f} kg &nbsp;·&nbsp; Nominal = {nom_r:.2f} kg</p>

<!-- ════ CAPACIDAD ════ -->
<h2>1. Capacidad del Proceso</h2>
<div class="kpi-row">
  {kpi(f"{xb:.4f} kg", "x̄ — Media")}
  {kpi(f"{sig:.4f} kg", "σ — Desv. estándar")}
  {kpi(f"{r_bar:.4f} kg", "R̄ — Rango promedio")}
  {kpi(str(n_sg), "n — Tamaño subgrupo")}
  {kpi(str(k_sg), "k — Subgrupos")}
  {kpi(f"{pnc_t:.3f}%", "p̂NC — Prop. No Conforme")}
</div>
<table>
  {thead("Índice", "Valor", "Interpretación")}
  <tbody>
    {row("Cp",  f"{Cp:.4f}",  ("✅ Proceso centrado" if Cp>=1.33 else "⚠ Margen ajustado" if Cp>=1.0 else "❌ Capacidad insuficiente"))}
    {row("Cpl", f"{Cpl:.4f}", "Capacidad respecto a LSL")}
    {row("Cpu", f"{Cpu:.4f}", "Capacidad respecto a USL")}
    {row('<strong>Cpk</strong>', f'<strong style="color:{cpk_col}">{Cpk:.4f}</strong>',
         f'<span class="tag" style="background:{cpk_col}">{cpk_lbl}</span>')}
    {row("% NC bajo LSL", f"{pnc_l:.4f}%", "Proporción bajo límite inferior")}
    {row("% NC sobre USL", f"{pnc_h:.4f}%", "Proporción sobre límite superior")}
  </tbody>
</table>
{"<p><strong>Shapiro-Wilk:</strong> " + sw_txt + "</p>" if sw_txt else ""}

<!-- ════ CARTAS CEP ════ -->
<h2>2. Cartas de Control — Fase I</h2>
<table>
  {thead("Carta", "LCI", "Línea Central", "LCS", "Estado")}
  <tbody>
    {row("X̄", f"{LCLx:.4f} kg", f"{xb:.4f} kg", f"{UCLx:.4f} kg",
         f'<span class="ok">{cx_ok}</span>' if not sx_ else f'<span class="bad">{cx_ok}</span>')}
    {row("R", f"{LCLr:.4f} kg", f"{r_bar:.4f} kg", f"{UCLr:.4f} kg",
         f'<span class="ok">{cr_ok}</span>' if not sr_ else f'<span class="bad">{cr_ok}</span>')}
  </tbody>
</table>

<!-- ════ DIAGNÓSTICO ════ -->
<h2>3. Diagnóstico del Proceso</h2>
<table>
  {thead("Indicador", "Estado")}
  <tbody>
    {row("Control estadístico X̄", '<span class="ok">✅ Bajo control</span>' if not sx_ else f'<span class="bad">❌ {len(sx_)} señal(es)</span>')}
    {row("Control estadístico R", '<span class="ok">✅ Bajo control</span>' if not sr_ else f'<span class="bad">❌ {len(sr_)} señal(es)</span>')}
    {row("Capacidad (Cpk ≥ 1.33)", f'<span class="{"ok" if Cpk>=1.33 else "warn" if Cpk>=1.0 else "bad"}">{cpk_lbl} ({Cpk:.3f})</span>')}
    {row("Sobrellenado", f'<span class="warn">+{over_g:.1f} g/saco</span>' if over_g > 0 else '<span class="ok">Sin sobrellenado</span>')}
    {row("Subllenado", f'<span class="bad">{und_g:.1f} g/saco</span>' if und_g < 0 else '<span class="ok">Sin subllenado</span>')}
    {row("Normalidad", ('<span class="ok">Confirmada</span>' if sw.get("normal") else '<span class="warn">Posible no normalidad</span>') if sw.get("W") else "—")}
  </tbody>
</table>

<!-- ════ POTENCIA ════ -->
<h2>4. Análisis de Potencia</h2>
<table>
  {thead("Parámetro", "Valor")}
  <tbody>
    {row("σ proceso estimada", f"{sig:.4f} kg")}
    {row("n subgrupo recomendado", str(n_prop))}
    {row("Desplazamiento detectable (1σ)", f"{sig:.4f} kg")}
    {row("Desplazamiento detectable (2σ)", f"{2*sig:.4f} kg")}
    {row("Frecuencia de muestreo sugerida", f"cada {freq} min")}
  </tbody>
</table>

<!-- ════ MONITOREO ════ -->
<h2>5. Monitoreo en Tiempo Real — Fase II</h2>
<p>{mon_txt}</p>
{"".join(_mon_bloque_html(b) for b in bloques[:5]) if bloques else ""}

<!-- ════ PLAN DE MUESTREO ════ -->
<h2>6. Plan de Muestreo Propuesto</h2>
<table>
  {thead("Parámetro", "Valor")}
  <tbody>
    {row("Tamaño de muestra (n)", str(n_prop))}
    {row("Frecuencia de muestreo", f"cada {freq} minutos")}
    {row("Límite inferior de control (LCI X̄)", f"{LCLx:.4f} kg")}
    {row("Límite superior de control (LCS X̄)", f"{UCLx:.4f} kg")}
    {row("LSL", f"{lsl_r:.4f} kg")}
    {row("USL", f"{usl_r:.4f} kg")}
  </tbody>
</table>

<!-- ════ ANÁLISIS ECONÓMICO ════ -->
<h2>7. Análisis Económico del Sobrellenado</h2>
<div class="kpi-row">
  {kpi(f"+{over_g:.1f} g", "Sobrellenado/saco", "#F39C12" if over_g>0 else "#27AE60")}
  {kpi(f"${costo_mes:,.0f}", "Pérdida mensual (COP)", "#E74C3C")}
  {kpi(f"${costo_anio:,.0f}", "Pérdida anual (COP)", "#E74C3C")}
  {kpi(f"{sacos_ext:.0f}", "Sacos extra/año", "#E74C3C")}
</div>
<table>
  {thead("Escenario", "Media (kg)", "Exceso/saco (g)", "Costo mensual (COP)", "Costo anual (COP)")}
  <tbody>
    {row('<span class="warn">⚠ Actual</span>', f"{xb:.4f}", f"+{over_g:.1f}", f"${costo_mes:,.0f}", f"${costo_anio:,.0f}")}
    {row('<span class="ok">✅ Óptimo (μ*)</span>', f"{mu_star_r:.4f}", f"+{des_opt_g:.1f}", f"${costo_opt_mes:,.0f}", f"${costo_opt_anio:,.0f}")}
    {row('<strong>💰 Ahorro</strong>', "—", f"{over_g-des_opt_g:.1f} g menos", f"${costo_mes-costo_opt_mes:,.0f}", f'<strong style="color:#27AE60">${ahorro_anio:,.0f}</strong>')}
  </tbody>
</table>
<p style="font-size:.82rem;color:#566573">
<strong>Interpretación:</strong> Con μ* = {mu_star_r:.4f} kg (+{des_opt_g:.1f} g sobre nominal),
la probabilidad de rechazo del lote de {eco_lote} sacos se mantiene ≤ {eco_p:.3f}%.
Esto representa un ahorro estimado de <strong>${ahorro_anio:,.0f} COP/año</strong>.
</p>

<footer>Reporte generado por CEP v2.1 · Molinos Santa Marta S.A.S. · {ts}</footer>
</div>
</body>
</html>"""
    return html


def _mon_bloque_html(b: dict) -> str:
    """Genera una tabla HTML resumida para un bloque de monitoreo."""
    df_p = b.get("_df_proc")
    if df_p is None or len(df_p) == 0:
        return f"<p style='font-size:.8rem'>Bloque {b['bid']}: sin datos procesados.</p>"
    n_new   = b.get("n_new", 0)
    signals = b.get("new_signals", [])
    sig_txt = (f'<span class="ok">Sin señales</span>' if not signals
               else f'<span class="bad">⚠ {len(signals)} señal(es) detectada(s)</span>')
    return f"""
<h3>Bloque {b['bid']} — {n_new} subgrupo(s) nuevos · {sig_txt}</h3>
<table>
  <thead><tr><th>Subgrupo</th><th>x̄</th><th>R</th></tr></thead>
  <tbody>
    {"".join(f"<tr><td>{i+1}</td><td>{row['xbar']:.4f}</td><td>{row['R']:.4f}</td></tr>"
             for i, row in df_p.head(10).iterrows())}
  </tbody>
</table>"""


def render_sidebar():
    """Construye el menú lateral de navegación SPA."""
    with st.sidebar:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1B4F72,#154360);
             color:white;padding:1rem 1.2rem;border-radius:10px;margin-bottom:1.2rem;">
          <div style="font-size:1rem;font-weight:700;letter-spacing:-.3px">⚙️ CEP Menu</div>
          <div style="font-size:.72rem;opacity:.8;margin-top:.2rem">Molinos Santa Marta S.A.S.</div>
        </div>
        """, unsafe_allow_html=True)

        for grupo, items in _PAGES.items():
            st.markdown(
                f'<div style="font-size:.68rem;font-weight:700;color:#7F8C8D;'
                f'text-transform:uppercase;letter-spacing:.8px;'
                f'margin:.9rem 0 .3rem;padding-left:.2rem">{grupo}</div>',
                unsafe_allow_html=True
            )
            for label, key in items:
                activo = st.session_state["pagina"] == key
                if st.button(
                    label,
                    key=f"nav_{key}",
                    width='stretch',
                    type="primary" if activo else "secondary",
                ):
                    st.session_state["pagina"] = key
                    # No st.rerun() — Streamlit re-renders automatically on session_state change

        st.markdown("---")
        try:
            _html_rep = generate_full_html_report()
            st.download_button(
                label="📥 Exportar Reporte HTML",
                data=_html_rep.encode("utf-8"),
                file_name="reporte_CEP_molinos.html",
                mime="text/html",
                use_container_width=True,
                help="Descarga un reporte HTML completo con todos los resultados del análisis",
            )
        except Exception:
            pass  # Si aún no hay datos, el botón no aparece sin romper la app
        st.markdown(
            '<div style="font-size:.7rem;color:#95A5A6;text-align:center;margin-top:.4rem">'
            'v2.1 · Molinos Santa Marta S.A.S.</div>',
            unsafe_allow_html=True
        )


render_sidebar()
pagina_activa = st.session_state["pagina"]

# ─────────────────────────────────────────────────────────────────────────────
# ROUTER — muestra la sección activa
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────

def page_capacidad():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed

    # ══════════════════════════════════════════════════════════════════════════
    # 1. TÍTULO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("📊 Análisis de Capacidad del Proceso — Fase I"),
                unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 2. INGRESO DE DATOS — Cambiar método + Cargar Excel
    #    (los widgets de modo_carga ya se renderizaron antes de entrar a esta
    #     función; aquí solo se ubica el separador visual para agruparlos)
    # ══════════════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════════════
    # 3. ESPECIFICACIONES DEL PROCESO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("⚙️ Especificaciones del Proceso"), unsafe_allow_html=True)
    esp_col1, esp_col2, esp_col3 = st.columns(3)
    with esp_col1:
        lsl_input = st.number_input("LSL — Límite inferior de especificación (kg)",
                                    value=st.session_state["cap_lsl"], format="%.4f",
                                    step=0.01, key="_widget_lsl")
        st.session_state["cap_lsl"] = lsl_input
    with esp_col2:
        usl_input = st.number_input("USL — Límite superior de especificación (kg)",
                                    value=st.session_state["cap_usl"], format="%.4f",
                                    step=0.01, key="_widget_usl")
        st.session_state["cap_usl"] = usl_input
    with esp_col3:
        st.metric("Tolerancia total", f"{usl_input - lsl_input:.4f} kg",
                  delta=f"{(usl_input-lsl_input - (USL-LSL))*1000:+.1f} g vs default")

    # Persistir nominal actualizado en session_state
    nominal_input = (lsl_input + usl_input) / 2.0
    st.session_state["cap_nominal"] = nominal_input

    # ── Reconstruir s completamente con los límites actuales ──────────────────
    # Se accede al df y metadatos del s global (construido en la carga),
    # pero todos los índices y límites se recalculan desde cero.
    s_cap = compute_spc(
        s["df"], s["x_cols"], s["n"],
        lsl=lsl_input, usl=usl_input, nominal=nominal_input,
    )

    _sig  = s_cap["sigma_st"]; _xb = s_cap["xbar_bar"]
    _Cp   = s_cap["Cp"];  _Cpu = s_cap["Cpu"]
    _Cpl  = s_cap["Cpl"]; _Cpk = s_cap["Cpk"]
    _pnc_low  = s_cap["pnc_low"]
    _pnc_high = s_cap["pnc_high"]
    _pnc_tot  = s_cap["pnc_total"]
    _cpk_color, _cpk_txt, _cpk_badge = cpk_st(_Cpk)

    # Aviso informativo si el usuario cambió los defaults
    if abs(lsl_input - LSL) > 1e-6 or abs(usl_input - USL) > 1e-6:
        st.markdown(render_alarm("info",
            f"ℹ Especificaciones activas: LSL = {lsl_input} kg | USL = {usl_input} kg. "
            f"Los indicadores de capacidad fueron actualizados."), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ESTADÍSTICOS DEL PROCESO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("📐 Estadísticos del Proceso"), unsafe_allow_html=True)
    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    for col, lbl, val in [
        (sc1, "x̄ — Media del proceso",       f"{s_cap['xbar_bar']:.4f} kg"),
        (sc2, "σ — Desv. estándar",           f"{s_cap['sigma_st']:.4f} kg"),
        (sc3, "R̄ — Rango promedio",           f"{s_cap['R_bar']:.4f} kg"),
        (sc4, "n — Tamaño subgrupo",          str(s_cap["n"])),
        (sc5, "k — Nº subgrupos",             str(len(s_cap["df"]))),
        (sc6, "p̂NC — Prop. No Conforme",      f"{_pnc_tot*100:.3f}%"),
    ]:
        with col: st.metric(lbl, val)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. TEST SHAPIRO-WILK
    # ══════════════════════════════════════════════════════════════════════════
    sw = s_cap["sw"]
    if sw["W"]:
        cls     = "alarm-ok" if sw["normal"] else "alarm-warning"
        verdict = "✅ Normalidad confirmada (p > 0.05)" if sw["normal"] else "⚠ Posible no normalidad (p ≤ 0.05)"
        st.markdown(f"""<div class="alarm-box {cls}">
        <strong>🔬 Test Shapiro-Wilk</strong> &nbsp;|&nbsp; W = {sw['W']:.5f} &nbsp;|&nbsp;
        p = {sw['p']:.5f} &nbsp;|&nbsp; {verdict}
        &nbsp;&nbsp;<span style="opacity:.6;font-size:.82em">▾ Ver gráfica de normalidad</span>
        </div>""", unsafe_allow_html=True)

        with st.expander("📈 Ver análisis de normalidad", expanded=False):
            _vals_sw = s_cap["all_vals"].astype(float)
            _xb_sw   = s_cap["xbar_bar"]
            _sig_sw  = s_cap["sigma_st"]

            _sw_col1, _sw_col2 = st.columns([1, 1])

            # ── Histograma con curva normal ajustada ─────────────────────────
            with _sw_col1:
                st.markdown("**Gráfico Q-Q**")
                # QQ Plot
                _sorted_vals = np.sort(_vals_sw)
                _n_sw = len(_sorted_vals)
                _quantiles_teo = stats.norm.ppf(
                    np.linspace(1 / (_n_sw + 1), _n_sw / (_n_sw + 1), _n_sw)
                )
                # Línea de referencia
                _q25, _q75 = np.percentile(_sorted_vals, [25, 75])
                _t25, _t75 = stats.norm.ppf([0.25, 0.75])
                _slope_qq = (_q75 - _q25) / (_t75 - _t25)
                _inter_qq = _q25 - _slope_qq * _t25
                _x_ref = np.array([_quantiles_teo[0], _quantiles_teo[-1]])
                _y_ref = _slope_qq * _x_ref + _inter_qq

                _fig_qq = go.Figure()
                _fig_qq.add_trace(go.Scatter(
                    x=_quantiles_teo, y=_sorted_vals,
                    mode="markers", name="Cuantiles observados",
                    marker=dict(color="#2D7AC4", size=6,
                                line=dict(color="white", width=0.8)),
                    hovertemplate="Teórico: %{x:.3f}<br>Observado: %{y:.4f}<extra></extra>"
                ))
                _fig_qq.add_trace(go.Scatter(
                    x=_x_ref, y=_y_ref,
                    mode="lines", name="Línea de referencia",
                    line=dict(color="#A93226", width=1.8, dash="dash"),
                    hoverinfo="skip"
                ))
                _fig_qq.update_layout(
                    height=280, template="plotly_white",
                    plot_bgcolor="#FAFCFE", paper_bgcolor="#FFFFFF",
                    margin=dict(l=48, r=16, t=32, b=48),
                    xaxis=dict(title="Cuantiles teóricos (Normal)",
                               tickfont=dict(size=9), gridcolor="#E8EEF4"),
                    yaxis=dict(title="Cuantiles observados (kg)",
                               tickfont=dict(size=9), gridcolor="#E8EEF4"),
                    legend=dict(font=dict(size=9), y=1.08, x=0),
                    font=dict(family="DM Sans, system-ui, sans-serif", size=10),
                )
                st.plotly_chart(_fig_qq, use_container_width=True,
                                key="chart_qq_norm")

            # ── QQ Plot ───────────────────────────────────────────────────────
            with _sw_col2:
                st.markdown("**Histograma de normalidad**")
                _xr_sw = np.linspace(_xb_sw - 4*_sig_sw, _xb_sw + 4*_sig_sw, 400)
                _pdf_sw = stats.norm.pdf(_xr_sw, _xb_sw, _sig_sw)

                _fig_hn = go.Figure()
                _fig_hn.add_trace(go.Histogram(
                    x=_vals_sw, histnorm="probability density",
                    name="Datos",
                    marker=dict(color="#4A90C4", opacity=0.45,
                                line=dict(color="white", width=0.8)),
                    nbinsx=max(8, _n_sw // 3),
                    hovertemplate="Rango: %{x:.3f}<br>Densidad: %{y:.4f}<extra></extra>"
                ))
                _fig_hn.add_trace(go.Scatter(
                    x=_xr_sw, y=_pdf_sw, mode="lines",
                    name=f"Normal ajustada",
                    line=dict(color="#0F2A40", width=2.4),
                    hovertemplate="x = %{x:.3f}<br>f(x) = %{y:.4f}<extra></extra>"
                ))
                _fig_hn.update_layout(
                    height=280, template="plotly_white",
                    plot_bgcolor="#FAFCFE", paper_bgcolor="#FFFFFF",
                    margin=dict(l=48, r=16, t=32, b=48),
                    xaxis=dict(title="Peso individual (kg)",
                               tickfont=dict(size=9), gridcolor="#E8EEF4"),
                    yaxis=dict(title="Densidad",
                               tickfont=dict(size=9), gridcolor="#E8EEF4"),
                    legend=dict(font=dict(size=9), y=1.08, x=0),
                    font=dict(family="DM Sans, system-ui, sans-serif", size=10),
                )
                st.plotly_chart(_fig_hn, use_container_width=True,
                                key="chart_hist_norm")

            # ── Resultados y tabla ────────────────────────────────────────────
            _res_col, _interp_col = st.columns([1, 2])
            with _res_col:
                st.markdown(f"""
                <div style="background:#F7FAFC;border:1px solid #DDE8F0;
                     border-radius:8px;padding:.9rem 1rem;">
                  <div style="font-size:.72rem;font-weight:700;color:#4A5A6A;
                       text-transform:uppercase;letter-spacing:.07em;margin-bottom:.6rem">
                    Resultados
                  </div>
                  <table style="width:100%;border-collapse:collapse;font-size:.84rem">
                    <tr>
                      <td style="color:#6B7A8A;padding:3px 0">W (Shapiro-Wilk)</td>
                      <td style="text-align:right;font-family:monospace;font-weight:600">
                        {sw['W']:.4f}
                      </td>
                    </tr>
                    <tr>
                      <td style="color:#6B7A8A;padding:3px 0">p-valor</td>
                      <td style="text-align:right;font-family:monospace;font-weight:600">
                        {sw['p']:.4f}
                      </td>
                    </tr>
                    <tr style="border-top:1px solid #DDE8F0">
                      <td colspan="2" style="padding-top:.5rem">
                        <span style="font-size:.82rem;font-weight:700;
                          color:{'#0E7C3A' if sw['normal'] else '#C47A00'}">
                          {'✔ Normalidad confirmada' if sw['normal'] else '⚠ Posible no normalidad'}
                        </span><br>
                        <span style="font-size:.74rem;color:#8FA3B3">
                          {'p > 0.05' if sw['normal'] else 'p ≤ 0.05'}
                        </span>
                      </td>
                    </tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

            with _interp_col:
                if sw["normal"]:
                    _interp_txt = (
                        f"Los <strong>{_n_sw} valores</strong> individuales de la muestra "
                        f"siguen una distribución <strong>aproximadamente normal</strong> "
                        f"(Shapiro-Wilk W = {sw['W']:.4f}, p = {sw['p']:.4f} > 0.05). "
                        f"No se detectan desviaciones severas respecto a la normalidad, "
                        f"lo que valida el uso de los límites de control 3σ y los índices "
                        f"de capacidad Cp / Cpk bajo el supuesto gaussiano."
                    )
                    _interp_cls = "alarm-ok"
                else:
                    _interp_txt = (
                        f"La prueba detecta <strong>posible no normalidad</strong> en los "
                        f"{_n_sw} valores individuales "
                        f"(Shapiro-Wilk W = {sw['W']:.4f}, p = {sw['p']:.4f} ≤ 0.05). "
                        f"Los índices Cp / Cpk se calcularon bajo el supuesto normal; "
                        f"se recomienda revisar el QQ-Plot e inspeccionar outliers o causas "
                        f"especiales antes de tomar decisiones sobre la capacidad del proceso."
                    )
                    _interp_cls = "alarm-warning"
                st.markdown(
                    f'<div class="alarm-box {_interp_cls}" '
                    f'style="font-size:.84rem;line-height:1.6">{_interp_txt}</div>',
                    unsafe_allow_html=True
                )

    # ══════════════════════════════════════════════════════════════════════════
    # 6. GRÁFICOS PRINCIPALES — Histograma capacidad + Indicador Cpk
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("📊 Gráficos de Capacidad"), unsafe_allow_html=True)

    # Clave única que cambia con los límites → fuerza a Streamlit/Plotly a
    # destruir y recrear el componente (evita el error removeChild del DOM).
    _hist_key = f"chart_histogram_{lsl_input:.4f}_{usl_input:.4f}"

    ch, cg = st.columns([3, 1])
    with ch:
        st.plotly_chart(fig_histogram(s_cap), key=_hist_key)
    with cg:
        st.plotly_chart(fig_gauge(_Cpk), key=f"chart_gauge_{lsl_input:.4f}_{usl_input:.4f}")
        st.markdown(f"""<div style="background:white;border-radius:8px;padding:.8rem;
            box-shadow:0 1px 6px rgba(0,0,0,.07);font-size:.82rem">
        <div class="section-title" style="margin-top:0">Índices</div>
        <table style="width:100%;border-collapse:collapse">
        <tr><td style="color:#7F8C8D;padding:3px 0">Cp</td><td style="text-align:right;font-family:monospace;font-weight:600">{_Cp:.4f}</td></tr>
        <tr><td style="color:#7F8C8D;padding:3px 0">Cpu</td><td style="text-align:right;font-family:monospace;font-weight:600">{_Cpu:.4f}</td></tr>
        <tr><td style="color:#7F8C8D;padding:3px 0">Cpl</td><td style="text-align:right;font-family:monospace;font-weight:600">{_Cpl:.4f}</td></tr>
        <tr style="border-top:2px solid #D5E8F3"><td style="font-weight:700;color:{_cpk_color};padding:5px 0">Cpk</td>
        <td style="text-align:right;font-family:monospace;font-weight:700;color:{_cpk_color}">{_Cpk:.4f}</td></tr>
        </table></div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. KPIs FINALES — Cpk · % NC · Sobrellenado
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    _kpi_nominal_cap = st.session_state["cap_nominal"]
    _kpi_over_g_cap  = max(0.0, s_cap["xbar_bar"] - _kpi_nominal_cap) * 1000
    _kpi_under_g_cap = min(0.0, s_cap["xbar_bar"] - _kpi_nominal_cap) * 1000  # negativo si hay subllenado

    k1, k2, k3, k4 = st.columns(4)

    bord = "red" if _Cpk < 1.0 else "yellow" if _Cpk < 1.33 else "green"
    with k1:
        st.markdown(f"""<div class="kpi-card {bord}">
        <div class="kpi-value" style="color:{_cpk_color}">{_Cpk:.3f}</div>
        <div class="kpi-label">Índice Cpk</div>
        <div class="kpi-sub"><span class="badge {_cpk_badge}">{_cpk_txt}</span></div></div>""",
        unsafe_allow_html=True)

    pnc = _pnc_tot * 100
    pb  = "red" if pnc > 5 else "yellow" if pnc > 0.27 else "green"
    pc  = CR if pnc > 5 else CY if pnc > 0.27 else CG
    with k2:
        st.markdown(f"""<div class="kpi-card {pb}">
        <div class="kpi-value" style="color:{pc}">{pnc:.2f}%</div>
        <div class="kpi-label">% Producto No Conforme</div>
        <div class="kpi-sub">↓{_pnc_low*100:.2f}% LIE | ↑{_pnc_high*100:.2f}% LSE</div></div>""",
        unsafe_allow_html=True)

    with k3:
        st.markdown(f"""<div class="kpi-card {'yellow' if _kpi_over_g_cap > 0 else 'green'}">
        <div class="kpi-value" style="color:{CY if _kpi_over_g_cap > 0 else CG}">{_kpi_over_g_cap:+.1f} g</div>
        <div class="kpi-label">Sobrellenado promedio</div>
        <div class="kpi-sub">Media = {s_cap['xbar_bar']:.4f} kg &nbsp;·&nbsp; Ver costos en 💰 Análisis Económico</div></div>""",
        unsafe_allow_html=True)

    with k4:
        if _kpi_under_g_cap < 0:
            st.markdown(f"""<div class="kpi-card red">
            <div class="kpi-value" style="color:{CR}">{_kpi_under_g_cap:.1f} g</div>
            <div class="kpi-label">Subllenado promedio</div>
            <div class="kpi-sub">⚠ Media bajo nominal: {s_cap['xbar_bar']:.4f} kg</div></div>""",
            unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="kpi-card green">
            <div class="kpi-value" style="color:{CG}; font-size:1rem">✅ Sin subllenado</div>
            <div class="kpi-label">Subllenado promedio</div>
            <div class="kpi-sub">Media ≥ nominal ({_kpi_nominal_cap:.1f} kg)</div></div>""",
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 8. TABLA DE SUBGRUPOS
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("📋 Tabla de subgrupos"):
        st.dataframe(s_cap["df"].round(4), key="df_subgrupos")


def page_cartas_cep():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed

    st.markdown(render_section_title("📈 Cartas de Control — Fase I"), unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca:
        cls = "alarm-ok" if not s["signals_x"] else "alarm-critical"
        msg = (f"✅ Carta X̄: Sin puntos fuera de control." if not s["signals_x"]
               else f"❌ Carta X̄: {len(s['signals_x'])}/{len(s['df'])} fuera de límites.")
        st.markdown(f'<div class="alarm-box {cls}">{msg}</div>', unsafe_allow_html=True)
    with cb:
        cls = "alarm-ok" if not s["signals_r"] else "alarm-critical"
        msg = (f"✅ Carta R: Variabilidad bajo control." if not s["signals_r"]
               else f"❌ Carta R: {len(s['signals_r'])}/{len(s['df'])} fuera de control.")
        st.markdown(f'<div class="alarm-box {cls}">{msg}</div>', unsafe_allow_html=True)

    st.plotly_chart(fig_xbar(s), key="chart_xbar")
    st.plotly_chart(fig_r(s),    key="chart_r")

    with st.expander("📐 Constantes y límites"):
        co = s["consts"]
        st.markdown(f"""
        |Parámetro|Valor| |Parámetro|Valor|
        |---------|-----|-|---------|-----|
        |n|**{s['n']}**| |LCS X̄|**{s['UCL_x']:.4f} kg**|
        |d₂|**{co['d2']}**| |LC X̄|**{s['xbar_bar']:.4f} kg**|
        |A₂|**{co['A2']}**| |LCI X̄|**{s['LCL_x']:.4f} kg**|
        |D₃|**{co['D3']}**| |LCS R|**{s['UCL_r']:.4f} kg**|
        |D₄|**{co['D4']}**| |R promedio|**{s['R_bar']:.4f} kg**|
        |σ proceso|**{s['sigma_st']:.4f} kg**| |LCI R|**{s['LCL_r']:.4f} kg**|
        """)


def page_diagnostico():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed

    st.markdown(render_section_title("🚦 Diagnóstico Integral"), unsafe_allow_html=True)
    alarmas = []
    if s["Cpk"] < 1.0:     alarmas.append(("critical", f"🔴 Proceso INCAPAZ: Cpk={s['Cpk']:.3f}. Reducir variabilidad urgente."))
    elif s["Cpk"] < 1.33:  alarmas.append(("warning",  f"🟡 Proceso MARGINAL: Cpk={s['Cpk']:.3f}. Monitoreo intensivo."))
    else:                   alarmas.append(("ok",       f"🟢 Proceso CAPAZ: Cpk={s['Cpk']:.3f} ≥ 1.33."))

    des_g = (s["xbar_bar"] - s.get("NOMINAL", st.session_state["cap_nominal"])) * 1000
    if abs(des_g) > 200:   alarmas.append(("warning", f"🟡 Descentrado {des_g:+.1f} g sobre nominal. Ajustar dosificador."))
    else:                   alarmas.append(("ok",      f"🟢 Centrado aceptable: desviación = {des_g:+.1f} g."))

    if s["signals_x"]:     alarmas.append(("critical", f"🔴 {len(s['signals_x'])} subgrupo(s) fuera de límites en carta X̄."))
    else:                   alarmas.append(("ok",       "🟢 Carta X̄: proceso bajo control estadístico."))

    if s["signals_r"]:     alarmas.append(("critical", f"🔴 {len(s['signals_r'])} subgrupo(s) con variabilidad fuera de control."))
    else:                   alarmas.append(("ok",       "🟢 Carta R: variabilidad estable."))

    pnc_t = s["pnc_total"]
    if pnc_t > 0.05:       alarmas.append(("critical", f"🔴 PNC={pnc_t*100:.2f}%. Riesgo legal y comercial elevado."))
    elif pnc_t > 0.0027:   alarmas.append(("warning",  f"🟡 PNC={pnc_t*100:.3f}%. Supera umbral 3σ."))
    else:                   alarmas.append(("ok",       f"🟢 PNC={pnc_t*100:.4f}% — dentro del estándar."))

    sw = s["sw"]
    if sw["W"]:
        if not sw["normal"]: alarmas.append(("warning", f"🟡 Shapiro-Wilk p={sw['p']:.4f} sugiere no normalidad."))
        else:                 alarmas.append(("ok",      f"🟢 Normalidad confirmada: p={sw['p']:.4f}."))

    for tipo, msg in alarmas:
        st.markdown(render_alarm(tipo, msg), unsafe_allow_html=True)


def page_potencia():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed


    # ── Variables de Fase I (autollenado desde s) ─────────────────────────────
    _mu0  = s["xbar_bar"]
    _sig  = s["sigma_st"]
    _n    = s["n"]
    _UCL  = s["UCL_x"]
    _LCL  = s["LCL_x"]
    _conf = 95.00

    # ── Inicializar session_state ─────────────────────────────────────────────
    if "pot_mu1_val"    not in st.session_state: st.session_state["pot_mu1_val"]    = ""
    if "pot_calculado"  not in st.session_state: st.session_state["pot_calculado"]  = False
    if "arl_mu1_val"    not in st.session_state: st.session_state["arl_mu1_val"]    = ""
    if "arl_calculado"  not in st.session_state: st.session_state["arl_calculado"]  = False

    # ══════════════════════════════════════════════════════════════════════════
    # BLOQUE A — ANÁLISIS DE POTENCIA
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""<style>
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] { display: none !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1B4F72,#2E86C1);color:white;
         padding:1.1rem 1.5rem;border-radius:10px;margin-bottom:.8rem;">
    <h3 style="margin:0 0 .25rem;font-size:1.15rem;">🔬 Análisis de Potencia Estadística</h3>
    <p style="margin:0;opacity:.85;font-size:.82rem;">
    Parámetros pre-llenados desde Fase I. Puedes editarlos si necesitas ajustarlos.</p>
    </div>
    """, unsafe_allow_html=True)

    pot_col1, pot_col2 = st.columns([1, 1])

    with pot_col1:
        pa1, pa2 = st.columns(2)
        with pa1:
            _mu0_txt = st.text_input("Media actual (μ₀)", value=f"{_mu0:.4f}", key="pot_mu0")
            try: _mu0 = float(_mu0_txt.replace(",", "."))
            except: pass
            _UCL_txt = st.text_input("LCS", value=f"{_UCL:.4f}", key="pot_UCL")
            try: _UCL = float(_UCL_txt.replace(",", "."))
            except: pass
        with pa2:
            _sig_txt = st.text_input("Sigma (σ)", value=f"{_sig:.6f}", key="pot_sig")
            try: _sig = float(_sig_txt.replace(",", "."))
            except: pass
            _LCL_txt = st.text_input("LCI", value=f"{_LCL:.4f}", key="pot_LCL")
            try: _LCL = float(_LCL_txt.replace(",", "."))
            except: pass
        _n_txt = st.text_input("Tamaño de muestra (n)", value=str(int(_n)), key="pot_n")
        try: _n = max(2, min(1000, int(_n_txt)))
        except: pass

    with pot_col2:
        st.markdown(render_section_title("✏️ Parámetro manual"), unsafe_allow_html=True)
        _mu1_pot_txt = st.text_input(
            "Nueva Media (μ₁) en kg",
            value=st.session_state["pot_mu1_val"],
            placeholder=f"Ej: {_mu0 - _sig:.3f}",
            help="Ingresa la media desplazada que deseas evaluar (kg)",
            key="pot_mu1_txt"
        )
        st.session_state["pot_mu1_val"] = _mu1_pot_txt

        if st.button("🔬 Calcular Potencia", type="primary", key="btn_pot_calcular",
                     width='stretch'):
            if not _mu1_pot_txt.strip():
                st.warning("⚠ Ingresa un valor para μ₁ antes de calcular.")
                st.session_state["pot_calculado"] = False
            else:
                try:
                    float(_mu1_pot_txt.replace(",", "."))
                    st.session_state["pot_calculado"] = True
                except ValueError:
                    st.warning("⚠ Ingresa un número válido para μ₁ (usa punto como decimal).")
                    st.session_state["pot_calculado"] = False

    # ── Resultados de Potencia ─────────────────────────────────────────────────
    if st.session_state["pot_calculado"] and st.session_state["pot_mu1_val"].strip():
        try:
            mu1_pot = float(st.session_state["pot_mu1_val"].replace(",", "."))
            fig_pot, res_pot = fig_campanas_potencia(_mu0, _sig, _n, _UCL, _LCL, mu1_pot)

            beta_p  = res_pot["beta"]
            power_p = res_pot["power"]
            ARL0_p  = res_pot["ARL0"]
            ARL1_p  = res_pot["ARL1"]
            pc_     = res_pot["pow_color"]

            st.markdown("<br>", unsafe_allow_html=True)
            kp1, kp2, kp3, kp4 = st.columns(4)
            pow_bord = "green" if power_p >= 0.9 else "yellow" if power_p >= 0.5 else "red"

            with kp1:
                st.markdown(f"""<div class="kpi-card {pow_bord}">
                <div class="kpi-value" style="color:{pc_}">{power_p:.2%}</div>
                <div class="kpi-label">Potencia (1 − β)</div>
                <div class="kpi-sub">Probabilidad de detectar el cambio</div></div>""",
                unsafe_allow_html=True)

            with kp2:
                col_b = CR if beta_p > 0.5 else CY if beta_p > 0.1 else CG
                st.markdown(f"""<div class="kpi-card {'red' if beta_p>0.5 else 'yellow' if beta_p>0.1 else 'green'}">
                <div class="kpi-value" style="color:{col_b}">{beta_p:.4f}</div>
                <div class="kpi-label">Error Tipo II (β)</div>
                <div class="kpi-sub">P(no detectar el cambio)</div></div>""",
                unsafe_allow_html=True)

            with kp3:
                st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:{CP}">{ARL0_p:.0f}</div>
                <div class="kpi-label">ARL₀</div>
                <div class="kpi-sub">1/α &nbsp;·&nbsp; α≈0.0027 (3σ)</div></div>""",
                unsafe_allow_html=True)

            with kp4:
                col_arl = CG if ARL1_p <= 5 else CY if ARL1_p <= 20 else CR
                st.markdown(f"""<div class="kpi-card {'green' if ARL1_p<=5 else 'yellow' if ARL1_p<=20 else 'red'}">
                <div class="kpi-value" style="color:{col_arl}">{ARL1_p:.1f}</div>
                <div class="kpi-label">ARL₁</div>
                <div class="kpi-sub">Muestras para detectar el cambio</div></div>""",
                unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.plotly_chart(fig_pot, key="chart_pot_campanas")

            delta_g = (mu1_pot - _mu0) * 1000
            if power_p >= 0.9:
                css_i = "alarm-ok"
                msg_i = (f"✅ Con μ₁ = {mu1_pot:.4f} kg (desplazamiento {delta_g:+.1f} g), "
                         f"la carta detecta el cambio con <strong>{power_p:.1%} de potencia</strong>. "
                         f"En promedio se necesitan <strong>{ARL1_p:.1f} muestras</strong> para dar señal.")
            elif power_p >= 0.5:
                css_i = "alarm-warning"
                msg_i = (f"⚠️ Potencia moderada de <strong>{power_p:.1%}</strong> para μ₁ = {mu1_pot:.4f} kg. "
                         f"Se necesitan ~<strong>{ARL1_p:.1f} muestras</strong> para detectar el cambio. "
                         f"Considera aumentar el tamaño de subgrupo.")
            else:
                css_i = "alarm-critical"
                msg_i = (f"❌ Potencia muy baja (<strong>{power_p:.1%}</strong>) para μ₁ = {mu1_pot:.4f} kg. "
                         f"La carta tardaría ~<strong>{ARL1_p:.0f} muestras</strong> en detectar el cambio. "
                         f"Se recomienda aumentar n o reducir el intervalo de muestreo.")
            st.markdown(f'<div class="alarm-box {css_i}">{msg_i}</div>', unsafe_allow_html=True)

        except ValueError:
            st.warning("⚠ Valor de μ₁ inválido.")
    else:
        st.markdown(render_alarm("info",
            "👆 Ingresa una <strong>Nueva Media (μ₁)</strong> y pulsa <strong>Calcular Potencia</strong> "
            "para visualizar la gráfica de dos campanas y los indicadores de detección."
        ), unsafe_allow_html=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # BLOQUE B — ARL y ATS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="background:linear-gradient(135deg,#154360,#1B4F72);color:white;
         padding:1.1rem 1.5rem;border-radius:10px;margin-bottom:.8rem;">
    <h3 style="margin:0 0 .25rem;font-size:1.15rem;">📊 ARL y ATS</h3>
    <p style="margin:0;opacity:.85;font-size:.82rem;">
    Calcula el tiempo promedio de alarma (ATS) dado un cambio en la media.</p>
    </div>
    """, unsafe_allow_html=True)

    arl_col1, arl_col2 = st.columns([1, 1])

    with arl_col1:
        _arl_n_txt = st.text_input("Tamaño de muestra (n)", value=str(int(_n)), key="arl_n")
        try: arl_n = max(2, min(1000, int(_arl_n_txt)))
        except: arl_n = int(_n)
        _arl_mu1_txt = st.text_input(
            "Media con cambio (μ₁) en kg",
            value=st.session_state["arl_mu1_val"],
            placeholder=f"Ej: {_mu0 - _sig:.3f}",
            help="Nueva media del proceso después del corrimiento",
            key="arl_mu1_txt"
        )
        st.session_state["arl_mu1_val"] = _arl_mu1_txt

        _arl_alfa_txt = st.text_input("Nivel de significancia (α)", value="0.0027",
                                      key="arl_alfa",
                                      help="0.0027 corresponde a límites 3-sigma")
        try: arl_alfa = max(0.0001, min(0.10, float(_arl_alfa_txt.replace(",", "."))))
        except: arl_alfa = 0.0027

    with arl_col2:
        _arl_h_txt = st.text_input("Tiempo entre muestras",
                                   value=f"{float(freq_min):.1f}", key="arl_h")
        try: arl_h = max(0.1, float(_arl_h_txt.replace(",", ".")))
        except: arl_h = float(freq_min)
        arl_unit = st.selectbox("Unidad de tiempo", ["Minutos", "Horas"],
                                key="arl_unit")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📊 Calcular ARL / ATS", type="primary", key="btn_arl_calcular",
                     width='stretch'):
            if not _arl_mu1_txt.strip():
                st.warning("⚠ Ingresa un valor para μ₁ antes de calcular.")
                st.session_state["arl_calculado"] = False
            else:
                try:
                    float(_arl_mu1_txt.replace(",", "."))
                    st.session_state["arl_calculado"] = True
                except ValueError:
                    st.warning("⚠ Ingresa un número válido para μ₁ (usa punto como decimal).")
                    st.session_state["arl_calculado"] = False

    # ── Resultados ARL/ATS ────────────────────────────────────────────────────
    if st.session_state["arl_calculado"] and st.session_state["arl_mu1_val"].strip():
        try:
            arl_mu1 = float(st.session_state["arl_mu1_val"].replace(",", "."))

            # Para n ≤ 10 usar constantes tabuladas; para n > 10, A2 ≈ 3/√n (aprox. 3-sigma)
            if int(arl_n) <= 10:
                _co_arl  = CONTROL_CONSTANTS[int(arl_n)]
                _UCL_arl = _mu0 + _co_arl["A2"] * s["R_bar"]
                _LCL_arl = _mu0 - _co_arl["A2"] * s["R_bar"]
            else:
                _A2_approx = 3.0 / np.sqrt(arl_n)
                _UCL_arl   = _mu0 + _A2_approx * s["R_bar"]
                _LCL_arl   = _mu0 - _A2_approx * s["R_bar"]
            _se_arl   = _sig / np.sqrt(arl_n)

            z_u_arl   = (_UCL_arl - arl_mu1) / _se_arl
            z_l_arl   = (_LCL_arl - arl_mu1) / _se_arl
            beta_arl  = max(0.0, min(stats.norm.cdf(z_u_arl) - stats.norm.cdf(z_l_arl), 1.0))
            power_arl = 1.0 - beta_arl

            ARL0_arl = 1.0 / max(arl_alfa, 1e-9)
            ARL1_arl = 1.0 / max(power_arl, 1e-9)
            ATS1_arl = ARL1_arl * arl_h
            ATS0_arl = ARL0_arl * arl_h

            unidad_lbl = "min" if arl_unit == "Minutos" else "h"

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(render_section_title("📋 Resultados ARL y ATS"), unsafe_allow_html=True)

            df_arl = pd.DataFrame({
                "Indicador": [
                    "ARL₀  (falsas alarmas — proceso en control)",
                    "ARL₁  (muestras para detectar el cambio)",
                    f"ATS₀  (tiempo entre falsas alarmas)",
                    f"ATS₁  (tiempo para detectar el cambio)",
                    "Potencia (1 − β)",
                    "Error Tipo II (β)",
                ],
                "Fórmula": [
                    "1 / α",
                    "1 / (1 − β)",
                    f"ARL₀ × h",
                    f"ARL₁ × h",
                    "1 − β",
                    "P(LCI < x̄ < LCS | μ₁)",
                ],
                "Valor": [
                    f"{ARL0_arl:.0f} muestras",
                    f"{ARL1_arl:.1f} muestras",
                    f"{ATS0_arl:.1f} {unidad_lbl}",
                    f"{ATS1_arl:.1f} {unidad_lbl}",
                    f"{power_arl:.4f}  ({power_arl:.2%})",
                    f"{beta_arl:.4f}  ({beta_arl:.2%})",
                ],
            })
            st.dataframe(df_arl, hide_index=True,
                         key="df_arl_resultados")

            ka, kb, kc, kd = st.columns(4)
            with ka:
                st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:{CP}">{ARL0_arl:.0f}</div>
                <div class="kpi-label">ARL₀ (muestras)</div>
                <div class="kpi-sub">1/α = 1/{arl_alfa:.4f}</div></div>""",
                unsafe_allow_html=True)

            c_arl1 = CG if ARL1_arl <= 5 else CY if ARL1_arl <= 20 else CR
            b_arl1 = "green" if ARL1_arl <= 5 else "yellow" if ARL1_arl <= 20 else "red"
            with kb:
                st.markdown(f"""<div class="kpi-card {b_arl1}">
                <div class="kpi-value" style="color:{c_arl1}">{ARL1_arl:.1f}</div>
                <div class="kpi-label">ARL₁ (muestras)</div>
                <div class="kpi-sub">1/(1−β) = 1/potencia</div></div>""",
                unsafe_allow_html=True)

            with kc:
                st.markdown(f"""<div class="kpi-card">
                <div class="kpi-value" style="color:{CP}">{ATS0_arl:.1f}</div>
                <div class="kpi-label">ATS₀ ({unidad_lbl})</div>
                <div class="kpi-sub">ARL₀ × h</div></div>""",
                unsafe_allow_html=True)

            c_ats1 = CG if ATS1_arl <= arl_h*5 else CY if ATS1_arl <= arl_h*20 else CR
            b_ats1 = "green" if ATS1_arl <= arl_h*5 else "yellow" if ATS1_arl <= arl_h*20 else "red"
            with kd:
                st.markdown(f"""<div class="kpi-card {b_ats1}">
                <div class="kpi-value" style="color:{c_ats1}">{ATS1_arl:.1f}</div>
                <div class="kpi-label">ATS₁ ({unidad_lbl})</div>
                <div class="kpi-sub">ARL₁ × h</div></div>""",
                unsafe_allow_html=True)

            delta_g2 = (arl_mu1 - _mu0) * 1000
            st.markdown(render_alarm("info",
                f"Con un corrimiento de <strong>{delta_g2:+.1f} g</strong> "
                f"(μ₁ = {arl_mu1:.4f} kg), "
                f"la carta tarda en promedio <strong>{ATS1_arl:.1f} {unidad_lbl}</strong> en dar señal "
                f"(= {ARL1_arl:.1f} muestras × {arl_h:.1f} {unidad_lbl}/muestra). "
                f"El proceso en control genera una falsa alarma cada "
                f"<strong>{ATS0_arl:.0f} {unidad_lbl}</strong>."
            ), unsafe_allow_html=True)

            st.markdown("---")
            # ── Decisiones de Muestreo y Carga Muestral ────────────────
            st.markdown("""
            <div style="background:linear-gradient(135deg,#0B3D0B,#1A6B1A);color:white;
                 padding:1.1rem 1.5rem;border-radius:10px;margin-bottom:.8rem;">
            <h3 style="margin:0 0 .25rem;font-size:1.15rem;">📋 Decisiones de Muestreo y Carga Muestral</h3>
            <p style="margin:0;opacity:.85;font-size:.82rem;">
            Interpretación automática basada en ARL₁, ATS₁ y carga muestral (CM = n / h).</p>
            </div>
            """, unsafe_allow_html=True)

            # ─ Cálculo CM ─────────────────────────────────────────────────
            _cm = arl_n / max(arl_h, 1e-9)  # unidades/tiempo

            # ─ Interpretación ATS/ARL ──────────────────────────────────────────
            _ats_threshold_alto     = arl_h * 20   # ATS alto: tarda más de 20 muestras
            _ats_threshold_moderado = arl_h * 5    # ATS moderado: entre 5 y 20 muestras

            if ATS1_arl > _ats_threshold_alto or ARL1_arl > 20:
                _sens_tipo  = "critical"
                _sens_icono = "⚠️"
                _sens_txt   = ("<strong>Baja sensibilidad para detectar cambios.</strong> "
                               f"ARL₁ = {ARL1_arl:.1f} muestras — "
                               "considera aumentar <em>n</em> o reducir el intervalo <em>h</em>.")
            elif ATS1_arl <= _ats_threshold_moderado and ARL1_arl <= 5:
                _sens_tipo  = "ok"
                _sens_icono = "✅"
                _sens_txt   = ("<strong>Detección rápida de desviaciones.</strong> "
                               f"ARL₁ = {ARL1_arl:.1f} muestras — "
                               "el plan de muestreo es muy sensible al corrimiento evaluado.")
            else:
                _sens_tipo  = "warn"
                _sens_icono = "🟡"
                _sens_txt   = ("<strong>Velocidad de detección aceptable.</strong> "
                               f"ARL₁ = {ARL1_arl:.1f} muestras — "
                               "el plan es funcional; puede optimizarse según el costo.")

            # ─ Interpretación CM ──────────────────────────────────────────────────
            if _cm > 2.0:
                _cm_tipo = "warn"
                _cm_txt  = (f"<strong>Carga muestral elevada</strong> (CM = {_cm:.2f} unidades/{unidad_lbl}). "
                             "Esto implica mayor costo operativo de inspección.")
            elif _cm >= 0.5:
                _cm_tipo = "ok"
                _cm_txt  = (f"<strong>Carga muestral balanceada</strong> (CM = {_cm:.2f} unidades/{unidad_lbl}). "
                             "Buena relación entre sensibilidad y costo de muestreo.")
            else:
                _cm_tipo = "info"
                _cm_txt  = (f"<strong>Carga muestral baja</strong> (CM = {_cm:.2f} unidades/{unidad_lbl}). "
                             "Posible menor sensibilidad ante corrimientos pequeños.")

            # ─ Layout KPIs + alarmas ─────────────────────────────────────────────
            _dm_c1, _dm_c2 = st.columns(2)
            with _dm_c1:
                st.markdown(render_section_title("🎯 Sensibilidad del Plan"), unsafe_allow_html=True)
                st.markdown(render_alarm(_sens_tipo, f"{_sens_icono} {_sens_txt}"), unsafe_allow_html=True)
            with _dm_c2:
                st.markdown(render_section_title("🔢 Carga Muestral (CM = n / h)"), unsafe_allow_html=True)
                st.markdown(render_alarm(_cm_tipo, _cm_txt), unsafe_allow_html=True)

            # ─ Tabla resumen ──────────────────────────────────────────────────────
            st.markdown(render_section_title("📊 Resumen de Decisiones"), unsafe_allow_html=True)
            _dm_df = pd.DataFrame({
                "Parámetro":   ["n (muestra)", "h (intervalo)", "CM = n/h",
                               "ARL₀ (control)", "ARL₁ (cambio)",
                               "ATS₀", "ATS₁"],
                "Fórmula":    ["configurado", "configurado", "n / h",
                               "1 / α", "1 / (1 − β)",
                               "ARL₀ × h", "ARL₁ × h"],
                "Valor":       [str(int(arl_n)), f"{arl_h:.1f} {unidad_lbl}",
                               f"{_cm:.3f} u/{unidad_lbl}",
                               f"{ARL0_arl:.0f} muestras", f"{ARL1_arl:.1f} muestras",
                               f"{ATS0_arl:.1f} {unidad_lbl}", f"{ATS1_arl:.1f} {unidad_lbl}"],
            })
            st.dataframe(_dm_df, use_container_width=True, hide_index=True,
                         key="df_decisiones_muestreo")

        except ValueError:
            st.warning("⚠ Valor de μ₁ inválido.")
    else:
        st.markdown(render_alarm("info",
            "👆 Ingresa una <strong>Media con cambio (μ₁)</strong> y pulsa "
            "<strong>Calcular ARL / ATS</strong> para obtener los resultados."
        ), unsafe_allow_html=True)


def page_monitoreo():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed

    import hashlib

    # ── Límites fijos desde Fase I ────────────────────────────────────────────
    UCL_fijo  = s["UCL_x"];    LCL_fijo  = s["LCL_x"]
    CL_fijo   = s["xbar_bar"]; UCLr_fijo = s["UCL_r"]
    LCLr_fijo = s["LCL_r"];   CLr_fijo  = s["R_bar"]
    sig_fijo  = s["sigma_st"]; n_fijo    = s["n"]

    # ── Inicializar session_state con arquitectura multi-bloque ──────────────
    def _make_bloque(n_muestra, n_sg=5):
        """Crea un bloque de monitoreo vacío con su propio tamaño de muestra."""
        xcols = [f"X{i+1}" for i in range(n_muestra)]
        data  = {"Subgrupo": list(range(1, n_sg + 1)), "Hora": [""]*n_sg}
        for xc in xcols:
            data[xc] = [float("nan")]*n_sg
        st.session_state["mon_bloque_counter"] = (
            st.session_state.get("mon_bloque_counter", 0) + 1
        )
        return {
            "bid":         st.session_state["mon_bloque_counter"],
            "n":           n_muestra,
            "n_sg":        n_sg,
            "df":          pd.DataFrame(data),
            "hash":        "",
            "new_signals":   [],
            "new_r_signals": [],
            "idx_new":     [],
            "df_nuevos":   None,
            "n_new":       0,
            "n_hist":      0,
        }

    st.session_state.setdefault("mon_bloque_counter", 0)

    if "mon_n_fijo" not in st.session_state:
        st.session_state["mon_n_fijo"] = n_fijo

    if st.session_state.get("mon_n_fijo") != n_fijo:
        # Archivo recargado con distinto n → resetear todo
        st.session_state["mon_bloques"]       = []
        st.session_state["mon_bloque_activo"] = 0
        st.session_state["mon_n_fijo"]        = n_fijo

    if "mon_bloques" not in st.session_state:
        st.session_state["mon_bloques"]       = []
        st.session_state["mon_bloque_activo"] = 0

    # Compatibilidad: si viene de versión anterior con mon_df suelto, migrar
    if "mon_df" in st.session_state and len(st.session_state.get("mon_bloques", [])) == 0:
        st.session_state["mon_bloques"]       = []
        st.session_state["mon_bloque_activo"] = 0

    # ── Si aún no hay bloques, mostrar controles de creación inicial ──────────
    if len(st.session_state["mon_bloques"]) == 0:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1A3F5C 0%,#0F2A40 100%);
             color:white;padding:1.1rem 1.5rem 1rem;border-radius:12px;
             border-bottom:3px solid #2563A8;
             box-shadow:0 4px 16px rgba(26,63,92,.18);margin-bottom:.75rem;">
          <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.3rem">
            <span style="font-size:1.25rem;line-height:1">🔴</span>
            <span style="font-size:1.05rem;font-weight:700;letter-spacing:-.3px;line-height:1.2">
              Monitoreo en Tiempo Real — Fase II
            </span>
          </div>
          <p style="margin:0;opacity:.72;font-size:.78rem;padding-left:2rem;line-height:1.45">
            Configura el tamaño del bloque inicial y pulsa
            <strong style="color:#D6E8F7">Crear bloque inicial</strong> para comenzar.
          </p>
        </div>
        """, unsafe_allow_html=True)
        _ci1, _ci2, _ci3 = st.columns([1, 1, 1])
        with _ci1:
            _init_sg = st.number_input("Filas (subgrupos)", min_value=2, max_value=50,
                                       value=5, key="mon_init_n_sg")
        with _ci2:
            _init_n = st.number_input("Columnas n (tamaño muestra)", min_value=2, max_value=1000,
                                      value=int(n_fijo), key="mon_init_n_n")
        with _ci3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Crear bloque inicial", type="primary", key="btn_crear_bloque_inicial"):
                st.session_state["mon_bloques"]       = [_make_bloque(int(_init_n), int(_init_sg))]
                st.session_state["mon_bloque_activo"] = 0
                st.rerun()
        return   # No renderizar nada más hasta que exista un bloque

    # Referencia corta al bloque activo
    _bi = st.session_state["mon_bloque_activo"]
    _bloques = st.session_state["mon_bloques"]

    # Migración: asignar bid a bloques creados antes de esta versión
    for _mbk in _bloques:
        if "bid" not in _mbk:
            st.session_state["mon_bloque_counter"] += 1
            _mbk["bid"] = st.session_state["mon_bloque_counter"]

    # x_cols_mon → columnas del bloque activo
    x_cols_mon = [f"X{i+1}" for i in range(_bloques[_bi]["n"])]

    # ══════════════════════════════════════════════════════════════════════════
    # ENCABEZADO OPERATIVO — Bloque 1
    # ══════════════════════════════════════════════════════════════════════════

    # Inicializar metadatos del turno (claves únicas, sin colisión con estado CEP)
    from datetime import date as _date
    st.session_state.setdefault("mon_meta_operador", "")
    st.session_state.setdefault("mon_meta_turno",    "Mañana")
    st.session_state.setdefault("mon_meta_fecha",    _date.today())
    st.session_state.setdefault("mon_meta_lote",     "")
    st.session_state.setdefault("mon_meta_obs",      "")

    with st.container():
        # ── Banner superior ────────────────────────────────────────────────────
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1A3F5C 0%,#0F2A40 100%);
             color:white;padding:1.1rem 1.5rem 1rem;border-radius:12px;
             border-bottom:3px solid #2563A8;
             box-shadow:0 4px 16px rgba(26,63,92,.18);margin-bottom:.75rem;">
          <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.3rem">
            <span style="font-size:1.25rem;line-height:1">🔴</span>
            <span style="font-size:1.05rem;font-weight:700;
                  letter-spacing:-.3px;line-height:1.2">
              Monitoreo en Tiempo Real — Fase II
            </span>
          </div>
          <p style="margin:0;opacity:.72;font-size:.78rem;padding-left:2rem;
               line-height:1.45">
            Límites de control <strong style="color:#D6E8F7">fijos</strong>
            desde la Fase I de estabilización.
            Ingresa los nuevos subgrupos y el sistema detectará
            automáticamente si el proceso sale de control estadístico.
          </p>
        </div>
        """, unsafe_allow_html=True)

        # ── Formulario operativo ───────────────────────────────────────────────
        st.markdown("""
        <div style="background:#EEF3F8;border:1px solid #D6E8F7;
             border-left:4px solid #2563A8;border-radius:8px;
             padding:.55rem 1rem .3rem;margin-bottom:.5rem;">
          <span style="font-size:.66rem;font-weight:700;color:#2563A8;
               text-transform:uppercase;letter-spacing:.85px;">
            📋 Datos del turno de muestreo
          </span>
        </div>
        """, unsafe_allow_html=True)

        with st.form("_form_meta_turno", border=False):
            _mc1, _mc2, _mc3, _mc4 = st.columns([2.2, 1.2, 1.2, 1.8])
            with _mc1:
                st.text_input(
                    "👤 Operador / Responsable",
                    placeholder="Nombre del operador...",
                    key="mon_meta_operador",
                )
            with _mc2:
                st.selectbox(
                    "🕐 Turno",
                    options=["Mañana", "Tarde", "Noche"],
                    key="mon_meta_turno",
                )
            with _mc3:
                st.date_input(
                    "📅 Fecha",
                    key="mon_meta_fecha",
                )
            with _mc4:
                st.text_input(
                    "🏷️ Línea / Lote",
                    placeholder="Ej: L-042 / Lote 2025-05",
                    key="mon_meta_lote",
                )
            st.form_submit_button("✓ Confirmar turno")

        with st.expander("💬 Observaciones del turno (opcional)"):
            st.text_area(
                "Observaciones",
                placeholder="Novedades del turno, incidentes, cambios de operario...",
                height=72,
                label_visibility="collapsed",
                key="mon_meta_obs",
            )

    # ── Separador ──────────────────────────────────────────────────────────────
    st.markdown(
        "<hr style='border:none;border-top:1px solid #E2E8EE;margin:.5rem 0 .6rem'>",
        unsafe_allow_html=True,
    )

    # ── Límites de control ────────────────────────────────────────────────────
    with st.container():
        st.markdown("""
        <div style="background:#EEF6FD;border:1px solid #BDD7EE;
             border-left:4px solid #2563A8;border-radius:8px;
             padding:.7rem 1.1rem .5rem;margin-bottom:.6rem;">
          <span style="font-size:.66rem;font-weight:700;color:#2563A8;
               text-transform:uppercase;letter-spacing:.85px;">
            🔒 Límites de Control — Fase I (Referencia) · Bloques Fase II calculan sus propios límites
          </span>
        </div>
        """, unsafe_allow_html=True)
        lf1, lf2, lf3, lf4, lf5, lf6 = st.columns(6)
        for col, lbl, val in [
            (lf1, "LCS X̄ (Fase I)",  f"{UCL_fijo:.4f} kg"),
            (lf2, "LC X̄ (Fase I)",   f"{CL_fijo:.4f} kg"),
            (lf3, "LCI X̄ (Fase I)",  f"{LCL_fijo:.4f} kg"),
            (lf4, "LCS R (Fase I)",   f"{UCLr_fijo:.4f} kg"),
            (lf5, "R̄ (Fase I)",      f"{CLr_fijo:.4f} kg"),
            (lf6, "n (Fase I)",       str(n_fijo)),
        ]:
            with col:
                st.metric(lbl, val)

    st.divider()
    st.markdown(
        render_section_title("📝 Ingreso de Nuevos Subgrupos (Fase II — Monitoreo)"),
        unsafe_allow_html=True,
    )

    # ══ SELECTOR DE BLOQUE ACTIVO (solo si hay más de uno) ═══════════════════
    _bloque_actual = _bloques[_bi]
    if len(_bloques) > 1:
        _info_bloques = " · ".join(
            [f"Bloque {i+1}: n={b['n']}, {b['n_sg']} subgr."
             for i, b in enumerate(_bloques)]
        )
        st.markdown(
            f"<div style='background:#EEF6FD;border:1px solid #BDD7EE;"
            f"border-left:4px solid #2563A8;border-radius:8px;"
            f"padding:.5rem 1rem;margin-bottom:.5rem;font-size:.82rem;'>"
            f"📦 <strong>Bloques registrados:</strong> {_info_bloques}</div>",
            unsafe_allow_html=True
        )
        _opciones_bloque = [f"Bloque {i+1} (n={b['n']}, {b['n_sg']} subgr.)"
                            for i, b in enumerate(_bloques)]
        _bi_sel = st.selectbox(
            "✏️ Editar bloque:",
            options=list(range(len(_bloques))),
            format_func=lambda i: _opciones_bloque[i],
            index=_bi,
            key="mon_bloque_selector"
        )
        if _bi_sel != _bi:
            st.session_state["mon_bloque_activo"] = _bi_sel
            st.rerun()
        _bi = _bi_sel
        _bloque_actual = _bloques[_bi]

    # x_cols_mon → fijas del bloque activo, inmutables
    x_cols_mon = [f"X{i+1}" for i in range(_bloque_actual["n"])]
    _estructura_cambio = False   # bloques son inmutables en estructura

    # ══ MODO DUAL DE ENTRADA ═════════════════════════════════════════════════
    _tab_manual, _tab_excel = st.tabs(["✏️ Ingreso Manual", "📂 Cargar Excel"])

    with _tab_manual:
        with st.container():
            # KEY DINÁMICA: usa bid (identidad persistente) para evitar colisión entre bloques
            _mon_editor_key = f"mon_editor_b{_bloque_actual['bid']}_{_bloque_actual['n']}_{_bloque_actual['n_sg']}"

            _df_para_editor = _bloque_actual["df"]

            st.markdown(f"**Anota los pesos nuevos (kg) — Bloque {_bi+1} · n={_bloque_actual['n']}:**")
            mon_edited = st.data_editor(
                _df_para_editor,
                width='stretch',
                num_rows="fixed",
                column_config={
                    "Subgrupo": st.column_config.NumberColumn("Subgrupo", disabled=True),
                    "Hora":     st.column_config.TextColumn("Hora"),
                    **{xc: st.column_config.NumberColumn(
                        xc, format="%.4f", step=0.001)
                       for xc in x_cols_mon}
                },
                key=_mon_editor_key
            )
            st.session_state[f"_mon_data_{_bloque_actual['bid']}"] = mon_edited

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                if st.button("🗑 Limpiar tabla", type="secondary", key="btn_limpiar_mon"):
                    empty_mon = {"Subgrupo": list(range(1, _bloque_actual["n_sg"]+1)),
                                 "Hora":     [""]*_bloque_actual["n_sg"]}
                    for xc in x_cols_mon:
                        empty_mon[xc] = [float("nan")]*_bloque_actual["n_sg"]
                    _df_vacio = pd.DataFrame(empty_mon)
                    _bloque_actual["df"]   = _df_vacio
                    _bloque_actual["hash"] = ""
                    st.session_state["mon_bloques"][_bi]["df"]   = _df_vacio
                    st.session_state["mon_bloques"][_bi]["hash"] = ""
                    st.session_state.pop(f"_mon_data_{_bloque_actual['bid']}", None)
                    if _mon_editor_key in st.session_state:
                        del st.session_state[_mon_editor_key]
                    st.rerun()

            with btn_col2:
                _df_export = mon_edited.copy()
                _xm_export = [c for c in _df_export.columns
                              if str(c).strip().upper().startswith("X")
                              and str(c).strip()[1:].isdigit()]
                if _xm_export:
                    _df_num = _df_export[_xm_export].apply(pd.to_numeric, errors="coerce")
                    _filas_ok = _df_num.dropna(how="any").index
                    if len(_filas_ok) > 0:
                        _df_export.loc[_filas_ok, "xbar"] = _df_num.loc[_filas_ok].mean(axis=1)
                        _df_export.loc[_filas_ok, "R"]    = (_df_num.loc[_filas_ok].max(axis=1)
                                                              - _df_num.loc[_filas_ok].min(axis=1))
                _buf_export = io.BytesIO()
                _df_export.to_excel(_buf_export, index=False, engine="openpyxl")
                st.download_button(
                    label="💾 Descargar datos de monitoreo",
                    data=_buf_export.getvalue(),
                    file_name=f"monitoreo_bloque{_bi+1}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_download_mon"
                )

    with _tab_excel:
        with st.container():
            _mon_xl_file = st.file_uploader(
                "Sube un archivo Excel con columnas numéricas",
                type=["xlsx", "xls"],
                key="mon_excel_uploader"
            )
            if _mon_xl_file is not None:
                try:
                    _mon_xl_raw = pd.read_excel(_mon_xl_file)
                    # Detectar columnas numéricas y eliminar vacías
                    _mon_num_cols = []
                    for _c in _mon_xl_raw.columns:
                        _series = pd.to_numeric(_mon_xl_raw[_c], errors="coerce")
                        if _series.notna().sum() > 0:
                            _mon_xl_raw[_c] = _series
                            _mon_num_cols.append(_c)
                    _mon_xl_clean = _mon_xl_raw[_mon_num_cols].dropna(axis=1, how="all")
                    # Convertir a float
                    _mon_xl_clean = _mon_xl_clean.apply(pd.to_numeric, errors="coerce")

                    # Validar mínimos
                    if len(_mon_xl_clean) < 2:
                        st.warning("⚠ Se necesitan al menos 2 filas con datos numéricos.")
                    elif len(_mon_num_cols) < 2:
                        st.warning("⚠ Se necesitan al menos 2 columnas numéricas.")
                    else:
                        _prev_n = min(10, len(_mon_xl_clean))
                        st.markdown(
                            f"**Vista previa** — {len(_mon_xl_clean)} filas × "
                            f"{len(_mon_num_cols)} columnas numéricas"
                            + (f" &nbsp;·&nbsp; <span style='color:#888;font-size:.82rem'>"
                               f"Mostrando primeras {_prev_n} filas para vista previa.</span>"
                               if len(_mon_xl_clean) > 10 else ""),
                            unsafe_allow_html=True,
                        )
                        st.dataframe(
                            _mon_xl_clean.head(_prev_n),
                            use_container_width=True,
                            height=min(350, 38 + _prev_n * 35),
                            key="mon_excel_preview",
                        )

                        if st.button("✅ Usar estos datos", key="btn_mon_usar_excel"):
                            _bloque_actual["df"]   = _mon_xl_clean.reset_index(drop=True)
                            _bloque_actual["hash"] = ""
                            st.session_state.pop(f"_mon_data_{_bloque_actual['bid']}", None)
                            st.session_state.pop(_mon_editor_key, None)
                except Exception as _xl_err:
                    st.error("❌ No se pudo leer el archivo. Verifica que contenga datos numéricos válidos.")
                    with st.expander("Ver detalle técnico"):
                        st.code(str(_xl_err))

    # ══ FORMULARIO NUEVO BLOQUE (debajo de la tabla del bloque activo) ════════
    st.divider()
    st.markdown(
        render_section_title("➕ Agregar Nuevo Bloque de Monitoreo"),
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='background:#EEF6FD;border:1px solid #BDD7EE;"
        "border-left:4px solid #2563A8;border-radius:8px;"
        "padding:.5rem 1rem;margin-bottom:.6rem;font-size:.82rem;'>"
        "Define la estructura del <strong>nuevo bloque</strong>. "
        "Los bloques existentes no se modifican.</div>",
        unsafe_allow_html=True
    )
    # Inicializar valores del formulario de nuevo bloque (desacoplados de cualquier bloque)
    st.session_state.setdefault("mon_new_rows", 5)
    st.session_state.setdefault("mon_new_n",    int(n_fijo))

    _nb_a, _nb_b, _nb_c, _nb_d = st.columns([1, 1, 1, 1])
    with _nb_a:
        _new_rows = st.number_input(
            "Nº de subgrupos (filas)",
            min_value=2, max_value=50,
            value=st.session_state["mon_new_rows"],
            key="mon_new_rows",
        )
    with _nb_b:
        _new_n = st.number_input(
            "Tamaño de muestra n (columnas X)",
            min_value=2, max_value=1000,
            value=st.session_state["mon_new_n"],
            key="mon_new_n",
        )
    with _nb_c:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Crear nuevo bloque", type="primary", key="btn_nuevo_bloque"):
            _bloques.append(_make_bloque(int(_new_n), int(_new_rows)))
            st.session_state["mon_bloques"]       = _bloques
            st.session_state["mon_bloque_activo"] = len(_bloques) - 1
            st.rerun()
    with _nb_d:
        st.markdown("<br>", unsafe_allow_html=True)
        _puede_eliminar = len(_bloques) > 1
        if st.button(
            f"🗑 Eliminar Bloque {_bi+1}",
            key="btn_eliminar_bloque",
            type="secondary",
            disabled=not _puede_eliminar,
            help=("Elimina el bloque activo" if _puede_eliminar
                  else "No se puede eliminar el único bloque existente"),
        ):
            _del_bid        = _bloques[_bi]["bid"]
            _del_editor_key = f"mon_editor_b{_del_bid}_{_bloques[_bi]['n']}_{_bloques[_bi]['n_sg']}"
            _bloques.pop(_bi)
            new_bi = min(_bi, len(_bloques) - 1)
            st.session_state["mon_bloques"]       = _bloques
            st.session_state["mon_bloque_activo"] = new_bi
            st.session_state.pop(f"_mon_data_{_del_bid}", None)
            st.session_state.pop(_del_editor_key, None)
            st.session_state.pop("mon_hash_global", None)
            st.rerun()

    # ══ BLOQUE 3 — PROCESAMIENTO (multi-bloque) ═══════════════════════════════
    # Procesar TODOS los bloques para concatenar en los gráficos.
    # Cada bloque tiene su propio n y columnas X; se calcula xbar/R independientemente.
    _cualquier_dato = False

    for _bk_idx, _bk in enumerate(_bloques):
        _bk_xcols = [f"X{i+1}" for i in range(_bk["n"])]
        _bk_raw   = st.session_state.get(f"_mon_data_{_bk['bid']}", _bk["df"]).copy()
        _bk_raw[_bk_xcols] = _bk_raw[[c for c in _bk_xcols if c in _bk_raw.columns]].apply(
            pd.to_numeric, errors="coerce"
        )
        _bk_cols_ok  = [c for c in _bk_xcols if c in _bk_raw.columns]
        _bk_n_valids = _bk_raw[_bk_cols_ok].notna().sum(axis=1)
        _bk_filas    = _bk_raw[_bk_n_valids >= 2].index
        if len(_bk_filas) >= 2:
            _bk_clean = _bk_raw.loc[_bk_filas].reset_index(drop=True)
            _bk_num   = _bk_clean[_bk_cols_ok].apply(pd.to_numeric, errors="coerce")
            _bk_clean["xbar"] = _bk_num.mean(axis=1, skipna=True)
            _bk_clean["R"]    = _bk_num.max(axis=1, skipna=True) - _bk_num.min(axis=1, skipna=True)
            _bk["_df_proc"] = _bk_clean   # resultado temporal para este render
            _cualquier_dato = True
        else:
            _bk["_df_proc"] = None

    # Avisar si el bloque activo aún no tiene suficientes datos
    if not _estructura_cambio and not _cualquier_dato:
        st.warning("⚠ Se requieren al menos 2 subgrupos con datos para graficar. "
                   "Completa más filas en la tabla.")

    # ── HASH Y FIGURAS PERSISTENTES (concatena todos los bloques) ────────────
    # Construir hash global sobre todos los bloques con datos
    _global_hash_src = "".join(
        bk["_df_proc"].to_csv(index=False)
        for bk in _bloques if bk.get("_df_proc") is not None
    )

    if not _estructura_cambio and _cualquier_dato:
        nuevo_hash = hashlib.md5(_global_hash_src.encode()).hexdigest()

        # Hash global sobre todos los bloques: reconstruir figuras si cambia cualquier bloque
        if nuevo_hash != st.session_state.get("mon_hash_global", ""):
            st.session_state["mon_hash_global"] = nuevo_hash

            n_hist   = len(s["df"]); df_hist = s["df"].copy()
            idx_hist = list(range(1, n_hist+1))

            # ── Acumular subgrupos nuevos de todos los bloques, con límites por bloque ──
            _all_xbar    = []
            _all_R       = []
            _all_idx_new = []
            _cursor      = n_hist + 1
            _bloque_boundaries = []   # (start_idx, end_idx, bloque_num, UCL_bk, LCL_bk, CL_bk, UCLr_bk, LCLr_bk, CLr_bk, n_bk)

            for _bk_idx, _bk in enumerate(_bloques):
                _bk_proc = _bk.get("_df_proc")
                if _bk_proc is None:
                    continue
                _bk_n    = int(_bk["n"])
                _bk_len  = len(_bk_proc)
                _bk_idx_new = list(range(_cursor, _cursor + _bk_len))

                # ── Límites derivados de Fase I ajustados al n de este bloque ──
                # UCL/LCL se fijan desde σ̂ Fase I; no se recalculan desde datos Fase II.
                # Para n_bk == n_fijo colapsa exactamente a UCL_fijo / LCL_fijo.
                _bk_xbar_list = list(_bk_proc["xbar"])
                _bk_R_list    = list(_bk_proc["R"])
                _bk_cc        = CONTROL_CONSTANTS.get(_bk_n, CONTROL_CONSTANTS[min(CONTROL_CONSTANTS.keys(), key=lambda k: abs(k-_bk_n))])
                _bk_R_ref     = sig_fijo * _bk_cc["d2"]   # R̄ esperado para n_bk desde σ̂ Fase I
                _bk_UCL       = CL_fijo + _bk_cc["A2"] * _bk_R_ref
                _bk_LCL       = CL_fijo - _bk_cc["A2"] * _bk_R_ref
                _bk_UCLr      = _bk_cc["D4"] * _bk_R_ref
                _bk_LCLr      = _bk_cc["D3"] * _bk_R_ref

                _all_xbar    += _bk_xbar_list
                _all_R       += _bk_R_list
                _all_idx_new += _bk_idx_new
                _bloque_boundaries.append((
                    _cursor, _cursor + _bk_len - 1, _bk_idx + 1,
                    _bk_UCL, _bk_LCL, CL_fijo,
                    _bk_UCLr, _bk_LCLr, _bk_R_ref, _bk_n
                ))
                _cursor += _bk_len

            n_new   = len(_all_xbar)
            idx_new = _all_idx_new

            # ── Señales usando límites propios de cada bloque ──────────────────
            new_signals   = []
            new_r_signals = []
            _all_UCL_seq  = []   # UCL correspondiente a cada punto nuevo (para Y-range)
            _all_LCL_seq  = []
            _offset = 0
            for _bnd in _bloque_boundaries:
                _bnd_start, _bnd_end, _bnd_num, _bk_UCL, _bk_LCL, _bk_CL, _bk_UCLr, _bk_LCLr, _bk_CLr, _bk_n = _bnd
                _bk_len = _bnd_end - _bnd_start + 1
                for _li in range(_bk_len):
                    _gi = _offset + _li
                    if _gi < len(_all_xbar) and (_all_xbar[_gi] > _bk_UCL or _all_xbar[_gi] < _bk_LCL):
                        new_signals.append(_gi)
                    if _gi < len(_all_R) and _all_R[_gi] > _bk_UCLr:
                        new_r_signals.append(_gi)
                    _all_UCL_seq.append(_bk_UCL)
                    _all_LCL_seq.append(_bk_LCL)
                _offset += _bk_len

            _C_NEW     = "#E67E22"   # naranja — puntos Fase II
            _LC_COLOR  = "#1B4F72"   # azul profundo — LC histórico
            _LIM_COLOR = "#C0392B"   # rojo contenido — límites / señales
            _C_GREEN   = "#1E8449"   # verde — carta R

            new_signals_set   = set(new_signals)
            new_r_signals_set = set(new_r_signals)
            new_colors   = [_LIM_COLOR if i in new_signals_set   else _C_NEW for i in range(n_new)]
            new_r_colors = [_LIM_COLOR if i in new_r_signals_set else _C_NEW for i in range(n_new)]

            # ════════════════════════════════════════════════════════════════════
            # CARTA X̄  — una sola figura continua, límites segmentados por bloque
            # ════════════════════════════════════════════════════════════════════
            fig_mon = go.Figure()

            # Fondo histórico: bandas suaves usando límites Fase I
            for y0, y1, col_bg in [
                (LCL_fijo, CL_fijo - (CL_fijo-LCL_fijo)*2/3, "rgba(44,62,80,.035)"),
                (CL_fijo + (UCL_fijo-CL_fijo)*2/3, UCL_fijo,  "rgba(44,62,80,.035)"),
                (CL_fijo - (CL_fijo-LCL_fijo)/3,   CL_fijo + (UCL_fijo-CL_fijo)/3, "rgba(37,99,168,.04)"),
            ]:
                fig_mon.add_hrect(y0=y0, y1=y1, x0=0, x1=n_hist+0.5,
                                  fillcolor=col_bg, line_width=0)

            # Líneas de control Fase I (solo sobre el segmento histórico)
            for y, lbl, col_ln, dash, lw in [
                (UCL_fijo, f"LCS₀={UCL_fijo:.3f}",  _LIM_COLOR, "dash",  1.8),
                (CL_fijo,  f"LC₀={CL_fijo:.3f}",    _LC_COLOR,  "solid", 1.8),
                (LCL_fijo, f"LCI₀={LCL_fijo:.3f}",  _LIM_COLOR, "dash",  1.8),
            ]:
                fig_mon.add_shape(type="line",
                    x0=0.5, x1=n_hist+0.5, y0=y, y1=y,
                    line=dict(color=col_ln, dash=dash, width=lw))
                fig_mon.add_annotation(
                    x=n_hist+0.5, y=y, text=f" {lbl}", showarrow=False,
                    xanchor="left", font=dict(size=9, color=col_ln),
                    bgcolor="rgba(255,255,255,.7)")

            # Separador Fase I → Fase II
            fig_mon.add_vline(x=n_hist+0.5, line_dash="dot", line_color="#7F8C8D",
                              line_width=1.4, annotation_text="▶ Fase II",
                              annotation_font_size=9, annotation_font_color="#5D6D7E",
                              annotation_bgcolor="rgba(255,255,255,.8)")

            # Líneas de control y separadores por bloque Fase II
            _prev_right = n_hist + 0.5
            for _bnd in _bloque_boundaries:
                _bnd_start, _bnd_end, _bnd_num, _bk_UCL, _bk_LCL, _bk_CL, _bk_UCLr, _bk_LCLr, _bk_CLr, _bk_n = _bnd
                _seg_x0 = _prev_right
                _seg_x1 = _bnd_end + 0.5
                # Fondo suave para este bloque
                fig_mon.add_hrect(y0=_bk_LCL, y1=_bk_CL - (_bk_CL-_bk_LCL)*2/3,
                                  x0=_seg_x0, x1=_seg_x1,
                                  fillcolor="rgba(231,76,60,.04)", line_width=0)
                fig_mon.add_hrect(y0=_bk_CL + (_bk_UCL-_bk_CL)*2/3, y1=_bk_UCL,
                                  x0=_seg_x0, x1=_seg_x1,
                                  fillcolor="rgba(231,76,60,.04)", line_width=0)
                fig_mon.add_hrect(y0=_bk_CL - (_bk_CL-_bk_LCL)/3,
                                  y1=_bk_CL + (_bk_UCL-_bk_CL)/3,
                                  x0=_seg_x0, x1=_seg_x1,
                                  fillcolor="rgba(37,99,168,.04)", line_width=0)
                # Líneas de control del bloque
                for y, lbl, col_ln, dash, lw in [
                    (_bk_UCL, f"LCS{_bnd_num}={_bk_UCL:.3f} (n={_bk_n})", _LIM_COLOR, "dash",  1.8),
                    (_bk_CL,  f"LC{_bnd_num}={_bk_CL:.3f}",               "#2563A8",  "solid", 1.8),
                    (_bk_LCL, f"LCI{_bnd_num}={_bk_LCL:.3f}",             _LIM_COLOR, "dash",  1.8),
                ]:
                    fig_mon.add_shape(type="line",
                        x0=_seg_x0, x1=_seg_x1, y0=y, y1=y,
                        line=dict(color=col_ln, dash=dash, width=lw))
                    fig_mon.add_annotation(
                        x=_seg_x1, y=y, text=f" {lbl}", showarrow=False,
                        xanchor="left", font=dict(size=9, color=col_ln),
                        bgcolor="rgba(255,255,255,.7)")
                # Separador entre bloques Fase II (excepto el primero)
                if _bnd_num > 1:
                    fig_mon.add_vline(x=_seg_x0, line_dash="dot",
                                      line_color="#8E44AD", line_width=1.2,
                                      annotation_text=f"B{_bnd_num} n={_bk_n}",
                                      annotation_font_size=9, annotation_font_color="#8E44AD",
                                      annotation_bgcolor="rgba(255,255,255,.7)")
                _prev_right = _seg_x1

            # Serie histórica
            hist_colors_mon = [_LIM_COLOR if ix in set(s["signals_x"]) else _LC_COLOR
                               for ix in df_hist.index]
            fig_mon.add_trace(go.Scatter(
                x=idx_hist, y=df_hist["xbar"], mode="lines+markers", name="Histórico (Fase I)",
                line=dict(color=_LC_COLOR, width=1.5),
                marker=dict(color=hist_colors_mon, size=7, opacity=0.75,
                            line=dict(color="white", width=1.2), symbol="circle"),
                hovertemplate=(
                    "<b>Subgrupo %{x}</b><br>"
                    "x̄ = %{y:.4f} kg<br>"
                    "<span style='color:#7F8C8D'>Fase I — Histórico</span>"
                    "<extra></extra>"
                )
            ))
            # Serie Fase II
            fig_mon.add_trace(go.Scatter(
                x=idx_new, y=_all_xbar, mode="lines+markers", name="Nuevos (Fase II)",
                line=dict(color=_C_NEW, width=2.2),
                marker=dict(color=new_colors, size=10,
                            line=dict(color="white", width=1.8), symbol="circle"),
                hovertemplate=(
                    "<b>Subgrupo %{x}</b><br>"
                    "x̄ = %{y:.4f} kg<br>"
                    "<span style='color:#E67E22'>Fase II — Nuevo</span>"
                    "<extra></extra>"
                )
            ))
            # Señales fuera de control — marcador X grande y visible
            if new_signals:
                si_new = [idx_new[i] for i in new_signals]
                sv_new = [_all_xbar[i] for i in new_signals]
                fig_mon.add_trace(go.Scatter(
                    x=si_new, y=sv_new, mode="markers", name="🚨 SEÑAL X̄",
                    marker=dict(color=_LIM_COLOR, size=20, symbol="x-open",
                                line=dict(color=_LIM_COLOR, width=3.5)),
                    hovertemplate=(
                        "<b>⚠ FUERA DE CONTROL</b><br>"
                        "Subgrupo %{x}<br>"
                        "x̄ = %{y:.4f} kg"
                        "<extra>🚨 Señal</extra>"
                    )
                ))

            # Rango Y: cubre todos los límites activos con 12 % padding
            _all_ys = ([UCL_fijo, LCL_fijo] +
                       [_bnd[3] for _bnd in _bloque_boundaries] +
                       [_bnd[4] for _bnd in _bloque_boundaries] +
                       list(_all_xbar) + list(df_hist["xbar"]))
            _rng_pad = (max(_all_ys) - min(_all_ys)) * 0.12 or 0.05
            _y_lo    = min(_all_ys) - _rng_pad
            _y_hi    = max(_all_ys) + _rng_pad

            fig_mon.update_layout(
                template="plotly_white", height=420,
                plot_bgcolor="white", paper_bgcolor="white",
                title=dict(
                    text=(f"Carta X̄ de Monitoreo — {n_hist} históricos + {n_new} nuevos"
                          f"{'  |  🚨 ' + str(len(new_signals)) + ' señal(es)' if new_signals else '  |  ✅ Proceso estable'}"),
                    font=dict(size=13, color=_LIM_COLOR if new_signals else _LC_COLOR,
                              family="DM Sans, sans-serif"),
                    x=0, xanchor="left", pad=dict(l=4)
                ),
                xaxis=dict(
                    title=dict(text="Número de Subgrupo", font=dict(size=11)),
                    tickmode="linear", tickfont=dict(size=10),
                    range=[0, n_hist+n_new+2],
                    gridcolor="#EEF3F8", gridwidth=1, zeroline=False,
                    linecolor="#DDE5ED", linewidth=1,
                ),
                yaxis=dict(
                    title=dict(text="Peso promedio x̄ (kg)", font=dict(size=11)),
                    tickfont=dict(size=10), tickformat=".4f",
                    range=[_y_lo, _y_hi],
                    gridcolor="#EEF3F8", gridwidth=1, zeroline=False,
                    linecolor="#DDE5ED", linewidth=1,
                ),
                legend=dict(orientation="h", y=1.07, x=0,
                            font=dict(size=10), bgcolor="rgba(255,255,255,0)"),
                hoverlabel=dict(bgcolor="white", bordercolor="#D5D8DC",
                                font=dict(size=11, family="DM Sans, sans-serif")),
                margin=dict(l=52, r=200, t=65, b=48),
            )

            # ════════════════════════════════════════════════════════════════════
            # CARTA R  — límites segmentados por bloque
            # ════════════════════════════════════════════════════════════════════
            fig_mon_r = go.Figure()

            # Líneas de control Fase I
            for y, lbl, col_ln, dash, lw in [
                (UCLr_fijo, f"LCS₀={UCLr_fijo:.3f}", _LIM_COLOR, "dash",  1.8),
                (CLr_fijo,  f"R̄₀={CLr_fijo:.3f}",   _C_GREEN,   "solid", 1.8),
            ]:
                fig_mon_r.add_shape(type="line",
                    x0=0.5, x1=n_hist+0.5, y0=y, y1=y,
                    line=dict(color=col_ln, dash=dash, width=lw))
                fig_mon_r.add_annotation(
                    x=n_hist+0.5, y=y, text=f" {lbl}", showarrow=False,
                    xanchor="left", font=dict(size=9, color=col_ln),
                    bgcolor="rgba(255,255,255,.7)")
            fig_mon_r.add_shape(type="line",
                x0=0.5, x1=n_hist+0.5, y0=LCLr_fijo, y1=LCLr_fijo,
                line=dict(color=_LIM_COLOR, dash="dash", width=1.8))
            fig_mon_r.add_annotation(
                x=n_hist+0.5, y=LCLr_fijo, text=f" LCI₀={LCLr_fijo:.3f}",
                showarrow=False, xanchor="left", font=dict(size=9, color=_LIM_COLOR),
                bgcolor="rgba(255,255,255,.7)")

            fig_mon_r.add_vline(x=n_hist+0.5, line_dash="dot", line_color="#7F8C8D",
                                line_width=1.4)

            # Líneas de control por bloque Fase II
            _prev_right_r = n_hist + 0.5
            for _bnd in _bloque_boundaries:
                _bnd_start, _bnd_end, _bnd_num, _bk_UCL, _bk_LCL, _bk_CL, _bk_UCLr, _bk_LCLr, _bk_CLr, _bk_n = _bnd
                _seg_x1_r = _bnd_end + 0.5
                for y, lbl, col_ln, dash, lw in [
                    (_bk_UCLr, f"LCS{_bnd_num}={_bk_UCLr:.3f} (n={_bk_n})", _LIM_COLOR, "dash",  1.8),
                    (_bk_CLr,  f"R̄{_bnd_num}={_bk_CLr:.3f}",               _C_GREEN,   "solid", 1.8),
                ]:
                    fig_mon_r.add_shape(type="line",
                        x0=_prev_right_r, x1=_seg_x1_r, y0=y, y1=y,
                        line=dict(color=col_ln, dash=dash, width=lw))
                    fig_mon_r.add_annotation(
                        x=_seg_x1_r, y=y, text=f" {lbl}", showarrow=False,
                        xanchor="left", font=dict(size=9, color=col_ln),
                        bgcolor="rgba(255,255,255,.7)")
                fig_mon_r.add_shape(type="line",
                    x0=_prev_right_r, x1=_seg_x1_r, y0=_bk_LCLr, y1=_bk_LCLr,
                    line=dict(color=_LIM_COLOR, dash="dash", width=1.8))
                fig_mon_r.add_annotation(
                    x=_seg_x1_r, y=_bk_LCLr,
                    text=f" LCI{_bnd_num}={_bk_LCLr:.3f}",
                    showarrow=False, xanchor="left",
                    font=dict(size=9, color=_LIM_COLOR),
                    bgcolor="rgba(255,255,255,.7)")
                if _bnd_num > 1:
                    fig_mon_r.add_vline(x=_prev_right_r, line_dash="dot",
                                        line_color="#8E44AD", line_width=1.2,
                                        annotation_text=f"B{_bnd_num}",
                                        annotation_font_size=9, annotation_font_color="#8E44AD",
                                        annotation_bgcolor="rgba(255,255,255,.7)")
                _prev_right_r = _seg_x1_r

            # Serie R histórica
            fig_mon_r.add_trace(go.Scatter(
                x=idx_hist, y=df_hist["R"], mode="lines+markers", name="R Histórico",
                line=dict(color=_C_GREEN, width=1.5),
                marker=dict(
                    color=[_LIM_COLOR if ix in set(s["signals_r"]) else _C_GREEN
                           for ix in df_hist.index],
                    size=7, opacity=0.75, symbol="diamond",
                    line=dict(color="white", width=1.2)
                ),
                hovertemplate=(
                    "<b>Subgrupo %{x}</b><br>"
                    "R = %{y:.4f} kg<br>"
                    "<span style='color:#7F8C8D'>Fase I — Histórico</span>"
                    "<extra></extra>"
                )
            ))
            # Serie R Fase II
            fig_mon_r.add_trace(go.Scatter(
                x=idx_new, y=_all_R, mode="lines+markers", name="R Nuevos",
                line=dict(color=_C_NEW, width=2.2),
                marker=dict(color=new_r_colors, size=10, symbol="diamond",
                            line=dict(color="white", width=1.8)),
                hovertemplate=(
                    "<b>Subgrupo %{x}</b><br>"
                    "R = %{y:.4f} kg<br>"
                    "<span style='color:#E67E22'>Fase II — Nuevo</span>"
                    "<extra></extra>"
                )
            ))
            # Señales R
            if new_r_signals:
                si_r = [idx_new[i] for i in new_r_signals]
                sv_r = [_all_R[i]  for i in new_r_signals]
                fig_mon_r.add_trace(go.Scatter(
                    x=si_r, y=sv_r, mode="markers", name="🚨 SEÑAL R",
                    marker=dict(color=_LIM_COLOR, size=20, symbol="x-open",
                                line=dict(color=_LIM_COLOR, width=3.5)),
                    hovertemplate=(
                        "<b>⚠ FUERA DE CONTROL</b><br>"
                        "Subgrupo %{x}<br>"
                        "R = %{y:.4f} kg"
                        "<extra>🚨 Señal R</extra>"
                    )
                ))

            # Rango Y carta R: margen negativo para que LCLr=0 quede visible sobre el eje
            _r_all_vals = (list(df_hist["R"]) + _all_R
                           + [UCLr_fijo]
                           + [_bnd[6] for _bnd in _bloque_boundaries])
            _r_ymax = max((v for v in _r_all_vals if not np.isnan(v)), default=UCLr_fijo)
            _r_ymax = max(_r_ymax, UCLr_fijo) * 1.12
            _r_y_lo = -0.15 * _r_ymax

            fig_mon_r.update_layout(
                template="plotly_white", height=310,
                plot_bgcolor="white", paper_bgcolor="white",
                title=dict(text="Carta R de Monitoreo — Variabilidad entre muestras (límites por bloque)",
                           font=dict(size=12, color=_LC_COLOR, family="DM Sans, sans-serif"),
                           x=0, xanchor="left", pad=dict(l=4)),
                xaxis=dict(
                    title=dict(text="Subgrupo", font=dict(size=11)),
                    tickmode="linear", tickfont=dict(size=10),
                    range=[0, n_hist+n_new+2],
                    gridcolor="#EEF3F8", gridwidth=1, zeroline=False,
                    linecolor="#DDE5ED", linewidth=1,
                ),
                yaxis=dict(
                    title=dict(text="Rango R (kg)", font=dict(size=11)),
                    tickfont=dict(size=10), tickformat=".4f",
                    gridcolor="#EEF3F8", gridwidth=1, zeroline=False,
                    linecolor="#DDE5ED", linewidth=1,
                    range=[_r_y_lo, _r_ymax],
                ),
                legend=dict(orientation="h", y=1.12, x=0,
                            font=dict(size=10), bgcolor="rgba(255,255,255,0)"),
                hoverlabel=dict(bgcolor="white", bordercolor="#D5D8DC",
                                font=dict(size=11, family="DM Sans, sans-serif")),
                margin=dict(l=52, r=200, t=60, b=48),
            )

            # Guardar señales en session_state para las alertas y exportación
            # df_nuevos_ss = bloque activo (para resumen); _all_* para alertas globales
            _df_nuevos_para_export = (
                _bloques[_bi].get("_df_proc")
                if _bloques[_bi].get("_df_proc") is not None
                else pd.DataFrame(columns=x_cols_mon + ["xbar", "R"])
            )
            st.session_state["mon_fig_x"]            = fig_mon
            st.session_state["mon_fig_r"]            = fig_mon_r
            st.session_state["mon_new_signals"]      = new_signals
            st.session_state["mon_new_r_signals"]    = new_r_signals
            st.session_state["mon_idx_new"]          = idx_new
            st.session_state["mon_df_nuevos"]        = _df_nuevos_para_export.copy()
            st.session_state["mon_n_new"]            = n_new
            st.session_state["mon_n_hist"]           = n_hist
            # Listas globales para alertas (índices coinciden con new_signals)
            st.session_state["mon_all_xbar"]         = list(_all_xbar)
            st.session_state["mon_all_R"]            = list(_all_R)
            # Límites por bloque (para exportación HTML)
            st.session_state["mon_bloque_boundaries"] = _bloque_boundaries

        # ── Renderizar figuras (desde session_state) ──────────────────────────
        st.markdown(render_section_title("📈 Carta X̄ — Histórico + Nuevos Subgrupos"),
                    unsafe_allow_html=True)
        st.plotly_chart(st.session_state["mon_fig_x"],
                        width='stretch', key="chart_mon_xbar")
        st.plotly_chart(st.session_state["mon_fig_r"],
                        width='stretch', key="chart_mon_r")

        # ── Alertas ───────────────────────────────────────────────────────────
        new_signals   = st.session_state["mon_new_signals"]
        new_r_signals = st.session_state["mon_new_r_signals"]
        idx_new       = st.session_state["mon_idx_new"]
        n_new         = st.session_state["mon_n_new"]
        # Listas globales: índices de new_signals/new_r_signals apuntan aquí
        _all_xbar_ss  = st.session_state.get("mon_all_xbar", [])
        _all_R_ss     = st.session_state.get("mon_all_R",    [])

        st.markdown(render_section_title("🚨 Alertas de Monitoreo"), unsafe_allow_html=True)
        if not new_signals and not new_r_signals:
            st.markdown(render_alarm("ok",
                "✅ Todos los subgrupos nuevos están bajo control. "
                "El proceso se mantiene estable."), unsafe_allow_html=True)
        else:
            if new_signals:
                sgs_txt  = ", ".join([f"S{idx_new[i]}" for i in new_signals])
                vals_txt = ", ".join([f"{_all_xbar_ss[i]:.4f}" for i in new_signals
                                      if i < len(_all_xbar_ss)])
                st.markdown(render_alarm("critical",
                    f"🚨 <strong>SEÑAL EN CARTA X̄:</strong> Subgrupos {sgs_txt} fuera de límites. "
                    f"x̄ = {vals_txt} kg. Investigar causa asignable inmediatamente."),
                    unsafe_allow_html=True)
            if new_r_signals:
                sgs_r = ", ".join([f"S{idx_new[i]}" for i in new_r_signals])
                st.markdown(render_alarm("critical",
                    f"🚨 <strong>SEÑAL EN CARTA R:</strong> Variabilidad inestable en "
                    f"subgrupos {sgs_r}. Posible problema en el dosificador o cambio de operario."),
                    unsafe_allow_html=True)

        # ── Resumen estadístico ───────────────────────────────────────────────
        st.divider()
        # ── Tablas por bloque ─────────────────────────────────────────────────
        st.markdown(render_section_title("📋 Tablas de Subgrupos por Bloque"),
                    unsafe_allow_html=True)
        for _tbl_bi, _tbl_bk in enumerate(_bloques):
            _tbl_proc = _tbl_bk.get("_df_proc")
            _is_active = (_tbl_bi == _bi)
            _border_color = "#2563A8" if _is_active else "#BDD7EE"
            _label_extra  = " (activo)" if _is_active else ""
            st.markdown(
                f"<div style='background:#EEF6FD;border:1px solid {_border_color};"
                f"border-left:4px solid {_border_color};border-radius:8px;"
                f"padding:.45rem 1rem;margin:.4rem 0 .25rem;font-size:.8rem;font-weight:600'>"
                f"📦 Bloque {_tbl_bi+1}{_label_extra} — n={_tbl_bk['n']} · "
                f"{_tbl_bk['n_sg']} subgrupos configurados</div>",
                unsafe_allow_html=True
            )
            if _tbl_proc is not None and len(_tbl_proc) > 0:
                _disp_cols = (
                    [c for c in _tbl_proc.columns
                     if c not in ("xbar", "R")]
                    + ["xbar", "R"]
                )
                _disp_cols = [c for c in _disp_cols if c in _tbl_proc.columns]
                st.dataframe(
                    _tbl_proc[_disp_cols].style.format(
                        {c: "{:.4f}" for c in _disp_cols
                         if c not in ("Subgrupo", "Hora", "xbar", "R")}
                        | {"xbar": "{:.4f}", "R": "{:.4f}"}
                    ),
                    use_container_width=True,
                    height=min(400, 38 + len(_tbl_proc) * 35),
                    key=f"tbl_bloque_{_tbl_bi}",
                )
            else:
                st.markdown(
                    "<span style='color:#95A5A6;font-size:.8rem'>— Sin datos suficientes aún —</span>",
                    unsafe_allow_html=True
                )

        with st.container():
            st.markdown(render_section_title("📊 Resumen de Nuevos Subgrupos"),
                        unsafe_allow_html=True)
            xb_new = sum(_all_xbar) / len(_all_xbar) if _all_xbar else 0.0
            r_new  = sum(_all_R)    / len(_all_R)    if _all_R    else 0.0
            rs1, rs2, rs3, rs4 = st.columns(4)
            with rs1:
                st.metric("x̄ nuevos", f"{xb_new:.4f} kg",
                          delta=f"{(xb_new-CL_fijo)*1000:+.1f} g vs LC")
            with rs2:
                st.metric("R̄ nuevos", f"{r_new:.4f} kg",
                          delta=f"{(r_new-CLr_fijo)*1000:+.1f} g vs R̄")
            with rs3:
                st.metric("Subgrupos bajo control",
                          f"{n_new - len(new_signals)}/{n_new}")
            with rs4:
                pct_ok   = (n_new - len(new_signals)) / n_new * 100
                color_ok = CG if pct_ok == 100 else CY if pct_ok >= 80 else CR
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:.8rem 1rem;
                     box-shadow:0 1px 6px rgba(0,0,0,.08);
                     border-left:4px solid {color_ok};text-align:center;">
                  <div style="font-size:1.6rem;font-weight:700;
                       color:{color_ok};line-height:1.2">{pct_ok:.0f}%</div>
                  <div style="font-size:.72rem;color:#7F8C8D;
                       margin-top:.2rem">Tasa de conformidad</div>
                </div>""", unsafe_allow_html=True)

        # ══ PASO 5 — EXPORTACIÓN HTML ════════════════════════════════════════
        st.divider()
        with st.container():
            st.markdown(render_section_title("📄 Exportar Reporte de Monitoreo"),
                        unsafe_allow_html=True)

            # ── Campos del reporte ────────────────────────────────────────────
            _exp_c1, _exp_c2 = st.columns([3, 1])
            with _exp_c1:
                _exp_title = st.text_input(
                    "Título del reporte",
                    value="Reporte de Monitoreo CEP — Línea de Empaque Mogolla",
                    key="mon_export_title",
                )
            with _exp_c2:
                _exp_resp = st.text_input(
                    "Responsable del reporte",
                    value=st.session_state.get("mon_meta_operador", ""),
                    key="mon_export_responsable",
                )
            _exp_notes = st.text_input(
                "Notas finales (opcional)",
                placeholder="Acciones tomadas, conclusiones, firma...",
                key="mon_export_notes",
            )
            _exp_obs = st.text_area(
                "Observaciones adicionales (opcional)",
                placeholder="Contexto del turno, condiciones del equipo...",
                height=68,
                key="mon_export_obs",
            )

            # ── Construir HTML ────────────────────────────────────────────────
            import datetime as _dt

            _fig_x_html = st.session_state["mon_fig_x"].to_html(
                full_html=False, include_plotlyjs="cdn"
            )
            _fig_r_html = st.session_state["mon_fig_r"].to_html(
                full_html=False, include_plotlyjs=False   # cdn ya incluido arriba
            )

            _ts       = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            _operador = st.session_state.get("mon_meta_operador", "—") or "—"
            _turno    = st.session_state.get("mon_meta_turno",    "—")
            _fecha    = str(st.session_state.get("mon_meta_fecha", "—"))
            _lote     = st.session_state.get("mon_meta_lote",     "—") or "—"
            _obs_tur  = st.session_state.get("mon_meta_obs",      "") or ""

            _n_h   = st.session_state.get("mon_n_hist", 0)
            _n_n   = st.session_state.get("mon_n_new",  0)
            _nsigs = len(st.session_state.get("mon_new_signals",   []))
            _rsigs = len(st.session_state.get("mon_new_r_signals", []))
            _pct_ok_exp = ((_n_n - _nsigs) / _n_n * 100) if _n_n > 0 else 0.0
            _estado_proceso = (
                "🚨 FUERA DE CONTROL" if (_nsigs + _rsigs) > 0 else "✅ BAJO CONTROL"
            )
            _estado_color = "#C0392B" if (_nsigs + _rsigs) > 0 else "#1E8449"

            # Tabla de subgrupos nuevos — construida desde listas globales
            _idx_new_ss   = st.session_state.get("mon_idx_new", list(range(1, _n_n+1)))
            _new_sigs_set = set(st.session_state.get("mon_new_signals", []))
            _all_xbar_exp = st.session_state.get("mon_all_xbar", [])
            _all_R_exp    = st.session_state.get("mon_all_R",    [])

            _trows = ""
            for _ri in range(_n_n):
                _bg    = "#FFF0F0" if _ri in _new_sigs_set else "white"
                _flag  = " 🚨" if _ri in _new_sigs_set else ""
                _sg_num = _idx_new_ss[_ri] if _ri < len(_idx_new_ss) else _ri + 1
                _xb_val = f"{_all_xbar_exp[_ri]:.4f}" if _ri < len(_all_xbar_exp) else "—"
                _r_val  = f"{_all_R_exp[_ri]:.4f}"    if _ri < len(_all_R_exp)    else "—"
                _trows += (
                    f"<tr style='background:{_bg}'>"
                    f"<td style='padding:.3rem .6rem;font-weight:600'>{_sg_num}{_flag}</td>"
                    f"<td style='padding:.3rem .6rem;text-align:right;font-family:monospace'>"
                    f"{_xb_val}</td>"
                    f"<td style='padding:.3rem .6rem;text-align:right;font-family:monospace'>"
                    f"{_r_val}</td>"
                    f"</tr>"
                )
            _thead_xcols = ""  # tabla simplificada: solo subgrupo, x̄, R (columnas X varían por bloque)

            # Alertas para el reporte
            _alerta_html = ""
            if _nsigs == 0 and _rsigs == 0:
                _alerta_html = (
                    "<div style='background:#EAFAF1;border-left:4px solid #1E8449;"
                    "padding:.6rem 1rem;border-radius:4px;margin:.4rem 0'>"
                    "✅ Todos los subgrupos nuevos están dentro de los límites de control.</div>"
                )
            else:
                if _nsigs > 0:
                    _sgs_t = ", ".join(
                        [f"S{_idx_new_ss[i]}" for i in st.session_state["mon_new_signals"]
                         if i < len(_idx_new_ss)]
                    )
                    _alerta_html += (
                        f"<div style='background:#FDEDEC;border-left:4px solid #C0392B;"
                        f"padding:.6rem 1rem;border-radius:4px;margin:.4rem 0'>"
                        f"🚨 <strong>SEÑAL CARTA X̄:</strong> Subgrupos {_sgs_t} fuera de límites.</div>"
                    )
                if _rsigs > 0:
                    _sgs_r = ", ".join(
                        [f"S{_idx_new_ss[i]}" for i in st.session_state["mon_new_r_signals"]
                         if i < len(_idx_new_ss)]
                    )
                    _alerta_html += (
                        f"<div style='background:#FDEDEC;border-left:4px solid #C0392B;"
                        f"padding:.6rem 1rem;border-radius:4px;margin:.4rem 0'>"
                        f"🚨 <strong>SEÑAL CARTA R:</strong> Variabilidad inestable en subgrupos {_sgs_r}.</div>"
                    )

            _notas_html  = f"<p style='margin:.3rem 0'>{_exp_notes}</p>" if _exp_notes.strip() else ""
            _obs_html    = (f"<p style='margin:.3rem 0;color:#555'>{_exp_obs}</p>"
                            if _exp_obs.strip() else "")
            _obs_tur_html = (f"<p style='margin:.3rem 0;font-style:italic;color:#666'>{_obs_tur}</p>"
                             if _obs_tur.strip() else "")

            _html_reporte = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_exp_title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;font-size:13px;color:#1A1A2E;background:#F4F6F9;padding:0}}
  .page{{max-width:1100px;margin:0 auto;background:white;padding:2rem 2.5rem 3rem}}
  .header{{background:linear-gradient(135deg,#1B4F72,#154360);color:white;
            padding:1.4rem 2rem;border-radius:10px;margin-bottom:1.5rem}}
  .header h1{{font-size:1.25rem;font-weight:700;margin-bottom:.3rem}}
  .header .sub{{font-size:.8rem;opacity:.8}}
  .meta-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin-bottom:1.2rem}}
  .meta-card{{background:#EEF3F8;border-radius:7px;padding:.55rem .8rem;
              border-left:3px solid #1B4F72}}
  .meta-card .lbl{{font-size:.65rem;font-weight:700;color:#5D6D7E;
                   text-transform:uppercase;letter-spacing:.6px}}
  .meta-card .val{{font-size:.88rem;font-weight:600;color:#1A1A2E;margin-top:.15rem}}
  .kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:.7rem;margin-bottom:1.2rem}}
  .kpi{{background:#F8F9FA;border-radius:7px;padding:.65rem .85rem;text-align:center;
         border-top:3px solid #1B4F72}}
  .kpi .v{{font-size:1.35rem;font-weight:700;line-height:1.2}}
  .kpi .l{{font-size:.68rem;color:#7F8C8D;margin-top:.2rem}}
  .section{{margin-bottom:1.3rem}}
  .section-title{{font-size:.72rem;font-weight:700;color:#1B4F72;text-transform:uppercase;
                  letter-spacing:.8px;padding:.4rem 0;border-bottom:2px solid #D6E8F7;
                  margin-bottom:.6rem}}
  table{{width:100%;border-collapse:collapse;font-size:.8rem}}
  th{{background:#1B4F72;color:white;padding:.4rem .6rem;text-align:left;font-weight:600}}
  td{{padding:.3rem .6rem;border-bottom:1px solid #EEF0F3}}
  tr:hover td{{background:#F8FBFF}}
  .estado{{display:inline-block;padding:.25rem .75rem;border-radius:20px;
            font-weight:700;font-size:.78rem;
            background:{_estado_color}18;color:{_estado_color};
            border:1px solid {_estado_color}44}}
  .footer{{margin-top:2rem;padding-top:1rem;border-top:1px solid #D5D8DC;
            font-size:.72rem;color:#95A5A6;display:flex;justify-content:space-between}}
  .fig-wrap{{margin:.6rem 0;border:1px solid #E8EDF2;border-radius:8px;overflow:hidden}}
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <h1>{_exp_title}</h1>
    <div class="sub">
      Molinos Santa Marta S.A.S. &nbsp;·&nbsp;
      Control Estadístico de Procesos — Fase II &nbsp;·&nbsp;
      Generado: {_ts} &nbsp;·&nbsp;
      Estado: <span style="font-weight:700;color:{'#FF8C8C' if (_nsigs+_rsigs)>0 else '#A8F0C6'}">{_estado_proceso}</span>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-card"><div class="lbl">Operador</div><div class="val">{_operador}</div></div>
    <div class="meta-card"><div class="lbl">Turno</div><div class="val">{_turno}</div></div>
    <div class="meta-card"><div class="lbl">Fecha</div><div class="val">{_fecha}</div></div>
    <div class="meta-card"><div class="lbl">Línea / Lote</div><div class="val">{_lote}</div></div>
  </div>

  <div class="kpi-row">
    <div class="kpi">
      <div class="v" style="color:#1B4F72">{_n_h}</div>
      <div class="l">Subgrupos históricos</div>
    </div>
    <div class="kpi">
      <div class="v" style="color:#E67E22">{_n_n}</div>
      <div class="l">Subgrupos nuevos</div>
    </div>
    <div class="kpi">
      <div class="v" style="color:{_estado_color}">{_nsigs + _rsigs}</div>
      <div class="l">Señales detectadas</div>
    </div>
    <div class="kpi">
      <div class="v" style="color:{_estado_color}">{_pct_ok_exp:.0f}%</div>
      <div class="l">Conformidad Fase II</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Límites de Control por Bloque</div>
    <table>
      <thead>
        <tr>
          <th>Bloque</th>
          <th style="text-align:center">n</th>
          <th style="text-align:right">x̄̄ (kg)</th>
          <th style="text-align:right">R̄ (kg)</th>
          <th style="text-align:right">LCS X̄</th>
          <th style="text-align:right">LCI X̄</th>
          <th style="text-align:right">LCS R</th>
        </tr>
      </thead>
      <tbody>
        <tr style="background:#EEF3F8">
          <td style="font-weight:600">Fase I (referencia)</td>
          <td style="text-align:center;font-family:monospace">{n_fijo}</td>
          <td style="text-align:right;font-family:monospace">{CL_fijo:.4f}</td>
          <td style="text-align:right;font-family:monospace">{CLr_fijo:.4f}</td>
          <td style="text-align:right;font-family:monospace">{UCL_fijo:.4f}</td>
          <td style="text-align:right;font-family:monospace">{LCL_fijo:.4f}</td>
          <td style="text-align:right;font-family:monospace">{UCLr_fijo:.4f}</td>
        </tr>
        {''.join(
          f"<tr><td style='font-weight:600'>Bloque {_bnd[2]}</td>"
          f"<td style='text-align:center;font-family:monospace'>{_bnd[9]}</td>"
          f"<td style='text-align:right;font-family:monospace'>{_bnd[5]:.4f}</td>"
          f"<td style='text-align:right;font-family:monospace'>{_bnd[8]:.4f}</td>"
          f"<td style='text-align:right;font-family:monospace'>{_bnd[3]:.4f}</td>"
          f"<td style='text-align:right;font-family:monospace'>{_bnd[4]:.4f}</td>"
          f"<td style='text-align:right;font-family:monospace'>{_bnd[6]:.4f}</td></tr>"
          for _bnd in st.session_state.get("mon_bloque_boundaries", [])
        )}
      </tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Alertas</div>
    {_alerta_html}
  </div>

  <div class="section">
    <div class="section-title">Tabla de Subgrupos Nuevos (Fase II)</div>
    <table>
      <thead>
        <tr>
          <th>Subgrupo</th>
          {_thead_xcols}
          <th style="text-align:right">x̄ (kg)</th>
          <th style="text-align:right">R (kg)</th>
        </tr>
      </thead>
      <tbody>{_trows}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Carta X̄ — Histórico + Nuevos Subgrupos</div>
    <div class="fig-wrap">{_fig_x_html}</div>
  </div>

  <div class="section">
    <div class="section-title">Carta R — Variabilidad</div>
    <div class="fig-wrap">{_fig_r_html}</div>
  </div>

  {"<div class='section'><div class='section-title'>Notas Finales</div>" + _notas_html + "</div>" if _exp_notes.strip() else ""}
  {"<div class='section'><div class='section-title'>Observaciones Adicionales</div>" + _obs_html + "</div>" if _exp_obs.strip() else ""}
  {"<div class='section'><div class='section-title'>Observaciones del Turno</div>" + _obs_tur_html + "</div>" if _obs_tur.strip() else ""}

  <div class="footer">
    <span>Responsable: <strong>{_exp_resp or "—"}</strong></span>
    <span>Molinos Santa Marta S.A.S. &nbsp;·&nbsp; CEP v2.1 &nbsp;·&nbsp; {_ts}</span>
  </div>

</div>
</body>
</html>"""

            st.download_button(
                label="📥 Descargar Reporte HTML de Monitoreo",
                data=_html_reporte.encode("utf-8"),
                file_name="reporte_monitoreo.html",
                mime="text/html",
                type="primary",
                key="btn_export_html_mon",
            )

    else:
        st.markdown(render_alarm("info", """
        <strong>📋 Cómo usar el Monitoreo:</strong><br><br>
        1. Los límites de arriba son <strong>fijos</strong> — vienen del análisis histórico<br>
        2. Selecciona el modo de ingreso (editor o Excel nuevo)<br>
        3. Ingresa los pesos de los nuevos subgrupos del turno actual<br>
        4. La gráfica mostrará los puntos nuevos a la derecha de los históricos<br>
        5. Si un punto se sale de los límites, aparece una <strong>🚨 alerta inmediata</strong>
        """), unsafe_allow_html=True)


def page_eco_analisis():
    global s, cpk_color, cpk_text, cpk_badge, freq_min, n_proposed

    # Límites activos — única fuente de verdad durante la sesión
    _LSL     = st.session_state["cap_lsl"]
    _USL     = st.session_state["cap_usl"]
    _NOMINAL = st.session_state["cap_nominal"]


    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 1 — PARÁMETROS DEL PROCESO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1B4F72,#154360);color:white;
         padding:1.1rem 1.5rem;border-radius:10px;margin-bottom:.8rem;">
    <h3 style="margin:0 0 .25rem;font-size:1.15rem;">💰 Análisis Económico del Sobrellenado</h3>
    <p style="margin:0;opacity:.85;font-size:.82rem;">
    Parámetros de Fase I (μ, σ) tomados automáticamente. Ajusta los parámetros de producción y costo.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(render_section_title("⚙️ Parámetros del Proceso"), unsafe_allow_html=True)
    ep1, ep2, ep3, ep4 = st.columns(4)
    with ep1:
        st.session_state["eco_cost_kg"] = st.number_input(
            "Costo mogolla ($/kg)", min_value=0.0, step=1.0,
            value=float(st.session_state["eco_cost_kg"]),
            key="eco_input_cost_kg",
            help="Costo unitario del producto en COP por kilogramo"
        )
    with ep2:
        st.session_state["eco_prod_h"] = st.number_input(
            "Producción (sacos/hora)", min_value=1, step=5,
            value=int(st.session_state["eco_prod_h"]),
            key="eco_input_prod_h",
            help="Velocidad de la línea en sacos por hora"
        )
    with ep3:
        st.session_state["eco_hours_day"] = st.number_input(
            "Horas productivas/día", min_value=1.0, max_value=24.0, step=0.5,
            value=float(st.session_state["eco_hours_day"]),
            key="eco_input_hours",
            help="Horas efectivas de producción por turno/día"
        )
    with ep4:
        st.session_state["eco_days_month"] = st.number_input(
            "Días productivos/mes", min_value=1, max_value=31,
            value=int(st.session_state["eco_days_month"]),
            key="eco_input_days",
            help="Días calendario con producción activa"
        )

    # Leer valores consolidados
    _e_cost  = st.session_state["eco_cost_kg"]
    _e_prod  = st.session_state["eco_prod_h"]
    _e_hours = st.session_state["eco_hours_day"]
    _e_days  = st.session_state["eco_days_month"]

    # Parámetros Fase I — autollenados, editables manualmente
    st.session_state.setdefault("eco_xb_edit",  float(s["xbar_bar"]))
    st.session_state.setdefault("eco_sig_edit", float(s["sigma_st"]))
    st.session_state.setdefault("eco_lsl_edit", float(_LSL))
    st.session_state.setdefault("eco_usl_edit", float(_USL))

    ep5, ep6, ep7, ep8 = st.columns(4)
    with ep5:
        _xb = st.number_input("μ proceso (kg)", value=float(s["xbar_bar"]),
                              format="%.4f", key="eco_xb_edit",
                              help="Autollenado desde Fase I (x̄). Editable para análisis manual.")
    with ep6:
        _sig = st.number_input("σ proceso (kg)", min_value=0.0001,
                               value=float(s["sigma_st"]),
                               format="%.4f", key="eco_sig_edit",
                               help="R̄/d₂ de Fase I. Editable para análisis manual.")
    with ep7:
        _LSL = st.number_input("LSL (kg)", value=float(st.session_state["cap_lsl"]),
                               format="%.2f", key="eco_lsl_edit",
                               help="Límite de especificación inferior.")
    with ep8:
        _USL = st.number_input("USL (kg)", value=float(st.session_state["cap_usl"]),
                               format="%.2f", key="eco_usl_edit",
                               help="Límite de especificación superior.")
    _des_g_nominal = round((_xb - _NOMINAL) * 1000, 1)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2 — SITUACIÓN ACTUAL
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("📊 Situación Actual — Sobrellenado Anual"), unsafe_allow_html=True)

    eco = compute_eco(s, _e_cost, _e_prod, _e_hours, _e_days)

    sa1, sa2, sa3, sa4, sa5 = st.columns(5)
    with sa1:
        _ov_color = CY if eco["overfill_g"] > 0 else CG
        _ov_borde = "yellow" if eco["overfill_g"] > 0 else "green"
        st.markdown(f"""<div class="kpi-card {_ov_borde}">
        <div class="kpi-value" style="color:{_ov_color}">{eco['overfill_g']:+.1f} g</div>
        <div class="kpi-label">Sobrellenado/saco</div>
        <div class="kpi-sub">x̄ − nominal = {_xb:.4f} − {_NOMINAL:.1f} kg</div></div>""",
        unsafe_allow_html=True)

    with sa2:
        st.markdown(f"""<div class="kpi-card">
        <div class="kpi-value" style="color:{CP}">{eco['sacos_mes']:,.0f}</div>
        <div class="kpi-label">Sacos/mes</div>
        <div class="kpi-sub">{eco['sacos_anio']:,.0f} sacos/año</div></div>""",
        unsafe_allow_html=True)

    with sa3:
        st.markdown(f"""<div class="kpi-card yellow">
        <div class="kpi-value" style="color:{CY}">{eco['kg_extra_mes']:,.1f} kg</div>
        <div class="kpi-label">kg extra/mes</div>
        <div class="kpi-sub">{eco['kg_extra_mes']*12:,.0f} kg extra/año</div></div>""",
        unsafe_allow_html=True)

    with sa4:
        st.markdown(f"""<div class="kpi-card red">
        <div class="kpi-value" style="color:{CR}">${eco['costo_mes']:,.0f}</div>
        <div class="kpi-label">Pérdida mensual (COP)</div>
        <div class="kpi-sub">${eco['costo_anio']:,.0f}/año</div></div>""",
        unsafe_allow_html=True)

    with sa5:
        st.markdown(f"""<div class="kpi-card red">
        <div class="kpi-value" style="color:{CR}">{eco['sacos_extra_anio']:.0f}</div>
        <div class="kpi-label">Sacos equivalentes/año</div>
        <div class="kpi-sub">kg extra ÷ 40 kg/saco</div></div>""",
        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Banner: pregunta central
    st.markdown("""
    <div style="background:linear-gradient(135deg,#154360,#1B4F72);color:white;
         padding:1rem 1.5rem;border-radius:10px;margin:.2rem 0 1rem;
         border-left:5px solid #F1C40F;font-size:.88rem;line-height:1.55">
    <strong style="font-size:.95rem">¿Cuál es la menor media que evita el rechazo del lote?</strong><br><br>
    La empresa sobrellenar por seguridad estadística. Sin embargo, existe una media mínima μ*
    tal que la probabilidad de que el promedio del lote caiga bajo el Nominal (40 kg) sea prácticamente nula.
    Operar en μ* reduce las pérdidas sin comprometer el peso comprometido con el cliente.
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — SIMULACIÓN: probabilidad de rechazo de lote
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("🎯 Simulación — Media Óptima por Probabilidad de Rechazo"),
                unsafe_allow_html=True)
    st.markdown(render_alarm("info",
        "<strong>Ingresa los parámetros de simulación:</strong> tamaño del lote y probabilidad máxima de rechazo "
        "tolerable. El sistema calculará la media mínima μ* que mantiene ese riesgo usando "
        "<code>μ* = Nominal + z(1−p) · σ/√n_lote</code>. "
        "Con valores pequeños de p (ej. 0.100%) se garantiza un margen estadístico robusto."
    ), unsafe_allow_html=True)

    sim1, sim2 = st.columns(2)
    with sim1:
        st.session_state["eco_lote"] = st.number_input(
            "Tamaño del lote (sacos)",
            min_value=1, max_value=100000,
            value=int(st.session_state["eco_lote"]),
            step=1, key="eco_input_lote",
            help="Número de sacos por lote de despacho al cliente"
        )
    with sim2:
        st.session_state["eco_p_rechazo"] = st.number_input(
            "Probabilidad máxima de rechazo (%)",
            min_value=0.001, max_value=10.0,
            value=float(st.session_state["eco_p_rechazo"]),
            step=0.001, format="%.3f",
            key="eco_input_p",
            help="P(x̄_lote < Nominal) tolerable. Ejemplo: 0.100 = 0.1 %"
        )

    _lote     = int(st.session_state["eco_lote"])
    _p_rec    = st.session_state["eco_p_rechazo"] / 100.0   # proporción
    _se_lote  = _sig / np.sqrt(_lote)                        # SE del promedio del lote
    _z_opt    = stats.norm.ppf(1.0 - _p_rec)                 # z tal que P(Z>z) = p_rechazo
    _mu_opt   = _NOMINAL + _z_opt * _se_lote                   # media óptima: base Nominal, no LSL

    # μ* ∈ [Nominal, x̄] — el cliente exige ≥ nominal, así que no proponemos bajar de ahí
    _mu_opt = float(np.clip(_mu_opt, _NOMINAL, max(_xb, _NOMINAL + 1e-6)))

    # Capacidad con media óptima
    _Cpk_opt = min((_USL - _mu_opt) / (3*_sig), (_mu_opt - _LSL) / (3*_sig))
    _pnc_opt = (stats.norm.cdf(_LSL, _mu_opt, _sig)
                + 1 - stats.norm.cdf(_USL, _mu_opt, _sig))

    st.markdown("<br>", unsafe_allow_html=True)
    sr1, sr2, sr3, sr4 = st.columns(4)
    with sr1:
        st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-value" style="color:{CG}">{_mu_opt:.4f} kg</div>
        <div class="kpi-label">Media óptima μ*</div>
        <div class="kpi-sub">{(_mu_opt-_NOMINAL)*1000:+.1f} g sobre nominal</div></div>""",
        unsafe_allow_html=True)

    with sr2:
        _zc, _zt, _zb = cpk_st(_Cpk_opt)
        st.markdown(f"""<div class="kpi-card {'green' if _Cpk_opt>=1.33 else 'yellow' if _Cpk_opt>=1.0 else 'red'}">
        <div class="kpi-value" style="color:{_zc}">{_Cpk_opt:.3f}</div>
        <div class="kpi-label">Cpk con μ*</div>
        <div class="kpi-sub"><span class="badge {_zb}">{_zt}</span></div></div>""",
        unsafe_allow_html=True)

    with sr3:
        _pnc_opt_pct = _pnc_opt * 100
        _pc_opt = CR if _pnc_opt_pct > 5 else CY if _pnc_opt_pct > 0.27 else CG
        st.markdown(f"""<div class="kpi-card {'red' if _pnc_opt_pct>5 else 'yellow' if _pnc_opt_pct>0.27 else 'green'}">
        <div class="kpi-value" style="color:{_pc_opt}">{_pnc_opt_pct:.4f}%</div>
        <div class="kpi-label">PNC con μ*</div>
        <div class="kpi-sub">vs {s['pnc_total']*100:.4f}% actual</div></div>""",
        unsafe_allow_html=True)

    with sr4:
        _z_disp  = stats.norm.ppf(1.0 - _p_rec)
        st.markdown(f"""<div class="kpi-card">
        <div class="kpi-value" style="color:{CP}">{_z_disp:.3f}</div>
        <div class="kpi-label">z crítico</div>
        <div class="kpi-sub">P(rechazo) ≤ {st.session_state['eco_p_rechazo']:.2f}% · SE = {_se_lote*1000:.2f} g</div></div>""",
        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 4 — RESULTADO: media óptima vs actual
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("📐 Resultado — Comparativa de Medias"), unsafe_allow_html=True)

    _des_actual = (_xb - _NOMINAL) * 1000
    _des_opt    = (_mu_opt - _NOMINAL) * 1000
    _reduccion_g = _des_actual - _des_opt

    comp1, comp2, comp3 = st.columns(3)
    with comp1:
        _cc = CY if _des_actual > 0 else CG
        st.markdown(f"""<div class="kpi-card {'yellow' if _des_actual>0 else 'green'}">
        <div class="kpi-value" style="color:{_cc}">{_xb:.4f} kg</div>
        <div class="kpi-label">Media actual (Fase I)</div>
        <div class="kpi-sub">Exceso: {_des_actual:+.1f} g/saco · Cpk = {s['Cpk']:.3f}</div></div>""",
        unsafe_allow_html=True)

    with comp2:
        st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-value" style="color:{CG}">{_mu_opt:.4f} kg</div>
        <div class="kpi-label">Media óptima propuesta</div>
        <div class="kpi-sub">Exceso: {_des_opt:+.1f} g/saco · Cpk = {_Cpk_opt:.3f}</div></div>""",
        unsafe_allow_html=True)

    with comp3:
        _rc = CG if _reduccion_g > 0 else CY
        st.markdown(f"""<div class="kpi-card {'green' if _reduccion_g>0 else 'yellow'}">
        <div class="kpi-value" style="color:{_rc}">{_reduccion_g:.1f} g</div>
        <div class="kpi-label">Reducción de exceso/saco</div>
        <div class="kpi-sub">{_des_actual:.1f} g → {_des_opt:.1f} g por saco</div></div>""",
        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 5 — AHORRO ECONÓMICO COMPARATIVO
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(render_section_title("💵 Ahorro Económico Comparativo"), unsafe_allow_html=True)

    # Cálculo escenario óptimo
    _sacos_anio   = eco["sacos_anio"]
    _over_opt_kg  = max(0.0, _mu_opt - _NOMINAL)
    _costo_opt_mes  = _over_opt_kg * _e_prod * _e_hours * _e_days * _e_cost
    _costo_opt_anio = _costo_opt_mes * 12
    _sacos_opt_anio = (_over_opt_kg * _sacos_anio / 40) if _over_opt_kg > 0 else 0.0

    _ahorro_mes    = eco["costo_mes"]  - _costo_opt_mes
    _ahorro_anio   = eco["costo_anio"] - _costo_opt_anio
    _ahorro_sacos  = eco["sacos_extra_anio"] - _sacos_opt_anio
    _pct_ahorro    = (_ahorro_anio / max(eco["costo_anio"], 1e-9)) * 100

    # Tabla comparativa
    st.markdown(f"""
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:.85rem;font-family:'IBM Plex Sans',sans-serif">
      <thead>
        <tr style="background:#1B4F72;color:white">
          <th style="padding:.6rem .9rem;text-align:left">Escenario</th>
          <th style="padding:.6rem .9rem;text-align:right">Media (kg)</th>
          <th style="padding:.6rem .9rem;text-align:right">Exceso/saco (g)</th>
          <th style="padding:.6rem .9rem;text-align:right">Sacos extra/año</th>
          <th style="padding:.6rem .9rem;text-align:right">Costo mensual (COP)</th>
          <th style="padding:.6rem .9rem;text-align:right">Costo anual (COP)</th>
        </tr>
      </thead>
      <tbody>
        <tr style="background:#FEF9E7">
          <td style="padding:.55rem .9rem;font-weight:600;color:{CY}">⚠ Actual</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{_xb:.4f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{_des_actual:+.1f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{eco['sacos_extra_anio']:.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">${eco['costo_mes']:,.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">${eco['costo_anio']:,.0f}</td>
        </tr>
        <tr style="background:#EAFAF1">
          <td style="padding:.55rem .9rem;font-weight:600;color:{CG}">✅ Óptimo</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{_mu_opt:.4f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{_des_opt:+.1f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">{_sacos_opt_anio:.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">${_costo_opt_mes:,.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace">${_costo_opt_anio:,.0f}</td>
        </tr>
        <tr style="background:#EBF5FB;border-top:2px solid #1B4F72">
          <td style="padding:.55rem .9rem;font-weight:700;color:{CP}">💰 Ahorro</td>
          <td style="padding:.55rem .9rem;text-align:right;color:#7F8C8D">—</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace;font-weight:700;color:{CG}">{_reduccion_g:.1f} g menos</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace;font-weight:700;color:{CG}">{_ahorro_sacos:.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace;font-weight:700;color:{CG}">${_ahorro_mes:,.0f}</td>
          <td style="padding:.55rem .9rem;text-align:right;font-family:monospace;font-weight:700;color:{CG}">${_ahorro_anio:,.0f}</td>
        </tr>
      </tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # KPIs de ahorro
    ak1, ak2, ak3, ak4 = st.columns(4)
    with ak1:
        st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-value" style="color:{CG}">${_ahorro_anio:,.0f}</div>
        <div class="kpi-label">Ahorro anual (COP)</div>
        <div class="kpi-sub">${_ahorro_mes:,.0f}/mes</div></div>""",
        unsafe_allow_html=True)

    with ak2:
        st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-value" style="color:{CG}">{_pct_ahorro:.1f}%</div>
        <div class="kpi-label">Reducción de pérdida</div>
        <div class="kpi-sub">Vs. situación actual</div></div>""",
        unsafe_allow_html=True)

    with ak3:
        st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-value" style="color:{CG}">{_ahorro_sacos:.0f}</div>
        <div class="kpi-label">Sacos recuperados/año</div>
        <div class="kpi-sub">{_ahorro_sacos*40:,.0f} kg de producto</div></div>""",
        unsafe_allow_html=True)

    with ak4:
        _roi_meses = (eco["costo_anio"] / max(_ahorro_anio, 1e-9)) * 12 if _ahorro_anio > 0 else float("inf")
        _roi_txt   = f"{_roi_meses:.1f} meses" if _roi_meses < 120 else "N/A"
        st.markdown(f"""<div class="kpi-card {'green' if _ahorro_anio>0 else 'yellow'}">
        <div class="kpi-value" style="color:{CG if _ahorro_anio>0 else CY}">{_roi_txt}</div>
        <div class="kpi-label">Payback implícito</div>
        <div class="kpi-sub">Pérdida actual / ahorro anual</div></div>""",
        unsafe_allow_html=True)

    # Alerta resumen
    if _ahorro_anio > 0:
        st.markdown(render_alarm("ok",
            f"<strong>📌 Conclusión estadística:</strong> La empresa está sobrellenando por seguridad. "
            f"Estadísticamente, es posible operar con una media de <strong>{_mu_opt:.4f} kg</strong> "
            f"({_des_opt:+.1f} g sobre nominal) manteniendo la probabilidad de rechazo del lote "
            f"de <strong>{_lote} sacos</strong> en "
            f"≤ <strong>{st.session_state['eco_p_rechazo']:.3f}%</strong> — prácticamente nula. "
            f"Esto representa un ahorro de <strong>${_ahorro_anio:,.0f} COP/año</strong>, "
            f"equivalente a recuperar <strong>{_ahorro_sacos:.0f} sacos/año</strong> de producto."
        ), unsafe_allow_html=True)
    else:
        st.markdown(render_alarm("info",
            "ℹ️ Con los parámetros actuales, la media de Fase I ya está en o por debajo de μ*. "
            "Reduce la probabilidad de rechazo aceptable (p_max) o aumenta el tamaño del lote "
            "para encontrar margen de optimización."
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Botón exportar reporte completo (aquí sí tenemos eco disponible)
    excel_rep = export_excel(s, eco)
    st.download_button(
        "📥 Exportar Reporte Completo a Excel", excel_rep,
        "reporte_CEP_Molinos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )



# ─────────────────────────────────────────────────────────────────────────────
# ROUTER — muestra la sección activa
# ─────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO: MUESTREO POR VARIABLES
# ══════════════════════════════════════════════════════════════════════════════
def page_muestreo():
    import math
    from scipy.stats import norm
    import numpy as np
    import plotly.graph_objects as go
    import pandas as pd

    CG = "#27AE60"; CY = "#F39C12"; CR = "#E74C3C"; CB = "#2980B9"

    st.markdown("""
    <style>
    .ms-section{background:linear-gradient(135deg,#1B4F72,#154360);color:white;
        padding:1.1rem 1.4rem;border-radius:12px;margin-bottom:1.2rem;
        font-size:1.05rem;font-weight:700}
    .ms-info{background:#EBF5FB;border-left:4px solid #2980B9;padding:.9rem 1.1rem;
        border-radius:8px;margin-bottom:1rem;font-size:.88rem}
    .ms-warn{background:#FEF9E7;border-left:4px solid #F39C12;padding:.9rem 1.1rem;
        border-radius:8px;margin-bottom:1rem;font-size:.88rem}
    .ms-kpi{background:white;border-radius:12px;padding:.9rem 1rem;text-align:center;
        box-shadow:0 2px 8px rgba(0,0,0,.08);border-top:4px solid #2980B9;margin-bottom:.5rem}
    .ms-kpi-val{font-size:1.7rem;font-weight:800;line-height:1.1}
    .ms-kpi-lbl{font-size:.72rem;color:#7F8C8D;text-transform:uppercase;
        letter-spacing:.6px;margin-top:.25rem}
    .ms-kpi-sub{font-size:.75rem;color:#95A5A6;margin-top:.15rem}
    .ms-placeholder{background:#F4F6F7;border:2px dashed #BDC3C7;border-radius:12px;
        padding:2rem;text-align:center;color:#7F8C8D;font-size:.9rem;margin-top:1rem}
    </style>""", unsafe_allow_html=True)

    # HEADER
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1B4F72,#154360);color:white;
         padding:1.4rem 1.8rem;border-radius:14px;margin-bottom:1.5rem">
      <div style="font-size:1.35rem;font-weight:800;letter-spacing:-.5px">
        📦 Muestreo por Variables — Diseño de Planes para Procesos Continuos
      </div>
      <div style="font-size:.82rem;opacity:.8;margin-top:.35rem">
        Distribución normal · Curva OC por variables · Diseño de n · Riesgos α / β
      </div>
    </div>""", unsafe_allow_html=True)

    # ── SECCIÓN 1: Parámetros del proceso ─────────────────────────────────────
    st.markdown('<div class="ms-section">⚙️ 1. Parámetros del Proceso</div>',
                unsafe_allow_html=True)
    st.markdown("""<div class="ms-info">
    Valores autollenados desde Fase I del proyecto. Editables para análisis manual.<br>
    El módulo trabaja con <b>variables continuas de peso (kg)</b>, no con clasificación
    defectuoso/no defectuoso.</div>""", unsafe_allow_html=True)

    s = st.session_state
    _mu0_def  = float(s["xbar_bar"])  if s.get("xbar_bar", 0) != 0 else 40.3845
    _sig_def  = float(s["sigma_st"])  if s.get("sigma_st", 0) != 0 else 0.5663
    _lsl_def  = float(s.get("cap_lsl", 39.50))
    _usl_def  = float(s.get("cap_usl", 40.50))
    _nom_def  = float(s.get("cap_nominal", 40.00))

    c1, c2, c3 = st.columns(3)
    with c1:
        _mu0 = st.number_input("μ₀ — Media del proceso (kg)", value=_mu0_def,
                               format="%.4f", help="Autollenado desde Fase I. Editable.")
        _sig = st.number_input("σ — Desv. estándar proceso (kg)", min_value=0.0001,
                               value=_sig_def, format="%.4f",
                               help="σ̂ = R̄/d₂ de Fase I. Editable.")
    with c2:
        _LSL = st.number_input("LSL — Límite inf. especificación (kg)",
                               value=_lsl_def, format="%.2f")
        _USL = st.number_input("USL — Límite sup. especificación (kg)",
                               value=_usl_def, format="%.2f")
        _nom = st.number_input("Nominal (kg)", value=_nom_def, format="%.2f")
    with c3:
        _alpha = st.number_input("α — Riesgo productor", min_value=0.001,
                                 max_value=0.30, value=0.05, format="%.3f",
                                 help="P(rechazar lote bueno) — Error Tipo I")
        _beta  = st.number_input("β — Riesgo consumidor", min_value=0.001,
                                 max_value=0.30, value=0.10, format="%.3f",
                                 help="P(aceptar lote malo) — Error Tipo II")
        _delta_sigma = st.number_input("Δμ — Cambio detectable (en σ)", min_value=0.05,
                                       max_value=5.0, value=0.5, format="%.2f",
                                       help="Desplazamiento mínimo a detectar en unidades de σ")
        _n_eval = st.number_input("n — Tamaño de muestra a evaluar", min_value=1,
                                  value=5, step=1, format="%d")

    _delta_kg = _delta_sigma * _sig   # desplazamiento real en kg
    _mu1      = _mu0 + _delta_kg      # media alternativa

    st.markdown(f"""<div class="ms-info">
    <b>Proceso real:</b> μ₀ = {_mu0:.4f} kg · σ = {_sig:.4f} kg ·
    Δμ = {_delta_sigma:.2f}σ = {_delta_kg:.4f} kg →
    μ₁ = {_mu1:.4f} kg</div>""", unsafe_allow_html=True)
    st.markdown("---")

    # ── Cálculos base ─────────────────────────────────────────────────────────
    Za2   = norm.ppf(1.0 - _alpha / 2.0)   # two-sided
    Za1   = norm.ppf(1.0 - _alpha)          # one-sided
    Zb    = norm.ppf(1.0 - _beta)
    d     = _delta_sigma                    # d = Δμ/σ

    # Potencia con n evaluado (two-sided)
    _se   = _sig / math.sqrt(_n_eval)
    _UCL  = _mu0 + Za2 * _se
    _LCL  = _mu0 - Za2 * _se
    # P(rechazar H0 | μ = μ1) — two-sided
    pot_upper = 1.0 - norm.cdf((_UCL - _mu1) / _se)
    pot_lower = norm.cdf((_LCL - _mu1) / _se)
    _potencia = pot_upper + pot_lower
    _beta_real = 1.0 - _potencia

    # n diseñado (fórmula exacta two-sided)
    _n_dis = math.ceil(((Za2 + Zb) / d) ** 2)
    _n_dis = max(2, _n_dis)

    # ── SECCIÓN 2: Potencia y evaluación del plan ──────────────────────────────
    st.markdown('<div class="ms-section">📊 2. Potencia y Evaluación del Plan</div>',
                unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    for col, sym, val, color, lbl, sub in [
        (k1, "d", f"{d:.3f}", CB, "Tamaño de efecto",
         f"Δμ/σ = {_delta_kg:.4f}/{_sig:.4f}"),
        (k2, f"{_potencia*100:.1f}%",
         f"{_potencia*100:.1f}%", CG if _potencia >= 0.80 else CY if _potencia >= 0.60 else CR,
         "Potencia (1−β)", f"n={_n_eval} · Obj ≥ {(1-_beta)*100:.0f}%%"),
        (k3, f"{_beta_real:.4f}",
         f"{_beta_real:.4f}", CG if _beta_real <= _beta else CR,
         "β real", f"Obj ≤ {_beta:.3f}  {'✅' if _beta_real <= _beta else '❌'}"),
        (k4, f"±{Za2*_se*1000:.1f} g",
         f"±{Za2*_se*1000:.1f} g", CB, "Semiancho IC (n evaluado)",
         f"x̄ ± Zα/2·σ/√{_n_eval}"),
    ]:
        with col:
            st.markdown(f"""<div class="ms-kpi" style="border-top-color:{color}">
              <div class="ms-kpi-val" style="color:{color}">{val}</div>
              <div class="ms-kpi-lbl">{lbl}</div>
              <div class="ms-kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    # Diagnóstico
    if _potencia >= 1 - _beta:
        bg, brd = "#D5F5E3", CG
        msg = (f"✅ <b>n = {_n_eval} detecta el cambio Δμ = {_delta_sigma:.2f}σ con potencia "
               f"{_potencia*100:.1f}%%</b> (objetivo ≥ {(1-_beta)*100:.0f}%%).")
    elif _potencia >= 0.60:
        bg, brd = "#FEF9E7", CY
        msg = (f"⚠️ <b>Potencia moderada {_potencia*100:.1f}%%.</b> Para alcanzar "
               f"{(1-_beta)*100:.0f}%% se requiere n ≥ {_n_dis}.")
    else:
        bg, brd = "#FADBD8", CR
        msg = (f"❌ <b>Potencia insuficiente {_potencia*100:.1f}%%.</b> n = {_n_eval} es "
               f"demasiado pequeño. Se recomienda n = {_n_dis}.")
    st.markdown(f"""<div style="background:{bg};border-left:5px solid {brd};
        padding:1rem 1.2rem;border-radius:8px;font-size:.9rem">{msg}</div>""",
        unsafe_allow_html=True)
    st.markdown("---")

    # ── SECCIÓN 3: Diseño automático de n ────────────────────────────────────
    st.markdown('<div class="ms-section">🔧 3. Diseño Automático del Tamaño de Muestra</div>',
                unsafe_allow_html=True)
    st.markdown(f"""<div class="ms-info">
    <b>Fórmula:</b> n = ⌈((Zα/2 + Z₁₋β) / d)²⌉ &nbsp;·&nbsp;
    Zα/2 = {Za2:.3f} · Z₁₋β = {Zb:.3f} · d = {d:.3f}<br>
    n = ⌈(({Za2:.3f} + {Zb:.3f}) / {d:.3f})²⌉ =
    ⌈{((Za2+Zb)/d)**2:.2f}⌉ = <b>{_n_dis}</b>
    </div>""", unsafe_allow_html=True)

    # Tabla potencia vs n
    ns = list(range(2, max(_n_dis + 15, 20)))
    rows = []
    for ni in ns:
        sei = _sig / math.sqrt(ni)
        ucli = _mu0 + Za2 * sei
        lcli = _mu0 - Za2 * sei
        pi = (1 - norm.cdf((ucli - _mu1)/sei)) + norm.cdf((lcli - _mu1)/sei)
        rows.append({"n": ni,
                     "Potencia (1−β) %%": f"{pi*100:.2f}",
                     "β": f"{(1-pi):.4f}",
                     "Semiancho IC (g)": f"{Za2*sei*1000:.2f}",
                     "Cumple potencia": "✅" if pi >= 1-_beta else "❌"})
    df_n = pd.DataFrame(rows)
    st.dataframe(df_n, use_container_width=True, hide_index=True, height=220)

    kn1, kn2, kn3 = st.columns(3)
    _pot_dis = 1 - norm.cdf((_mu0 + Za2*_sig/math.sqrt(_n_dis) - _mu1)/(_sig/math.sqrt(_n_dis))) +                norm.cdf((_mu0 - Za2*_sig/math.sqrt(_n_dis) - _mu1)/(_sig/math.sqrt(_n_dis)))
    for col, sym, val, color, lbl, sub in [
        (kn1, "n recomendado", str(_n_dis), CB, "n recomendado",
         f"Para Δμ={_delta_sigma:.2f}σ · 1−β={1-_beta:.2f}"),
        (kn2, f"{_pot_dis*100:.1f}%%", f"{_pot_dis*100:.1f}%%",
         CG if _pot_dis >= 1-_beta else CY, "Potencia con n recomendado",
         f"β = {1-_pot_dis:.4f}"),
        (kn3, f"±{Za2*_sig/math.sqrt(_n_dis)*1000:.1f} g",
         f"±{Za2*_sig/math.sqrt(_n_dis)*1000:.1f} g", CB,
         "Precisión del IC", f"n={_n_dis}"),
    ]:
        with col:
            st.markdown(f"""<div class="ms-kpi" style="border-top-color:{color}">
              <div class="ms-kpi-val" style="color:{color}">{val}</div>
              <div class="ms-kpi-lbl">{lbl}</div>
              <div class="ms-kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="background:#EBF5FB;border-left:5px solid {CB};
        padding:1rem 1.2rem;border-radius:8px;font-size:.9rem">
      🎯 <b>Se requieren mínimo {_n_dis} muestras</b> para detectar un cambio de
      {_delta_sigma:.2f}σ ({_delta_kg*1000:.1f} g) con potencia ≥ {(1-_beta)*100:.0f}%%.<br>
      Con n = {_n_eval} evaluado se obtiene potencia = {_potencia*100:.1f}%%.
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    # ── SECCIÓN 4: Curva OC por variables ────────────────────────────────────
    st.markdown('<div class="ms-section">📈 4. Curva OC — Muestreo por Variables</div>',
                unsafe_allow_html=True)
    st.markdown("""<div class="ms-info">
    <b>Pa(δ)</b> = probabilidad de aceptar H₀ cuando la media se desplaza δ·σ.<br>
    Pa = Φ(Zα/2 − δ√n) − Φ(−Zα/2 − δ√n) &nbsp;·&nbsp; distribución normal estándar.
    </div>""", unsafe_allow_html=True)

    delta_vals = np.linspace(-3.5, 3.5, 400)  # desplazamiento en unidades de σ

    def oc_curve(n_val):
        pa = []
        for dv in delta_vals:
            pa.append(norm.cdf(Za2 - dv * math.sqrt(n_val)) -
                      norm.cdf(-Za2 - dv * math.sqrt(n_val)))
        return pa

    Pa_eval = oc_curve(_n_eval)
    Pa_rec  = oc_curve(_n_dis)

    fig_oc = go.Figure()
    fig_oc.add_trace(go.Scatter(x=delta_vals, y=Pa_eval, mode="lines",
        name=f"n = {_n_eval} (evaluado)", line=dict(color=CB, width=2.5),
        hovertemplate="δ=%{x:.3f}σ<br>Pa=%{y:.4f}<extra></extra>"))
    fig_oc.add_trace(go.Scatter(x=delta_vals, y=Pa_rec, mode="lines",
        name=f"n = {_n_dis} (recomendado)", line=dict(color=CG, width=2.5, dash="dash"),
        hovertemplate="δ=%{x:.3f}σ<br>Pa=%{y:.4f}<extra></extra>"))

    # Líneas horizontales
    fig_oc.add_hline(y=1-_alpha, line_width=1.5, line_dash="dot", line_color=CG,
                     annotation_text=f"1−α = {1-_alpha:.2f}", annotation_position="right",
                     annotation_font_size=11)
    fig_oc.add_hline(y=_beta, line_width=1.5, line_dash="dot", line_color=CY,
                     annotation_text=f"β = {_beta:.2f}", annotation_position="right",
                     annotation_font_size=11)
    # Línea δ = 0
    fig_oc.add_vline(x=0, line_width=1.2, line_dash="dot", line_color="#BDC3C7",
                     annotation_text="H₀: δ=0", annotation_position="top",
                     annotation_font_size=10)
    # Línea desplazamiento objetivo
    fig_oc.add_vline(x=_delta_sigma, line_width=1.5, line_dash="dot", line_color=CR,
                     annotation_text=f"Δ={_delta_sigma:.2f}σ", annotation_position="top right",
                     annotation_font_size=11)

    fig_oc.add_vrect(x0=-0.5, x1=0.5, fillcolor="rgba(39,174,96,0.06)", line_width=0,
                     annotation_text="Zona aceptable", annotation_position="top left",
                     annotation_font_size=10)
    fig_oc.add_vrect(x0=_delta_sigma, x1=3.5, fillcolor="rgba(231,76,60,0.06)", line_width=0,
                     annotation_text="Zona rechazo", annotation_position="top right",
                     annotation_font_size=10)

    fig_oc.update_layout(
        height=420,
        xaxis=dict(title="δ — Desplazamiento de la media (unidades de σ)",
                   tickformat=".2f", showgrid=True, gridcolor="#F0F3F4"),
        yaxis=dict(title="Pa — Probabilidad de aceptación H₀",
                   tickformat=".2f", range=[0, 1.05], showgrid=True, gridcolor="#F0F3F4"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=52, r=110, t=60, b=48),
        title=dict(text="Curva OC — Plan de Muestreo por Variables (distribución normal)",
                   font_size=13, x=0.01),
        hovermode="x unified"
    )
    st.plotly_chart(fig_oc, use_container_width=True)

    # Tabla puntos clave
    deltas_tabla = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    st.dataframe(pd.DataFrame({
        "δ (σ)": [f"{d:.2f}" for d in deltas_tabla],
        f"Pa n={_n_eval}":  [f"{norm.cdf(Za2 - d*math.sqrt(_n_eval)) - norm.cdf(-Za2 - d*math.sqrt(_n_eval)):.4f}"
                              for d in deltas_tabla],
        f"Pa n={_n_dis}":   [f"{norm.cdf(Za2 - d*math.sqrt(_n_dis))  - norm.cdf(-Za2 - d*math.sqrt(_n_dis)):.4f}"
                              for d in deltas_tabla],
    }), use_container_width=True, hide_index=True)
    st.markdown("---")

    # ── SECCIÓN 5: Interpretación ─────────────────────────────────────────────
    st.markdown('<div class="ms-section">🎓 5. Interpretación del Plan</div>',
                unsafe_allow_html=True)

    interp = []
    if _potencia >= 0.90:
        interp.append((CG, "✅ Alta potencia",
            f"El plan detecta cambios de {_delta_sigma:.2f}σ con potencia {_potencia*100:.1f}%%. "
            "Sensibilidad excelente para el proceso."))
    elif _potencia >= 0.70:
        interp.append((CY, "⚠ Potencia moderada",
            f"Potencia {_potencia*100:.1f}%%. Aumentar n mejora la detección. "
            f"Se recomienda n = {_n_dis}."))
    else:
        interp.append((CR, "❌ Potencia baja",
            f"n = {_n_eval} es insuficiente para detectar Δμ = {_delta_sigma:.2f}σ. "
            f"Use n = {_n_dis}."))

    slope_oc = abs(norm.cdf(Za2 - 1.0*math.sqrt(_n_eval)) -
                   norm.cdf(Za2 - 0.0*math.sqrt(_n_eval)))
    if slope_oc > 0.5:
        interp.append((CG, "✅ Curva OC muy inclinada",
            f"El plan discrimina bien entre μ = μ₀ y μ = μ₀ + σ. Alta sensibilidad."))
    else:
        interp.append((CY, "⚠ Curva OC poco inclinada",
            "El plan tiene dificultad para separar lotes marginales de buenos."))

    if _delta_sigma <= 0.5:
        interp.append((CY, "🔍 Cambio pequeño a detectar",
            f"Δμ = {_delta_sigma:.2f}σ = {_delta_kg*1000:.1f} g requiere muestras grandes. "
            f"n recomendado = {_n_dis}."))
    elif _delta_sigma <= 1.0:
        interp.append((CB, "⚖ Cambio moderado",
            f"Δμ = {_delta_sigma:.2f}σ = {_delta_kg*1000:.1f} g. Plan balanceado."))
    else:
        interp.append((CG, "📏 Cambio grande a detectar",
            f"Δμ = {_delta_sigma:.2f}σ = {_delta_kg*1000:.1f} g. "
            "El plan necesita pocas muestras para detectarlo."))

    if _n_eval >= _n_dis:
        interp.append((CG, "✅ Tamaño de muestra adecuado",
            f"n = {_n_eval} ≥ n recomendado = {_n_dis}. Todos los objetivos cubiertos."))
    else:
        interp.append((CR, "❌ Muestra insuficiente",
            f"n = {_n_eval} < n recomendado = {_n_dis}. "
            "Aumentar la muestra para cumplir los riesgos especificados."))

    for color, title, body in interp:
        st.markdown(f"""<div style="background:white;border-left:5px solid {color};
            padding:.9rem 1.1rem;border-radius:8px;margin-bottom:.7rem;
            box-shadow:0 1px 4px rgba(0,0,0,.06)">
          <b style="color:{color}">{title}</b><br>
          <span style="font-size:.87rem;color:#566573">{body}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:#EBF5FB;border-left:5px solid {CB};
        padding:1rem 1.2rem;border-radius:8px;font-size:.9rem">
      📌 <b>Resumen del plan para el proceso de mogolla:</b><br>
      μ₀ = {_mu0:.4f} kg · σ = {_sig:.4f} kg · LSL = {_LSL:.2f} · USL = {_USL:.2f}<br>
      Para detectar un cambio de <b>{_delta_sigma:.2f}σ ({_delta_kg*1000:.1f} g)</b>
      con potencia ≥ {(1-_beta)*100:.0f}%% se requieren <b>n = {_n_dis} muestras por subgrupo</b>.<br>
      Plan evaluado con n = {_n_eval}: potencia = {_potencia*100:.1f}%% ·
      β real = {_beta_real:.4f}
    </div>""", unsafe_allow_html=True)



if pagina_activa == "capacidad":
    page_capacidad()

elif pagina_activa == "cartas_cep":
    page_cartas_cep()

elif pagina_activa == "diagnostico":
    page_diagnostico()

elif pagina_activa == "potencia":
    page_potencia()

elif pagina_activa == "monitoreo":
    page_monitoreo()

elif pagina_activa == "muestreo":
    page_muestreo()

elif pagina_activa == "eco_analisis":
    page_eco_analisis()
