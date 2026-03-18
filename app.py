import streamlit as st
import os
import requests
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
import zipfile

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
st.markdown("L'ordre d'entrée sera **strictement respecté** dans le fichier CSV final.")

col_input1, col_input2 = st.columns(2)

with col_input1:
    urls_text = st.text_area(
        "📌 Colle tes liens WEBP (1 par ligne)",
        placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp",
        height=150
    )

with col_input2:
    uploaded_file = st.file_uploader("📁 Ou upload un fichier (.txt ou .csv)", type=["txt", "csv"])

urls = []

# Extraction depuis le champ texte
if urls_text.strip():
    urls += [u.strip() for u in urls_text.splitlines() if u.strip()]

# Extraction depuis le fichier
if uploaded_file is not None:
    if uploaded_file.name.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8")
        urls += [u.strip() for u in content.splitlines() if u.strip()]
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        # On suppose que les liens sont dans la 1ère colonne
        first_col = df.columns[0]
        urls += [str(x).strip() for x in df[first_col].dropna().tolist()]

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
        
        # Buffer pour le ZIP
        zip_buffer = BytesIO()
        
        # Utilisation d'une session pour optimiser les multiples requêtes GET
        session = requests.Session()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(ordered_urls):
                
                # Objet résultat par défaut
                row_data = {
                    "Index": i + 1,
                    "URL Input": url,
                    "Nom Fichier PNG": "",
                    "URL ImgBB": "N/A",
                    "Statut": "En attente"
                }

                try:
                    status_text.text(f"⏳ Traitement ({i+1}/{len(ordered_urls)}) : {url}")
                    
                    # 1. Téléchargement de l'image source
                    response = session.get(url, timeout=10)
                    response.raise_for_status()

                    # Définition du nom de fichier propre
                    filename = url.split("/")[-1].split("?")[0] 
                    if not filename: 
                        filename = f"image_{i+1}.webp"
                    
                    name_png = filename.replace(".webp", ".png")
                    if not name_png.lower().endswith(".png"):
                        name_png += ".png"
                    
                    # 2. Conversion en mémoire (WEBP -> PNG)
                    img = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    # Sauvegarde dans un buffer
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    # 3. Ajout dans le ZIP
                    zip_file.writestr(name_png, img_bytes)
                    
                    row_data["Nom Fichier PNG"] = name_png
                    row_data["Statut"] = "Succès local"

                    # 4. Upload sur ImgBB (si activé)
                    if upload_to_imgbb:
                        status_text.text(f"☁️ Upload ImgBB ({i+1}/{len(ordered_urls)}) : {name_png}")
                        
                        b64_image = base64.b64encode(img_bytes).decode('utf-8')
                        payload = {
                            "key": imgbb_api_key,
                            "image": b64_image,
                            "name": name_png.replace(".png", "")
                        }
                        
                        imgbb_res = requests.post("https://api.imgbb.com/1/upload", data=payload, timeout=15)
                        imgbb_res.raise_for_status()
                        imgbb_data = imgbb_res.json()
                        
                        if imgbb_data.get("success"):
                            row_data["URL ImgBB"] = imgbb_data["data"]["url"]
                            row_data["Statut"] = "Succès complet (Converti + Uploadé)"
                        else:
                            error_msg = imgbb_data.get('error', {}).get('message', 'Erreur API Inconnue')
                            row_data["Statut"] = f"Succès local, mais échec ImgBB: {error_msg}"

                except Exception as e:
                    row_data["Statut"] = f"Erreur: {str(e)}"

                # Ajout de la ligne au tableau de résultats
                results.append(row_data)

                # Mise à jour de la barre de progression
                progress_bar.progress((i + 1) / len(ordered_urls))

        status_text.text("✅ Traitement terminé !")
        
        # ------------------------------
        # 3) RESULTATS & TELECHARGEMENT
        # ------------------------------
        df_res = pd.DataFrame(results)

        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        
        # Bouton 1 : ZIP des images
        with col_dl1:
            st.download_button(
                label="📥 Télécharger Images (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="images_converties.zip",
                mime="application/zip",
                use_container_width=True
            )

        # Bouton 2 : CSV (Ordre conservé)
        with col_dl2:
            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Télécharger la liste (CSV)",
                data=csv_data,
                file_name="liste_liens_ordonnee.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.write("### 🔍 Rapport détaillé de l'opération")
        # On stylise un peu le dataframe pour qu'il prenne toute la largeur
        st.dataframe(df_res, use_container_width=True)
