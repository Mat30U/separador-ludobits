import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile
import os

st.title("✂️ Separador Inteligente Multi-Libro - Ludo Bits")
st.write("¡Hola! Esta versión permite subir múltiples PDFs a la vez para procesar colecciones completas.")

st.divider()

# MODIFICACIÓN: Ahora acepta múltiples archivos a la vez
archivos_subidos = st.file_uploader(
    "Arrastra o selecciona uno o varios libros en PDF aquí", 
    type="pdf", 
    accept_multiple_files=True
)

# Inicializamos el almacén de datos en la sesión si no existe
if "procesamiento_completo" not in st.session_state:
    st.session_state.procesamiento_completo = {}

if archivos_subidos:
    st.success(f"¡Se han cargado {len(archivos_subidos)} archivos correctamente!")
    
    # Botón principal para procesar todo el lote
    if st.button("🚀 Escanear todos los libros cargados"):
        st.session_state.procesamiento_completo = {} # Limpiamos registros anteriores
        
        unidades_a_buscar = ["UNIDAD 1", "UNIDAD 2", "UNIDAD 3", "UNIDAD 4", "UNIDAD 5", "UNIDAD 6"]
        
        # Iteramos libro por libro
        for archivo in archivos_subidos:
            st.write(f"📖 Analizando: **{archivo.name}**...")
            lector_pdf = PdfReader(archivo)
            total_paginas = len(lector_pdf.pages)
            
            resultados_libro = {}
            extras_libro = {}
            indice_busqueda = 0
            
            barra = st.progress(0)
            
            for i in range(total_paginas):
                texto_pagina = lector_pdf.pages[i].extract_text()
                if texto_pagina:
                    texto_mayusculas = texto_pagina.upper()
                    
                    # Escudo Anti-Índice
                    if texto_mayusculas.count("UNIDAD") >= 3:
                        continue 
                    
                    # Fase 1: Unidades
                    if indice_busqueda < len(unidades_a_buscar):
                        unidad_actual = unidades_a_buscar[indice_busqueda]
                        if unidad_actual in texto_mayusculas:
                            resultados_libro[unidad_actual] = i + 1
                            indice_busqueda += 1
                    
                    # Fase 2: Extras (Se activa tras la Unidad 6)
                    elif indice_busqueda == 6:
                        if "Evaluación Trimestral" not in extras_libro:
                            if "EVALUACIÓN TRIMESTRAL" in texto_mayusculas or "EVALUARTE TERCER" in texto_mayusculas:
                                extras_libro["Evaluación Trimestral"] = i + 1

                        if "Bibliografía" not in extras_libro:
                            if "BIBLIOGRAFÍA" in texto_mayusculas:
                                extras_libro["Bibliografía"] = i + 1

                        # MODIFICACIÓN: Ahora busca también la palabra "DIAGNÓSTICO"
                        if "Evaluación Diagnóstica" not in extras_libro:
                            if "EVALUACIÓN DIAGNÓSTICA" in texto_mayusculas or "DIAGNÓSTICO" in texto_mayusculas:
                                extras_libro["Evaluación Diagnóstica"] = i + 1
                
                barra.progress((i + 1) / total_paginas)
            
            # Guardamos la información de este libro específico
            st.session_state.procesamiento_completo[archivo.name] = {
                "lector": lector_pdf,
                "total_paginas": total_paginas,
                "resultados": resultados_libro,
                "extras": extras_libro
            }
            
        st.success("¡Análisis de todo el lote terminado con éxito!")

    # Si ya hay libros procesados en la memoria, mostramos el panel de descarga
    if st.session_state.procesamiento_completo:
        st.divider()
        st.subheader("📦 Paso Final: Cortar y Descargar Lote")
        st.write("El sistema creará un archivo ZIP organizado en carpetas por cada libro.")
        
        if st.button("Cortar todos los PDFs y Crear Súper ZIP"):
            with st.spinner("Cortando y organizando carpetas... esto puede tomar un momento."):
                
                # Creamos el súper ZIP en memoria
                master_zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(master_zip_buffer, "w") as master_zip:
                    
                    # Procesamos cada libro guardado
                    for nombre_archivo, datos in st.session_state.procesamiento_completo.items():
                        lector_pdf = datos["lector"]
                        total_paginas = datos["total_paginas"]
                        resultados = datos["resultados"]
                        extras = datos["extras"]
                        
                        # Limpiamos el nombre del archivo para usarlo como nombre de carpeta
                        nombre_carpeta = os.path.splitext(nombre_archivo)[0]
                        
                        # Si el libro no tiene las 6 unidades, lo saltamos o lo metemos entero para revisión
                        if len(resultados) < 6:
                            continue
                            
                        # Estructura de cortes
                        todas_secciones = [
                            ("00_Introduccion", 0),
                            ("01_Unidad_1", resultados["UNIDAD 1"] - 1),
                            ("02_Unidad_2", resultados["UNIDAD 2"] - 1),
                            ("03_Unidad_3", resultados["UNIDAD 3"] - 1),
                            ("04_Unidad_4", resultados["UNIDAD 4"] - 1),
                            ("05_Unidad_5", resultados["UNIDAD 5"] - 1),
                            ("06_Unidad_6", resultados["UNIDAD 6"] - 1)
                        ]
                        
                        nombres_archivos_extras = {
                            "Evaluación Trimestral": "07_Evaluacion_Trimestral",
                            "Bibliografía": "08_Bibliografia",
                            "Evaluación Diagnóstica": "09_Evaluacion_Diagnostica"
                        }
                        
                        for extra_nombre, extra_pagina in extras.items():
                            todas_secciones.append((nombres_archivos_extras[extra_nombre], extra_pagina - 1))
                        
                        # Ordenamos cortes por número de página
                        todas_secciones.sort(key=lambda x: x[1])
                        
                        # Cortamos las secciones de este libro
                        for i in range(len(todas_secciones)):
                            nombre_seccion, inicio = todas_secciones[i]
                            
                            if i < len(todas_secciones) - 1:
                                fin = todas_secciones[i+1][1]
                            else:
                                fin = total_paginas
                                
                            if inicio < fin:
                                escritor = PdfWriter()
                                for num_pag in range(inicio, fin):
                                    escritor.add_page(lector_pdf.pages[num_pag])
                                    
                                pdf_buffer = io.BytesIO()
                                escritor.write(pdf_buffer)
                                
                                # TRUCO DE CARPETA: Al poner '/' en el nombre dentro del ZIP, 
                                # Windows y Mac lo entienden automáticamente como una carpeta.
                                ruta_dentro_zip = f"{nombre_carpeta}/{nombre_carpeta}_{nombre_seccion}.pdf"
                                master_zip.writestr(ruta_dentro_zip, pdf_buffer.getvalue())
                                
                st.success("¡Todos los libros han sido cortados y empaquetados!")
                
                # Botón de descarga final del súper lote
                st.download_button(
                    label="⬇️ Descargar Súper ZIP del Lote",
                    data=master_zip_buffer.getvalue(),
                    file_name="Lote_Libros_Separados.zip",
                    mime="application/zip"
                )