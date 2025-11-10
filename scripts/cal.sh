#!/bin/bash

# Configuration
MEM_LIMIT_GB=2.0  # Memory limit in GB
DATA_PATH="/Users/lmarthur/Documents/Research/ASTEP/data"

# Check that at least one date argument is provided
if [ $# -eq 0 ]; then
    echo "Error: No date provided"
    echo "Usage: $0 <date1> [date2 ...]"
    echo "Example: $0 2012-06-04"
    exit 1
fi

# Check that the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    mamba activate astep
fi

# Run the photometric calibration with the provided date(s) and memory limit
python src/photocal.py "$@" --mem-limit $MEM_LIMIT_GB

# Run the astrometric calibration for each date
echo ""
echo "============================================================"
echo "Running astrometric calibration"
echo "============================================================"

for date in "$@"; do
    # Skip if this argument is a flag (starts with --)
    if [[ "$date" == --* ]]; then
        continue
    fi

    echo ""
    echo "Processing astrometric calibration for date: $date"

    cal_dir="${DATA_PATH}/${date}-CAMS_CAL"

    # Check if calibration directory exists
    if [ ! -d "$cal_dir" ]; then
        echo "WARNING: Calibration directory not found: $cal_dir"
        echo "Skipping astrometric calibration for date $date"
        continue
    fi

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


