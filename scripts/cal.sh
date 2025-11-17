#!/bin/bash

################################################################################
# ASTEP Calibration Pipeline - Master Script
#
# This script performs both photometric and astrometric calibration on ASTEP
# telescope images. It automatically discovers all date directories in the
# provided data path and processes them sequentially.
#
# Usage: ./cal.sh <data_path> [--force]
#
# Arguments:
#   data_path: Path to directory containing date subdirectories (YYYY-MM-DD)
#   --force:   Optional flag to force recalibration even if already done
#
# The script performs two main steps:
#   1. Photometric calibration (Python script)
#   2. Astrometric calibration (Astrometry.net solve-field)
################################################################################

# Configuration
MEM_LIMIT_GB=2.0  # Memory limit in GB for photometric calibration

# ========================================
# Validate command-line arguments
# ========================================
if [ $# -lt 1 ]; then
    echo "Error: Data path not provided"
    echo "Usage: $0 <data_path> [--force]"
    echo "Example: $0 /path/to/data"
    echo "Options:"
    echo "  --force    Force recalibration even if calibrated files already exist"
    exit 1
fi

# Extract data path from command line
DATA_PATH="$1"
shift  # Remove data path from arguments, leaving optional flags

# Check for --force flag in remaining arguments
FORCE_FLAG=""
if [[ "$1" == "--force" ]]; then
    FORCE_FLAG="--force"
    echo "Force recalibration enabled"
fi

# ========================================
# Step 1: Environment setup
# ========================================
# Ensure the correct conda environment is activated
# Note: This may not work in all shell configurations
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    conda activate astep
fi

# ========================================
# Step 2: Photometric calibration
# ========================================
# This step performs:
# - Dark frame combination
# - Flat field generation
# - Science image calibration
# - Cosmic ray removal
echo "Starting photometric calibration..."
python src/photocal.py "$DATA_PATH" --mem-limit $MEM_LIMIT_GB $FORCE_FLAG

# ========================================
# Step 3: Astrometric calibration
# ========================================
# This step uses Astrometry.net to solve the WCS
# (World Coordinate System) for each calibrated image
echo ""
echo "============================================================"
echo "Running astrometric calibration"
echo "============================================================"

# Auto-discover dates by finding date directories (YYYY-MM-DD format)
# Iterate through all subdirectories in the data path
for date_dir in "$DATA_PATH"/*; do
    # Skip if not a directory
    if [ ! -d "$date_dir" ]; then
        continue
    fi

    # Extract the date from the directory name
    date=$(basename "$date_dir")

    # Validate that directory name matches YYYY-MM-DD format
    if [[ ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        continue
    fi

    # Construct path to calibrated images directory
    cal_dir="${date_dir}/${date}-CAMS_CAL"

    # Verify that photometric calibration was completed for this date
    if [ ! -d "$cal_dir" ]; then
        echo "WARNING: Calibration directory not found: $cal_dir"
        echo "Skipping astrometric calibration for date $date"
        continue
    fi

    echo ""
    echo "Processing astrometric calibration for date: $date"

    # Find all calibrated science images (those with '_CAL.fits' suffix)
    cal_files=("$cal_dir"/*_SCIENCE_CAL.fits)

    # Check if any calibrated files exist
    if [ ! -e "${cal_files[0]}" ]; then
        echo "WARNING: No calibrated science files found in $cal_dir"
        echo "Skipping astrometric calibration for date $date"
        continue
    fi

    echo "Found ${#cal_files[@]} calibrated science files"

    # Process each calibrated image with Astrometry.net
    for cal_file in "${cal_files[@]}"; do
        echo "Running solve-field on $(basename "$cal_file")..."

        # Run astrometry.net plate solver
        # Parameters:
        #   --fits-image: Update the FITS file with WCS solution
        #   --overwrite: Overwrite existing WCS if present
        #   --scale-units degwidth: Field width in degrees
        #   --scale-low/high: Expected field width range (0.9-1.1 degrees)
        #   --no-plots: Don't generate PNG plots
        #   --corr/rdls/match/solved/new-fits none: Disable extra output files
        solve-field "$cal_file" \
            --fits-image \
            --overwrite \
            --scale-units degwidth \
            --scale-low 0.9 \
            --scale-high 1.1 \
            --no-plots \
            --corr none \
            --rdls none \
            --match none \
            --solved none \
            --new-fits none

        # Check if solve-field succeeded
        if [ $? -eq 0 ]; then
            echo "Successfully processed $(basename "$cal_file")"
        else
            echo "ERROR: Failed to process $(basename "$cal_file")"
        fi
    done
done

echo ""
echo "============================================================"
echo "Calibration complete"
echo "============================================================" 


