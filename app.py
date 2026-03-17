import streamlit as st
import PyPDF2
import re
import io
import zipfile

st.set_page_config(page_title="Separador de Facturas | PasajeBus", page_icon="🚌")

st.title("🚌 Separador de Facturas KAME ERP")
st.write("Sube el PDF consolidado. La app cortará estrictamente cada 2 páginas (Original + Cedible) y usará el número de factura real para el nombre.")

archivo_subido = st.file_uploader("Arrastra aquí el PDF con las facturas", type="pdf")

if archivo_subido is not None:
    if st.button("Cortar y Procesar Facturas"):
        with st.spinner("Procesando el documento..."):
            
            # Convertimos el archivo subido a BytesIO para que PyPDF2 lo lea completo
            lector = PyPDF2.PdfReader(io.BytesIO(archivo_subido.read()))
            total_paginas = len(lector.pages)

            # Validación: si no es múltiplo de 2, advertimos
            if total_paginas % 2 != 0:
                st.warning("El PDF no tiene un número par de páginas. La última factura puede estar incompleta.")

            # Creamos el buffer del ZIP
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Recorremos el PDF de 2 en 2 páginas
                for i in range(0, total_paginas, 2):
                    escritor_pdf = PyPDF2.PdfWriter()
                    
                    # Página Original
                    pagina_original = lector.pages[i]
                    escritor_pdf.add_page(pagina_original)
                    
                    # Página Cedible (si existe)
                    if i + 1 < total_paginas:
                        pagina_cedible = lector.pages[i + 1]
                        escritor_pdf.add_page(pagina_cedible)
                    
                    # Extraemos texto de la página Original
                    texto = pagina_original.extract_text() or ""
                    
                    # Regex más robusto: acepta N° y Nº
                    busquedas = re.findall(r'N[°º]\s*(\d+)', texto)
                    
                    if busquedas:
                        numero_factura = busquedas[0]
                    else:
                        numero_factura = f"Desconocida_Pag_{i+1}"
                    
                    # Guardamos el PDF de 2 páginas en el ZIP
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