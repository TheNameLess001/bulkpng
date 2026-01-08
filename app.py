import streamlit as st
import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO

st.title("WEBP ➜ PNG Converter")
st.write("Colle tes liens ou importe un fichier .txt / .csv")

# ------------------------------
# 1) INPUT SECTION
# ------------------------------

# Text area manual input
urls_text = st.text_area(
    "📌 Colle tes liens WEBP (1 par ligne)",
    placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp"
)

# File uploader
uploaded_file = st.file_uploader("📁 Ou upload un fichier (.txt ou .csv)", type=["txt", "csv"])

urls = []

# Extract URLs from text input
if urls_text.strip():
    urls += [u.strip() for u in urls_text.splitlines() if u.strip()]

# Extract URLs from uploaded file
if uploaded_file is not None:
    if uploaded_file.name.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8")
        urls += [u.strip() for u in content.splitlines() if u.strip()]
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        # prend la première colonne
        first_col = df.columns[0]
        urls += [str(x).strip() for x in df[first_col].dropna().tolist()]

# Remove duplicates but preserve original order
seen = set()
ordered_urls = []
for u in urls:
    if u not in seen:
        ordered_urls.append(u)
        seen.add(u)

# ------------------------------
# 2) PROCESSING
# ------------------------------

output_folder = "png_output"
os.makedirs(output_folder, exist_ok=True)

if st.button("🚀 Convertir"):
    if not ordered_urls:
        st.warning("⚠️ Insère ou upload au moins un lien WEBP.")
    else:
        results = []
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(ordered_urls):
            try:
                status.text(f"Téléchargement : {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                # Nom PNG
                name = url.split("/")[-1].replace(".webp", ".png")
                if not name.lower().endswith(".png"):
                    name += ".png"

                output_path = os.path.join(output_folder, name)

                img = Image.open(BytesIO(response.content)).convert("RGBA")
                img.save(output_path, "PNG")

                results.append({"webp_url": url, "png_path": output_path})
            except Exception as e:
                results.append({"webp_url": url, "png_path": None})

            progress.progress((i + 1) / len(ordered_urls))

        # ------------------------------
        # 3) SAVE OUTPUT TO EXCEL
        # ------------------------------
        df = pd.DataFrame(results)
        excel_file = "converted_links.xlsx"
        df.to_excel(excel_file, index=False)

        st.success("🎉 Conversion terminée !")
        st.download_button("📥 Télécharger Excel", data=open(excel_file, "rb"), file_name=excel_file)

        st.write("### 📊 Résultat")
        st.dataframe(df)

        st.write("### 📸 Aperçu des PNG :")
        for r in results:
            if r["png_path"]:
                st.image(r["png_path"], width=200)
