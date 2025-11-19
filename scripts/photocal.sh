#!/bin/bash

################################################################################
# ASTEP Photometric Calibration Pipeline
#
# This script performs photometric calibration on ASTEP telescope images.
# It can process either all date directories in a data path or a single
# specific date directory.
#
# Usage: ./photocal.sh <data_path> [OPTIONS]
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
# The script performs:
#   - Dark frame combination
#   - Flat field generation
#   - Science image calibration
#   - Cosmic ray removal
#
# Examples:
#   ./photocal.sh /path/to/data                    # Process all dates
#   ./photocal.sh /path/to/data/2024-01-15         # Process specific date
#   ./photocal.sh /path/to/data --force            # Force reprocess all dates
#   ./photocal.sh /path/to/data --mem-limit 16.0   # Use 16GB memory limit
################################################################################

# Configuration
# Auto-detect memory limit based on environment
MEM_LIMIT_GB=2.0  # Default memory limit in GB for laptop/local use

# Check if running on Engaging cluster with SLURM allocation
if [[ -n "$SLURM_JOB_ID" ]]; then
    echo "Detected SLURM job environment (Job ID: $SLURM_JOB_ID)"
    module load miniforge
    source activate base

    # Check if high memory is allocated (SLURM_MEM_PER_NODE is in MB)
    if [[ -n "$SLURM_MEM_PER_NODE" ]]; then
        # Convert MB to GB and use 25% of allocated memory
        ALLOCATED_GB=$(echo "scale=1; $SLURM_MEM_PER_NODE / 1024" | bc)
        MEM_LIMIT_GB=$(echo "scale=1; $ALLOCATED_GB * 0.25" | bc)
        echo "SLURM allocated memory: ${ALLOCATED_GB} GB"
        echo "Setting memory limit to ${MEM_LIMIT_GB} GB (25% of allocation)"
    elif [[ -n "$SLURM_MEM_PER_CPU" ]] && [[ -n "$SLURM_CPUS_ON_NODE" ]]; then
        # Calculate total memory from per-CPU allocation
        TOTAL_MEM_MB=$(echo "$SLURM_MEM_PER_CPU * $SLURM_CPUS_ON_NODE" | bc)
        ALLOCATED_GB=$(echo "scale=1; $TOTAL_MEM_MB / 1024" | bc)
        MEM_LIMIT_GB=$(echo "scale=1; $ALLOCATED_GB * 0.25" | bc)
        echo "SLURM allocated memory: ${ALLOCATED_GB} GB (${SLURM_MEM_PER_CPU}MB × ${SLURM_CPUS_ON_NODE} CPUs)"
        echo "Setting memory limit to ${MEM_LIMIT_GB} GB (25% of allocation)"
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
# Environment setup
# ========================================
# Ensure the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    conda activate astep
fi

# ========================================
# Photometric calibration
# ========================================
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

echo ""
echo "============================================================"
echo "Photometric calibration complete"
echo "============================================================"
