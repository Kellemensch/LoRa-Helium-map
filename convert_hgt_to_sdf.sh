#!/bin/bash

# === CONFIGURATION ===
INPUT_DIR="/app/maps"                  # Dossier contenant les fichiers .hgt
SRTM2SDF_CMD="srtm2sdf"             # Commande ou chemin vers srtm2sdf
OUTPUT_DIR="$INPUT_DIR"             # Dossier de sortie des .sdf

# === SCRIPT ===
echo "Conversion of .hgt to .sdf in $INPUT_DIR..."

for hgt_file in "$INPUT_DIR"/*.hgt; do
    if [[ -f "$hgt_file" ]]; then
        base=$(basename "$hgt_file" .hgt)

        echo "[→] Conversion of $base.hgt..."
        "$SRTM2SDF_CMD" "$hgt_file"
    fi
done

mv *.sdf "$OUTPUT_DIR"

echo "Conversion finished."
