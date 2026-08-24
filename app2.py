"""Documentary pre-audit of clinical notes.

This application identifies potential documentation omissions in Excel/CSV files.
It does not issue a legal opinion or replace a clinical or legal audit.
"""

from __future__ import annotations

import re
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Medical Records Pre-audit", page_icon="⚖️", layout="wide")

REQUIRED_COLUMNS = ["ID_Nota", "Medico", "Cedula", "Nota_Medica"]
STATUS_ORDER = ["No automatic findings", "Priority review", "Critical review"]
STATUS_COLORS = {
    "No automatic findings": "#2E8B57",
    "Priority review": "#F59E0B",
    "Critical review": "#DC2626",
}


def normalize_text(value: object) -> str:
    """Converts null values to empty text and normalizes whitespace."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def contains(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def audit_note(row: pd.Series) -> pd.Series:
    """Evaluates only elements that can be observed in the uploaded dataset."""
    note = normalize_text(row["Nota_Medica"])
    license_number = re.sub(r"\D", "", normalize_text(row["Cedula"]))

    # Deliberately specific patterns: reduce false positives from isolated words.
    has_blood_pressure = contains(
        r"\b(?:ta|t/a|blood pressure|bp|tension arterial)\s*:?\s*\d{2,3}\s*/\s*\d{2,3}\b", note
    )
    has_heart_rate = contains(r"\b(?:fc|hr|heart rate|frecuencia cardiaca)\s*:?\s*\d{2,3}\b", note)
    has_resp_rate = contains(r"\b(?:fr|rr|resp rate|respiratory rate|frecuencia respiratoria)\s*:?\s*\d{1,2}\b", note)
    has_temperature = contains(
        r"\b(?:temp(?:erature)?)\s*:?\s*\d{2}(?:[\.,]\d+)?\s*(?:°?[cf])?\b", note
    )
    has_vitals = all([has_blood_pressure, has_heart_rate, has_resp_rate, has_temperature])
    has_diagnosis = contains(r"\b(?:diagnosis|dx|impression|impresi[oó]n diagn[oó]stica)\s*:?", note)
    has_plan = contains(r"\b(?:plan|treatment|conducta terap[eé]utica)\s*:?", note)
    has_license = license_number.isdigit() and 5 <= len(license_number) <= 8

    findings: list[str] = []
    if not has_vitals:
        missing = []
        if not has_blood_pressure:
            missing.append("BP")
        if not has_heart_rate:
            missing.append("HR")
        if not has_resp_rate:
            missing.append("RR")
        if not has_temperature:
            missing.append("Temperature")
        findings.append("No automatic evidence of vital signs: " + ", ".join(missing))
    if not has_diagnosis:
        findings.append("No explicit diagnosis label")
    if not has_plan:
        findings.append("No explicit plan or treatment label")
    if not has_license:
        findings.append("Medical license missing or unexpected format")

    # Regulatory compliance is not declared: only human review is prioritized.
    if len(findings) == 0:
        status = "No automatic findings"
    elif len(findings) <= 2:
        status = "Priority review"
    else:
        status = "Critical review"

    return pd.Series(
        {
            "Evidence_BP": has_blood_pressure,
            "Evidence_HR": has_heart_rate,
            "Evidence_RR": has_resp_rate,
            "Evidence_Temperature": has_temperature,
            "Evidence_Vital_Signs": has_vitals,
            "Evidence_Diagnosis": has_diagnosis,
            "Evidence_Plan": has_plan,
            "Valid_License_Format": has_license,
            "Findings_Count": len(findings),
            "Findings": " | ".join(findings) if findings else "No automatic findings",
            "Pre_Audit_Status": status,
        }
    )


@st.cache_data(show_spinner=False)
def load_data(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".xlsx"):
        return pd.read_excel(uploaded_file, engine="openpyxl")
    # utf-8-sig ensures headers are read correctly if originating from Excel.
    return pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=None, engine="python")


def to_excel(data: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Results")
        summary = (
            data["Pre_Audit_Status"]
            .value_counts()
            .reindex(STATUS_ORDER, fill_value=0)
            .rename_axis("Pre_Audit_Status")
            .reset_index(name="Notes")
        )
        summary.to_excel(writer, index=False, sheet_name="Summary")
    return output.getvalue()


st.title("⚖️ Clinical Records Documentary Pre-audit")
st.caption("Support tool for detecting potential registration omissions; requires validation by authorized personnel.")

with st.expander("Scope and Limitations", expanded=False):
    st.warning(
        "This application does not determine legal compliance or clinical quality. It only evaluates text "
        "evidence across the four available columns. Regulatory standards require elements not contained "
        "in this dataset — such as patient identification, date, time, and signature —, which must be "
        "verified in the original record. Please upload de-identified data only."
    )

uploaded_file = st.file_uploader("Upload a clinical report (.xlsx or .csv)", type=["xlsx", "csv"])

if uploaded_file is None:
    st.info("Expected dataset must include: ID_Nota, Medico, Cedula, and Nota_Medica.")
    st.stop()

try:
    source_df = load_data(uploaded_file)
except Exception as exc:
    st.error(f"Could not read file: {exc}")
    st.stop()

missing_columns = [column for column in REQUIRED_COLUMNS if column not in source_df.columns]
if missing_columns:
    st.error("Missing required columns: " + ", ".join(missing_columns))
    st.stop()

df = source_df.copy()
audit_results = df.apply(audit_note, axis=1)
df = pd.concat([df, audit_results], axis=1)

st.success(f"Processed {len(df):,} notes from {uploaded_file.name}.")

counts = df["Pre_Audit_Status"].value_counts()
metric_cols = st.columns(4)
metric_cols[0].metric("Processed notes", len(df))
metric_cols[1].metric("No automatic findings", counts.get("No automatic findings", 0))
metric_cols[2].metric("Priority review", counts.get("Priority review", 0))
metric_cols[3].metric("Critical review", counts.get("Critical review", 0))

st.divider()
left, right = st.columns([1, 2])
with left:
    chart_df = (
        df["Pre_Audit_Status"]
        .value_counts()
        .reindex(STATUS_ORDER, fill_value=0)
        .rename_axis("Pre_Audit_Status")
        .reset_index(name="Notes")
    )
    figure = px.bar(
        chart_df,
        x="Pre_Audit_Status",
        y="Notes",
        color="Pre_Audit_Status",
        color_discrete_map=STATUS_COLORS,
        text="Notes",
    )
    figure.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Notes")
    st.plotly_chart(figure, use_container_width=True)

with right:
    status_filter = st.multiselect(
        "Filter by priority", STATUS_ORDER, default=STATUS_ORDER
    )
    doctor_options = sorted(df["Medico"].fillna("Unassigned").astype(str).unique())
    doctor_filter = st.multiselect("Filter by physician", doctor_options)

    filtered = df[df["Pre_Audit_Status"].isin(status_filter)]
    if doctor_filter:
        filtered = filtered[filtered["Medico"].fillna("Unassigned").astype(str).isin(doctor_filter)]

    st.dataframe(
        filtered[
            ["ID_Nota", "Medico", "Pre_Audit_Status", "Findings_Count", "Findings", "Nota_Medica"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Export Results")
st.download_button(
    "Download Excel Report",
    data=to_excel(df),
    file_name="Pre_Audit_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    "Download CSV Report",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="Pre_Audit_Report.csv",
    mime="text/csv",
)
