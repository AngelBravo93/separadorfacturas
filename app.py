import streamlit as st
import PyPDF2
import re
import io
import zipfile
import pandas as pd

st.set_page_config(page_title="Herramienta de Facturas y Estados de Pago", page_icon="🛠️", layout="wide")

st.title("🛠️ Herramienta Unificada: Separador de Facturas + Estado de Pago")

st.sidebar.markdown("## Menú rápido")
if 'modo' not in st.session_state:
    st.session_state.modo = "Separador de Facturas"

if st.sidebar.button("🚌 Separador de Facturas"):
    st.session_state.modo = "Separador de Facturas"
if st.sidebar.button("📊 Cuadratura de Estado de Pago"):
    st.session_state.modo = "Cuadratura de Estado de Pago"

modo = st.session_state.modo

if modo == "Separador de Facturas":
    st.header("🚌 Separador de Facturas KAME ERP")
    st.write("Sube el PDF consolidado. La app cortará estrictamente cada 2 páginas (Original + Cedible) y usará el número de factura real para el nombre.")

    archivo_subido = st.file_uploader("Arrastra aquí el PDF con las facturas", type="pdf")

    if archivo_subido is not None:
        if st.button("Cortar y Procesar Facturas"):
            with st.spinner("Procesando el documento..."):
                lector = PyPDF2.PdfReader(io.BytesIO(archivo_subido.read()))
                total_paginas = len(lector.pages)

                if total_paginas % 2 != 0:
                    st.warning("El PDF no tiene un número par de páginas. La última factura puede estar incompleta.")

                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for i in range(0, total_paginas, 2):
                        escritor_pdf = PyPDF2.PdfWriter()

                        pagina_original = lector.pages[i]
                        escritor_pdf.add_page(pagina_original)

                        if i + 1 < total_paginas:
                            pagina_cedible = lector.pages[i + 1]
                            escritor_pdf.add_page(pagina_cedible)

                        texto = pagina_original.extract_text() or ""
                        busquedas = re.findall(r'N[°º]\s*(\d+)', texto)

                        if busquedas:
                            numero_factura = busquedas[0]
                        else:
                            numero_factura = f"Desconocida_Pag_{i+1}"

                        pdf_buffer = io.BytesIO()
                        escritor_pdf.write(pdf_buffer)
                        pdf_buffer.seek(0)

                        zip_file.writestr(f"Factura_{numero_factura}.pdf", pdf_buffer.read())

                st.success("¡Facturas separadas con éxito! 🎉")

                st.download_button(
                    label="📥 Descargar Facturas (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="Facturas_PasajeBus.zip",
                    mime="application/zip"
                )

elif modo == "Cuadratura de Estado de Pago":
    st.header("📊 Generador de Estados de Pago")
    st.write("Sube los reportes para cruzar la información y generar el estado de pago del nuevo período.")

    col1, col2 = st.columns(2)
    with col1:
        file_prev = st.file_uploader("1️⃣ Sube el Reporte Anterior (Febrero)", type=['csv', 'xlsx'])
    with col2:
        file_new = st.file_uploader("2️⃣ Sube el Reporte Nuevo (Acumulado a hoy)", type=['csv', 'xlsx'])

    st.write("---")
    st.subheader("💰 Datos para la Cuadratura")
    col3, col4 = st.columns(2)
    with col3:
        saldo_billetera = st.number_input("Saldo actual en Billetera ($)", value=14088.0, step=100.0)
    with col4:
        linea_credito = st.number_input("Línea de Crédito Total ($)", value=1999999.0, step=100.0)

    if file_prev and file_new:
        if st.button("🚀 Procesar Estado de Pago", type="primary"):
            try:
                df_prev = pd.read_csv(file_prev) if file_prev.name.endswith('.csv') else pd.read_excel(file_prev)
                df_new = pd.read_csv(file_new) if file_new.name.endswith('.csv') else pd.read_excel(file_new)

                df_prev.columns = df_prev.columns.str.strip()
                df_new.columns = df_new.columns.str.strip()

                df_prev['Llave_Unica'] = df_prev['Número PNR'].astype(str) + "_" + df_prev['No. Tarjeta de Identificación'].astype(str) + "_" + df_prev['Monto neto'].astype(str)
                df_new['Llave_Unica'] = df_new['Número PNR'].astype(str) + "_" + df_new['No. Tarjeta de Identificación'].astype(str) + "_" + df_new['Monto neto'].astype(str)

                llaves_ya_cobradas = df_prev['Llave_Unica'].unique()
                df_resultado = df_new[~df_new['Llave_Unica'].isin(llaves_ya_cobradas)].copy()
                df_resultado = df_resultado.drop(columns=['Llave_Unica'])

                consumo_total = df_resultado['Monto neto'].sum()
                cuadratura = consumo_total + saldo_billetera

                st.write("---")
                st.subheader("📋 Resultados de la Cuadratura")
                st.metric(label="Total Consumo Nuevo Período", value=f"${consumo_total:,.0f}")

                if round(cuadratura, 2) == round(linea_credito, 2):
                    st.success(f"✅ ¡CUADRATURA EXACTA! El Consumo (${consumo_total:,.0f}) + Saldo en Billetera (${saldo_billetera:,.0f}) = Línea de Crédito (${linea_credito:,.0f}).")
                else:
                    diferencia = linea_credito - cuadratura
                    st.error(f"⚠️ ATENCIÓN: La suma da ${cuadratura:,.0f}, pero tu línea es ${linea_credito:,.0f}. Hay una diferencia de ${diferencia:,.0f}.")

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Nuevo_Estado_Pago')

                st.write("Vista previa de las transacciones:")
                st.dataframe(df_resultado)

                st.download_button(
                    label="📥 Descargar Excel Listo",
                    data=output.getvalue(),
                    file_name="Nuevo_Estado_Pago.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"❌ Ocurrió un error: {e}")