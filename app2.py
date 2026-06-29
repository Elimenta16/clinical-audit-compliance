import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Auditoría NOM-004-SSA3-2012", layout="wide")

st.title("⚖️ Sistema de Auditoría Digital de Expedientes Clínicos")
st.caption("Validación Automatizada de Calidad de Datos Clínicos en base a la NOM-004-SSA3-2012")
st.markdown("---")

st.markdown("""
### Enfoque Industrial y de Calidad Hospitalaria
Esta plataforma procesa bases de datos extraídas de sistemas de **Expediente Clínico Electrónico (ECE)** en formato Excel o CSV. El algoritmo evalúa de forma masiva si el personal médico cumple con los registros obligatorios por ley, mitigando riesgos de sanciones institucionales.
""")

# Módulo de carga de archivos
st.subheader("📊 Carga Masiva de Registros de Excel / CSV")
archivo_cargado = st.file_uploader("Arrastra aquí tu reporte clínico (.xlsx o .csv):", type=["xlsx", "csv"])

if archivo_cargado is not None:
    try:
        # Leer el archivo según su extensión
        if archivo_cargado.name.endswith('.xlsx'):
            df = pd.read_excel(archivo_cargado)
        else:
            df = pd.read_csv(archivo_cargado)
        
        st.success(f"✅ Archivo '{archivo_cargado.name}' cargado exitosamente con {len(df)} notas médicas.")
        
        # Verificar que existan las columnas necesarias
        columnas_requeridas = ['ID_Nota', 'Medico', 'Cedula', 'Nota_Medica']
        if all(col in df.columns for col in columnas_requeridas):
            
            # Algoritmo de auditoría basado en la NOM-004
            def auditar_nota(row):
                nota = str(row['Nota_Medica']).lower()
                cedula = str(row['Cedula'])
                
                # Criterios legales mínimos de la norma
                tiene_signos = any(x in nota for x in ['ta', 'fc', 'fr', 'temp', 'signos', 't/a', 'lpm', 'rpm', '°c'])
                tiene_cedula = len(cedula) >= 5 and cedula.isdigit()
                tiene_diagnostico = any(x in nota for x in ['dx', 'diagnostico', 'impresion', 'sintomas', 'cefalea', 'faringitis', 'bradicardia', 'coronario'])
                tiene_plan = any(x in nota for x in ['plan', 'tratamiento', 'mg', 'ml', 'administra', 'alta', 'pendiente', 'dosis', 'cita', 'valorar'])
                
                # Puntuación
                puntos = sum([tiene_signos, tiene_cedula, tiene_diagnostico, tiene_plan])
                
                if puntos == 4:
                    return "🟢 Cumplimiento Total"
                elif puntos >= 2:
                    return "🟡 Riesgo Moderado (Datos Incompletos)"
                else:
                    return "🔴 Riesgo Crítico (Omisión Legal)"

            # Aplicar auditoría masiva mediante Pandas
            df['Dictamen_Legal'] = df.apply(auditar_nota, axis=1)
            
            # 📊 KPIs del Dashboard de Calidad
            st.markdown("---")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.metric("Total Notas Auditadas", len(df))
            with kpi2:
                st.metric("🟢 Dictamen Aprobado", len(df[df['Dictamen_Legal'] == "🟢 Cumplimiento Total"]))
            with kpi3:
                st.metric("🟡 Advertencias Técnicas", len(df[df['Dictamen_Legal'] == "🟡 Riesgo Moderado (Datos Incompletos)"]))
            with kpi4:
                st.metric("🔴 Alertas Jurídicas", len(df[df['Dictamen_Legal'] == "🔴 Riesgo Crítico (Omisión Legal)"]))
                
            # Gráficas analíticas
            st.markdown("---")
            col_izq, col_der = st.columns(2)
            
            with col_izq:
                st.subheader("Distribución de Cumplimiento Normativo")
                fig = px.pie(df, names='Dictamen_Legal', color='Dictamen_Legal',
                             color_discrete_map={
                                 "🟢 Cumplimiento Total": "#2ca02c",
                                 "🟡 Riesgo Moderado (Datos Incompletos)": "#ff7f0e",
                                 "🔴 Riesgo Crítico (Omisión Legal)": "#d62728"
                             })
                st.plotly_chart(fig, use_container_width=True)
                
            with col_der:
                st.subheader("Vista de Datos Procesados")
                st.dataframe(df[['ID_Nota', 'Medico', 'Dictamen_Legal', 'Nota_Medica']], use_container_width=True)
                
            # Descarga del reporte corregido en CSV
            st.markdown("---")
            st.subheader("💾 Exportar Resultados de Auditoría")
            st.markdown("Descarga este reporte procesado para enviarlo directamente al departamento de Calidad o Dirección Médica.")
            
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte Auditado (.CSV)",
                data=csv_data,
                file_name="Reporte_Auditoria_NOM004.csv",
                mime="text/csv"
            )
            
        else:
            st.error(f"❌ El archivo no tiene el formato correcto. Debe contener las columnas: {columnas_requeridas}")
            st.info("💡 Consejo: Asegúrate de que tu archivo tenga exactamente esos encabezados en la primera fila.")
            
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

else:
    st.info("💡 Por favor, sube tu archivo de Excel o CSV para desplegar las métricas analíticas y la auditoría legal.")
