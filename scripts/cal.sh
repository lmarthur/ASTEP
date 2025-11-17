#!/bin/bash

# Configuration
MEM_LIMIT_GB=2.0  # Memory limit in GB

# Check that data path argument is provided
if [ $# -lt 1 ]; then
    echo "Error: Data path not provided"
    echo "Usage: $0 <data_path> [--force]"
    echo "Example: $0 /path/to/data"
    echo "Options:"
    echo "  --force    Force recalibration even if calibrated files already exist"
    exit 1
fi

# First argument is the data path
DATA_PATH="$1"
shift  # Remove data path from arguments, leaving optional flags

# Check for --force flag
FORCE_FLAG=""
if [[ "$1" == "--force" ]]; then
    FORCE_FLAG="--force"
    echo "Force recalibration enabled"
fi

# Check that the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    mamba activate astep
fi

# Run the photometric calibration with the data path and memory limit
python src/photocal.py "$DATA_PATH" --mem-limit $MEM_LIMIT_GB $FORCE_FLAG

# Run the astrometric calibration for each date
echo ""
echo "============================================================"
echo "Running astrometric calibration"
echo "============================================================"

# Auto-discover dates by finding date directories (YYYY-MM-DD format)
for date_dir in "$DATA_PATH"/*; do
    # Check if it's a directory
    if [ ! -d "$date_dir" ]; then
        continue
    fi

    # Extract the date from the directory name
    date=$(basename "$date_dir")

    # Check if the directory name matches date format (YYYY-MM-DD)
    if [[ ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        continue
    fi

    cal_dir="${date_dir}/${date}-CAMS_CAL"

    # Check if calibration directory exists
    if [ ! -d "$cal_dir" ]; then
        echo "WARNING: Calibration directory not found: $cal_dir"
        echo "Skipping astrometric calibration for date $date"
        continue
    fi

    echo ""
    echo "Processing astrometric calibration for date: $date"

    # Find all calibrated science images
    cal_files=("$cal_dir"/*_SCIENCE_CAL.fits)

    # Check if any files were found
    if [ ! -e "${cal_files[0]}" ]; then
        echo "WARNING: No calibrated science files found in $cal_dir"
        echo "Skipping astrometric calibration for date $date"
        continue
    fi

    echo "Found ${#cal_files[@]} calibrated science files"

    # Run solve-field on each calibrated image
    for cal_file in "${cal_files[@]}"; do
        echo "Running solve-field on $(basename "$cal_file")..."
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


