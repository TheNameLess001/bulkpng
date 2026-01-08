import streamlit as st
import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO

st.title("WEBP ➜ PNG Converter (From URL List)")

# 🔽 Zone d'entrée des liens (un par ligne)
urls_text = st.text_area(
    "Colle ici tes liens WEBP (un par ligne)",
    placeholder="https://site.com/img1.webp\nhttps://site.com/img2.webp"
)

output_folder = "png_output"
os.makedirs(output_folder, exist_ok=True)

if st.button("🚀 Convertir"):
    # Convertit le text area en liste
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]

    if not urls:
        st.warning("⚠️ Insère au moins 1 lien WEBP.")
    else:
        results = []
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(urls):
            try:
                status.text(f"Téléchargement: {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                # Nom fichier PNG
                name = url.split("/")[-1].replace(".webp", ".png")
                output_path = os.path.join(output_folder, name)

                # Conversion
                img = Image.open(BytesIO(response.content)).convert("RGBA")
                img.save(output_path, "PNG")

                results.append({"webp_url": url, "png_path": output_path})
            except Exception as e:
                results.append({"webp_url": url, "png_path": None})

            progress.progress((i + 1) / len(urls))

        # CSV export
        df = pd.DataFrame(results)
        df.to_csv("converted_links.csv", index=False)

        st.success("🎉 Conversion terminée !")
        st.dataframe(df)

        st.write("### 📸 Prévisualisation:")
        for r in results:
            if r["png_path"]:
                st.image(r["png_path"], width=200)
