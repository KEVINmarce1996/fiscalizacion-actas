import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from PIL import Image
import io
import os

# Configuración
st.set_page_config(page_title="Fiscalización Actas ONPE", page_icon="🗳️", layout="centered")

# API Key
api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
if api_key:
    genai.configure(api_key=api_key)

# Inicializar tabla en sesión
if "actas" not in st.session_state:
    st.session_state.actas = []

st.title("🗳️ Fiscalización Actas ONPE")
st.caption("Segunda Vuelta Presidencial 2026 — Trujillo")

# Subir foto
foto = st.file_uploader("📷 Sube la foto del acta", type=["jpg", "jpeg", "png"])

if foto and api_key:
    image = Image.open(foto)
    st.image(image, caption="Acta cargada", use_column_width=True)

    with st.spinner("🤖 Gemini analizando el acta..."):
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = """Eres un experto en actas electorales peruanas ONPE.
Analiza esta imagen de un acta de sufragio de la segunda vuelta presidencial 2026.
Extrae TODOS los datos y responde SOLO con un JSON válido, sin texto adicional, sin markdown:

{
  "mesa": "",
  "local": "",
  "distrito": "",
  "provincia": "",
  "departamento": "",
  "hora_instalacion": "",
  "hora_cierre": "",
  "electores_habiles": 0,
  "votaron": 0,
  "no_votaron": 0,
  "votos_keiko_fujimori": 0,
  "votos_roberto_sanchez": 0,
  "votos_blancos": 0,
  "votos_nulos": 0,
  "votos_impugnados": 0,
  "total_votos_emitidos": 0
}

Si un campo es ilegible escribe null."""

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        img_bytes = img_bytes.getvalue()

        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": img_bytes}
        ])

        try:
            text = response.text.strip().replace("```json", "").replace("```", "")
            data = json.loads(text)

            st.success("✅ Acta procesada correctamente")

            # Validación automática
            suma = (data.get("votos_keiko_fujimori") or 0) + \
                   (data.get("votos_roberto_sanchez") or 0) + \
                   (data.get("votos_blancos") or 0) + \
                   (data.get("votos_nulos") or 0) + \
                   (data.get("votos_impugnados") or 0)
            total = data.get("total_votos_emitidos") or 0

            if total > 0 and suma != total:
                st.warning(f"⚠️ Verificar: suma parciales ({suma}) ≠ total ({total})")

            # Verificar duplicado
            mesas_existentes = [a.get("mesa") for a in st.session_state.actas]
            if data.get("mesa") and data["mesa"] in mesas_existentes:
                st.error(f"🚨 Mesa {data['mesa']} ya fue ingresada antes")
            else:
                # Mostrar datos editables
                st.subheader("📋 Datos extraídos — verifica y corrige si es necesario")
                col1, col2 = st.columns(2)
                with col1:
                    data["mesa"] = st.text_input("N° Mesa", value=str(data.get("mesa") or ""))
                    data["distrito"] = st.text_input("Distrito", value=str(data.get("distrito") or ""))
                    data["hora_cierre"] = st.text_input("Hora cierre", value=str(data.get("hora_cierre") or ""))
                    data["votos_keiko_fujimori"] = st.number_input("Votos Keiko Fujimori", value=int(data.get("votos_keiko_fujimori") or 0), min_value=0)
                    data["votos_roberto_sanchez"] = st.number_input("Votos Roberto Sánchez", value=int(data.get("votos_roberto_sanchez") or 0), min_value=0)
                with col2:
                    data["electores_habiles"] = st.number_input("Electores hábiles", value=int(data.get("electores_habiles") or 0), min_value=0)
                    data["votaron"] = st.number_input("Votaron", value=int(data.get("votaron") or 0), min_value=0)
                    data["votos_blancos"] = st.number_input("Votos blancos", value=int(data.get("votos_blancos") or 0), min_value=0)
                    data["votos_nulos"] = st.number_input("Votos nulos", value=int(data.get("votos_nulos") or 0), min_value=0)
                    data["total_votos_emitidos"] = st.number_input("Total votos emitidos", value=int(data.get("total_votos_emitidos") or 0), min_value=0)

                if st.button("💾 Guardar acta", type="primary"):
                    st.session_state.actas.append(data)
                    st.success(f"✅ Acta mesa {data['mesa']} guardada. Total: {len(st.session_state.actas)} actas")

        except Exception as e:
            st.error(f"Error procesando respuesta: {e}")
            st.text(response.text)

elif foto and not api_key:
    st.error("❌ Falta configurar GOOGLE_API_KEY en Streamlit Secrets")

# Tabla acumulada
if st.session_state.actas:
    st.divider()
    st.subheader(f"📊 Resultados acumulados — {len(st.session_state.actas)} actas")
    df = pd.DataFrame(st.session_state.actas)
    st.dataframe(df, use_container_width=True)

    # Totales
    col1, col2, col3 = st.columns(3)
    col1.metric("🟠 Keiko Fujimori", df["votos_keiko_fujimori"].sum())
    col2.metric("🔴 Roberto Sánchez", df["votos_roberto_sanchez"].sum())
    col3.metric("📋 Actas procesadas", len(df))

    # Descarga
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    st.download_button(
        label="⬇️ Descargar Excel",
        data=excel_buffer.getvalue(),
        file_name="actas_fiscalizacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
