"""Preauditoría documental de notas clínicas.

Esta aplicación identifica posibles omisiones documentales en archivos Excel/CSV.
No emite un dictamen legal ni sustituye la auditoría clínica o jurídica.
"""

from __future__ import annotations

import re
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Preauditoría de expedientes", page_icon="⚖️", layout="wide")

REQUIRED_COLUMNS = ["ID_Nota", "Medico", "Cedula", "Nota_Medica"]
STATUS_ORDER = ["Sin hallazgos automáticos", "Revisión prioritaria", "Revisión crítica"]
STATUS_COLORS = {
    "Sin hallazgos automáticos": "#2E8B57",
    "Revisión prioritaria": "#F59E0B",
    "Revisión crítica": "#DC2626",
}


def normalize_text(value: object) -> str:
    """Convierte valores nulos en texto vacío y normaliza espacios."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def contains(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def audit_note(row: pd.Series) -> pd.Series:
    """Evalúa únicamente elementos que pueden observarse en la base cargada."""
    note = normalize_text(row["Nota_Medica"])
    license_number = re.sub(r"\D", "", normalize_text(row["Cedula"]))

    # Patrones deliberadamente específicos: reducen falsos positivos por palabras aisladas.
    has_blood_pressure = contains(
        r"\b(?:ta|t/a|tension arterial)\s*:?\s*\d{2,3}\s*/\s*\d{2,3}\b", note
    )
    has_heart_rate = contains(r"\b(?:fc|frecuencia cardiaca)\s*:?\s*\d{2,3}\b", note)
    has_resp_rate = contains(r"\b(?:fr|frecuencia respiratoria)\s*:?\s*\d{1,2}\b", note)
    has_temperature = contains(
        r"\b(?:temp(?:eratura)?)\s*:?\s*\d{2}(?:[\.,]\d+)?\s*(?:°?c)?\b", note
    )
    has_vitals = all([has_blood_pressure, has_heart_rate, has_resp_rate, has_temperature])
    has_diagnosis = contains(r"\b(?:diagn[oó]stico|impresi[oó]n diagn[oó]stica|dx)\s*:?", note)
    has_plan = contains(r"\b(?:plan|tratamiento|conducta terap[eé]utica)\s*:?", note)
    has_license = license_number.isdigit() and 5 <= len(license_number) <= 8

    findings: list[str] = []
    if not has_vitals:
        missing = []
        if not has_blood_pressure:
            missing.append("TA")
        if not has_heart_rate:
            missing.append("FC")
        if not has_resp_rate:
            missing.append("FR")
        if not has_temperature:
            missing.append("temperatura")
        findings.append("Sin evidencia automática de signos vitales: " + ", ".join(missing))
    if not has_diagnosis:
        findings.append("Sin etiqueta explícita de diagnóstico")
    if not has_plan:
        findings.append("Sin etiqueta explícita de plan o tratamiento")
    if not has_license:
        findings.append("Cédula ausente o con formato no esperado")

    # No se afirma cumplimiento NOM: solo se prioriza revisión humana.
    if len(findings) == 0:
        status = "Sin hallazgos automáticos"
    elif len(findings) <= 2:
        status = "Revisión prioritaria"
    else:
        status = "Revisión crítica"

    return pd.Series(
        {
            "Evidencia_TA": has_blood_pressure,
            "Evidencia_FC": has_heart_rate,
            "Evidencia_FR": has_resp_rate,
            "Evidencia_Temperatura": has_temperature,
            "Evidencia_Signos_Vitales": has_vitals,
            "Evidencia_Diagnostico": has_diagnosis,
            "Evidencia_Plan": has_plan,
            "Formato_Cedula_Valido": has_license,
            "Numero_Hallazgos": len(findings),
            "Hallazgos": " | ".join(findings) if findings else "Sin hallazgos automáticos",
            "Estado_Pre_auditoria": status,
        }
    )


@st.cache_data(show_spinner=False)
def load_data(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    # utf-8-sig hace que los encabezados se lean correctamente si vienen de Excel.
    return pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=None, engine="python")


def to_excel(data: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Resultados")
        resumen = (
            data["Estado_Pre_auditoria"]
            .value_counts()
            .reindex(STATUS_ORDER, fill_value=0)
            .rename_axis("Estado_Pre_auditoria")
            .reset_index(name="Notas")
        )
        resumen.to_excel(writer, index=False, sheet_name="Resumen")
    return output.getvalue()


st.title("⚖️ Preauditoría documental de expedientes clínicos")
st.caption("Apoyo para detectar posibles omisiones de registro; requiere validación por personal autorizado.")

with st.expander("Alcance y límites", expanded=False):
    st.warning(
        "La aplicación no determina cumplimiento legal ni calidad clínica. Solo evalúa evidencia "
        "textual en las cuatro columnas disponibles. La NOM-004 requiere elementos que esta base "
        "no contiene —por ejemplo, identificación del paciente, fecha, hora y firma—, por lo que "
        "deben revisarse en el expediente original. Cargue únicamente datos desidentificados."
    )

uploaded_file = st.file_uploader("Carga un reporte clínico (.xlsx o .csv)", type=["xlsx", "csv"])

if uploaded_file is None:
    st.info("La base esperada debe incluir: ID_Nota, Medico, Cedula y Nota_Medica.")
    st.stop()

try:
    source_df = load_data(uploaded_file)
except Exception as exc:
    st.error(f"No se pudo leer el archivo: {exc}")
    st.stop()

missing_columns = [column for column in REQUIRED_COLUMNS if column not in source_df.columns]
if missing_columns:
    st.error("Faltan columnas obligatorias: " + ", ".join(missing_columns))
    st.stop()

df = source_df.copy()
audit_results = df.apply(audit_note, axis=1)
df = pd.concat([df, audit_results], axis=1)

st.success(f"Se procesaron {len(df):,} notas de {uploaded_file.name}.")

counts = df["Estado_Pre_auditoria"].value_counts()
metric_cols = st.columns(4)
metric_cols[0].metric("Notas procesadas", len(df))
metric_cols[1].metric("Sin hallazgos automáticos", counts.get("Sin hallazgos automáticos", 0))
metric_cols[2].metric("Revisión prioritaria", counts.get("Revisión prioritaria", 0))
metric_cols[3].metric("Revisión crítica", counts.get("Revisión crítica", 0))

st.divider()
left, right = st.columns([1, 2])
with left:
    chart_df = (
        df["Estado_Pre_auditoria"]
        .value_counts()
        .reindex(STATUS_ORDER, fill_value=0)
        .rename_axis("Estado_Pre_auditoria")
        .reset_index(name="Notas")
    )
    figure = px.bar(
        chart_df,
        x="Estado_Pre_auditoria",
        y="Notas",
        color="Estado_Pre_auditoria",
        color_discrete_map=STATUS_COLORS,
        text="Notas",
    )
    figure.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Notas")
    st.plotly_chart(figure, use_container_width=True)

with right:
    status_filter = st.multiselect(
        "Filtrar por prioridad", STATUS_ORDER, default=STATUS_ORDER
    )
    doctor_options = sorted(df["Medico"].fillna("Sin médico").astype(str).unique())
    doctor_filter = st.multiselect("Filtrar por médico", doctor_options)

    filtered = df[df["Estado_Pre_auditoria"].isin(status_filter)]
    if doctor_filter:
        filtered = filtered[filtered["Medico"].fillna("Sin médico").astype(str).isin(doctor_filter)]

    st.dataframe(
        filtered[
            ["ID_Nota", "Medico", "Estado_Pre_auditoria", "Numero_Hallazgos", "Hallazgos", "Nota_Medica"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Exportar resultados")
st.download_button(
    "Descargar reporte Excel",
    data=to_excel(df),
    file_name="Reporte_Pre_auditoria.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    "Descargar reporte CSV",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="Reporte_Pre_auditoria.csv",
    mime="text/csv",
)
