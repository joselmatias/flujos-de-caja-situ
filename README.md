# Flujo de Caja SITU – Panel Ejecutivo

Panel financiero interactivo para la simulación y análisis del flujo de caja del **Sistema Integrado de Transporte Urbano (SITU)**, desarrollado con Python y Streamlit.

---

## Descripción

Este modelo proyecta a **12 años** los ingresos, costos y flujo de caja del sistema de buses urbanos, permitiendo evaluar la viabilidad financiera bajo diferentes escenarios de demanda, tarifas y precios de combustible.

El sistema incluye análisis de sensibilidad, indicadores financieros clave (VAN, TIR, Payback) y exportación de reportes en Excel y PDF.

---

## Parámetros principales

| Parámetro | Valor base |
|---|---|
| Número de buses (12 m) | **1,933** |
| Pasajeros por bus por día | **504** |
| Días de operación al año | **365** |
| Demanda total Año 1 | **355,620,360 pasajeros** |
| Horizonte de análisis | **12 años** |
| Tasa de descuento (VAN) | **12%** |
| Inflación anual | **1.55%** |
| Precio galón combustible | **$2.80** |
| Salario mensual chofer | **$960.85** |
| Precio bus unitario | **$156,848** |
| Inversión total flota | **~$303.2 M** |

---

## Estructura tarifaria

| Categoría | Tarifa (USD) | Participación |
|---|---|---|
| GENERAL | $0.30 | 89.19% |
| ADULTOS MAYORES | $0.15 | 6.30% |
| CAPACIDADES ESPECIALES | $0.15 | 2.35% |
| ESTUDIANTES | $0.15 | 2.16% |

---

## Estructura del proyecto

```
Flujos de caja SITU/
├── app.py              # Aplicación Streamlit (UI y visualizaciones)
├── funciones.py        # Lógica de cálculo del flujo de caja
├── parametros.py       # Parámetros por defecto y tooltips
├── requirements.txt    # Dependencias Python
├── .gitignore
├── README.md
└── .streamlit/
    └── secrets.toml    # Contraseña de acceso (no incluido en repo)
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/flujos-de-caja-situ.git
cd flujos-de-caja-situ
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar contraseña de acceso

Crea el archivo `.streamlit/secrets.toml` (no está en el repo por seguridad):

```toml
password = "tu_contraseña_aqui"
```

---

## Ejecutar la aplicación

```bash
streamlit run app.py
```

La app estará disponible en `http://localhost:8501`

---

## Funcionalidades

| Pestaña | Contenido |
|---|---|
| 📊 Resumen Ejecutivo | KPIs (VAN, TIR, Payback), gráficos, semáforo de viabilidad, análisis de sensibilidad, descarga PDF |
| 👥 Demanda | Fórmula de demanda, distribución por categoría, proyección anual |
| 💵 Ingresos | Ingresos por categoría de pasajero proyectados a 12 años |
| 📦 Costos | Costos variables (combustible, mantenimiento, neumáticos) y fijos (sueldos, financiamiento, admin) |
| 💰 Flujo de Caja | Utilidad bruta, impuesto a la renta, flujo neto y acumulado |
| 📥 Exportar | Descarga en Excel (flujo + parámetros) |

---

## Parámetros ajustables (sidebar)

Todos los parámetros son editables en tiempo real desde el panel lateral:

- **Demanda**: número de buses, pasajeros/día, días/año, distribución por categoría (%)
- **Tarifas**: precio por tipo de pasajero
- **Combustible**: precio del galón, rendimiento (km/gal)
- **Mantenimiento**: km totales, costo/km, costo de llantas
- **Flota**: número de buses, precio unitario, costo total de inversión
- **Financiamiento**: tasa de interés, plazo, % financiado
- **Sueldos**: salario mensual chofer, choferes por bus
- **Macroeconomía**: inflación, tasa de descuento, ITOR, Fee Metrovía

---

## Stack tecnológico

- [Streamlit](https://streamlit.io/) – Interfaz web interactiva
- [Pandas](https://pandas.pydata.org/) – Manipulación de datos
- [NumPy](https://numpy.org/) – Cálculo numérico
- [Plotly](https://plotly.com/) – Gráficos interactivos
- [openpyxl](https://openpyxl.readthedocs.io/) – Exportación Excel
- [fpdf2](https://py-pdf.github.io/fpdf2/) – Generación de PDF
- [Matplotlib](https://matplotlib.org/) – Gráficos para PDF

---

## Despliegue en Streamlit Cloud

1. Sube el repositorio a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. En **Advanced settings → Secrets**, agrega:
   ```toml
   password = "tu_contraseña"
   ```
5. Haz clic en **Deploy**
