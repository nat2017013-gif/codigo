"""
=============================================================================
  MÓDULO: visualizaciones.py
  Figuras Plotly para el sistema CEP
  Molinos Santa Marta S.A.S.
=============================================================================
  Funciones exportadas:
      fig_histogram(s)
      fig_xbar(s)
      fig_r(s)
      fig_power(s, n_prop, freq_min)
      fig_gauge(cpk)
      fig_simulador_campanas(s, delta_sigma, signo, freq_min)
      fig_campanas_potencia(mu0, sigma, n, UCL, LCL, mu1)
=============================================================================
"""

import numpy as np
from scipy import stats
import plotly.graph_objects as go

from calculos_cep import LSL, USL, NOMINAL, CONTROL_CONSTANTS
from interfaz_estilos import CP, CR, CG, CY, CN



# ─────────────────────────────────────────────────────────────────────────────
# SISTEMA DE DISEÑO PLOTLY — tokens compartidos entre todas las figuras
# ─────────────────────────────────────────────────────────────────────────────
_FONT_FAMILY  = "DM Sans, system-ui, sans-serif"
_FONT_MONO    = "JetBrains Mono, monospace"
_GRID_COLOR   = "#E8EEF4"          # gris-azulado muy suave — más sutil
_TITLE_COLOR  = "#0F2A40"          # azul profundo — más contraste en título
_AXIS_COLOR   = "#4A5A6A"          # gris medio con ligero tinte azul
_BG_PLOT      = "#FAFCFE"          # fondo levemente tintado — no blanco puro
_BG_PAPER     = "#FFFFFF"

def _base_layout(**overrides):
    """Devuelve un dict de layout con estética industrial consistente."""
    base = dict(
        template      = "plotly_white",
        plot_bgcolor  = _BG_PLOT,
        paper_bgcolor = _BG_PAPER,
        font          = dict(family=_FONT_FAMILY, size=11, color=_AXIS_COLOR),
        title         = dict(
            font=dict(family=_FONT_FAMILY, size=13, color=_TITLE_COLOR, weight="bold"),
            x=0, xanchor="left", pad=dict(l=4, t=6),
        ),
        legend = dict(
            orientation="h",
            y=1.10, x=0,
            bgcolor="rgba(255,255,255,0.85)",
            borderwidth=0,
            font=dict(family=_FONT_FAMILY, size=10.5, color=_AXIS_COLOR),
            itemsizing="constant",
        ),
        hoverlabel = dict(
            bgcolor       = "#FFFFFF",
            bordercolor   = "#C8D8E8",
            font          = dict(family=_FONT_FAMILY, size=12, color="#0F2A40"),
            namelength    = -1,
        ),
        xaxis = dict(
            showgrid=True, gridcolor=_GRID_COLOR, gridwidth=1,
            zeroline=False,
            linecolor="#C8D8E8", linewidth=1, showline=True,
            tickfont=dict(family=_FONT_MONO, size=9.5, color=_AXIS_COLOR),
            title_font=dict(family=_FONT_FAMILY, size=11, color=_AXIS_COLOR),
            ticks="outside", ticklen=4, tickcolor="#C8D8E8",
        ),
        yaxis = dict(
            showgrid=True, gridcolor=_GRID_COLOR, gridwidth=1,
            zeroline=False,
            linecolor="#C8D8E8", linewidth=1, showline=True,
            tickfont=dict(family=_FONT_MONO, size=9.5, color=_AXIS_COLOR),
            title_font=dict(family=_FONT_FAMILY, size=11, color=_AXIS_COLOR),
            ticks="outside", ticklen=4, tickcolor="#C8D8E8",
        ),
        margin = dict(l=56, r=124, t=76, b=56),
        modebar = dict(
            bgcolor="rgba(255,255,255,0)",
            color="#8FA3B3",
            activecolor="#1A3F5C",
            remove=["lasso2d","select2d","resetScale2d"],
            orientation="v",
        ),
    )
    # Aplicar overrides recursivos un nivel
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — HISTOGRAMA DE CAPACIDAD
# ─────────────────────────────────────────────────────────────────────────────

def fig_histogram(s):
    xb, sig, vals = s["xbar_bar"], s["sigma_st"], s["all_vals"]
    # Usar límites efectivos del dict de resultados (dinámicos).
    # Fallback a constantes de módulo para compatibilidad con llamadas antiguas.
    _LSL     = s.get("LSL",     LSL)
    _USL     = s.get("USL",     USL)
    _NOMINAL = s.get("NOMINAL", NOMINAL)

    margin = max(1.5 * sig, 0.6)
    X_MIN  = min(_LSL - margin, xb - 3.5*sig)
    X_MAX  = max(_USL + margin, xb + 3.5*sig)
    xr = np.linspace(X_MIN, X_MAX, 600)

    pdf_curve = stats.norm.pdf(xr, xb, sig)
    y_peak    = pdf_curve.max()
    y_max     = y_peak * 1.30

    # Paleta refinada
    _C_HIST   = "#4A90C4"          # azul medio-claro — barras sin aplastar la curva
    _C_HIST_L = "#FFFFFF"          # borde blanco — separación limpia entre barras
    _C_CURVE  = "#0F2A40"          # azul casi negro — curva normal (máximo contraste)
    _C_ZONE   = "rgba(30,90,142,.05)"   # zona conforme — tinte muy suave
    _C_NC     = "rgba(176,41,32,.18)"   # no conforme — relleno bajo curva, más visible
    _C_LIE    = "#A93226"          # LIE — rojo oscuro corporativo
    _C_LSE    = "#A93226"          # LSE — mismo rojo
    _C_NOM    = "#7F8C8D"          # nominal — gris medio
    _C_XBAR   = "#9A5200"          # x̄ — ámbar oscuro más serio

    fig = go.Figure()

    # ── Zona conforme (fondo suave, sin zonas rojas) ──────────────────────────
    fig.add_vrect(x0=_LSL, x1=_USL, fillcolor=_C_ZONE, line_width=0)

    # ── Histograma ────────────────────────────────────────────────────────────
    fig.add_trace(go.Histogram(
        x=vals, histnorm="probability density", name="Datos muestrales",
        marker=dict(
            color=_C_HIST, opacity=0.45,
            line=dict(color=_C_HIST_L, width=0.8)
        ),
        nbinsx=max(8, len(vals)//3),
        hovertemplate="Rango: %{x}<br>Densidad: %{y:.4f}<extra></extra>"
    ))

    # ── Área bajo curva fuera de especificación (sutil, sin vrect rojo) ───────
    for mask, lbl in [
        (xr <= _LSL, "No conforme  <  LIE"),
        (xr >= _USL, "No conforme  >  LSE"),
    ]:
        if mask.any():
            fig.add_trace(go.Scatter(
                x=xr[mask], y=pdf_curve[mask],
                fill="tozeroy", mode="none",
                fillcolor=_C_NC, name=lbl,
                hoverinfo="skip"
            ))

    # ── Curva normal ajustada ─────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=xr, y=pdf_curve, mode="lines",
        name=f"Normal  σ̂ = {sig:.4f} kg",
        line=dict(color=_C_CURVE, width=2.8),
        hovertemplate="x = %{x:.3f} kg<br>f(x) = %{y:.4f}<extra></extra>"
    ))

    # ── Líneas verticales — separación automática de etiquetas ──────────────
    _vlines = [
        # (valor_x, etiqueta, color, dash, grosor)
        (_LSL,     f"LIE = {_LSL} kg",      _C_LIE,  "solid", 2.2),
        (_USL,     f"LSE = {_USL} kg",      _C_LSE,  "solid", 2.2),
        (_NOMINAL, f"Nom = {_NOMINAL} kg",  _C_NOM,  "dot",   1.5),
        (xb,       f"x̄ = {xb:.4f} kg",     _C_XBAR, "dash",  1.8),
    ]

    # Dibujar las líneas (shape ocupa todo el eje Y en coordenadas "paper")
    for v, _lbl, col, dash, width in _vlines:
        fig.add_shape(
            type="line", xref="x", yref="paper",
            x0=v, x1=v, y0=0, y1=1,
            line=dict(color=col, width=width, dash=dash),
        )

    # ── Separación automática de etiquetas ───────────────────────────────────
    # Umbral: si dos líneas están más próximas que este % del rango X,
    # se escalona la etiqueta más baja en yanchor alternado.
    _x_range   = X_MAX - X_MIN
    _min_gap   = _x_range * 0.07      # 7 % del rango visible
    _label_gap = 0.10                  # separación vertical en coords "paper"

    # Ordenar por posición X para detectar colisiones entre vecinos
    _sorted = sorted(enumerate(_vlines), key=lambda t: t[1][0])

    # Asignar nivel Y a cada etiqueta (0 = más alto, se incrementa por colisión)
    _y_levels = [0] * len(_vlines)
    for k in range(1, len(_sorted)):
        idx_prev, (v_prev, *_) = _sorted[k - 1]
        idx_curr, (v_curr, *_) = _sorted[k]
        if abs(v_curr - v_prev) < _min_gap:
            # El vecino anterior ya tiene nivel asignado; subir uno más
            _y_levels[idx_curr] = _y_levels[idx_prev] + 1

    # Escalonar también hacia atrás si hay tres líneas seguidas muy juntas
    for k in range(len(_sorted) - 2, -1, -1):
        idx_curr, (v_curr, *_) = _sorted[k]
        idx_next, (v_next, *_) = _sorted[k + 1]
        if abs(v_next - v_curr) < _min_gap:
            if _y_levels[idx_curr] >= _y_levels[idx_next]:
                _y_levels[idx_next] = _y_levels[idx_curr] + 1

    # Pintar anotaciones con posición Y calculada
    for (orig_idx, (v, lbl, col, _dash, _w)) in _sorted:
        level   = _y_levels[orig_idx]
        y_paper = 1.0 - level * _label_gap   # baja según nivel
        y_paper = max(0.60, min(1.0, y_paper))

        fig.add_annotation(
            x=v, y=y_paper,
            xref="x", yref="paper",
            text=lbl,
            showarrow=False,
            font=dict(size=10, color=col, family="DM Sans, sans-serif"),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=col,
            borderwidth=1,
            borderpad=5,
            xanchor="left",
            yanchor="top",
            # Pequeño desplazamiento horizontal para no tapar la línea exacta
            xshift=5,
        )

    # ── Título con estado Cpk y Shapiro-Wilk ─────────────────────────────────
    sw = s["sw"]
    sw_txt = (f"  ·  Shapiro-Wilk W={sw['W']:.4f} p={sw['p']:.4f} "
              f"({'normal' if sw['normal'] else 'no normal'})") if sw.get("W") else ""
    cpk = s["Cpk"]
    _tc = "#1A7A4A" if cpk >= 1.33 else "#B7620A" if cpk >= 1.0 else "#C0392B"
    _ts = "CAPAZ" if cpk >= 1.33 else "MARGINAL" if cpk >= 1.0 else "INCAPAZ"
    title_txt = f"Capacidad del Proceso  —  Cpk = {cpk:.3f}  [{_ts}]{sw_txt}"

    fig.update_layout(**_base_layout(
        height = 420,
        title  = dict(text=title_txt, font=dict(size=13, color=_tc)),
        xaxis  = dict(
            title="Peso individual (kg)", range=[X_MIN, X_MAX],
            tickformat=".2f",
            # dtick dinámico: ~10 ticks en el rango visible
            dtick=round(max((X_MAX - X_MIN) / 10, 0.05), 2),
        ),
        yaxis  = dict(title="Densidad de probabilidad", range=[0, y_max]),
        legend = dict(y=1.08, x=0),
        margin = dict(l=52, r=28, t=76, b=52),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — CARTA X̄
# ─────────────────────────────────────────────────────────────────────────────

def fig_xbar(s):
    df = s["df"]; UCL, LCL, CL = s["UCL_x"], s["LCL_x"], s["xbar_bar"]
    z1u, z1l, z2u, z2l = s["z1u"], s["z1l"], s["z2u"], s["z2l"]
    signals   = set(s["signals_x"])
    sens_hits = set(h for r in s.get("sens_rules", []) for h in r["hits"])
    idx       = list(range(1, len(df)+1))

    # Paleta carta X̄
    _C_CL      = "#1E5A8E"          # línea central — azul industrial profundo
    _C_LIMIT   = "#A93226"          # UCL/LCL — rojo corporativo
    _C_SIGMA2  = "#9A5200"          # ±2σ — ámbar oscuro
    _C_SIGMA1  = "#1A6B40"          # ±1σ — verde oscuro
    _C_NORMAL  = "#2D7AC4"          # puntos normales — azul medio
    _C_SENS    = "#C4780A"          # puntos sensibilización — ámbar
    _C_OOC     = "#A93226"          # puntos fuera de control — rojo

    # Colores por punto
    colors = [
        _C_OOC  if i in signals else
        _C_SENS if (j in sens_hits) else
        _C_NORMAL
        for j, i in enumerate(df.index)
    ]
    sizes = [
        14 if i in signals else
        10 if j in sens_hits else
        7
        for j, i in enumerate(df.index)
    ]

    fig = go.Figure()

    # ── Bandas de fondo por zona sigma (más definidas pero sin estridencia) ───
    for y0, y1, col in [
        (LCL, z2l, "rgba(169,50,38,.05)"),
        (z2u, UCL, "rgba(169,50,38,.05)"),
        (z2l, z1l, "rgba(154,82,0,.04)"),
        (z1u, z2u, "rgba(154,82,0,.04)"),
        (z1l, z1u, "rgba(30,90,142,.04)"),
    ]:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=col, line_width=0)

    # ── Líneas de control ─────────────────────────────────────────────────────
    for y, lbl, col, dash, width in [
        (UCL, f"LCS = {UCL:.4f}", _C_LIMIT,  "dash",  2.0),
        (LCL, f"LCI = {LCL:.4f}", _C_LIMIT,  "dash",  2.0),
        (z2u, "+2σ",               _C_SIGMA2, "dot",   1.2),
        (z2l, "−2σ",               _C_SIGMA2, "dot",   1.2),
        (z1u, "+1σ",               _C_SIGMA1, "dot",   1.2),
        (z1l, "−1σ",               _C_SIGMA1, "dot",   1.2),
        (CL,  f"LC = {CL:.4f}",   _C_CL,     "solid", 2.2),
    ]:
        fig.add_hline(
            y=y, line_dash=dash, line_color=col, line_width=width,
            annotation_text=lbl, annotation_position="right",
            annotation_font_size=9, annotation_font_color=col,
            annotation_bgcolor="rgba(250,252,254,0.90)",
        )

    # ── Serie principal ───────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=idx, y=df["xbar"], mode="lines+markers", name="x̄",
        line=dict(color=_C_CL, width=1.8),
        marker=dict(
            color=colors, size=sizes,
            line=dict(color="white", width=1.6),
            symbol="circle",
        ),
        hovertemplate=(
            "<b>Subgrupo %{x}</b><br>"
            "x̄ = %{y:.4f} kg<br>"
            "<extra></extra>"
        ),
    ))

    # ── Overlay: puntos fuera de control con anillo de alerta ────────────────
    if signals:
        si = [i+1 for i, ix in enumerate(df.index) if ix in signals]
        sv = [df["xbar"].iloc[i-1] for i in si]
        fig.add_trace(go.Scatter(
            x=si, y=sv, mode="markers", name="Fuera de control",
            marker=dict(
                color="rgba(169,50,38,0)",   # transparente — solo borde
                size=22, symbol="circle",
                line=dict(color=_C_OOC, width=2.4)
            ),
            hovertemplate="<b>⚠ Fuera LC</b><br>Subgrupo %{x}<br>x̄ = %{y:.4f}<extra></extra>",
        ))

    n_hit = sum(1 for r in s.get("sens_rules", []) if r["hits"])
    fig.update_layout(**_base_layout(
        height = 360,
        title  = dict(text="Carta X̄"),
        xaxis  = dict(title="N° Subgrupo", tickmode="linear", tick0=1, dtick=1),
        yaxis  = dict(title="Peso promedio x̄ (kg)", tickformat=".4f"),
        margin = dict(l=52, r=128, t=68, b=48),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — CARTA R
# ─────────────────────────────────────────────────────────────────────────────

def fig_r(s):
    df = s["df"]; UCL, LCL, CL = s["UCL_r"], s["LCL_r"], s["R_bar"]
    signals = set(s["signals_r"])
    idx     = list(range(1, len(df)+1))

    _C_CL    = "#1A6B40"   # verde industrial oscuro — línea central R
    _C_LIMIT = "#A93226"   # rojo corporativo — UCL/LCL
    _C_NORM  = "#1A6B40"   # puntos normales
    _C_OOC   = "#A93226"   # fuera de control

    colors = [_C_OOC if ix in signals else _C_NORM for ix in df.index]
    sizes  = [14 if ix in signals else 7 for ix in df.index]

    fig = go.Figure()

    # ── Banda de fondo zona de alerta (sutil) ─────────────────────────────────
    fig.add_hrect(y0=UCL * 0.83, y1=UCL, fillcolor="rgba(169,50,38,.05)", line_width=0)

    # ── Líneas de control ─────────────────────────────────────────────────────
    for y, lbl, col, dash, width in [
        (UCL, f"LCS = {UCL:.4f}", _C_LIMIT, "dash",  2.0),
        (CL,  f"R̄  = {CL:.4f}",  _C_CL,   "solid", 2.2),
        (LCL, f"LCI = {LCL:.4f}", _C_LIMIT, "dash",  2.0),
    ]:
        fig.add_hline(
            y=y, line_dash=dash, line_color=col, line_width=width,
            annotation_text=lbl, annotation_position="right",
            annotation_font_size=9, annotation_font_color=col,
            annotation_bgcolor="rgba(250,252,254,0.90)",
        )

    # ── Serie principal ───────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=idx, y=df["R"], mode="lines+markers", name="R",
        line=dict(color=_C_CL, width=1.8),
        marker=dict(
            color=colors, size=sizes, symbol="diamond",
            line=dict(color="white", width=1.6),
        ),
        hovertemplate=(
            "<b>Subgrupo %{x}</b><br>"
            "R = %{y:.4f} kg<br>"
            "<extra></extra>"
        ),
    ))

    # ── Overlay fuera de control ──────────────────────────────────────────────
    if signals:
        si = [i+1 for i, ix in enumerate(df.index) if ix in signals]
        sv = [df["R"].iloc[i-1] for i in si]
        fig.add_trace(go.Scatter(
            x=si, y=sv, mode="markers", name="Fuera de control",
            marker=dict(
                color="rgba(169,50,38,0)", size=22, symbol="diamond",
                line=dict(color=_C_OOC, width=2.4),
            ),
            hovertemplate="<b>⚠ Fuera LC</b><br>Subgrupo %{x}<br>R = %{y:.4f}<extra></extra>",
        ))

    fig.update_layout(**_base_layout(
        height = 300,
        title  = dict(text="Carta R  —  Variabilidad Interna del Subgrupo"),
        xaxis  = dict(title="N° Subgrupo", tickmode="linear", tick0=1, dtick=1),
        yaxis  = dict(title="Rango R (kg)", tickformat=".4f", rangemode="tozero"),
        margin = dict(l=52, r=128, t=62, b=48),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — CURVA DE POTENCIA
# ─────────────────────────────────────────────────────────────────────────────

def fig_power(s, n_prop, freq_min):
    xb, sig, n_cur = s["xbar_bar"], s["sigma_st"], s["n"]
    UCL, LCL = s["UCL_x"], s["LCL_x"]
    deltas = np.linspace(-3*sig, 3*sig, 300)

    def pw(n_val, ucl, lcl):
        se = sig / np.sqrt(n_val)
        return [stats.norm.cdf(lcl, m, se) + (1 - stats.norm.cdf(ucl, m, se)) for m in xb + deltas]

    pow_cur = pw(n_cur, UCL, LCL)
    conp    = CONTROL_CONSTANTS[n_prop]
    pow_pro = pw(n_prop, xb + conp["A2"]*s["R_bar"], xb - conp["A2"]*s["R_bar"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=deltas, y=pow_cur, mode="lines",
                             name=f"n={n_cur} (actual)", line=dict(color=CP, width=2.5)))
    fig.add_trace(go.Scatter(x=deltas, y=pow_pro, mode="lines",
                             name=f"n={n_prop} (propuesto)",
                             line=dict(color=CG, width=2.5, dash="dot")))

    delta_c = NOMINAL - xb
    for d_kg, lbl in [(delta_c, "δ crítico"), (-0.5*sig, "-½σ"), (0.5*sig, "+½σ")]:
        idx_d = np.argmin(np.abs(deltas - d_kg))
        pv    = pow_cur[idx_d]
        arl   = 1 / max(pv, 1e-9); ats = arl * freq_min
        fig.add_annotation(
            x=deltas[idx_d], y=pv,
            text=f"<b>{lbl}</b><br>1-β={pv:.2%}<br>ARL={arl:.1f}<br>ATS={ats:.0f} min",
            showarrow=True, arrowhead=2, arrowcolor=CY,
            bgcolor="white", bordercolor=CY, borderwidth=1,
            font=dict(size=9), ax=45, ay=-50
        )

    fig.add_hline(y=0.90, line_dash="dash", line_color=CY,
                  annotation_text="90% potencia", annotation_font_size=10)
    fig.add_vline(x=0, line_color=CN, line_width=1)
    fig.add_vline(x=delta_c, line_dash="dash", line_color=CR,
                  annotation_text=f"δ crítico={delta_c:.3f} kg", annotation_font_size=9)

    fig.update_layout(**_base_layout(
        height = 400,
        title  = dict(text="Curva de Potencia  —  ARL y ATS por desplazamiento"),
        xaxis  = dict(title="Desplazamiento δ (kg)", tickformat=".3f",
                      zerolinecolor="#D6E4EF", zerolinewidth=1.5, zeroline=True),
        yaxis  = dict(title="Potencia (1 − β)", range=[0, 1.05],
                      tickformat=".0%", tickfont=dict(family=_FONT_MONO, size=10)),
        margin = dict(l=52, r=96, t=68, b=52),
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — GAUGE CPK
# ─────────────────────────────────────────────────────────────────────────────

def fig_gauge(cpk):
    # Colores vivos pero corporativos — máxima legibilidad
    _C_OK   = "#0E7C3A"   # verde intenso
    _C_WARN = "#C47A00"   # naranja/ámbar intenso
    _C_BAD  = "#C0392B"   # rojo fuerte

    # Fondos de zona con más saturación — visibles sin ser agresivos
    _BG_R = "#FADADD"   # rojo tenue saturado
    _BG_Y = "#FDEBD0"   # naranja tenue saturado
    _BG_G = "#D5F5E3"   # verde tenue saturado

    _col = _C_OK if cpk >= 1.33 else _C_WARN if cpk >= 1.0 else _C_BAD

    # Texto de estado debajo del número
    _estado = "CAPAZ" if cpk >= 1.33 else "MARGINAL" if cpk >= 1.0 else "INCAPAZ"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=cpk,
        delta={
            "reference": 1.33, "valueformat": ".3f",
            "increasing": {"color": _C_OK},
            "decreasing": {"color": _C_BAD},
            "font": {"size": 13, "family": _FONT_MONO},
        },
        title={
            "text": f"Índice C<sub>pk</sub><br><span style='font-size:.72em;color:{_col};font-weight:700'>{_estado}</span>",
            "font": {"size": 14, "color": _TITLE_COLOR, "family": _FONT_FAMILY}
        },
        number={
            "valueformat": ".3f",
            "font": {"size": 48, "color": _col, "family": _FONT_MONO},
        },
        gauge={
            "axis": {
                "range": [0, 2],
                "tickwidth": 1.5,
                "tickcolor": "#8FA3B3",
                "tickfont": {"size": 9, "family": _FONT_MONO, "color": _AXIS_COLOR},
                "tickvals": [0, 0.5, 1.0, 1.33, 1.67, 2.0],
                "ticktext": ["0", "0.5", "1.0", "1.33", "1.67", "2.0"],
            },
            "bar":   {"color": _col, "thickness": 0.32},
            "bgcolor": "#FAFCFE",
            "borderwidth": 0,
            "steps": [
                {"range": [0,    1.0],  "color": _BG_R},
                {"range": [1.0,  1.33], "color": _BG_Y},
                {"range": [1.33, 2.0],  "color": _BG_G},
            ],
            "threshold": {
                "line": {"color": "#0A1E2E", "width": 3.5},
                "thickness": 0.82, "value": 1.33,
            },
        },
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=52, b=16),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=_FONT_FAMILY),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — GRÁFICA DE DOS CAMPANAS (SIMULADOR)
# ─────────────────────────────────────────────────────────────────────────────

def fig_simulador_campanas(s, delta_sigma, signo, freq_min):
    """
    Genera la figura de dos campanas para el simulador de corrimiento.

    Parámetros:
        s           : dict resultado de compute_spc()
        delta_sigma : magnitud del desplazamiento en unidades de σ (float)
        signo       : +1 o -1 (dirección del corrimiento)
        freq_min    : frecuencia de muestreo en minutos

    Retorna:
        fig         : go.Figure
        resultados  : dict con beta, power, ARL0, ARL1, ATS0, ATS1, mu1, delta_kg
    """
    xb   = s["xbar_bar"]
    sig  = s["sigma_st"]
    n_sg = s["n"]
    UCL  = s["UCL_x"]
    LCL  = s["LCL_x"]
    se   = sig / np.sqrt(n_sg)

    mu1      = xb + signo * delta_sigma * sig
    delta_kg = mu1 - xb

    z_UCL = (UCL - mu1) / se
    z_LCL = (LCL - mu1) / se
    beta  = max(0.0, min(stats.norm.cdf(z_UCL) - stats.norm.cdf(z_LCL), 1.0))
    power = 1 - beta

    alpha = 0.0027
    ARL0  = 1 / alpha
    ATS0  = ARL0 * freq_min
    ARL1  = 1 / max(power, 1e-9)
    ATS1  = ARL1 * freq_min

    x_min = min(xb, mu1) - 4*se
    x_max = max(xb, mu1) + 4*se
    xr    = np.linspace(x_min, x_max, 600)
    pdf0  = stats.norm.pdf(xr, xb,  se)
    pdf1  = stats.norm.pdf(xr, mu1, se)
    y_max = max(pdf0.max(), pdf1.max()) * 1.12

    fig = go.Figure()

    # Campana proceso en control
    fig.add_trace(go.Scatter(
        x=xr, y=pdf0, mode="lines", name=f"Proceso en control (μ₀={xb:.4f})",
        line=dict(color=CP, width=2.5),
        hovertemplate="x=%{x:.4f}<br>f(x)=%{y:.4f}<extra>Proceso en control</extra>"
    ))

    # Campana proceso desplazado
    fig.add_trace(go.Scatter(
        x=xr, y=pdf1, mode="lines", name=f"Proceso desplazado (μ₁={mu1:.4f})",
        line=dict(color=CR, width=2.5),
        hovertemplate="x=%{x:.4f}<br>f(x)=%{y:.4f}<extra>Proceso desplazado</extra>"
    ))

    # Área β (no detectada)
    mask_beta = (xr >= LCL) & (xr <= UCL)
    if mask_beta.any():
        xb_zone = xr[mask_beta]; yb_zone = pdf1[mask_beta]
        fig.add_trace(go.Scatter(
            x=np.concatenate([[xb_zone[0]], xb_zone, [xb_zone[-1]]]),
            y=np.concatenate([[0], yb_zone, [0]]),
            fill="toself", mode="none",
            fillcolor="rgba(231,76,60,0.20)",
            name=f"β = {beta:.3f} (no detectado)", hoverinfo="skip"
        ))

    # Área potencia (detectada)
    for mask_pow, label_pow in [((xr < LCL), "Potencia izq."), ((xr > UCL), "Potencia der.")]:
        if mask_pow.any():
            xp = xr[mask_pow]; yp = pdf1[mask_pow]
            if len(xp) > 1:
                fig.add_trace(go.Scatter(
                    x=np.concatenate([[xp[0]], xp, [xp[-1]]]),
                    y=np.concatenate([[0], yp, [0]]),
                    fill="toself", mode="none",
                    fillcolor="rgba(39,174,96,0.35)",
                    name=label_pow, hoverinfo="skip"
                ))

    # Líneas de límites de control
    for xv, lbl, col, dash in [
        (UCL, f"LCS = {UCL:.4f}", CR, "dash"),
        (LCL, f"LCI = {LCL:.4f}", CR, "dash"),
        (xb,  f"μ₀ = {xb:.4f}",  CP, "dot"),
        (mu1, f"μ₁ = {mu1:.4f}", CR, "dot"),
    ]:
        fig.add_vline(x=xv, line_dash=dash, line_color=col, line_width=2,
                      annotation_text=lbl, annotation_position="top",
                      annotation_font_size=10, annotation_font_color=col)

    # Anotaciones de potencia y beta
    pow_color = CG if power >= 0.9 else CY if power >= 0.5 else CR
    fig.add_annotation(
        x=max(xb, mu1) + 1.5*se, y=y_max * 0.7,
        text=f"<b>Potencia = {power:.1%}</b><br>ARL₁ = {ARL1:.1f}<br>ATS₁ = {ATS1:.1f} min",
        showarrow=False, bgcolor="white", bordercolor=CG, borderwidth=2,
        font=dict(size=12, color="#1D6A39")
    )
    fig.add_annotation(
        x=min(xb, mu1) - 1.5*se, y=y_max * 0.7,
        text=f"<b>β = {beta:.4f}</b><br>({beta*100:.1f}% no detectado)",
        showarrow=False, bgcolor="white", bordercolor=CR, borderwidth=2,
        font=dict(size=12, color="#641E16")
    )

    fig.update_layout(**_base_layout(
        height = 440,
        title  = dict(
            text=f"Simulador  —  H₀ (control) vs H₁ (δ = {signo*delta_sigma:.2f}σ)",
        ),
        xaxis  = dict(title="Peso promedio del subgrupo x̄ (kg)", tickformat=".4f"),
        yaxis  = dict(title="Densidad de probabilidad", range=[0, y_max]),
        margin = dict(l=52, r=52, t=76, b=52),
    ))

    resultados = {
        "beta": beta, "power": power, "pow_color": pow_color,
        "ARL0": ARL0, "ARL1": ARL1, "ATS0": ATS0, "ATS1": ATS1,
        "mu1": mu1, "delta_kg": delta_kg,
        "z_UCL": z_UCL, "z_LCL": z_LCL,
    }
    return fig, resultados


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — CAMPANAS H0 vs H1 (ANÁLISIS DE POTENCIA con mu1 manual)
# ─────────────────────────────────────────────────────────────────────────────

def fig_campanas_potencia(mu0, sigma, n, UCL, LCL, mu1):
    """
    Gráfica de dos campanas para el Análisis de Potencia.
    Las distribuciones son de x̄ (sigma/√n), no de valores individuales.

    Parámetros:
        mu0   : media del proceso bajo control (H0)
        sigma : desviación estándar del proceso (σ̂)
        n     : tamaño del subgrupo
        UCL   : límite de control superior de la carta X̄
        LCL   : límite de control inferior de la carta X̄
        mu1   : nueva media propuesta (H1)

    Retorna:
        fig       : go.Figure
        resultados: dict con beta, power, ARL0, ARL1
    """
    se    = sigma / np.sqrt(n)          # error estándar de x̄
    alpha = 2 * (1 - stats.norm.cdf(3)) # ≈ 0.0027 (3-sigma)

    # β = P(LCI < x̄ < LCS | μ = μ1)
    z_u  = (UCL - mu1) / se
    z_l  = (LCL - mu1) / se
    beta  = max(0.0, min(stats.norm.cdf(z_u) - stats.norm.cdf(z_l), 1.0))
    power = 1.0 - beta

    ARL0 = 1.0 / alpha
    ARL1 = 1.0 / max(power, 1e-9)

    # Rango del eje X: cubre ambas campanas holgadamente
    span  = max(abs(mu1 - mu0), se) * 1.5
    x_min = min(mu0, mu1) - 4 * se - span * 0.2
    x_max = max(mu0, mu1) + 4 * se + span * 0.2
    xr    = np.linspace(x_min, x_max, 600)

    pdf0  = stats.norm.pdf(xr, mu0, se)
    pdf1  = stats.norm.pdf(xr, mu1, se)
    y_max = max(pdf0.max(), pdf1.max()) * 1.18

    fig = go.Figure()

    # ── Zona β (no detectada): área de H1 entre LCI y LCS
    mask_beta = (xr >= LCL) & (xr <= UCL)
    if mask_beta.any():
        xb_z = xr[mask_beta]; yb_z = pdf1[mask_beta]
        fig.add_trace(go.Scatter(
            x=np.concatenate([[xb_z[0]], xb_z, [xb_z[-1]]]),
            y=np.concatenate([[0],       yb_z,  [0]]),
            fill="toself", mode="none",
            fillcolor="rgba(231,76,60,0.18)",
            name=f"β = {beta:.4f}  (no detectado)",
            hoverinfo="skip"
        ))

    # ── Zona potencia (detectada): colas de H1 fuera de límites
    for mask_p, lbl_p in [((xr < LCL), "Potencia izq."), ((xr > UCL), "Potencia der.")]:
        if mask_p.any():
            xp = xr[mask_p]; yp = pdf1[mask_p]
            if len(xp) > 1:
                fig.add_trace(go.Scatter(
                    x=np.concatenate([[xp[0]], xp, [xp[-1]]]),
                    y=np.concatenate([[0],     yp,  [0]]),
                    fill="toself", mode="none",
                    fillcolor="rgba(39,174,96,0.30)",
                    name=lbl_p, hoverinfo="skip"
                ))

    # ── Campana H0 (azul)
    fig.add_trace(go.Scatter(
        x=xr, y=pdf0, mode="lines",
        name=f"H₀: μ₀ = {mu0:.4f} kg",
        line=dict(color=CP, width=2.5),
        hovertemplate="x̄ = %{x:.4f}<br>f(x̄) = %{y:.4f}<extra>H₀</extra>"
    ))

    # ── Campana H1 (roja)
    fig.add_trace(go.Scatter(
        x=xr, y=pdf1, mode="lines",
        name=f"H₁: μ₁ = {mu1:.4f} kg",
        line=dict(color=CR, width=2.5),
        hovertemplate="x̄ = %{x:.4f}<br>f(x̄) = %{y:.4f}<extra>H₁</extra>"
    ))

    # ── Líneas de límites de control
    for xv, lbl, col, dash in [
        (UCL, f"LCS = {UCL:.4f}", CR, "dash"),
        (LCL, f"LCI = {LCL:.4f}", CR, "dash"),
        (mu0, f"μ₀ = {mu0:.4f}",  CP, "dot"),
        (mu1, f"μ₁ = {mu1:.4f}",  CR, "dot"),
    ]:
        fig.add_vline(x=xv, line_dash=dash, line_color=col, line_width=1.8,
                      annotation_text=lbl, annotation_position="top",
                      annotation_font_size=10, annotation_font_color=col)

    # ── Anotación de resultados
    pow_color = CG if power >= 0.9 else CY if power >= 0.5 else CR
    ann_x     = max(mu0, mu1) + 1.8 * se
    fig.add_annotation(
        x=ann_x, y=y_max * 0.75,
        text=(f"<b>Potencia = {power:.2%}</b><br>"
              f"β = {beta:.4f}<br>"
              f"ARL₀ = {ARL0:.0f}<br>"
              f"ARL₁ = {ARL1:.1f}"),
        showarrow=False,
        bgcolor="white", bordercolor=pow_color, borderwidth=2,
        font=dict(size=11, color="#1B4F72")
    )

    fig.update_layout(**_base_layout(
        height = 420,
        title  = dict(
            text  = (f"H₀ (μ₀={mu0:.4f}) vs H₁ (μ₁={mu1:.4f})  —  "
                     f"Potencia = {power:.2%}"),
            font  = dict(size=13, color=pow_color),
        ),
        xaxis  = dict(title="Peso promedio del subgrupo x̄ (kg)", tickformat=".4f"),
        yaxis  = dict(title="Densidad de probabilidad", range=[0, y_max]),
        margin = dict(l=52, r=52, t=72, b=52),
    ))

    return fig, {"beta": beta, "power": power, "ARL0": ARL0, "ARL1": ARL1,
                 "pow_color": pow_color, "alpha": alpha}
