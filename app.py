# =========================================================
#  app.py – Aplicación Streamlit
#  Flujo de Caja SITU – Panel Ejecutivo
# =========================================================

import copy
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from funciones import (calcular_modelo, exportar_excel,
                       tarifa_general_van_cero_situ)
from parametros import TOOLTIPS, SITU_DEFAULT

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Flujo de Caja SITU",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# LOGIN DESACTIVADO TEMPORALMENTE PARA REVISIÓN


# ─────────────────────────────────────────────
#  CSS PERSONALIZADO
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Encabezado principal ── */
.main-header {
    background: linear-gradient(135deg, #1F4E79 0%, #2E86AB 100%);
    padding: 1.2rem 1.8rem;
    border-radius: 10px;
    margin-bottom: 1.2rem;
    color: white;
}
.main-header h1 { margin: 0; font-size: 1.7rem; }
.main-header p  { margin: 0.2rem 0 0; opacity: 0.85; font-size: 0.9rem; }

/* ── Tarjetas KPI ── */
.kpi-card {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.kpi-label { font-size: 0.78rem; color: #6c757d; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: #1F4E79; }
.kpi-sub   { font-size: 0.75rem; color: #6c757d; margin-top: 0.2rem; }

/* ── Semaforo ── */
.semaforo { font-size: 2rem; text-align: center; }
.semaforo-label { font-size: 0.85rem; font-weight: 700; text-align: center; }

/* ── Tablas ── */
.stDataFrame { font-size: 0.82rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background-color: #f0f4f8; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  HELPERS DE FORMATO
# ─────────────────────────────────────────────

def fmt_usd(val: float) -> str:
    """Formatea un número como moneda USD con signo."""
    if val >= 0:
        return f"${val:,.0f}"
    return f"-${abs(val):,.0f}"


def fmt_pct(val: float) -> str:
    return f"{val * 100:.2f}%"


def estilo_df(df: pd.DataFrame, entero: bool = False):
    """Aplica formato de moneda o entero a todas las columnas numéricas."""
    fmt = "{:,.0f}" if entero else "${:,.2f}"
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return df.style.format({c: fmt for c in num_cols}, na_rep="—")


def color_filas_totales(styler):
    """Pinta las filas que comienzan con 'TOTAL' o 'SUBTOTAL'."""
    def resaltar(row):
        nombre = str(row.name)
        if nombre.startswith("TOTAL") or nombre.startswith("SUBTOTAL"):
            return ["background-color: #dbe9f7; font-weight: bold"] * len(row)
        return [""] * len(row)
    return styler.apply(resaltar, axis=1)


# ─────────────────────────────────────────────
#  SEMÁFORO DE VIABILIDAD
# ─────────────────────────────────────────────

def semaforo_viabilidad(van: float, tir: float, tasa_descuento: float):
    """Devuelve emoji, color y texto de viabilidad."""
    if np.isnan(tir):
        return "🔴", "red", "No viable (TIR indefinida)"
    if van > 0 and tir > tasa_descuento:
        return "🟢", "green", "Viable"
    if van > 0 or tir > tasa_descuento:
        return "🟡", "orange", "Viable con reservas"
    return "🔴", "red", "No viable"


# ─────────────────────────────────────────────
#  SIDEBAR – PARÁMETROS
# ─────────────────────────────────────────────

def _recalcular_base_demanda(numero_buses: int, pax_dia: int, dias: int,
                              dist: dict) -> dict:
    """Recalcula base_demanda a partir de la fórmula y distribución porcentual."""
    total = numero_buses * pax_dia * dias
    base = {}
    cats = list(dist.keys())
    asignado = 0
    for i, cat in enumerate(cats):
        if i < len(cats) - 1:
            val = int(total * dist[cat] / 100.0)
            base[cat] = val
            asignado += val
        else:
            # La última categoría absorbe el residual para que sumen exacto
            base[cat] = total - asignado
    return base


def render_sidebar() -> dict:
    """Construye el sidebar y retorna el dict de parámetros activos."""
    with st.sidebar:
        st.markdown("## ⚙️ Parámetros del Modelo")

        p = copy.deepcopy(SITU_DEFAULT)

        if st.button("↺ Restablecer valores", use_container_width=True):
            p = copy.deepcopy(SITU_DEFAULT)
            st.rerun()

        st.divider()

        # ── DEMANDA ──────────────────────────────────────────────
        with st.expander("📊 Demanda base (Año 1)", expanded=False):
            st.caption(TOOLTIPS["base_demanda"])

            numero_buses_dem = st.number_input(
                "Número de buses",
                min_value=1, value=int(p["numero_buses"]), step=1,
                help=TOOLTIPS["numero_buses"], key="dem_numero_buses"
            )
            pax_dia = st.number_input(
                "Pasajeros por bus por día",
                min_value=1, value=int(p["pasajeros_por_bus_dia"]), step=1,
                help=TOOLTIPS["pasajeros_por_bus_dia"], key="dem_pax_dia"
            )
            dias_op = st.number_input(
                "Días de operación anual",
                min_value=1, max_value=366, value=int(p["dias_operacion_anual"]), step=1,
                help=TOOLTIPS["dias_operacion_anual"], key="dem_dias_op"
            )
            total_pax = numero_buses_dem * pax_dia * dias_op
            st.info(f"Total Año 1: **{total_pax:,}** pasajeros  \n({numero_buses_dem:,} buses × {pax_dia} pax/día × {dias_op} días)")

            st.markdown("**Distribución por categoría (%)**")
            st.caption("Las proporciones deben sumar 100%.")

            dist_vals = {}
            for cat in list(p["distribucion_demanda"].keys()):
                dist_vals[cat] = st.number_input(
                    cat,
                    min_value=0.0, max_value=100.0,
                    value=float(p["distribucion_demanda"][cat]),
                    step=0.01, format="%.2f",
                    key=f"dist_{cat}"
                )

            suma_dist = sum(dist_vals.values())
            if abs(suma_dist - 100.0) > 0.01:
                st.warning(f"⚠️ Las proporciones suman {suma_dist:.2f}% (deben sumar 100%).")

            # Actualizar parametros con valores de la seccion demanda
            p["numero_buses"]          = numero_buses_dem
            p["pasajeros_por_bus_dia"] = pax_dia
            p["dias_operacion_anual"]  = dias_op
            p["distribucion_demanda"]  = dist_vals
            p["base_demanda"]          = _recalcular_base_demanda(
                numero_buses_dem, pax_dia, dias_op, dist_vals
            )

        # ── TARIFAS ──────────────────────────────────────────────
        with st.expander("💵 Tarifas (USD)", expanded=False):
            st.caption(TOOLTIPS["tarifas"])
            for cat in list(p["tarifas"].keys()):
                p["tarifas"][cat] = st.number_input(
                    cat, min_value=0.01, max_value=10.0,
                    value=float(p["tarifas"][cat]),
                    step=0.01, format="%.2f", key=f"tar_{cat}"
                )

        # ── TASAS DE CRECIMIENTO ─────────────────────────────────
        with st.expander("📈 Tasas de crecimiento anuales", expanded=False):
            st.caption(TOOLTIPS["tasas_por_anio"])
            nuevas_tasas = []
            for i, tasa in enumerate(p["tasas_por_anio"]):
                val = st.number_input(
                    f"Año {i+1} → Año {i+2}",
                    min_value=-0.5, max_value=0.5,
                    value=float(tasa), step=0.0001,
                    format="%.4f", key=f"tasa_{i}"
                )
                nuevas_tasas.append(val)
            p["tasas_por_anio"] = nuevas_tasas

        # ── COMBUSTIBLE ──────────────────────────────────────────
        with st.expander("⛽ Combustible", expanded=False):
            p["precio_galon"] = st.number_input(
                "Precio galón (USD)", min_value=0.01,
                value=float(p["precio_galon"]), step=0.05, format="%.2f",
                help=TOOLTIPS["precio_galon"], key="precio_galon"
            )
            p["rend_km_gal_buses"] = st.number_input(
                "Rendimiento buses SITU (km/gal)", min_value=0.1,
                value=float(p["rend_km_gal_buses"]), step=0.1, format="%.2f",
                help=TOOLTIPS["rend_km_gal_buses"], key="rend_buses"
            )

        # ── MANTENIMIENTO ────────────────────────────────────────
        with st.expander("🔧 Mantenimiento", expanded=False):
            p["km_totales_buses"] = st.number_input(
                "Km totales buses SITU", min_value=1,
                value=int(p["km_totales_buses"]), step=1_000, format="%d",
                help=TOOLTIPS["km_totales_buses"], key="km_buses"
            )
            p["costo_km_buses"] = st.number_input(
                "Costo/km buses SITU (USD)", min_value=0.01,
                value=float(p["costo_km_buses"]), step=0.01, format="%.2f",
                help=TOOLTIPS["costo_km_buses"], key="costo_km_buses"
            )
            p["costo_llanta"] = st.number_input(
                "Costo por llanta (USD)", min_value=1.0,
                value=float(p["costo_llanta"]), step=10.0, format="%.0f",
                help=TOOLTIPS["costo_llanta"], key="costo_llanta"
            )

        # ── FLOTA ────────────────────────────────────────────────
        with st.expander("🚌 Flota", expanded=False):
            # numero_buses se define en la sección Demanda; aquí se muestra como referencia
            st.info(f"Buses SITU: **{p['numero_buses']:,}** unidades  \n(editable en sección Demanda)")
            precio_bus = st.number_input(
                "Costo bus SITU (12 m) USD", min_value=0.0,
                value=float(p["precio_bus"]),
                step=1000.0, format="%.2f",
                help=TOOLTIPS["precio_bus"], key="precio_bus"
            )
            inv_total_flota = p["numero_buses"] * precio_bus
            equity_flota    = inv_total_flota * p["porcentaje_equity"]
            st.metric("Total inversión flota", fmt_usd(inv_total_flota))
            st.metric("Equity (aporte propio)", fmt_usd(equity_flota),
                      help=f"= {p['porcentaje_equity']*100:.0f}% de la inversión total")
            st.caption(f"Km referencia: {p['km_totales_buses']:,} km/año")

            p["precio_bus"] = precio_bus

        # ── FINANCIAMIENTO ───────────────────────────────────────
        with st.expander("🏦 Financiamiento", expanded=False):
            p["tasa_interes_anual"] = st.number_input(
                "Tasa interés anual", min_value=0.001, max_value=0.5,
                value=float(p["tasa_interes_anual"]),
                step=0.001, format="%.4f",
                help=TOOLTIPS["tasa_interes_anual"], key="tasa_interes"
            )
            p["plazo_anios_financ"] = st.number_input(
                "Plazo (años)", min_value=1, max_value=30,
                value=int(p["plazo_anios_financ"]), step=1,
                help=TOOLTIPS["plazo_anios_financ"], key="plazo_financ"
            )
            p["porcentaje_financiado"] = st.slider(
                "% Financiado con deuda", min_value=0.0, max_value=1.0,
                value=float(p["porcentaje_financiado"]), step=0.01,
                format="%.2f%%",
                help=TOOLTIPS["porcentaje_financiado"], key="pct_financiado"
            )
            p["porcentaje_equity"] = 1.0 - p["porcentaje_financiado"]

        # ── SUELDOS Y ADMIN ──────────────────────────────────────
        with st.expander("👥 Sueldos y Administración", expanded=False):
            p["salario_mensual"] = st.number_input(
                "Salario mensual chofer (USD)", min_value=100.0,
                value=float(p["salario_mensual"]), step=50.0, format="%.2f",
                help=TOOLTIPS["salario_mensual"], key="salario"
            )
            p["choferes_por_bus"] = st.number_input(
                "Choferes por bus", min_value=1.0, max_value=5.0,
                value=float(p["choferes_por_bus"]), step=0.1, format="%.1f",
                help=TOOLTIPS["choferes_por_bus"], key="choferes_por_bus"
            )

        # ── MACROECONOMÍA ────────────────────────────────────────
        with st.expander("🌐 Macroeconomía", expanded=False):
            p["inflacion_anual"] = st.number_input(
                "Inflación anual", min_value=0.0, max_value=0.5,
                value=float(p["inflacion_anual"]),
                step=0.001, format="%.4f",
                help=TOOLTIPS["inflacion_anual"], key="inflacion"
            )
            p["tasa_descuento"] = st.number_input(
                "Tasa de descuento (VAN)", min_value=0.001, max_value=0.5,
                value=float(p["tasa_descuento"]),
                step=0.005, format="%.3f",
                help=TOOLTIPS["tasa_descuento"], key="tasa_descuento"
            )
            p["itor_porcentaje_oper_recaudo"] = st.number_input(
                "ITOR – % ingresos (recaudo)", min_value=0.0, max_value=0.5,
                value=float(p["itor_porcentaje_oper_recaudo"]),
                step=0.001, format="%.4f",
                help=TOOLTIPS["itor_porcentaje_oper_recaudo"], key="itor_pct"
            )

        return p


# ─────────────────────────────────────────────
#  PANEL KPIs
# ─────────────────────────────────────────────

def render_kpis(res: dict, p: dict):
    van  = res["van"]
    tir  = res["tir"]
    anios = p["anios"]

    emoji, color_sem, texto_sem = semaforo_viabilidad(van, tir, p["tasa_descuento"])

    c1, c2, c3, c4, c5 = st.columns([1, 1.2, 1.2, 1.2, 1])

    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="semaforo">{emoji}</div>
            <div class="semaforo-label" style="color:{color_sem}">{texto_sem}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        van_fmt = fmt_usd(van)
        color_van = "#1a7a4a" if van > 0 else "#c0392b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">VAN ({p['tasa_descuento']*100:.0f}%)</div>
            <div class="kpi-value" style="color:{color_van}">{van_fmt}</div>
            <div class="kpi-sub">Valor Actual Neto</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        tir_fmt = "N/A" if np.isnan(tir) else fmt_pct(tir)
        color_tir = "#1a7a4a" if (not np.isnan(tir) and tir > p["tasa_descuento"]) else "#c0392b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">TIR</div>
            <div class="kpi-value" style="color:{color_tir}">{tir_fmt}</div>
            <div class="kpi-sub">Tasa Interna de Retorno</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        ultimo = res["flujo_ultimo"]
        color_u = "#1a7a4a" if ultimo > 0 else "#c0392b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Flujo Año {anios}</div>
            <div class="kpi-value" style="color:{color_u}">{fmt_usd(ultimo)}</div>
            <div class="kpi-sub">Último año del horizonte</div>
        </div>""", unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Payback</div>
            <div class="kpi-value">{res['payback']}</div>
            <div class="kpi-sub">Recuperación inversión</div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  GRÁFICOS
# ─────────────────────────────────────────────

PALETA = {
    "azul_oscuro":  "#1F4E79",
    "azul_claro":   "#2E86AB",
    "verde":        "#27AE60",
    "rojo":         "#E74C3C",
    "naranja":      "#F39C12",
    "gris":         "#95A5A6",
}


def fig_ingresos_vs_costos(res: dict) -> go.Figure:
    """Líneas: Ingresos totales vs Costos totales por año."""
    cols = res["cols_anios"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cols, y=res["serie_ingresos"],
        name="Ingresos totales",
        mode="lines+markers",
        line=dict(color=PALETA["verde"], width=2.5),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Ingresos: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=cols, y=res["serie_costos"],
        name="Costos totales",
        mode="lines+markers",
        line=dict(color=PALETA["rojo"], width=2.5),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Costos: $%{y:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        title="Ingresos vs Costos totales",
        xaxis_title="Año", yaxis_title="USD",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", y=1.12),
        template="plotly_white", height=360,
        margin=dict(t=60, b=40, l=60, r=20)
    )
    return fig


def fig_flujo_barras(res: dict) -> go.Figure:
    """Barras coloreadas de flujo de caja anual (verde=positivo, rojo=negativo)."""
    cols  = res["cols_0aN"]
    vals  = res["flujos_0aN"]
    colores = [PALETA["verde"] if v >= 0 else PALETA["rojo"] for v in vals]
    fig = go.Figure(go.Bar(
        x=cols, y=vals,
        marker_color=colores,
        text=[fmt_usd(v) for v in vals],
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="<b>%{x}</b><br>Flujo: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        title="Flujo de Caja Anual",
        xaxis_title="Año", yaxis_title="USD",
        yaxis_tickformat="$,.0f",
        template="plotly_white", height=360,
        margin=dict(t=60, b=40, l=60, r=20)
    )
    return fig


def fig_flujo_acumulado(res: dict) -> go.Figure:
    """Área del flujo de caja acumulado."""
    cols  = res["cols_0aN"]
    acum  = np.cumsum(res["flujos_0aN"])
    if acum[-1] >= 0:
        line_color = PALETA["verde"]
        fill_color = "rgba(39, 174, 96, 0.15)"
    else:
        line_color = PALETA["rojo"]
        fill_color = "rgba(231, 76, 60, 0.15)"
    fig = go.Figure(go.Scatter(
        x=cols, y=acum,
        fill="tozeroy",
        line=dict(color=line_color, width=2.5),
        fillcolor=fill_color,
        hovertemplate="<b>%{x}</b><br>Acumulado: $%{y:,.0f}<extra></extra>",
        name="Flujo acumulado"
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        title="Flujo de Caja Acumulado",
        xaxis_title="Año", yaxis_title="USD",
        yaxis_tickformat="$,.0f",
        template="plotly_white", height=360,
        margin=dict(t=60, b=40, l=60, r=20)
    )
    return fig


def fig_composicion_costos(res: dict) -> go.Figure:
    """Stacked bar: costos variables vs costos fijos por año."""
    cols = res["cols_anios"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cols, y=res["serie_cv"],
        name="Costos Variables",
        marker_color=PALETA["naranja"],
        hovertemplate="<b>%{x}</b><br>CV: $%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=cols, y=res["serie_cf"],
        name="Costos Fijos",
        marker_color=PALETA["azul_claro"],
        hovertemplate="<b>%{x}</b><br>CF: $%{y:,.0f}<extra></extra>"
    ))
    fig.update_layout(
        barmode="stack",
        title="Composición de Costos",
        xaxis_title="Año", yaxis_title="USD",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", y=1.12),
        template="plotly_white", height=360,
        margin=dict(t=60, b=40, l=60, r=20)
    )
    return fig


# ─────────────────────────────────────────────
#  RENDER DE TABLAS
# ─────────────────────────────────────────────

def render_tabla(df: pd.DataFrame, entero: bool = False, titulo: str = ""):
    """Muestra una tabla estilizada con totales resaltados."""
    if titulo:
        st.markdown(f"**{titulo}**")
    styled = color_filas_totales(estilo_df(df, entero=entero))
    st.dataframe(styled, use_container_width=True)


# ─────────────────────────────────────────────
#  INFORME GERENCIAL – PDF
# ─────────────────────────────────────────────

def _txt_kpis(van: float, tir: float, tasa_desc: float,
              payback: str, flujo_ultimo: float, anios: int) -> str:
    """Párrafo de análisis financiero basado en KPIs (texto ASCII para PDF)."""
    tir_s = "no calculada" if np.isnan(tir) else f"{tir*100:.2f}%"
    viable = van > 0 and not np.isnan(tir) and tir > tasa_desc

    if viable:
        ap = ("El sistema SITU presenta indicadores financieros sólidos que respaldan "
              "la viabilidad del proyecto bajo los supuestos actuales del modelo.")
        vc = (f"El Valor Actual Neto de {fmt_usd(van)}, descontado al {tasa_desc*100:.1f}%, "
              "confirma que el proyecto genera valor por encima del costo de oportunidad del capital.")
        tc = (f"La TIR de {tir_s} supera la tasa de descuento, reforzando la rentabilidad "
              "y la conveniencia de la inversión en la flota de buses urbanos.")
    elif van > 0:
        ap = ("El sistema SITU genera valor positivo, aunque con retorno "
              "por debajo del umbral de referencia establecido.")
        vc = (f"El VAN positivo de {fmt_usd(van)} indica recuperación de la inversión a valor "
              f"presente; sin embargo, la TIR de {tir_s} no supera la tasa de descuento del "
              f"{tasa_desc*100:.1f}%.")
        tc = ("Se recomienda revisar la estructura de costos operativos y la política tarifaria "
              "para fortalecer la rentabilidad del sistema.")
    else:
        ap = ("El sistema SITU no alcanza los indicadores mínimos de viabilidad "
              "financiera bajo los supuestos actuales del modelo.")
        vc = (f"El VAN negativo de {fmt_usd(van)} señala que el proyecto no recupera el costo "
              f"de oportunidad del capital a la tasa de descuento del {tasa_desc*100:.1f}%.")
        tc = (f"Con una TIR de {tir_s}, se requieren ajustes estructurales en tarifas, "
              "demanda proyectada o estructura de financiamiento para alcanzar la viabilidad.")

    if payback == "No recupera":
        pc = (f"La inversión inicial no se recupera dentro del horizonte de {anios} años, "
              "lo que representa un riesgo relevante que debe ser ponderado por los inversionistas.")
    else:
        pc = (f"La inversión inicial se recupera en {payback}, dentro del horizonte de "
              f"{anios} años analizado, lo cual es positivo para la gestión del riesgo financiero.")

    fy = (f"El flujo de caja del último año del horizonte ({fmt_usd(flujo_ultimo)}) es "
          + ("positivo, reflejando sostenibilidad operativa al cierre del período analizado."
             if flujo_ultimo > 0
             else "negativo, evidenciando presión financiera en los períodos finales del proyecto."))

    return f"{ap} {vc} {tc} {pc} {fy}"


def _txt_sens(precio_galon: float, van_actual: float,
              tarifa_be: float, tarifa_base: float) -> str:
    """Párrafo de análisis de sensibilidad (texto ASCII para PDF)."""
    if np.isnan(tarifa_be):
        return (f"Con un precio del galón de combustible de ${precio_galon:.2f}, el análisis "
                "no pudo determinar una tarifa de equilibrio para el sistema SITU en el rango "
                "evaluado, lo que puede indicar una estructura de costos con alta presión "
                "financiera que requiere revisión integral del modelo.")

    delta = tarifa_be - tarifa_base

    if van_actual >= 0:
        vc = (f"a la tarifa GENERAL vigente de ${tarifa_base:.2f}, el VAN del sistema es "
              f"positivo ({fmt_usd(van_actual)}), confirmando viabilidad bajo este precio "
              "de combustible.")
    else:
        vc = (f"a la tarifa GENERAL vigente de ${tarifa_base:.2f}, el VAN del sistema es "
              f"negativo ({fmt_usd(van_actual)}), indicando que el costo del combustible "
              "compromete la viabilidad del proyecto.")

    if tarifa_be <= tarifa_base:
        pct = abs(delta) / tarifa_base * 100
        bc = (f"La tarifa de equilibrio calculada es ${tarifa_be:.4f}, es decir ${abs(delta):.4f} "
              f"({pct:.1f}%) por debajo de la tarifa actual. Este margen de seguridad refleja "
              "que el proyecto puede absorber incrementos en el precio del combustible sin "
              "necesidad de un ajuste tarifario inmediato, brindando estabilidad financiera "
              "y predictibilidad en la planificación operativa.")
    else:
        pct = abs(delta) / tarifa_base * 100
        bc = (f"Para alcanzar el punto de equilibrio (VAN = 0) sería necesario incrementar "
              f"la tarifa de ${tarifa_base:.2f} a ${tarifa_be:.4f} por pasajero "
              f"(alza de ${abs(delta):.4f}, equivalente a +{pct:.1f}%).")

    return (f"Con un precio del galón de combustible de ${precio_galon:.2f}, {vc} {bc}")


def _matplotlib_charts(res: dict) -> list:
    """Genera 4 gráficos con matplotlib (backend Agg) y retorna lista de BytesIO PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import io as _io

    VERDE   = "#27AE60"
    ROJO    = "#E74C3C"
    AZUL_C  = "#2E86C1"
    NARANJA = "#E67E22"
    GDASH   = "#888888"

    def _fmt_y(x, _):
        if abs(x) >= 1_000_000:
            return f"${x/1_000_000:.1f}M"
        elif abs(x) >= 1_000:
            return f"${x/1_000:.0f}k"
        return f"${x:.0f}"

    images = []

    # 1. Ingresos vs Costos
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    cols = res["cols_anios"]
    ax.plot(cols, res["serie_ingresos"], color=VERDE, linewidth=2.0,
            marker="o", markersize=4, label="Ingresos totales")
    ax.plot(cols, res["serie_costos"],   color=ROJO,  linewidth=2.0,
            marker="o", markersize=4, label="Costos totales")
    ax.set_title("Ingresos vs Costos totales", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Anio", fontsize=9); ax.set_ylabel("USD", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_y))
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buf = _io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); buf.seek(0); images.append(buf)

    # 2. Flujo de Caja Anual
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    cols0 = res["cols_0aN"]; vals = res["flujos_0aN"]
    colors = [VERDE if v >= 0 else ROJO for v in vals]
    ax.bar(cols0, vals, color=colors, width=0.6)
    ax.axhline(0, color=GDASH, linewidth=0.8, linestyle="--")
    ax.set_title("Flujo de Caja Anual", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Anio", fontsize=9); ax.set_ylabel("USD", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_y))
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buf = _io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); buf.seek(0); images.append(buf)

    # 3. Flujo Acumulado
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    acum = np.cumsum(vals)
    lc = VERDE if acum[-1] >= 0 else ROJO
    x_idx = range(len(cols0))
    ax.plot(list(x_idx), acum, color=lc, linewidth=2.0)
    ax.fill_between(list(x_idx), acum, 0, color=lc, alpha=0.15)
    ax.set_xticks(list(x_idx)); ax.set_xticklabels(cols0, rotation=45, fontsize=7)
    ax.axhline(0, color=GDASH, linewidth=0.8, linestyle="--")
    ax.set_title("Flujo de Caja Acumulado", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Anio", fontsize=9); ax.set_ylabel("USD", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_y))
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buf = _io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); buf.seek(0); images.append(buf)

    # 4. Composición de Costos
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    cols = res["cols_anios"]; x = list(range(len(cols)))
    cv = res["serie_cv"]; cf = res["serie_cf"]
    ax.bar(x, cv, color=NARANJA, label="Costos Variables", width=0.6)
    ax.bar(x, cf, bottom=cv,    color=AZUL_C,  label="Costos Fijos",     width=0.6)
    ax.set_xticks(x); ax.set_xticklabels(cols, rotation=45, fontsize=7)
    ax.set_title("Composicion de Costos", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Anio", fontsize=9); ax.set_ylabel("USD", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_y))
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    buf = _io.BytesIO(); fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig); buf.seek(0); images.append(buf)

    return images


def _build_pdf(res: dict, p: dict,
               precio_galon_sens: float, van_actual_s: float,
               tarifa_be: float, tarifa_base: float) -> bytes:
    """Construye el PDF del informe gerencial (2 páginas) y retorna bytes."""
    from fpdf import FPDF
    import io as _io, datetime

    van     = res["van"]
    tir     = res["tir"]
    payback = res["payback"]
    flujo_u = res["flujo_ultimo"]
    tasa    = p["tasa_descuento"]
    anios   = p["anios"]
    buses   = p["numero_buses"]

    tir_s = "N/A" if np.isnan(tir) else f"{tir*100:.2f}%"
    if np.isnan(tir):
        viab = "No viable (TIR indefinida)"
    elif van > 0 and tir > tasa:
        viab = "VIABLE"
    elif van > 0 or tir > tasa:
        viab = "Viable con reservas"
    else:
        viab = "No viable"

    txt1 = _txt_kpis(van, tir, tasa, payback, flujo_u, anios)
    txt2 = _txt_sens(precio_galon_sens, van_actual_s, tarifa_be, tarifa_base)

    AZUL   = (31, 78, 121)
    BLANCO = (255, 255, 255)
    NEGRO  = (30, 30, 30)
    GRIS_C = (240, 247, 255)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(10, 10, 10)

    # ── PAGINA 1 ───────────────────────────────────────────────────
    pdf.add_page()

    # Banner
    pdf.set_fill_color(*AZUL)
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_text_color(*BLANCO)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 6)
    pdf.cell(190, 10, "Informe Gerencial  -  Flujo de Caja SITU", align="C", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(10, 20)
    pdf.cell(190, 8, f"Sistema de Buses Urbanos 12 m  |  {buses:,} buses  |  Horizonte: {anios} anios", align="C", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(10, 30)
    pdf.cell(190, 6, f"Generado: {datetime.date.today().strftime('%d/%m/%Y')}", align="C")
    pdf.set_text_color(*NEGRO)
    pdf.ln(20)

    # Seccion 1: KPIs
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 8, "1. Indicadores Financieros Clave", ln=True)
    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*NEGRO)

    ca, cb = 80, 110
    for i, (lab, val) in enumerate([
        ("Viabilidad del Proyecto",            viab),
        (f"VAN  (tasa {tasa*100:.1f}%)",       fmt_usd(van)),
        ("TIR",                                tir_s),
        (f"Flujo de Caja - Anio {anios}",       fmt_usd(flujo_u)),
        ("Periodo de Recuperacion (Payback)",  payback),
    ]):
        pdf.set_fill_color(*(GRIS_C if i % 2 == 0 else BLANCO))
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(ca, 8, lab, border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(cb, 8, val, border=1, fill=True, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 6, "Análisis Financiero:", ln=True)
    pdf.set_text_color(*NEGRO)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.multi_cell(0, 5.5, txt1)
    pdf.ln(8)

    # Seccion 2: Sensibilidad
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 8, "2. Análisis de Sensibilidad  -  Precio del Combustible", ln=True)
    pdf.set_draw_color(*AZUL)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_text_color(*NEGRO)

    tbe_s = "N/A" if np.isnan(tarifa_be) else f"${tarifa_be:.4f}"
    dlt_s = "N/A" if np.isnan(tarifa_be) else f"${tarifa_be - tarifa_base:+.4f}"
    for i, (lab, val) in enumerate([
        ("Precio galon de combustible",              f"${precio_galon_sens:.2f}"),
        (f"VAN SITU (tarifa ${tarifa_base:.2f})",    fmt_usd(van_actual_s)),
        ("Tarifa GENERAL para VAN = 0",              tbe_s),
        ("Diferencia vs tarifa actual",              dlt_s),
    ]):
        pdf.set_fill_color(*(GRIS_C if i % 2 == 0 else BLANCO))
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(ca, 8, lab, border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(cb, 8, val, border=1, fill=True, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 6, "Análisis de Sensibilidad:", ln=True)
    pdf.set_text_color(*NEGRO)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.multi_cell(0, 5.5, txt2)

    # ── PAGINA 2: Gráficos ─────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*AZUL)
    pdf.rect(0, 0, 210, 22, "F")
    pdf.set_xy(10, 6)
    pdf.set_text_color(*BLANCO)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(190, 10, "Graficos  |  Sistema SITU", align="C")
    pdf.set_text_color(*NEGRO)

    chart_w, chart_h = 93, 63
    grid  = [(8, 28), (108, 28), (8, 103), (108, 103)]
    names = ["Ingresos vs Costos", "Flujo de Caja Anual",
             "Flujo Acumulado",    "Composicion de Costos"]
    imgs = _matplotlib_charts(res)
    for buf, (x, y), nm in zip(imgs, grid, names):
        pdf.image(buf, x=x, y=y, w=chart_w, h=chart_h)
        pdf.set_xy(x, y + chart_h + 0.5)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(chart_w, 4, nm, align="C")
        pdf.set_text_color(*NEGRO)

    return bytes(pdf.output())


_PDF_VER = "1"   # incrementar cuando cambie el formato/texto del PDF

@st.cache_data(show_spinner="Generando informe PDF…")
def _gen_pdf_informe(p_frozen: str, precio_galon_sens: float,
                     _ver: str = _PDF_VER) -> bytes:
    """Genera el PDF del informe gerencial (cacheable por parámetros)."""
    import copy as _copy
    params  = json.loads(p_frozen)
    res_pdf = calcular_modelo(params)
    tb      = params["tarifas"]["GENERAL"]
    p_test  = _copy.deepcopy(params)
    p_test["precio_galon"] = precio_galon_sens
    va      = calcular_modelo(p_test)["van"]
    tbe     = tarifa_general_van_cero_situ(precio_galon_sens, params)
    return _build_pdf(res_pdf, params, precio_galon_sens, va, tbe, tb)


# ─────────────────────────────────────────────
#  PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────

def render_tab_resumen(res: dict, p: dict):
    """Tab: Resumen Ejecutivo con KPIs, gráficos y análisis de sensibilidad."""
    # ── KPIs ──────────────────────────────────────────────────────
    render_kpis(res, p)
    st.divider()

    # ── Gráficos ──────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_ingresos_vs_costos(res), use_container_width=True)
        st.plotly_chart(fig_flujo_acumulado(res),    use_container_width=True)
    with col2:
        st.plotly_chart(fig_flujo_barras(res),        use_container_width=True)
        st.plotly_chart(fig_composicion_costos(res),  use_container_width=True)

    # ── ANÁLISIS DE SENSIBILIDAD ──────────────────────────────────
    st.divider()
    st.subheader("🔎 Análisis de Sensibilidad")
    st.caption(
        "Modifica el **precio del galón de combustible** y calcula la **tarifa GENERAL** "
        "mínima que hace VAN = 0 para el sistema SITU, "
        "manteniendo todas las demás variables constantes."
    )

    @st.cache_data(show_spinner="Calculando sensibilidad…")
    def _sens_situ(precio_galon: float, p_frozen: str) -> tuple:
        import copy as _copy
        params = json.loads(p_frozen)
        p_test = _copy.deepcopy(params)
        p_test["precio_galon"] = precio_galon
        van_actual = calcular_modelo(p_test)["van"]
        tarifa_be  = tarifa_general_van_cero_situ(precio_galon, params)
        return van_actual, tarifa_be

    precio_galon_sens = st.number_input(
        "Precio del galón de combustible (USD)",
        min_value=0.50, max_value=10.0,
        value=float(p["precio_galon"]), step=0.05, format="%.2f",
        key="sens_precio_galon",
    )

    p_frozen    = json.dumps(p, sort_keys=True, default=str)
    van_actual, tarifa_be = _sens_situ(precio_galon_sens, p_frozen)
    tarifa_base  = p["tarifas"]["GENERAL"]

    c1, c2, c3 = st.columns(3)

    with c1:
        color_van = "#1a7a4a" if van_actual >= 0 else "#c0392b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">VAN SITU<br>(tarifa actual ${tarifa_base:.2f})</div>
            <div class="kpi-value" style="color:{color_van};font-size:1.15rem">{fmt_usd(van_actual)}</div>
            <div class="kpi-sub">Con galón a ${precio_galon_sens:.2f}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        if np.isnan(tarifa_be):
            be_str, color_be = "N/A", "#c0392b"
        else:
            be_str, color_be = f"${tarifa_be:.4f}", "#1F4E79"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tarifa GENERAL<br>para VAN = 0</div>
            <div class="kpi-value" style="color:{color_be};font-size:1.4rem">{be_str}</div>
            <div class="kpi-sub">Break-even SITU</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        if np.isnan(tarifa_be):
            delta_str, color_d = "N/A", "#6c757d"
        else:
            delta     = tarifa_be - tarifa_base
            delta_str = f"${delta:+.4f}"
            color_d   = "#1a7a4a" if delta <= 0 else "#c0392b"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Diferencia vs<br>Tarifa Actual</div>
            <div class="kpi-value" style="color:{color_d};font-size:1.4rem">{delta_str}</div>
            <div class="kpi-sub">Respecto a tarifa base ${tarifa_base:.2f}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    if not np.isnan(tarifa_be):
        if tarifa_be <= tarifa_base:
            st.markdown(f"""
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:6px;
            padding:0.75rem 1rem;color:#155724;font-size:0.95rem">
✅ Con galón a <b>${precio_galon_sens:.2f}</b>, la tarifa actual
(<b>${tarifa_base:.2f}</b>) supera el break-even (<b>${tarifa_be:.4f}</b>).
El proyecto genera VAN positivo.
</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="background:#fff3cd;border:1px solid #ffeeba;border-radius:6px;
            padding:0.75rem 1rem;color:#856404;font-size:0.95rem">
⚠️ Con galón a <b>${precio_galon_sens:.2f}</b>, la tarifa debería subir
de <b>${tarifa_base:.2f}</b> a <b>${tarifa_be:.4f}</b> para alcanzar VAN = 0.
</div>""", unsafe_allow_html=True)

    # ── INFORME GERENCIAL PDF ─────────────────────────────────────
    st.divider()
    st.subheader("📄 Informe Gerencial")
    st.caption(
        "Genera un informe ejecutivo en PDF con indicadores financieros, "
        "análisis experto y gráficos del sistema SITU. "
        "La primera página incluye el análisis y la segunda los gráficos."
    )
    with st.spinner("Preparando informe PDF…"):
        pdf_bytes = _gen_pdf_informe(p_frozen, precio_galon_sens)
    st.download_button(
        label="📥 Descargar Informe Gerencial (PDF)",
        data=pdf_bytes,
        file_name="Informe_SITU.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )


def render_tab_demanda(res: dict, p: dict):
    """Tab: Demanda con fórmula explicativa y tablas proyectadas."""
    st.subheader("Demanda de pasajeros proyectada")

    # ── Fórmula explicativa ───────────────────────────────────────
    buses = p["numero_buses"]
    pax_dia = p["pasajeros_por_bus_dia"]
    dias = p["dias_operacion_anual"]
    total_anio1 = buses * pax_dia * dias
    st.markdown(f"""
<div style="background:#eef4fb;border:1px solid #c3d9f0;border-radius:8px;
            padding:0.85rem 1.2rem;margin-bottom:1rem">
<b>Fórmula de demanda Año 1:</b><br>
<span style="font-size:1.05rem">
{buses:,} buses × {pax_dia} pax/día × {dias} días = <b>{total_anio1:,} pasajeros/año</b>
</span>
</div>""", unsafe_allow_html=True)

    # ── Tabla de distribución Año 1 ───────────────────────────────
    st.markdown("**Distribución de demanda Año 1 por categoría**")
    dist_data = []
    for cat, dem in p["base_demanda"].items():
        pct = dem / total_anio1 * 100 if total_anio1 > 0 else 0
        dist_data.append({"Categoría": cat, "Pasajeros": dem, "%": round(pct, 2)})
    dist_data.append({"Categoría": "TOTAL", "Pasajeros": total_anio1, "%": 100.0})
    df_dist = pd.DataFrame(dist_data).set_index("Categoría")
    st.dataframe(
        df_dist.style.format({"Pasajeros": "{:,.0f}", "%": "{:.2f}%"}),
        use_container_width=True
    )

    st.divider()
    render_tabla(res["demanda"],             entero=True, titulo="Demanda proyectada por categoría (pasajeros)")
    st.divider()
    render_tabla(res["demanda_equivalente"], entero=True, titulo="Demanda equivalente (ajustada por tarifa reducida)")


def render_tab_ingresos(res: dict):
    st.subheader("Ingresos proyectados (USD)")
    render_tabla(res["ingresos"],              titulo="Ingresos por categoría de pasajero")
    st.divider()
    render_tabla(res["ingresos_equivalentes"], titulo="Ingresos equivalentes")


def render_tab_costos(res: dict):
    st.subheader("Costos Variables (USD)")
    render_tabla(res["costos_variables_op"], titulo="Mantenimiento y Combustible (Buses SITU)")
    st.divider()
    render_tabla(res["df_itor"],             titulo="Otros Costos – ITOR")
    st.divider()
    render_tabla(res["df_total_cv"],         titulo="TOTAL Costos Variables")

    st.subheader("Costos Fijos (USD)")
    render_tabla(res["costos_fijos"],        titulo="Financiamiento, Sueldos y Gastos Administrativos")
    st.divider()
    render_tabla(res["df_costos_totales"],   titulo="TOTAL Costos (Variables + Fijos)")


def render_tab_flujo(res: dict):
    st.subheader("Estado de Resultados y Flujo de Caja (USD)")
    render_tabla(res["df_utilidad_bruta"],   titulo="Utilidad Bruta")
    st.divider()
    render_tabla(res["df_imp_renta"],        titulo="Impuesto a la Renta (25%)")
    st.divider()
    render_tabla(res["df_flujo"],            titulo="Flujo de Caja (Año 0 = aporte equity)")
    st.divider()
    render_tabla(res["df_flujo_acum"],       titulo="Flujo de Caja Acumulado")

    # Mini-tabla de indicadores financieros
    st.divider()
    st.subheader("Indicadores Financieros")
    van = res["van"]
    tir = res["tir"]
    df_ind = pd.DataFrame({
        "Indicador": ["VAN", "TIR", "Payback"],
        "Valor":     [
            fmt_usd(van),
            "N/A" if np.isnan(tir) else fmt_pct(tir),
            res["payback"],
        ]
    }).set_index("Indicador")
    st.table(df_ind)


def render_tab_equilibrio(res: dict):
    st.subheader("⚖️ Tarifa de Equilibrio")
    st.markdown(
        "Calcula la **tarifa técnica** que cubre exactamente los costos totales "
        "del sistema SITU, excluyendo el ITOR, en el horizonte del proyecto."
    )

    cols_anios = res["cols_anios"]

    # Totales acumulados en el horizonte del proyecto
    costos_sin_itor_total = float(res["serie_costos_sin_itor"].sum())

    # Demanda total: suma de todos los pasajeros de todas las categorías
    demanda_df = res["demanda"]
    filas_dem  = [r for r in demanda_df.index if r not in ("TOTAL DEMANDA",)]
    demanda_total = float(
        demanda_df.loc[filas_dem, cols_anios].astype(float).values.sum()
    )

    tarifa_equilibrio = costos_sin_itor_total / demanda_total if demanda_total > 0 else 0.0

    # ── Tabla resumen ─────────────────────────────────────────────
    datos = {
        "Rubro": [
            "Costos Totales sin ITOR (USD)",
            "Demanda Total (pasajeros)",
            "Tarifa de Equilibrio / Técnica (USD)",
        ],
        "Valor (acumulado horizonte proyecto)": [
            f"${costos_sin_itor_total:,.2f}",
            f"{demanda_total:,.0f}",
            f"${tarifa_equilibrio:.4f}",
        ],
    }
    import pandas as pd
    df_eq = pd.DataFrame(datos).set_index("Rubro")
    st.table(df_eq)

    # ── Comparación con tarifa actual ────────────────────────────
    tarifa_actual = float(res.get("tarifa_general_activa", 0.30))
    diferencia    = tarifa_actual - tarifa_equilibrio
    color = "green" if diferencia >= 0 else "red"
    icono = "✅" if diferencia >= 0 else "⚠️"
    st.markdown(
        f"{icono} Tarifa actual **${tarifa_actual:.2f}** — "
        f"Diferencia vs equilibrio: <span style='color:{color}'>**${diferencia:+.4f}**</span>",
        unsafe_allow_html=True,
    )
    if diferencia >= 0:
        st.success(f"La tarifa actual cubre los costos. Excedente de ${diferencia:.4f} por pasajero.")
    else:
        st.error(f"La tarifa actual NO cubre los costos. Déficit de ${abs(diferencia):.4f} por pasajero.")


def render_tab_exportar(res: dict, p: dict):
    st.subheader("Exportar resultados")
    st.markdown("""
    Descarga todos los resultados en un archivo Excel con formato financiero.
    Incluye: Demanda, Ingresos, Costos Variables, Costos Fijos, Flujo de Caja, KPIs
    y una hoja de Parámetros y Supuestos del modelo SITU.
    """)

    try:
        excel_bytes = exportar_excel(res, nombre_troncal="SITU", p=p)
        st.download_button(
            label="📥 Descargar Excel",
            data=excel_bytes,
            file_name="FlujoCaja_SITU.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    except ImportError:
        st.error("openpyxl no está instalado. Ejecuta: pip install openpyxl")
    except Exception as e:
        st.error(f"Error generando Excel: {e}")

    st.divider()
    st.subheader("Resumen de parámetros activos")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Flota SITU**")
        st.markdown(f"- Buses: **{p['numero_buses']:,}** unidades")
        st.markdown(f"- Pasajeros/bus/día: **{p['pasajeros_por_bus_dia']:,}**")
        st.markdown(f"- Días operación/año: **{p['dias_operacion_anual']}**")
        total_pax = p["numero_buses"] * p["pasajeros_por_bus_dia"] * p["dias_operacion_anual"]
        st.markdown(f"- Total pasajeros Año 1: **{total_pax:,}**")
        st.markdown("**Demanda base (Año 1)**")
        for cat, val in p["base_demanda"].items():
            st.markdown(f"- {cat}: **{val:,}** pasajeros")
        st.markdown("**Tarifas**")
        for cat, val in p["tarifas"].items():
            st.markdown(f"- {cat}: **${val:.2f}**")
    with col2:
        st.markdown("**Parámetros financieros**")
        st.markdown(f"- Tasa descuento: **{p['tasa_descuento']*100:.1f}%**")
        st.markdown(f"- Tasa interés:   **{p['tasa_interes_anual']*100:.2f}%**")
        st.markdown(f"- Plazo financ.:  **{p['plazo_anios_financ']} años**")
        st.markdown(f"- Inflación:      **{p['inflacion_anual']*100:.2f}%**")
        st.markdown(f"- Precio galón:   **${p['precio_galon']:.2f}**")
        st.markdown(f"- Salario chofer: **${p['salario_mensual']:.0f}/mes**")
        st.markdown(f"- Precio bus:     **${p['precio_bus']:,.2f}**")
        inv = p["precio_bus"] * p["numero_buses"]
        st.markdown(f"- Inversión total flota: **{fmt_usd(inv)}**")


# ─────────────────────────────────────────────
#  APLICACIÓN PRINCIPAL
# ─────────────────────────────────────────────

def main():
    # ── Encabezado ───────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🚌 Flujo de Caja SITU – Panel Ejecutivo</h1>
        <p>Sistema Integrado de Transporte Urbano · Buses 12 m · Modelo financiero a 12 años</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────
    p = render_sidebar()

    # ── Cálculo (con caché basado en parámetros) ─────────────────
    @st.cache_data(show_spinner="Calculando modelo financiero…")
    def _calcular(p_frozen: str) -> dict:
        params = json.loads(p_frozen)
        return calcular_modelo(params)

    try:
        p_frozen = json.dumps(p, sort_keys=True, default=str)
        resultado = _calcular(p_frozen)
    except ValueError as e:
        st.error(f"⚠️ Parámetro inválido: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error en el cálculo: {e}")
        st.stop()

    # ── Pestañas ─────────────────────────────────────────────────
    tab_res, tab_dem, tab_ing, tab_cos, tab_flu, tab_teq, tab_exp = st.tabs([
        "📊 Resumen Ejecutivo",
        "👥 Demanda",
        "💵 Ingresos",
        "📦 Costos",
        "💰 Flujo de Caja",
        "⚖️ Tarifa de Equilibrio",
        "📥 Exportar",
    ])

    with tab_res:
        render_tab_resumen(resultado, p)
    with tab_dem:
        render_tab_demanda(resultado, p)
    with tab_ing:
        render_tab_ingresos(resultado)
    with tab_cos:
        render_tab_costos(resultado)
    with tab_flu:
        render_tab_flujo(resultado)
    with tab_teq:
        render_tab_equilibrio(resultado)
    with tab_exp:
        render_tab_exportar(resultado, p)


if __name__ == "__main__":
    main()
