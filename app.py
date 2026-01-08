import streamlit as st
import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
import zipfile

# Configuration de la page
st.set_page_config(page_title="WEBP to PNG (Ordre conservé)", page_icon="📝")

st.title("📝 WEBP ➜ PNG (Export CSV Ordonné)")
st.markdown("L'ordre d'entrée sera **strictement respecté** dans le fichier CSV final.")

# ------------------------------
# 1) INPUT SECTION
# ------------------------------

urls_text = st.text_area(
    "📌 Colle tes liens WEBP (1 par ligne)",
    placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp",
    height=150
)

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
        st.warning("⚠️ Aucun lien trouvé.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Buffer pour le ZIP
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # On utilise enumerate pour garder la trace de l'index (1, 2, 3...)
            for i, url in enumerate(ordered_urls):
                
                # Objet résultat par défaut pour maintenir la ligne même en cas d'erreur
                row_data = {
                    "Index": i + 1,  # Pour garantir l'ordre visuel
                    "URL Input": url,
                    "Nom Fichier PNG": "",
                    "Statut": "En attente"
                }

                try:
                    status_text.text(f"Traitement ({i+1}/{len(ordered_urls)}) : {url}")
                    
                    # Téléchargement
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()

                    # Définition du nom de fichier
                    # On nettoie l'URL pour avoir un nom propre
                    filename = url.split("/")[-1].split("?")[0] 
                    if not filename: 
                        filename = f"image_{i+1}.webp"
                    
                    name_png = filename.replace(".webp", ".png")
                    # Sécurité si l'extension n'était pas .webp
                    if not name_png.lower().endswith(".png"):
                        name_png += ".png"
                    
                    # Conversion en mémoire
                    img = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    # Ajout dans le ZIP
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    zip_file.writestr(name_png, img_byte_arr.getvalue())

                    # Mise à jour des données de réussite
                    row_data["Nom Fichier PNG"] = name_png
                    row_data["Statut"] = "Succès"
                
                except Exception as e:
                    row_data["Statut"] = f"Erreur: {str(e)}"

                # On ajoute la ligne au tableau de résultats
                results.append(row_data)

                # Mise à jour barre de progression
                progress_bar.progress((i + 1) / len(ordered_urls))

        status_text.text("✅ Traitement terminé !")
        
        # ------------------------------
        # 3) RESULTATS & TELECHARGEMENT
        # ------------------------------
        
        # Création du DataFrame (Tableau)
        df_res = pd.DataFrame(results)

        col1, col2 = st.columns(2)
        
        # Bouton 1 : ZIP des images
        with col1:
            st.download_button(
                label="📥 Télécharger Images (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="images_converties.zip",
                mime="application/zip"
            )

        # Bouton 2 : CSV (Ordre conservé)
        with col2:
            # Conversion du DataFrame en CSV (string encoded utf-8)
            csv_data = df_res.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📊 Télécharger la liste (CSV)",
                data=csv_data,
                file_name="liste_liens_ordonnee.csv",
                mime="text/csv"
            )

        st.write("### 🔍 Vérification de l'ordre")
        st.dataframe(df_res, use_container_width=True)
