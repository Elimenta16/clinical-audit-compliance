# Clinical Audit System (NOM-004-SSA3-2012) ⚖️🏥

A fun and practical project using Python and Streamlit to audit hospital Electronic Health Record (EHR) data against Mexican medical regulations (**NOM-004-SSA3-2012**).

## 🚀 Live Demo
🔗 [Check out the live app here!](PASTE_YOUR_STREAMLIT_URL_HERE)

## 🛠️ What this app does
Instead of manually checking medical notes row by row in Excel, I built this app to automate the whole quality control process in seconds:
* **Bulk Upload:** You can drop a messy Excel (`.xlsx`) or `.csv` report straight from any hospital system.
* **Smart Compliance Check:** The script instantly scans the text for mandatory legal metrics required by Mexican law (like vital signs, diagnoses, treatment plans, and doctor credentials).
* **Risk KPIs:** It breaks down data into interactive charts to highlight administrative errors and legal liabilities immediately.
* **Exportable Clean Reports:** You can download the processed and scored audit report ready to hand over to hospital management.

## 🧰 Tech Stack
* **Language:** Python
* **Web Framework:** Streamlit
* **Data Processing:** Pandas & OpenPyXL
* **Charts:** Plotly Express

## 📋 How to test it
Just upload a file containing these 4 columns: `ID_Nota`, `Medico`, `Cedula`, and `Nota_Medica`.
