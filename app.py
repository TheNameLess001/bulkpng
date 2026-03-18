import streamlit as st
import os
import requests
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
import zipfile
import re

# Configuration de la page
st.set_page_config(page_title="WEBP to PNG & ImgBB", page_icon="📝", layout="wide")

# ------------------------------
# 0) SIDEBAR: CONFIGURATION API
# ------------------------------
st.sidebar.header("⚙️ Configuration ImgBB")
st.sidebar.markdown("Crée un compte sur [api.imgbb.com](https://api.imgbb.com/) pour obtenir une clé API.")
imgbb_api_key = st.sidebar.text_input("🔑 Clé API ImgBB", type="password")
upload_to_imgbb = st.sidebar.checkbox("☁️ Héberger sur ImgBB après conversion", value=False)

if upload_to_imgbb and not imgbb_api_key:
    st.sidebar.warning("⚠️ Attention : Tu as activé l'upload, mais la clé API est vide.")

# ------------------------------
# 1) INPUT SECTION
# ------------------------------
st.title("📝 WEBP ➜ PNG (Export & ImgBB)")
st.markdown("L'ordre d'entrée sera **strictement respecté** dans le fichier CSV final. Le script gère intelligemment les CSV avec séparateurs `;` ou `,` et les erreurs d'encodage Excel.")

col_input1, col_input2 = st.columns(2)

with col_input1:
    urls_text = st.text_area(
        "📌 Colle tes liens (1 par ligne)",
        placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp",
        height=150
    )

with col_input2:
    uploaded_file = st.file_uploader("📁 Ou upload un fichier (.txt ou .csv)", type=["txt", "csv"])

urls = []

# Extraction depuis le champ texte
if urls_text.strip():
    urls += [u.strip() for u in urls_text.splitlines() if u.strip().startswith("http")]

# Extraction intelligente depuis le fichier CSV ou TXT
if uploaded_file is not None:
    if uploaded_file.name.endswith(".txt"):
        # On tente de lire le TXT
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        urls += [u.strip() for u in content.splitlines() if u.strip().startswith("http")]
    
    elif uploaded_file.name.endswith(".csv"):
        # Liste des encodages fréquents (UTF-8 classique, puis formats Excel)
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        for enc in encodings:
            try:
                uploaded_file.seek(0) # Rembobine le fichier au début
                df_temp = pd.read_csv(uploaded_file, encoding=enc)
                
                # Vérification du séparateur si tout est sur une seule colonne
                if len(df_temp.columns) == 1 and ';' in str(df_temp.columns[0]):
                    uploaded_file.seek(0)
                    df_temp = pd.read_csv(uploaded_file, sep=';', encoding=enc)
                
                df = df_temp
                break # On sort de la boucle si la lecture a réussi sans erreur d'encodage
            except UnicodeDecodeError:
                continue # Passe à l'encodage suivant si ça plante
                
        if df is None:
            st.error("❌ Impossible de lire le fichier CSV. Format d'encodage inconnu.")
        else:
            # Chercher intelligemment la colonne contenant les images
            url_col = None
            for col in df.columns:
                if str(col).strip().lower() in ['image', 'url', 'lien', 'link']:
                    url_col = col
                    break
            
            # Si pas de nom explicite, chercher une colonne contenant "http"
            if not url_col:
                for col in df.columns:
                    if df[col].astype(str).str.contains('http').any():
                        url_col = col
                        break
                        
            if url_col:
                urls += [str(x).strip() for x in df[url_col].dropna().tolist() if str(x).strip().startswith("http")]
            else:
                st.error("❌ Impossible de trouver une colonne avec des URLs dans le CSV.")

# Dédoublonnage en gardant l'ordre STRICT d'apparition
seen = set()
ordered_urls = []
for u in urls:
    if u not in seen:
        ordered_urls.append(u)
        seen.add(u)

# ------------------------------
# 2) PROCESSING
# ------------------------------
if st.button("🚀 Convertir", type="primary"):
    if not ordered_urls:
        st.warning("⚠️ Aucun lien valide trouvé.")
    elif upload_to_imgbb and not imgbb_api_key:
         st.error("❌ Impossible de lancer : La clé API ImgBB est requise pour l'hébergement.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        zip_buffer = BytesIO()
        session = requests.Session()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(ordered_urls):
                row_data = {
                    "Index": i + 1,
                    "URL Input": url,
                    "Nom Fichier PNG": "",
                    "URL ImgBB": "N/A",
                    "Statut": "En attente"
                }

                try:
                    status_text.text(f"⏳ Traitement ({i+1}/{len(ordered_urls)}) : {url}")
                    
                    response = session.get(url, timeout=15)
                    response.raise_for_status()

                    raw_filename = url.split("/")[-1].split("?")[0] 
                    if not raw_filename: 
                        raw_filename = f"image_{i+1}"
                    
                    name_png = re.sub(r'\.[a-zA-Z0-9]+$', '', raw_filename) + ".png"
                    
                    img = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    zip_file.writestr(name_png, img_bytes)
                    
                    row_data["Nom Fichier PNG"] = name_png
                    row_data["Statut"] = "Succès local"

                    # Upload sur ImgBB
                    if upload_to_imgbb:
                        status_text.text(f"☁️ Upload ImgBB ({i+1}/{len(ordered_urls)}) : {name_png}")
                        
                        b64_image = base64.b64encode(img_bytes).decode('utf-8')
                        payload = {
                            "key": imgbb_api_key,
                            "image": b64_image,
                            "name": name_png.replace(".png", "")
                        }
                        
                        imgbb_res = requests.post("https://api.imgbb.com/1/upload", data=payload, timeout=20)
                        imgbb_res.raise_for_status()
                        imgbb_data = imgbb_res.json()
                        
                        if imgbb_data.get("success"):
                            row_data["URL ImgBB"] = imgbb_data["data"]["url"]
                            row_data["Statut"] = "Succès complet"
                        else:
                            error_msg = imgbb_data.get('error', {}).get('message', 'Erreur API')
                            row_data["Statut"] = f"Echec ImgBB: {error_msg}"

                except Exception as e:
                    row_data["Statut"] = f"Erreur: {str(e)}"

                results.append(row_data)
                progress_bar.progress((i + 1) / len(ordered_urls))

        status_text.text("✅ Traitement terminé !")
        
        # ------------------------------
        # 3) RESULTATS & TELECHARGEMENT
        # ------------------------------
        df_res = pd.DataFrame(results)

        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            st.download_button(
                label="📥 Télécharger Images (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="images_converties.zip",
                mime="application/zip",
                use_container_width=True
            )

        with col_dl2:
            # On exporte le résultat en utf-8 avec signature BOM pour qu'Excel l'ouvre bien sans casser les accents
            csv_data = "\ufeff" + df_res.to_csv(index=False, sep=';')
            st.download_button(
                label="📊 Télécharger la liste (CSV)",
                data=csv_data.encode('utf-8'),
                file_name="resultats_ordonnes.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.write("### 🔍 Rapport détaillé de l'opération")
        st.dataframe(df_res, use_container_width=True)
