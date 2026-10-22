"""
Packaging script for AutoML track solution.
Builds solution.zip strictly conforming to platform rules:
- All required .py files and requirements.txt placed in root of ZIP
- No nested folders or hidden directories
- Max ZIP size < 100 MB
"""

import os
import zipfile
import sys

FILES_TO_PACK = [
    "solution.py",
    "requirements.txt",
    "automl_core.py",
    "llm_advisor.py"
]

OUTPUT_ZIP = "solution.zip"

def create_submission_zip():
    print(f"[Packager] Preparing {OUTPUT_ZIP} for Boosters platform...")
    
    # Check existence
    for fname in FILES_TO_PACK:
        if not os.path.exists(fname):
            raise FileNotFoundError(f"Missing required file: {fname}")
            
    # Create ZIP archive
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in FILES_TO_PACK:
            # arcname ensures file is placed directly in root of archive without path
            zf.write(fname, arcname=fname)
            print(f"  + Added: {fname} (size: {os.path.getsize(fname)} bytes)")
            
    # Verify contents
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as zf:
        names = zf.namelist()
        print(f"\n[Verification] Files in {OUTPUT_ZIP} ({len(names)} total):")
        for n in names:
            if "/" in n or "\\" in n:
                raise ValueError(f"CRITICAL ERROR: Nested directory detected in ZIP: {n}")
            print(f"  ✓ {n}")
            
    zip_size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"\n[Success] {OUTPUT_ZIP} created successfully!")
    print(f"📦 Archive size: {zip_size_mb:.2f} MB (Limit: 100 MB - OK)")
    print("👉 You can now download and upload solution.zip to the Boosters platform.")

if __name__ == "__main__":
    create_submission_zip()
