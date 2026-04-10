#!/usr/bin/env bash
# ===========================================================================
# build_lambda_zip.sh
#
# Packages the OutlookPlus backend into a ZIP file that AWS Lambda can run.
#
# Usage:
#   cd OutlookPlus/backend
#   bash build_lambda_zip.sh
#
# Output:  lambda_package.zip  (in the current directory)
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use /tmp for the build to avoid filesystem permission issues.
BUILD_DIR=$(mktemp -d /tmp/lambda_build_XXXXXX)
ZIP_FILE="$SCRIPT_DIR/lambda_package.zip"

cleanup() { rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

rm -f "$ZIP_FILE"

# ------------------------------------------------------------------
# 1. Install Python dependencies into the build directory.
#    --platform manylinux2014_x86_64 ensures wheels match Lambda runtime.
#    If you're on an ARM Mac, this flag is essential.
# ------------------------------------------------------------------
echo "==> Installing dependencies..."
pip install \
  --target "$BUILD_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  -r requirements.txt \
  2>&1 | tail -5

# ------------------------------------------------------------------
# 2. Copy application code into the build directory.
# ------------------------------------------------------------------
echo "==> Copying application code..."
cp -r outlookplus_backend "$BUILD_DIR/"
cp lambda_handler.py      "$BUILD_DIR/"

# ------------------------------------------------------------------
# 3. Remove unnecessary files to shrink the ZIP.
# ------------------------------------------------------------------
echo "==> Trimming unnecessary files..."
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type d -name "tests"       -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -name "*.pyc"               -delete 2>/dev/null || true
rm -rf "$BUILD_DIR/uvicorn" 2>/dev/null || true

# ------------------------------------------------------------------
# 4. Create the ZIP using Python (cross-platform, no external tools).
# ------------------------------------------------------------------
echo "==> Creating ZIP..."
python3 -c "
import zipfile, os, sys

build_dir = sys.argv[1]
zip_path  = sys.argv[2]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(build_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, build_dir)
            zf.write(full, arcname)

size = os.path.getsize(zip_path)
count = len(zipfile.ZipFile(zip_path).namelist())
unit = f'{size/1024/1024:.1f}M' if size > 1024*1024 else f'{size/1024:.0f}K'
print(f'  Wrote {zip_path}  ({unit}, {count} files)')
" "$BUILD_DIR" "$ZIP_FILE"

echo ""
echo "==> Done!  lambda_package.zip created."
echo ""
echo "Next steps:"
echo "  1. Create a Lambda function:"
echo "     aws lambda create-function \\"
echo "       --function-name OutlookPlusBackend \\"
echo "       --runtime python3.10 \\"
echo "       --handler lambda_handler.handler \\"
echo "       --role arn:aws:iam::<ACCOUNT_ID>:role/<LAMBDA_ROLE> \\"
echo "       --zip-file fileb://lambda_package.zip \\"
echo "       --timeout 30 \\"
echo "       --memory-size 256"
echo ""
echo "  2. Or update an existing function:"
echo "     aws lambda update-function-code \\"
echo "       --function-name OutlookPlusBackend \\"
echo "       --zip-file fileb://lambda_package.zip"
echo ""
echo "  3. Or run the full deploy script:"
echo "     export LAMBDA_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/<ROLE>"
echo "     bash deploy_aws.sh"
