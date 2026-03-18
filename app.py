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
st.title("📝 WEBP ➜ PNG (Modification du Fichier Source)")
st.markdown("Uploade ton CSV : le script convertira les images et te renverra **ton fichier d'origine avec la colonne des liens mise à jour** !")

col_input1, col_input2 = st.columns(2)

with col_input1:
    urls_text = st.text_area(
        "📌 Colle tes liens (Optionnel, si tu n'as pas de CSV)",
        placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp",
        height=150
    )

with col_input2:
    uploaded_file = st.file_uploader("📁 Upload ton fichier source (.csv ou .txt)", type=["txt", "csv"])

urls = []
df_original = None     # Pour stocker le dataframe d'origine
url_col_name = None    # Pour mémoriser le nom de la colonne à modifier
is_csv_upload = False  # Pour savoir si on doit reconstituer un CSV à la fin

# Extraction depuis le champ texte
if urls_text.strip():
    urls += [u.strip() for u in urls_text.splitlines() if u.strip().startswith("http")]

# Extraction intelligente depuis le fichier CSV ou TXT
if uploaded_file is not None:
    if uploaded_file.name.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        urls += [u.strip() for u in content.splitlines() if u.strip().startswith("http")]
    
    elif uploaded_file.name.endswith(".csv"):
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        df = None
        
        for enc in encodings:
            try:
                uploaded_file.seek(0)
                df_temp = pd.read_csv(uploaded_file, encoding=enc, sep=None, engine='python')
                df = df_temp
                break 
            except (UnicodeDecodeError, pd.errors.ParserError, Exception):
                continue 
                
        if df is None:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';', on_bad_lines='skip')
            st.warning("⚠️ Certaines lignes mal formées ont dû être ignorées.")

        if df is not None:
            url_col = None
            for col in df.columns:
                if str(col).strip().lower() in ['image', 'url', 'lien', 'link']:
                    url_col = col
                    break
            
            if not url_col:
                for col in df.columns:
                    if df[col].astype(str).str.contains('http').any():
                        url_col = col
                        break
                        
            if url_col:
                # On sauvegarde les infos pour recréer le fichier à la fin
                df_original = df.copy()
                url_col_name = url_col
                is_csv_upload = True
                urls += [str(x).strip() for x in df[url_col].dropna().tolist() if str(x).strip().startswith("http")]
            else:
                st.error("❌ Impossible de trouver une colonne avec des URLs dans le CSV.")

# Dédoublonnage
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
        url_mapping = {} # Dictionnaire magique pour remplacer les anciennes URLs par les nouvelles
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        zip_buffer = BytesIO()
        session = requests.Session()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(ordered_urls):
                row_data = {
                    "URL Input": url,
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
                            new_link = imgbb_data["data"]["url"]
                            url_mapping[url] = new_link # On associe l'ancien lien au nouveau
                            row_data["Statut"] = "Succès complet"
                        else:
                            url_mapping[url] = url # En cas d'échec, on garde l'ancien lien
                            row_data["Statut"] = "Echec ImgBB"
                    else:
                        # Si pas d'upload ImgBB, on remplace le lien par le nom du fichier image (ex: image.png)
                        url_mapping[url] = name_png 
                        row_data["Statut"] = "Converti en local"

                except Exception as e:
                    url_mapping[url] = url # En cas d'erreur de téléchargement, on garde le lien d'origine intact
                    row_data["Statut"] = f"Erreur: {str(e)}"

                results.append(row_data)
                progress_bar.progress((i + 1) / len(ordered_urls))

        status_text.text("✅ Traitement terminé !")
        
        # ------------------------------
        # 3) RESULTATS & TELECHARGEMENT
        # ------------------------------
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

        # Création du fichier CSV final à télécharger
        if is_csv_upload and df_original is not None and url_col_name:
            df_final = df_original.copy()
            
            # MAGIE : On remplace les vieilles URLs par les nouvelles grâce au dictionnaire
            df_final[url_col_name] = df_final[url_col_name].apply(
                lambda x: url_mapping.get(str(x).strip(), x) if pd.notnull(x) else x
            )
            
            csv_data = "\ufeff" + df_final.to_csv(index=False, sep=';')
            file_name = uploaded_file.name.replace(".csv", "_modifie.csv")
            
            st.success(f"🎉 Le fichier a été mis à jour ! La colonne '{url_col_name}' contient désormais les nouveaux liens.")
            df_to_display = df_final
            
        else:
            # Si l'utilisateur a juste collé du texte, on lui sort un tableau classique de résultats
            df_to_display = pd.DataFrame(results)
            csv_data = "\ufeff" + df_to_display.to_csv(index=False, sep=';')
            file_name = "resultats_liens.csv"

        with col_dl2:
            st.download_button(
                label="📊 Télécharger le fichier CSV mis à jour",
                data=csv_data.encode('utf-8'),
                file_name=file_name,
                mime="text/csv",
                use_container_width=True
            )

        st.write("### 🔍 Aperçu du fichier de sortie")
        st.dataframe(df_to_display, use_container_width=True)
