import streamlit as st
import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
import zipfile
import shutil

# Configuration de la page
st.set_page_config(page_title="WEBP to PNG Converter", page_icon="🔄")

st.title("🔄 Convertisseur WEBP ➜ PNG")
st.markdown("Colle tes liens ci-dessous pour les convertir et les télécharger en **ZIP**.")

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

# Dédoublonnage en gardant l'ordre
seen = set()
ordered_urls = []
for u in urls:
    if u not in seen:
        ordered_urls.append(u)
        seen.add(u)

# ------------------------------
# 2) PROCESSING
# ------------------------------

# Dossier temporaire pour stocker les images avant le zip
output_folder = "png_output"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

if st.button("🚀 Convertir les images", type="primary"):
    if not ordered_urls:
        st.warning("⚠️ Aucun lien trouvé. Ajoute des URLs pour commencer.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Préparation du fichier ZIP en mémoire
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, url in enumerate(ordered_urls):
                try:
                    status_text.text(f"Traitement : {url}")
                    
                    # Téléchargement
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()

                    # Définition du nom de fichier
                    filename = url.split("/")[-1].split("?")[0] # Nettoie les paramètres URL
                    name_png = filename.replace(".webp", ".png")
                    if not name_png.lower().endswith(".png"):
                        name_png += ".png"
                    
                    # Conversion en mémoire
                    img = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    # Sauvegarde locale (optionnel, mais utile pour le debug ou l'affichage)
                    local_path = os.path.join(output_folder, name_png)
                    img.save(local_path, "PNG")
                    
                    # Ajout direct dans le ZIP (plus propre que de relire le fichier disque)
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    zip_file.writestr(name_png, img_byte_arr.getvalue())

                    results.append({"URL Source": url, "Statut": "Succès", "Fichier": name_png})
                
                except Exception as e:
                    results.append({"URL Source": url, "Statut": f"Erreur: {e}", "Fichier": "N/A"})

                # Mise à jour barre de progression
                progress_bar.progress((i + 1) / len(ordered_urls))

        status_text.text("✅ Terminé !")
        
        # ------------------------------
        # 3) RESULTATS & TELECHARGEMENT
        # ------------------------------
        
        col1, col2 = st.columns(2)
        
        # Bouton Télécharger ZIP
        with col1:
            st.success(f"{len(results)} liens traités.")
            st.download_button(
                label="📥 Télécharger toutes les images (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="images_converties.zip",
                mime="application/zip"
            )

        # Bouton Télécharger Excel (Log)
        with col2:
            df_res = pd.DataFrame(results)
            excel_buffer = BytesIO()
            # Nécessite openpyxl installé
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_res.to_excel(writer, index=False)
            
            st.download_button(
                label="📊 Télécharger le rapport (Excel)",
                data=excel_buffer.getvalue(),
                file_name="rapport_conversion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Affichage du tableau
        with st.expander("Voir le rapport détaillé"):
            st.dataframe(df_res)

        # Galerie d'aperçu (limité aux 10 premières pour ne pas surcharger)
        st.write("### 📸 Aperçu (10 premières images)")
        
        # On récupère les chemins locaux pour l'affichage
        images_to_show = [os.path.join(output_folder, r["Fichier"]) for r in results if r["Statut"] == "Succès"]
        
        # Affichage en grille
        cols = st.columns(4)
        for idx, img_path in enumerate(images_to_show[:12]): # Affiche max 12 images
            with cols[idx % 4]:
                st.image(img_path, use_container_width=True, caption=os.path.basename(img_path))

        # Nettoyage du dossier temporaire (optionnel)
        # shutil.rmtree(output_folder)
