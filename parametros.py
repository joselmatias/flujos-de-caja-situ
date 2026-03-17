# =========================================================
#  parametros.py – Valores por defecto y configuración
#  SITU – Flujo de Caja Sistema de buses urbanos 12 m
# =========================================================

# ---------- SITU DEFAULT – Parámetros por defecto ----------
SITU_DEFAULT = {
    # --- Identificación ---
    "nombre": "SITU",

    # --- Horizonte temporal ---
    "anios": 10,

    # --- Flota ---
    "numero_buses": 1933,

    # --- Demanda base (Año 1) – calculada como:
    #     pasajeros_por_bus_dia × dias_operacion_anual × numero_buses ---
    "pasajeros_por_bus_dia":   504,
    "dias_operacion_anual":    365,

    # Distribución porcentual de demanda por categoría (sumar 100%)
    "distribucion_demanda": {
        "ESTUDIANTES":              2.16,
        "ADULTOS MAYORES":          6.30,
        "CAPACIDADES ESPECIALES":   2.35,
        "GENERAL":                 89.19,
    },

    # base_demanda calculada: 504 × 365 × 1933 = 355,620,360
    "base_demanda": {
        "ESTUDIANTES":            7_681_400,
        "ADULTOS MAYORES":       22_404_082,
        "CAPACIDADES ESPECIALES": 8_357_078,
        "GENERAL":              317_177_800,
    },

    # --- Tarifas (USD por pasajero) ---
    "tarifas": {
        "ESTUDIANTES":              0.15,
        "ADULTOS MAYORES":          0.15,
        "CAPACIDADES ESPECIALES":   0.15,
        "GENERAL":                  0.30,
    },

    # --- Tasas de crecimiento anuales (11 valores para 12 años) ---
    "tasas_por_anio": [
        0.0091, 0.0091, 0.0090, 0.0089, 0.0088,
        0.0087, 0.0087, 0.0086, 0.0085
    ],

    # --- Equivalencia (divisor por categoría) ---
    "divisores_equivalencia": {
        "ESTUDIANTES":              2,
        "ADULTOS MAYORES":          2,
        "CAPACIDADES ESPECIALES":   3,
        "GENERAL":                  1,
    },

    # --- Modo de redondeo para proyección de demanda ---
    "modo_redondeo": "floor",   # "floor" o "round"

    # --- Costos Variables: Mantenimiento ---
    "divisor_meses":  12,
    "div_pre_7":       2.0,   # divisor años 1-6
    "div_post_7":      1.5,   # divisor años 7-12

    "km_totales_buses": 869_963,
    "costo_km_buses":         0.22,

    # --- Costos Variables: Combustible ---
    "precio_galon":          2.80,
    "rend_km_gal_buses":     7.90,   # km/gal buses 12 m

    # --- Costos Variables: Neumaticos ---
    "costo_llanta":                   450.0,
    "llantas_por_bus":                    6,
    "renovaciones_llantas_por_anio":      1,

    # --- Costos Fijos: Financiamiento ---
    "precio_bus":             156_848.0,
    "tasa_interes_anual":        0.0948,
    "plazo_anios_financ":             7,
    "porcentaje_financiado":       0.80,
    "porcentaje_equity":           0.20,

    # --- Costos Fijos: Sueldos ---
    "salario_mensual":           960.85,
    "choferes_por_bus":             2.4,

    # --- Costos Fijos: Gastos Administrativos (mensuales) ---
    "gastos_adm_items": [
        {"rubro": "Gerente",                 "cantidad": 1, "precio": 2500},
        {"rubro": "Presidente",              "cantidad": 1, "precio": 1800},
        {"rubro": "Asistente (Adm.)",        "cantidad": 1, "precio":  700},
        {"rubro": "Jefe de talento humano",  "cantidad": 1, "precio": 1200},
        {"rubro": "Asistente TH",            "cantidad": 1, "precio":  700},
        {"rubro": "Jefe de contabilidad",    "cantidad": 1, "precio": 1200},
        {"rubro": "Asistente contable",      "cantidad": 1, "precio":  700},
        {"rubro": "Operaciones",             "cantidad": 5, "precio":  500},
        {"rubro": "Jefe de infraestructura", "cantidad": 1, "precio": 1200},
        {"rubro": "Asistente (Infraest.)",   "cantidad": 1, "precio":  700},
        {"rubro": "Bodega",                  "cantidad": 3, "precio":  650},
        {"rubro": "Compras",                 "cantidad": 1, "precio":  500},
        {"rubro": "Salud Ocupacional",       "cantidad": 1, "precio":  800},
        {"rubro": "Jurídico",                "cantidad": 1, "precio": 1200},
    ],

    # --- Costos Fijos: Seguros ---
    "seguro_fiel_cumpl":           7_500.0,
    "seguro_todo_riesgo_unidades": 70_000.0,

    # --- Costos Fijos: Servicios basicos ---
    "serv_basicos_mensual": 1_400.0,

    # --- Costos Fijos: Matricula e impuestos ---
    "matricula_precio":         250.00,
    "iva_compras":           11_500.00,
    "seg_unid_precio_mensual":  144.59,

    # --- Costos Fijos: Otros administrativos ---
    "otros_adm_anual": 14_000.00,

    # --- Otros Costos: ITOR ---
    "itor_porcentaje_oper_recaudo":  0.0995,
    "itor_transporte_valores_anual": 104_430.27,
    "itor_fideicomiso_admin_anual":   15_600.00,

    # --- Fee Metrovia ---
    "fee_metrovia_por_pasajero": 0.02,

    # --- Parametros macroeconómicos ---
    "inflacion_anual":  0.0155,   # 1.55%
    "tasa_descuento":   0.12,     # 12% para VAN

    # --- Impuesto ---
    "tasa_impuesto_renta": 0.25,  # 25%
}


# ---------- TOOLTIPS PARA LA UI ----------
TOOLTIPS = {
    "base_demanda":               "Número de pasajeros anuales del Año 1 por categoría.",
    "distribucion_demanda":       "Porcentaje de la demanda total para cada categoría de pasajero. Deben sumar 100%.",
    "pasajeros_por_bus_dia":      "Pasajeros promedio transportados por cada bus al día.",
    "dias_operacion_anual":       "Días de operación por año (normalmente 365).",
    "numero_buses":               "Número total de buses SITU de 12 m (operativos + reserva).",
    "tarifas":                    "Precio del pasaje en USD por tipo de pasajero.",
    "tasas_por_anio":             "Tasa de crecimiento de la demanda para cada año (9 valores para 10 años).",
    "km_totales_buses":           "Kilómetros totales recorridos por la flota SITU durante el período de análisis.",
    "costo_km_buses":             "Costo de mantenimiento por kilómetro para buses SITU de 12 m.",
    "precio_galon":               "Precio del galón de combustible en USD.",
    "rend_km_gal_buses":          "Rendimiento de combustible (km/gal) de buses SITU de 12 m.",
    "costo_llanta":               "Precio por llanta en USD.",
    "precio_bus":                 "Precio de compra de un bus SITU de 12 m (USD).",
    "tasa_interes_anual":         "Tasa de interés anual del préstamo bancario.",
    "plazo_anios_financ":         "Número de años del financiamiento bancario.",
    "porcentaje_financiado":      "Porcentaje del costo de los buses financiado con deuda (80% = 0.80).",
    "salario_mensual":            "Salario mensual base por chofer en USD.",
    "choferes_por_bus":           "Número de choferes por bus (incluyendo turnos).",
    "inflacion_anual":            "Tasa de inflación anual aplicada a sueldos, neumáticos y gastos administrativos.",
    "tasa_descuento":             "Tasa de descuento para el cálculo del VAN (Valor Actual Neto).",
    "itor_porcentaje_oper_recaudo": "Porcentaje de los ingresos totales que corresponde al costo de operación y recaudo ITOR.",
    "fee_metrovia_por_pasajero":  "Fee fijo pagado a Metrovía por cada pasajero transportado (USD).",
}
