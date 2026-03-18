# =========================================================
#  funciones.py – Lógica de cálculo del flujo de caja
#  SITU – Sistema de buses urbanos 12 m
# =========================================================

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────
#  UTILIDADES GENÉRICAS
# ─────────────────────────────────────────────

def serie_inflacion(base_anual: float, anios: int, inflacion: float) -> list:
    """Devuelve lista Año1..AñoN aplicando inflación acumulada (t=1 sin inflación)."""
    return [base_anual * ((1.0 + inflacion) ** (t - 1)) for t in range(1, anios + 1)]


def cuota_francesa_mensual(monto: float, tasa_anual: float, plazo_anios: int) -> float:
    """Calcula la cuota mensual de un préstamo con amortización francesa."""
    i = tasa_anual / 12.0
    n = int(plazo_anios * 12)
    if i == 0 or n == 0:
        return monto / n if n > 0 else 0.0
    return monto * i / (1 - (1 + i) ** (-n))


def npv(rate: float, cashflows) -> float:
    """Valor Actual Neto dado una tasa y una serie de flujos (t=0, 1, 2, ...)."""
    return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows))


def irr_biseccion(cashflows, low: float = -0.99, high: float = 10.0,
                  tol: float = 1e-8, max_iter: int = 1_000) -> float:
    """
    Calcula la TIR mediante bisección.
    Retorna np.nan si no converge o no hay cambio de signo.
    """
    def f(r):
        return npv(r, cashflows)

    f_low, f_high = f(low), f(high)
    tries = 0
    while f_low * f_high > 0 and tries < 60:
        high *= 2
        f_high = f(high)
        tries += 1

    if f_low * f_high > 0:
        return np.nan

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return mid


def _cols_anios(anios: int) -> list:
    return [f"Año {i}" for i in range(1, anios + 1)]


def _add_year0(df: pd.DataFrame) -> pd.DataFrame:
    """Inserta columna 'Año 0' con 0.0 si no existe."""
    if "Año 0" not in df.columns:
        df.insert(0, "Año 0", 0.0)
    return df


def calcular_payback(flujos_0aN: np.ndarray) -> str:
    """
    Devuelve el año en que el flujo acumulado se vuelve positivo.
    Retorna 'No recupera' si nunca ocurre en el horizonte.
    """
    acum = np.cumsum(flujos_0aN)
    for i, v in enumerate(acum):
        if v >= 0:
            return f"Año {i}"
    return "No recupera"


# ─────────────────────────────────────────────
#  DEMANDA
# ─────────────────────────────────────────────

def proyectar_demanda(base_demanda: dict, anios: int,
                      tasas_por_anio: list, modo_redondeo: str = "floor") -> pd.DataFrame:
    """
    Proyecta la demanda anual por categoría.

    Parámetros
    ----------
    base_demanda    : dict  {categoría: pasajeros_año1}
    anios           : int   número de años del horizonte
    tasas_por_anio  : list  (anios-1) tasas de crecimiento
    modo_redondeo   : str   'floor' o 'round'

    Retorna DataFrame con índice = categorías + TOTAL, columnas = Año 1..N + TOTAL
    """
    if len(tasas_por_anio) != anios - 1:
        raise ValueError(
            f"tasas_por_anio debe tener {anios - 1} elementos, "
            f"pero tiene {len(tasas_por_anio)}."
        )

    cols = _cols_anios(anios)
    df = pd.DataFrame(0.0, index=list(base_demanda.keys()), columns=cols)

    for k, v in base_demanda.items():
        df.loc[k, "Año 1"] = float(v)

    for t in range(1, anios):
        factor = 1 + float(tasas_por_anio[t - 1])
        prev_col, curr_col = cols[t - 1], cols[t]
        tmp = df[prev_col] * factor
        if modo_redondeo == "floor":
            df[curr_col] = np.floor(tmp)
        else:
            df[curr_col] = np.round(tmp, 0)

    df.loc["TOTAL DEMANDA"] = df.sum(axis=0)
    df["TOTAL"] = df.sum(axis=1)
    return df


def demanda_equivalente_por_regla(demanda_df: pd.DataFrame,
                                   divisores_equivalencia: dict) -> pd.DataFrame:
    """Divide cada categoría por su divisor de equivalencia y totaliza."""
    cats = [c for c in demanda_df.index if c in divisores_equivalencia]
    cols = [c for c in demanda_df.columns if c.startswith("Año")]
    df_eq = demanda_df.loc[cats, cols].astype(float).copy()
    for cat in cats:
        df_eq.loc[cat] = np.round(df_eq.loc[cat] / divisores_equivalencia[cat], 0)
    df_eq.loc["TOTAL DEMANDA EQUIVALENTE"] = df_eq.sum(axis=0)
    df_eq["TOTAL"] = df_eq.sum(axis=1)
    return df_eq


# ─────────────────────────────────────────────
#  INGRESOS
# ─────────────────────────────────────────────

def calcular_ingresos_por_categoria(demanda_df: pd.DataFrame,
                                    tarifas: dict) -> pd.DataFrame:
    """Multiplica demanda × tarifa por categoría y totaliza."""
    cats = [c for c in demanda_df.index if c in tarifas]
    cols = [c for c in demanda_df.columns if c.startswith("Año")]
    ing = pd.DataFrame(0.0, index=cats, columns=cols)
    for cat in cats:
        ing.loc[cat] = demanda_df.loc[cat, cols].astype(float) * float(tarifas[cat])
    ing.loc["TOTAL INGRESOS"] = ing.sum(axis=0)
    ing["TOTAL"] = ing.sum(axis=1)
    return ing


# ─────────────────────────────────────────────
#  COSTOS VARIABLES
# ─────────────────────────────────────────────

def serie_mantenimiento(km_totales: float, costo_km: float, unidades: int,
                         divisor_meses: int, div_pre_7: float,
                         div_post_7: float, anios: int) -> list:
    """
    Calcula la serie anual de costos de mantenimiento.
    Años 1-6 dividen por div_pre_7, años 7-N por div_post_7.
    """
    base_anual = km_totales * costo_km * unidades / divisor_meses
    return [
        base_anual / div_pre_7 if i <= 6 else base_anual / div_post_7
        for i in range(1, anios + 1)
    ]


# ─────────────────────────────────────────────
#  NÚCLEO DE CÁLCULO PRINCIPAL
# ─────────────────────────────────────────────

def calcular_modelo(p: dict) -> dict:
    """
    Ejecuta el modelo completo de flujo de caja para el sistema SITU.

    Parámetros
    ----------
    p : dict  - parámetros del sistema (estructura de SITU_DEFAULT)

    Retorna
    -------
    dict con todos los DataFrames y KPIs listos para la UI.
    """
    # ── Validaciones básicas ─────────────────────────────────────
    anios = int(p["anios"])
    cols  = _cols_anios(anios)

    if any(v <= 0 for v in p["tarifas"].values()):
        raise ValueError("Todas las tarifas deben ser mayores que 0.")
    if p["tasa_descuento"] < 0:
        raise ValueError("La tasa de descuento no puede ser negativa.")
    if p["rend_km_gal_buses"] == 0:
        raise ValueError("El rendimiento de combustible no puede ser 0.")
    if any(abs(t) > 0.5 for t in p["tasas_por_anio"]):
        raise ValueError("Alguna tasa de crecimiento supera +/-50%. Revise los valores.")
    if p["numero_buses"] == 0:
        raise ValueError("El número de buses no puede ser 0.")

    # ── DEMANDA ──────────────────────────────────────────────────
    demanda = proyectar_demanda(
        p["base_demanda"], anios, p["tasas_por_anio"], p["modo_redondeo"]
    )
    demanda_equivalente = demanda_equivalente_por_regla(demanda, p["divisores_equivalencia"])

    # ── INGRESOS ─────────────────────────────────────────────────
    ingresos = calcular_ingresos_por_categoria(
        demanda.loc[list(p["base_demanda"].keys())], p["tarifas"]
    )
    ingresos_equivalentes = calcular_ingresos_por_categoria(
        demanda_equivalente, p["tarifas"]
    )

    serie_ingresos_totales = ingresos.loc["TOTAL INGRESOS", cols].astype(float)

    # ── COSTOS VARIABLES: Mantenimiento ─────────────────────────
    serie_mant_buses = serie_mantenimiento(
        p["km_totales_buses"], p["costo_km_buses"], p["numero_buses"],
        p["divisor_meses"], p["div_pre_7"], p["div_post_7"], anios
    )
    df_mant = pd.DataFrame(
        [serie_mant_buses],
        index=["Mantenimiento (Buses SITU 12 m)"],
        columns=cols
    ).astype(float)
    df_mant.loc["SUBTOTAL MANTENIMIENTO"] = df_mant.sum(axis=0)

    # ── COSTOS VARIABLES: Combustible ────────────────────────────
    km_anual = p["km_totales_buses"] / p["divisor_meses"]
    gal_base = (km_anual * p["numero_buses"]) / p["rend_km_gal_buses"]
    serie_comb = [gal_base * p["precio_galon"] for _ in range(1, anios + 1)]

    df_comb = pd.DataFrame(
        [serie_comb],
        index=["Combustible (Buses SITU)"],
        columns=cols
    ).astype(float)
    df_comb.loc["SUBTOTAL COMBUSTIBLE"] = df_comb.sum(axis=0)

    # ── COSTOS VARIABLES: Neumáticos ─────────────────────────────
    costo_neum_base = (
        p["costo_llanta"] *
        p["numero_buses"] * p["llantas_por_bus"] *
        p["renovaciones_llantas_por_anio"]
    )
    df_neum = pd.DataFrame(
        [serie_inflacion(costo_neum_base, anios, p["inflacion_anual"])],
        index=["Neumáticos"], columns=cols
    ).astype(float)

    # ── COSTOS VARIABLES: Consolidado operativos ─────────────────
    costos_variables_op = pd.concat([df_mant, df_comb, df_neum], axis=0)
    costos_variables_op.loc["SUBTOTAL COSTOS VARIABLES (operativos)"] = (
        costos_variables_op.loc[
            ["SUBTOTAL MANTENIMIENTO", "SUBTOTAL COMBUSTIBLE", "Neumáticos"]
        ].sum(axis=0)
    )
    costos_variables_op["TOTAL"] = costos_variables_op.sum(axis=1)
    costos_variables_op = costos_variables_op.round(2)

    # ── OTROS COSTOS: ITOR ───────────────────────────────────────
    # Solo aplica cuando la tarifa GENERAL supera la tarifa base
    tarifa_actual  = float(p["tarifas"]["GENERAL"])
    tarifa_base    = float(p.get("tarifa_general_base", 0.30))
    aplica_itor    = tarifa_actual > tarifa_base
    serie_oper_recaudo = (
        (serie_ingresos_totales * p["itor_porcentaje_oper_recaudo"]).tolist()
        if aplica_itor else [0.0] * anios
    )
    df_itor = pd.DataFrame(
        [serie_oper_recaudo],
        index=["Costo de Operación y Recaudo (9.95% ingresos)"],
        columns=cols
    ).astype(float)
    df_itor.loc["TOTAL OTROS COSTOS (ITOR)"] = df_itor.sum(axis=0)
    df_itor["TOTAL"] = df_itor.sum(axis=1)
    df_itor = df_itor.round(2)

    # ── TOTAL COSTOS VARIABLES ───────────────────────────────────
    serie_cv_total = (
        costos_variables_op.loc["SUBTOTAL COSTOS VARIABLES (operativos)", cols].astype(float)
        + df_itor.loc["TOTAL OTROS COSTOS (ITOR)", cols].astype(float)
    )
    df_total_cv = pd.DataFrame(
        [serie_cv_total.tolist()], index=["TOTAL COSTOS VARIABLES"], columns=cols
    ).astype(float)
    df_total_cv["TOTAL"] = df_total_cv.sum(axis=1)
    df_total_cv = df_total_cv.round(2)

    # ── COSTOS FIJOS: Financiamiento ─────────────────────────────
    cuota_mensual_bus = cuota_francesa_mensual(
        p["precio_bus"] * p["porcentaje_financiado"],
        p["tasa_interes_anual"], p["plazo_anios_financ"]
    )
    cuota_total_mensual = cuota_mensual_bus * p["numero_buses"]
    serie_financ = [
        cuota_total_mensual * 12 if i <= p["plazo_anios_financ"] else 0.0
        for i in range(1, anios + 1)
    ]
    df_financ = pd.DataFrame(
        [serie_financ], index=["Costos de financiamiento"], columns=cols
    ).astype(float)

    # ── COSTOS FIJOS: Sueldos ────────────────────────────────────
    sueldo_base = (
        p["numero_buses"] * p["choferes_por_bus"] *
        p["salario_mensual"] * 12
    )
    df_sueldos = pd.DataFrame(
        [serie_inflacion(sueldo_base, anios, p["inflacion_anual"])],
        index=["Sueldos (Buses SITU)"],
        columns=cols
    ).astype(float)
    df_sueldos.loc["SUBTOTAL SUELDOS"] = df_sueldos.sum(axis=0)

    # ── COSTOS FIJOS: Gastos Administrativos ─────────────────────
    df_adm_items = pd.DataFrame(p["gastos_adm_items"])
    total_adm_anual_base = float((df_adm_items["cantidad"] * df_adm_items["precio"]).sum()) * 12.0
    df_gastos_adm = pd.DataFrame(
        [serie_inflacion(total_adm_anual_base, anios, p["inflacion_anual"])],
        index=["Gastos Administrativos"], columns=cols
    ).astype(float)

    # ── COSTOS FIJOS: Otros rubros ───────────────────────────────
    seguro_total_anual     = p["seguro_fiel_cumpl"] + p["seguro_todo_riesgo_unidades"]
    serv_basicos_anual     = p["serv_basicos_mensual"] * 12
    total_buses            = int(p["numero_buses"])
    matric_impuestos_anual = total_buses * p["matricula_precio"]

    df_seguro    = pd.DataFrame([[seguro_total_anual]     * anios], index=["Seguro"],                columns=cols).astype(float)
    df_serv      = pd.DataFrame([[serv_basicos_anual]     * anios], index=["Servicios básicos"],     columns=cols).astype(float)
    df_matric    = pd.DataFrame([[matric_impuestos_anual] * anios], index=["Matrícula e impuestos"], columns=cols).astype(float)
    df_otros_adm = pd.DataFrame(
        [serie_inflacion(p["otros_adm_anual"], anios, p["inflacion_anual"])],
        index=["Otros costos administrativos"], columns=cols
    ).astype(float)

    # ── COSTOS FIJOS: Consolidado ─────────────────────────────────
    costos_fijos = pd.concat(
        [df_financ, df_sueldos, df_gastos_adm, df_seguro, df_serv, df_matric, df_otros_adm],
        axis=0
    )
    costos_fijos.loc["TOTAL COSTOS FIJOS"] = costos_fijos.loc[
        ["Costos de financiamiento", "SUBTOTAL SUELDOS", "Gastos Administrativos",
         "Seguro", "Servicios básicos", "Matrícula e impuestos",
         "Otros costos administrativos"]
    ].sum(axis=0)
    costos_fijos["TOTAL"] = costos_fijos.sum(axis=1)
    costos_fijos = costos_fijos.round(2)

    # ── COSTOS TOTALES ────────────────────────────────────────────
    serie_costos_totales = (
        df_total_cv.loc["TOTAL COSTOS VARIABLES", cols].astype(float) +
        costos_fijos.loc["TOTAL COSTOS FIJOS", cols].astype(float)
    )
    df_costos_totales = pd.DataFrame(
        [serie_costos_totales.tolist()], index=["COSTOS TOTALES"], columns=cols
    ).astype(float).round(2)
    df_costos_totales["TOTAL"] = df_costos_totales.sum(axis=1)

    # ── UTILIDAD E IMPUESTO ───────────────────────────────────────
    serie_ub = (
        serie_ingresos_totales -
        df_costos_totales.loc["COSTOS TOTALES", cols].astype(float)
    )
    df_utilidad_bruta = pd.DataFrame(
        [serie_ub.tolist()], index=["UTILIDAD BRUTA"], columns=cols
    ).astype(float).round(2)
    df_utilidad_bruta["TOTAL"] = df_utilidad_bruta.sum(axis=1)

    serie_ir = np.where(serie_ub > 0, serie_ub * p["tasa_impuesto_renta"], 0.0)
    df_imp_renta = pd.DataFrame(
        [serie_ir.tolist()],
        index=["Impuesto a la renta (25% util. > 0)"],
        columns=cols
    ).astype(float).round(2)
    df_imp_renta["TOTAL"] = df_imp_renta.sum(axis=1)

    # ── FLUJO DE CAJA ─────────────────────────────────────────────
    # Equity: aporte inicial sobre el porcentaje no financiado
    aporte_equity = p["precio_bus"] * p["numero_buses"] * p["porcentaje_equity"]
    serie_flujo = (
        serie_ub - df_imp_renta.loc["Impuesto a la renta (25% util. > 0)", cols].astype(float)
    ).tolist()
    df_flujo = pd.DataFrame(
        [[-float(aporte_equity)] + serie_flujo],
        index=["FLUJO DE CAJA"],
        columns=["Año 0"] + cols
    ).astype(float).round(2)
    df_flujo["TOTAL"] = df_flujo.loc[
        "FLUJO DE CAJA",
        [c for c in df_flujo.columns if c.startswith("Año")]
    ].sum()

    # ── FLUJO ACUMULADO ───────────────────────────────────────────
    cols_0aN = [c for c in df_flujo.columns if c.startswith("Año")]
    flujos_0aN = df_flujo.loc["FLUJO DE CAJA", cols_0aN].astype(float).values
    df_flujo_acum = pd.DataFrame(
        [np.cumsum(flujos_0aN).tolist()],
        index=["FLUJO DE CAJA ACUMULADO"],
        columns=cols_0aN
    ).astype(float).round(2)
    df_flujo_acum["TOTAL"] = flujos_0aN.sum()

    # ── AÑADIR AÑO 0 A TABLAS SIN ÉL ────────────────────────────
    for df in [demanda, demanda_equivalente, ingresos, ingresos_equivalentes,
               costos_variables_op, df_itor, df_total_cv,
               costos_fijos, df_costos_totales, df_utilidad_bruta, df_imp_renta]:
        _add_year0(df)

    # ── KPIs ──────────────────────────────────────────────────────
    van   = npv(p["tasa_descuento"], flujos_0aN)
    tir   = irr_biseccion(flujos_0aN)
    flujo_ultimo = flujos_0aN[-1]
    payback      = calcular_payback(flujos_0aN)

    return {
        # DataFrames
        "demanda":               demanda,
        "demanda_equivalente":   demanda_equivalente,
        "ingresos":              ingresos,
        "ingresos_equivalentes": ingresos_equivalentes,
        "costos_variables_op":   costos_variables_op,
        "df_itor":               df_itor,
        "df_total_cv":           df_total_cv,
        "costos_fijos":          costos_fijos,
        "df_costos_totales":     df_costos_totales,
        "df_utilidad_bruta":     df_utilidad_bruta,
        "df_imp_renta":          df_imp_renta,
        "df_flujo":              df_flujo,
        "df_flujo_acum":         df_flujo_acum,
        # Series para gráficos (sin columna TOTAL, con Año 0)
        "cols_0aN":        cols_0aN,
        "cols_anios":      cols,
        "flujos_0aN":      flujos_0aN,
        "serie_ingresos":  ingresos.loc["TOTAL INGRESOS", cols].astype(float).values,
        "serie_costos":    df_costos_totales.loc["COSTOS TOTALES", cols].astype(float).values,
        "serie_cv":        df_total_cv.loc["TOTAL COSTOS VARIABLES", cols].astype(float).values,
        "serie_cf":        costos_fijos.loc["TOTAL COSTOS FIJOS", cols].astype(float).values,
        "serie_costos_sin_itor": (
            costos_variables_op.loc["SUBTOTAL COSTOS VARIABLES (operativos)", cols].astype(float).values +
            costos_fijos.loc["TOTAL COSTOS FIJOS", cols].astype(float).values
        ),
        # KPIs
        "van":          van,
        "tir":          tir,
        "flujo_ultimo": flujo_ultimo,
        "payback":      payback,
        "tarifa_general_activa": tarifa_actual,
    }


# ─────────────────────────────────────────────
#  ANÁLISIS DE SENSIBILIDAD
# ─────────────────────────────────────────────

def tarifa_general_van_cero_situ(precio_galon: float, params: dict,
                                   tol_usd: float = 1.0) -> float:
    """
    Bisección: encuentra la tarifa GENERAL que hace VAN = 0 para el sistema SITU,
    dado un precio_galon fijo. Devuelve np.nan si no hay cruce de cero en [0.01, 10.0].
    """
    import copy

    def van_para(tarifa: float) -> float:
        p = copy.deepcopy(params)
        p["precio_galon"] = precio_galon
        p["tarifas"]["GENERAL"] = tarifa
        return calcular_modelo(p)["van"]

    low, high = 0.01, 10.0
    f_low, f_high = van_para(low), van_para(high)

    if f_low * f_high > 0:
        return np.nan

    for _ in range(50):
        mid = (low + high) / 2.0
        f_mid = van_para(mid)
        if abs(f_mid) < tol_usd:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2.0


# ─────────────────────────────────────────────
#  EXPORTACIÓN A EXCEL
# ─────────────────────────────────────────────

def exportar_excel(resultado: dict, nombre_troncal: str = "SITU",
                   p: dict = None) -> bytes:
    """
    Genera un archivo Excel con:
      - Hoja 1 "Flujo de Caja": todas las secciones financieras en formato vertical.
      - Hoja 2 "Parámetros y Supuestos": supuestos del modelo SITU (si se pasa p).
    """
    import io
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, PatternFill, Alignment

    AZUL   = "1F4E79"
    AZUL_H = "2E86AB"
    GRIS_T = "D6E4F0"
    FMT_USD = "#,##0.00"
    FMT_ENT = "#,##0"

    wb = Workbook()

    # Columnas de años: Año 0, Año 1, ..., Año N
    year_cols = [c for c in resultado["df_flujo"].columns if c.startswith("Año")]

    # ── Helpers ──────────────────────────────────────────────────
    def _title(ws, row, text, ncols):
        if ncols > 1:
            ws.merge_cells(start_row=row, start_column=1,
                           end_row=row, end_column=ncols)
        c = ws.cell(row=row, column=1, value=text)
        c.font = Font(bold=True, color="FFFFFF", size=11)
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[row].height = 17
        return row + 1

    def _hdr(ws, row, labels):
        for j, lbl in enumerate(labels, 1):
            c = ws.cell(row=row, column=j, value=lbl)
            c.font = Font(bold=True, color="FFFFFF", size=9)
            c.fill = PatternFill("solid", fgColor=AZUL_H)
            c.alignment = Alignment(
                horizontal="center" if j > 1 else "left",
                vertical="center", wrap_text=True)
        ws.row_dimensions[row].height = 16
        return row + 1

    def _dat(ws, row, label, values, fmt=FMT_USD):
        lbl = str(label)
        is_tot = lbl.startswith("TOTAL") or lbl.startswith("SUBTOTAL")
        fill = PatternFill("solid", fgColor=GRIS_T) if is_tot else None
        c = ws.cell(row=row, column=1, value=lbl)
        c.font = Font(bold=is_tot, size=9)
        c.alignment = Alignment(horizontal="left")
        if fill:
            c.fill = fill
        for j, v in enumerate(values, 2):
            cell = ws.cell(row=row, column=j, value=v)
            cell.number_format = fmt
            cell.font = Font(bold=is_tot, size=9)
            cell.alignment = Alignment(horizontal="right")
            if fill:
                cell.fill = fill
        return row + 1

    def _section(ws, row, title, df, fmt=FMT_USD):
        ncols = 1 + len(year_cols)
        row = _title(ws, row, title, ncols)
        row = _hdr(ws, row, ["Rubro"] + year_cols)
        for idx in df.index:
            vals = [df.loc[idx, c] if c in df.columns else 0.0
                    for c in year_cols]
            row = _dat(ws, row, idx, vals, fmt=fmt)
        return row + 1  # fila en blanco

    # ── HOJA 1: Flujo de Caja ────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Flujo de Caja"
    row = 1

    # 1. Pasaje por tipo
    if p and "tarifas" in p:
        row = _title(ws1, row, "PASAJE POR TIPO", 2)
        row = _hdr(ws1, row, ["Tipo", "Tarifa (USD)"])
        for tipo, tarifa in p["tarifas"].items():
            ws1.cell(row=row, column=1, value=tipo).font = Font(size=9)
            c = ws1.cell(row=row, column=2, value=float(tarifa))
            c.number_format = FMT_USD
            c.font = Font(size=9)
            c.alignment = Alignment(horizontal="right")
            row += 1
        row += 1

    # 2-13. Secciones financieras
    row = _section(ws1, row, "DEMANDA",
                   resultado["demanda"], fmt=FMT_ENT)
    row = _section(ws1, row, "INGRESOS",
                   resultado["ingresos"], fmt=FMT_USD)
    row = _section(ws1, row, "COSTOS VARIABLES (operativos)",
                   resultado["costos_variables_op"], fmt=FMT_USD)
    row = _section(ws1, row, "OTROS COSTOS (ITOR)",
                   resultado["df_itor"], fmt=FMT_USD)
    row = _section(ws1, row, "TOTAL COSTOS VARIABLES",
                   resultado["df_total_cv"], fmt=FMT_USD)
    row = _section(ws1, row, "COSTOS FIJOS",
                   resultado["costos_fijos"], fmt=FMT_USD)
    row = _section(ws1, row, "COSTOS TOTALES",
                   resultado["df_costos_totales"], fmt=FMT_USD)
    row = _section(ws1, row, "UTILIDAD BRUTA",
                   resultado["df_utilidad_bruta"], fmt=FMT_USD)
    row = _section(ws1, row, "IMPUESTO A LA RENTA",
                   resultado["df_imp_renta"], fmt=FMT_USD)
    row = _section(ws1, row, "FLUJO DE CAJA",
                   resultado["df_flujo"], fmt=FMT_USD)
    row = _section(ws1, row, "FLUJO DE CAJA ACUMULADO",
                   resultado["df_flujo_acum"], fmt=FMT_USD)

    # 14. VAN y TIR
    van  = resultado["van"]
    tir  = resultado["tir"]
    tasa = p["tasa_descuento"] if p else 0.12
    pct  = int(round(tasa * 100))
    row = _title(ws1, row, f"VAN y TIR ({pct}%)", 2)
    row = _hdr(ws1, row, ["Indicador", "Valor"])
    ws1.cell(row=row, column=1, value=f"VAN ({pct}%)").font = Font(size=9)
    c = ws1.cell(row=row, column=2, value=van)
    c.number_format = FMT_USD
    c.alignment = Alignment(horizontal="right")
    row += 1
    ws1.cell(row=row, column=1, value="TIR").font = Font(size=9)
    if not np.isnan(tir):
        c = ws1.cell(row=row, column=2, value=tir)
        c.number_format = "0.00%"
        c.alignment = Alignment(horizontal="right")
    else:
        ws1.cell(row=row, column=2, value="N/A")
    row += 1
    ws1.cell(row=row, column=1, value="Payback").font = Font(size=9)
    ws1.cell(row=row, column=2, value=resultado["payback"]).font = Font(size=9)

    # Dimensiones hoja 1
    ws1.column_dimensions["A"].width = 50
    for j in range(2, 2 + len(year_cols)):
        ws1.column_dimensions[get_column_letter(j)].width = 14
    ws1.freeze_panes = "B3"

    # ── HOJA 2: Parámetros y Supuestos ───────────────────────────
    if p:
        ws2 = wb.create_sheet("Parámetros y Supuestos")
        r = 1

        def _pt(ws, row, text):
            ws.merge_cells(start_row=row, start_column=1,
                           end_row=row, end_column=3)
            c = ws.cell(row=row, column=1, value=text)
            c.font  = Font(bold=True, color="FFFFFF", size=10)
            c.fill  = PatternFill("solid", fgColor=AZUL)
            c.alignment = Alignment(horizontal="left")
            return row + 1

        def _pr(ws, row, name, value, unit=""):
            ws.cell(row=row, column=1, value=name).font = Font(size=9)
            c = ws.cell(row=row, column=2, value=value)
            c.font = Font(size=9)
            c.alignment = Alignment(horizontal="right")
            if isinstance(value, float):
                c.number_format = "#,##0.00"
            elif isinstance(value, int):
                c.number_format = "#,##0"
            ws.cell(row=row, column=3, value=unit).font = Font(
                size=9, color="808080")
            return row + 1

        r = _pt(ws2, r, "FLOTA SITU")
        r = _pr(ws2, r, "Número de buses SITU (12 m)",
                int(p["numero_buses"]), "unidades")
        r = _pr(ws2, r, "Pasajeros por bus por día",
                int(p["pasajeros_por_bus_dia"]), "pax/bus/día")
        r = _pr(ws2, r, "Días de operación anual",
                int(p["dias_operacion_anual"]), "días/año")
        total_pax = p["numero_buses"] * p["pasajeros_por_bus_dia"] * p["dias_operacion_anual"]
        r = _pr(ws2, r, "Total pasajeros Año 1 (calculado)",
                int(total_pax), "pasajeros/año")
        r += 1

        r = _pt(ws2, r, "TARIFAS (USD)")
        for tipo, tarifa in p["tarifas"].items():
            r = _pr(ws2, r, tipo, float(tarifa), "USD/pasajero")
        r += 1

        r = _pt(ws2, r, "DEMANDA BASE (AÑO 1)")
        for cat, dem in p["base_demanda"].items():
            r = _pr(ws2, r, cat, int(dem), "pasajeros/año")
        r += 1

        r = _pt(ws2, r, "DISTRIBUCIÓN DEMANDA (%)")
        for cat, pct_val in p["distribucion_demanda"].items():
            r = _pr(ws2, r, cat, float(pct_val), "%")
        r += 1

        r = _pt(ws2, r, "TASAS DE CRECIMIENTO ANUAL")
        for i, tasa_c in enumerate(p["tasas_por_anio"]):
            r = _pr(ws2, r, f"Año {i+1} -> Año {i+2}",
                    float(round(tasa_c * 100, 4)), "%")
        r += 1

        r = _pt(ws2, r, "COMBUSTIBLE")
        r = _pr(ws2, r, "Precio galón (USD)",
                float(p["precio_galon"]), "USD/galón")
        r = _pr(ws2, r, "Rendimiento buses SITU (12 m)",
                float(p["rend_km_gal_buses"]), "km/galón")
        r += 1

        r = _pt(ws2, r, "MANTENIMIENTO")
        r = _pr(ws2, r, "Km totales buses SITU",
                int(p["km_totales_buses"]), "km/año")
        r = _pr(ws2, r, "Costo/km buses SITU (USD)",
                float(p["costo_km_buses"]), "USD/km")
        r = _pr(ws2, r, "Costo por llanta",
                float(p["costo_llanta"]), "USD")
        r = _pr(ws2, r, "Llantas por bus",
                int(p["llantas_por_bus"]), "llantas")
        r = _pr(ws2, r, "Renovaciones de llantas por año",
                int(p["renovaciones_llantas_por_anio"]), "veces/año")
        r += 1

        r = _pt(ws2, r, "FINANCIAMIENTO")
        r = _pr(ws2, r, "Precio bus SITU (12 m)",
                float(p["precio_bus"]), "USD/bus")
        r = _pr(ws2, r, "Tasa de interés anual",
                float(p["tasa_interes_anual"] * 100), "%")
        r = _pr(ws2, r, "Plazo",
                int(p["plazo_anios_financ"]), "años")
        r = _pr(ws2, r, "% Financiado con deuda",
                float(p["porcentaje_financiado"] * 100), "%")
        r = _pr(ws2, r, "% Equity (capital propio)",
                float(p["porcentaje_equity"] * 100), "%")
        inv_total = p["precio_bus"] * p["numero_buses"]
        r = _pr(ws2, r, "Inversión total flota",
                float(inv_total), "USD")
        r = _pr(ws2, r, "Aporte equity total",
                float(inv_total * p["porcentaje_equity"]), "USD")
        r += 1

        r = _pt(ws2, r, "SUELDOS")
        r = _pr(ws2, r, "Salario mensual chofer",
                float(p["salario_mensual"]), "USD/mes")
        r = _pr(ws2, r, "Choferes por bus",
                float(p["choferes_por_bus"]), "choferes/bus")
        r += 1

        r = _pt(ws2, r, "MACROECONOMÍA")
        r = _pr(ws2, r, "Inflación anual",
                float(p["inflacion_anual"] * 100), "%")
        r = _pr(ws2, r, "Tasa de descuento (VAN)",
                float(p["tasa_descuento"] * 100), "%")
        r = _pr(ws2, r, "ITOR (% sobre ingresos recaudo)",
                float(p["itor_porcentaje_oper_recaudo"] * 100), "%")
        r = _pr(ws2, r, "Tasa impuesto a la renta",
                float(p["tasa_impuesto_renta"] * 100), "%")

        ws2.column_dimensions["A"].width = 44
        ws2.column_dimensions["B"].width = 18
        ws2.column_dimensions["C"].width = 18

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
