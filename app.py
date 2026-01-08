import streamlit as st
import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO

st.title("WEBP ➜ PNG Converter (From URLs)")

# 🔗 Put your links here
urls = [
    "https://example.com/img1.webp",
    "https://example.com/img2.webp",
    "https://example.com/img3.webp"
]

output_folder = "png_output"
os.makedirs(output_folder, exist_ok=True)

results = []

if st.button("🚀 Convert ALL"):
    progress = st.progress(0)
    status = st.empty()

    for i, url in enumerate(urls):
        try:
            status.text(f"Downloading: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Filename
            name = url.split("/")[-1].replace(".webp", ".png")
            output_path = os.path.join(output_folder, name)

            # Convert
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            img.save(output_path, "PNG")

            results.append({"webp_url": url, "png_path": output_path})
        except Exception as e:
            results.append({"webp_url": url, "png_path": None})

        progress.progress((i + 1) / len(urls))

    # dataframe output
    df = pd.DataFrame(results)
    df.to_csv("converted_links.csv", index=False)

    st.success("🎉 Done! PNGs saved and CSV created.")
    st.dataframe(df)

    # preview of converted images
    st.write("### 📸 Preview:")
    for r in results:
        if r["png_path"]:
            st.image(r["png_path"], width=200)
