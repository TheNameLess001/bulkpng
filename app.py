import os
import requests
import pandas as pd
from PIL import Image
from io import BytesIO

# 🔗 Put your links here, in order
urls = [
    "https://example.com/img1.webp",
    "https://example.com/img2.webp",
    "https://example.com/img3.webp"
]

output_folder = "png_output"
os.makedirs(output_folder, exist_ok=True)

results = []

for url in urls:
    try:
        # Download file
        print(f"Downloading: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Create output name
        name = url.split("/")[-1].replace(".webp", ".png")
        output_path = os.path.join(output_folder, name)

        # Convert to PNG
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img.save(output_path, "PNG")

        results.append({"webp_url": url, "png_path": output_path})
        print(f"✓ Converted → {output_path}")

    except Exception as e:
        print(f"❌ Failed for: {url} | {e}")
        results.append({"webp_url": url, "png_path": None})

# Export to CSV
df = pd.DataFrame(results)
df.to_csv("converted_links.csv", index=False)

print("\n🎉 DONE — PNG files saved + CSV created!")
print("📁 Folder:", output_folder)
print("📄 CSV: converted_links.csv")
