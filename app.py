from PIL import Image
import os

input_folder = "webp_images"      # folder where your .webp files are
output_folder = "png_images"      # folder where your .png files will be saved

os.makedirs(output_folder, exist_ok=True)

for file in os.listdir(input_folder):
    if file.lower().endswith(".webp"):
        webp_path = os.path.join(input_folder, file)
        png_name = os.path.splitext(file)[0] + ".png"
        png_path = os.path.join(output_folder, png_name)

        try:
            img = Image.open(webp_path).convert("RGBA")
            img.save(png_path, "PNG")
            print(f"Converted: {file} → {png_name}")
        except Exception as e:
            print(f"Failed to convert {file}: {e}")

print("\n🎉 DONE — All PNG files ready for GitHub upload!")
