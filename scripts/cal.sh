#!/bin/bash

################################################################################
# ASTEP Calibration Pipeline - Master Script
#
# This script performs both photometric and astrometric calibration on ASTEP
# telescope images. It can process either all date directories in a data path
# or a single specific date directory.
#
# Usage: ./cal.sh <data_path> [OPTIONS]
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
#   1. Photometric calibration (Python script)
#   2. Astrometric calibration (Astrometry.net solve-field)
#
# Examples:
#   ./cal.sh /path/to/data                    # Process all dates
#   ./cal.sh /path/to/data/2024-01-15         # Process specific date
#   ./cal.sh /path/to/data --force            # Force reprocess all dates
#   ./cal.sh /path/to/data --mem-limit 16.0   # Use 16GB memory limit
################################################################################

# Configuration
# Auto-detect memory limit based on environment
MEM_LIMIT_GB=2.0  # Default memory limit in GB for laptop/local use

# Check if running on Engaging cluster with SLURM allocation
if [[ -n "$SLURM_JOB_ID" ]]; then
    echo "Detected SLURM job environment (Job ID: $SLURM_JOB_ID)"

    # Check if high memory is allocated (SLURM_MEM_PER_NODE is in MB)
    if [[ -n "$SLURM_MEM_PER_NODE" ]]; then
        # Convert MB to GB and use 75% of allocated memory
        ALLOCATED_GB=$(echo "scale=1; $SLURM_MEM_PER_NODE / 1024" | bc)
        MEM_LIMIT_GB=$(echo "scale=1; $ALLOCATED_GB * 0.75" | bc)
        echo "SLURM allocated memory: ${ALLOCATED_GB} GB"
        echo "Setting memory limit to ${MEM_LIMIT_GB} GB (75% of allocation)"
    elif [[ -n "$SLURM_MEM_PER_CPU" ]] && [[ -n "$SLURM_CPUS_ON_NODE" ]]; then
        # Calculate total memory from per-CPU allocation
        TOTAL_MEM_MB=$(echo "$SLURM_MEM_PER_CPU * $SLURM_CPUS_ON_NODE" | bc)
        ALLOCATED_GB=$(echo "scale=1; $TOTAL_MEM_MB / 1024" | bc)
        MEM_LIMIT_GB=$(echo "scale=1; $ALLOCATED_GB * 0.75" | bc)
        echo "SLURM allocated memory: ${ALLOCATED_GB} GB (${SLURM_MEM_PER_CPU}MB × ${SLURM_CPUS_ON_NODE} CPUs)"
        echo "Setting memory limit to ${MEM_LIMIT_GB} GB (75% of allocation)"
    else
        # Running on cluster but can't determine allocation, use conservative estimate
        MEM_LIMIT_GB=8.0
        echo "Running on SLURM cluster, setting memory limit to ${MEM_LIMIT_GB} GB"
    fi
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

# Extract data path from command line
DATA_PATH="$1"
shift  # Remove data path from arguments, leaving optional flags

# Parse optional arguments
FORCE_FLAG=""
MEM_LIMIT_OVERRIDE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mem-limit)
            if [[ -n "$2" && "$2" != --* ]]; then
                MEM_LIMIT_OVERRIDE="$2"
                echo "Memory limit manually overridden to ${MEM_LIMIT_OVERRIDE} GB"
                shift 2
            else
                echo "Error: --mem-limit requires a numeric value"
                exit 1
            fi
            ;;
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

# Apply manual override if provided
if [[ -n "$MEM_LIMIT_OVERRIDE" ]]; then
    MEM_LIMIT_GB="$MEM_LIMIT_OVERRIDE"
fi

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

# Determine the path to pass to photocal.py
if [[ -n "$SPECIFIC_DATE" ]]; then
    # Pass the specific date directory
    PHOTOCAL_PATH="$DATA_PATH/$SPECIFIC_DATE"
else
    # Pass the parent data directory
    PHOTOCAL_PATH="$DATA_PATH"
fi

python src/photocal.py "$PHOTOCAL_PATH" --mem-limit $MEM_LIMIT_GB $FORCE_FLAG

# ========================================
# Step 3: Astrometric calibration
# ========================================
# This step uses Astrometry.net to solve the WCS
# (World Coordinate System) for each calibrated image
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
echo "Calibration complete"
echo "============================================================" 


