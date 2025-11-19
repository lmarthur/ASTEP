#!/bin/bash

################################################################################
# ASTEP Astrometric Calibration Pipeline
#
# This script performs astrometric calibration on ASTEP telescope images
# using Astrometry.net. It can process either all date directories in a data
# path or a single specific date directory.
#
# Usage: ./astrocal.sh <data_path> [OPTIONS]
#
# Arguments:
#   data_path: Either:
#              - Path to directory containing date subdirectories (YYYY-MM-DD)
#              - Path to a specific date directory (YYYY-MM-DD)
#
# Options:
#   --force             Force recalibration even if already done
#
# The script uses Astrometry.net to solve the WCS (World Coordinate System)
# for each calibrated image.
#
# Examples:
#   ./astrocal.sh /path/to/data                    # Process all dates
#   ./astrocal.sh /path/to/data/2024-01-15         # Process specific date
#   ./astrocal.sh /path/to/data --force            # Force reprocess all dates
################################################################################

# Check if running on Engaging cluster with SLURM allocation
if [[ -n "$SLURM_JOB_ID" ]]; then
    echo "Detected SLURM job environment (Job ID: $SLURM_JOB_ID)"
    module load miniforge
    source activate base
fi

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
    echo "  --force             Force recalibration even if already done"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/data"
    echo "  $0 /path/to/data/2024-01-15"
    echo "  $0 /path/to/data --force"
    exit 1
fi

# Extract data path from command line
DATA_PATH="$1"
shift  # Remove data path from arguments, leaving optional flags

# Parse optional arguments
FORCE_FLAG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE_FLAG="--force"
            echo "Force recalibration enabled"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ========================================
# Detect if path is a specific date directory
# ========================================
# Extract the basename to check if it's a date
BASENAME=$(basename "$DATA_PATH")

# Check if the basename matches YYYY-MM-DD pattern
if [[ "$BASENAME" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Detected specific date directory: $BASENAME"
    SPECIFIC_DATE="$BASENAME"
    # Adjust DATA_PATH to be the parent directory
    DATA_PATH=$(dirname "$DATA_PATH")
    echo "Adjusted data path to parent: $DATA_PATH"
else
    SPECIFIC_DATE=""
fi

# ========================================
# Environment setup
# ========================================
# Ensure the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    conda activate astep
fi

# ========================================
# Astrometric calibration
# ========================================
echo ""
echo "============================================================"
echo "Running astrometric calibration"
echo "============================================================"

# Determine which dates to process
if [[ -n "$SPECIFIC_DATE" ]]; then
    # Process only the specific date
    DATES_TO_PROCESS=("$SPECIFIC_DATE")
else
    # Auto-discover all date directories (YYYY-MM-DD format)
    DATES_TO_PROCESS=()
    for date_dir in "$DATA_PATH"/*; do
        # Skip if not a directory
        if [ ! -d "$date_dir" ]; then
            continue
        fi

        # Extract the date from the directory name
        date=$(basename "$date_dir")

        # Validate that directory name matches YYYY-MM-DD format
        if [[ "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            DATES_TO_PROCESS+=("$date")
        fi
    done
fi

# Process each date
for date in "${DATES_TO_PROCESS[@]}"; do
    date_dir="$DATA_PATH/$date"

    # Skip if the date directory doesn't exist
    if [ ! -d "$date_dir" ]; then
        echo "WARNING: Date directory not found: $date_dir"
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
echo "Astrometric calibration complete"
echo "============================================================"
