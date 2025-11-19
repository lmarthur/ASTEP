#!/bin/bash

################################################################################
# ASTEP Full Calibration Pipeline
#
# This script performs both photometric and astrometric calibration on ASTEP
# telescope images. It can process either all date directories in a data path
# or a single specific date directory.
#
# Usage: ./full_calibration.sh <data_path> [OPTIONS]
#
# Arguments:
#   data_path: Either:
#              - Path to directory containing date subdirectories (YYYY-MM-DD)
#              - Path to a specific date directory (YYYY-MM-DD)
#
# Options:
#   --mem-limit LIMIT   Override memory limit in GB (default: auto-detect or 2.0)
#   --force             Force recalibration even if already done
#
# The script performs two main steps:
#   1. Photometric calibration (photocal.sh)
#   2. Astrometric calibration (astrocal.sh)
#
# Examples:
#   ./full_calibration.sh /path/to/data                    # Process all dates
#   ./full_calibration.sh /path/to/data/2024-01-15         # Process specific date
#   ./full_calibration.sh /path/to/data --force            # Force reprocess all dates
#   ./full_calibration.sh /path/to/data --mem-limit 16.0   # Use 16GB memory limit
################################################################################

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ========================================
# Validate command-line arguments
# ========================================
if [ $# -lt 1 ]; then
    echo "Error: Data path not provided"
    echo "Usage: $0 <data_path> [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  data_path           Path to data directory (containing date subdirectories)"
    echo "                      or specific date directory (YYYY-MM-DD)"
    echo ""
    echo "Options:"
    echo "  --mem-limit LIMIT   Override memory limit in GB (default: auto-detect or 2.0)"
    echo "  --force             Force recalibration even if calibrated files already exist"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/data"
    echo "  $0 /path/to/data/2024-01-15"
    echo "  $0 /path/to/data --force"
    echo "  $0 /path/to/data --mem-limit 16.0"
    exit 1
fi

# Store all arguments to pass to sub-scripts
ALL_ARGS="$@"

# Extract data path for display
DATA_PATH="$1"

echo "============================================================"
echo "ASTEP Full Calibration Pipeline"
echo "============================================================"
echo "Data path: $DATA_PATH"
echo ""

# ========================================
# Step 1: Photometric calibration
# ========================================
echo "============================================================"
echo "Step 1: Photometric Calibration"
echo "============================================================"

"$SCRIPT_DIR/photocal.sh" $ALL_ARGS

# Check if photometric calibration succeeded
if [ $? -ne 0 ]; then
    echo "ERROR: Photometric calibration failed"
    exit 1
fi

# ========================================
# Step 2: Astrometric calibration
# ========================================
echo ""
echo "============================================================"
echo "Step 2: Astrometric Calibration"
echo "============================================================"

# Filter out --mem-limit argument for astrocal.sh (it doesn't need it)
ASTRO_ARGS=""
SKIP_NEXT=false
for arg in $ALL_ARGS; do
    if $SKIP_NEXT; then
        SKIP_NEXT=false
        continue
    fi
    if [[ "$arg" == "--mem-limit" ]]; then
        SKIP_NEXT=true
        continue
    fi
    ASTRO_ARGS="$ASTRO_ARGS $arg"
done

"$SCRIPT_DIR/astrocal.sh" $ASTRO_ARGS

# Check if astrometric calibration succeeded
if [ $? -ne 0 ]; then
    echo "ERROR: Astrometric calibration failed"
    exit 1
fi

echo ""
echo "============================================================"
echo "Full calibration complete"
echo "============================================================"
