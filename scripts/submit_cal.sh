#!/bin/bash

################################################################################
# SLURM Job Submission Script for ASTEP Calibration Pipeline
#
# This script submits calibration jobs to a SLURM cluster. It can be used to
# process either a single date or multiple dates in parallel using SLURM array
# jobs.
#
# Usage:
#   1. Edit the configuration section below to set your data path and options
#   2. Submit the job: sbatch scripts/submit_cal.sh
#
# For array jobs (processing multiple dates in parallel):
#   sbatch --array=0-N scripts/submit_cal.sh
#   where N is the number of dates minus 1
################################################################################

#SBATCH --job-name=astep_cal          # Job name
#SBATCH --partition=sched_mit_hill    # Partition (queue) name
#SBATCH --nodes=1                      # Number of nodes
#SBATCH --ntasks=1                     # Number of tasks (processes)
#SBATCH --cpus-per-task=4              # Number of CPU cores per task
#SBATCH --mem=16G                      # Total memory for the job
#SBATCH --time=04:00:00                # Time limit (HH:MM:SS)
#SBATCH --output=logs/cal_%A_%a.out    # Standard output log (%A = job ID, %a = array index)
#SBATCH --error=logs/cal_%A_%a.err     # Standard error log

################################################################################
# CONFIGURATION - Edit these variables for your setup
################################################################################

# Base data directory containing date subdirectories
DATA_BASE_DIR="/path/to/your/data"

# Memory limit in GB (should match or be less than SLURM --mem)
# The script auto-detects SLURM allocation, but you can override it here
MEM_LIMIT="12.0"  # Use 75% of allocated memory for safety

# Force recalibration even if calibrated files exist (uncomment to enable)
# FORCE_FLAG="--force"
FORCE_FLAG=""

# Conda environment name
CONDA_ENV="astep"

################################################################################
# ARRAY JOB CONFIGURATION (optional)
################################################################################
# If using SLURM array jobs to process multiple dates in parallel, define
# the list of dates here. The array index will select which date to process.
#
# Example: To process 3 dates in parallel, submit with:
#   sbatch --array=0-2 scripts/submit_cal.sh
#
# Uncomment and edit the DATES array below:

# DATES=(
#     "2024-01-15"
#     "2024-01-16"
#     "2024-01-17"
# )

################################################################################
# SCRIPT EXECUTION - No need to edit below this line
################################################################################

# Create logs directory if it doesn't exist
mkdir -p logs

# Print job information
echo "==============================================="
echo "ASTEP Calibration Job Information"
echo "==============================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Node: $SLURM_NODELIST"
echo "Partition: $SLURM_JOB_PARTITION"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE MB"
echo "Start Time: $(date)"
echo "==============================================="
echo ""

# Determine which date to process
if [ -n "$SLURM_ARRAY_TASK_ID" ]; then
    # Array job - process the date corresponding to the array index
    if [ -z "${DATES+x}" ]; then
        echo "ERROR: SLURM_ARRAY_TASK_ID is set but DATES array is not defined"
        echo "Please edit the CONFIGURATION section to define the DATES array"
        exit 1
    fi

    if [ "$SLURM_ARRAY_TASK_ID" -ge "${#DATES[@]}" ]; then
        echo "ERROR: Array index $SLURM_ARRAY_TASK_ID exceeds DATES array size ${#DATES[@]}"
        exit 1
    fi

    DATE_TO_PROCESS="${DATES[$SLURM_ARRAY_TASK_ID]}"
    DATA_PATH="$DATA_BASE_DIR/$DATE_TO_PROCESS"
    echo "Array job mode: Processing date $DATE_TO_PROCESS"
else
    # Single job - process all dates in the base directory
    DATA_PATH="$DATA_BASE_DIR"
    echo "Single job mode: Processing all dates in $DATA_BASE_DIR"
fi

echo "Data path: $DATA_PATH"
echo ""

# Check if data path exists
if [ ! -d "$DATA_PATH" ]; then
    echo "ERROR: Data path does not exist: $DATA_PATH"
    exit 1
fi

# Initialize conda for bash shell
echo "Initializing conda..."
source $(conda info --base)/etc/profile.d/conda.sh

# Activate the astep conda environment
echo "Activating $CONDA_ENV environment..."
conda activate $CONDA_ENV

if [ "$CONDA_DEFAULT_ENV" != "$CONDA_ENV" ]; then
    echo "ERROR: Failed to activate $CONDA_ENV environment"
    echo "Current environment: $CONDA_DEFAULT_ENV"
    exit 1
fi

echo "Successfully activated $CONDA_ENV environment"
echo ""

# Navigate to the repository root directory
REPO_ROOT=$(dirname $(dirname $(readlink -f $0)))
cd "$REPO_ROOT" || exit 1

echo "Repository root: $REPO_ROOT"
echo "Current directory: $(pwd)"
echo ""

# Construct the command with optional flags
CMD="./scripts/full_calibration.sh \"$DATA_PATH\" --mem-limit $MEM_LIMIT $FORCE_FLAG"

echo "==============================================="
echo "Running calibration pipeline..."
echo "Command: $CMD"
echo "==============================================="
echo ""

# Run the calibration pipeline
eval $CMD

# Capture exit status
EXIT_STATUS=$?

echo ""
echo "==============================================="
echo "Job completed with exit status: $EXIT_STATUS"
echo "End Time: $(date)"
echo "==============================================="

# Exit with the same status as the calibration script
exit $EXIT_STATUS
