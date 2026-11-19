import zipfile
from pathlib import Path

source_dir = Path(__file__).parent / "ecommerce-playwright-suite"
zip_path = Path(__file__).parent / "ecommerce-playwright-suite.zip"

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for file in source_dir.rglob("*"):
        if file.is_file():
            arcname = file.relative_to(source_dir)
            zf.write(file, arcname)

print(f"Created {zip_path} with {len(zf.filelist)} files.")
