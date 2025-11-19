#!/bin/bash

################################################################################
# Quick SLURM Job Submission for Single Date Calibration
#
# This script submits a single calibration job for a specific date.
# For processing multiple dates in parallel, use submit_cal_array.sh instead.
#
# Usage: ./scripts/submit_single_date.sh <date_path> [OPTIONS]
#
# Arguments:
#   date_path: Path to specific date directory (e.g., /data/2024-01-15)
#              or date string with base path
#
# Options:
#   --mem MEM         Memory in GB (default: 16)
#   --time TIME       Time limit (default: 04:00:00)
#   --partition NAME  SLURM partition (default: sched_mit_hill)
#   --cpus N          Number of CPUs (default: 4)
#   --force           Force recalibration
#   --dry-run         Show sbatch command without submitting
#
# Examples:
#   ./scripts/submit_single_date.sh /data/2024-01-15
#   ./scripts/submit_single_date.sh /data/2024-01-15 --mem 32 --time 08:00:00
#   ./scripts/submit_single_date.sh /data/2024-01-15 --force --dry-run
################################################################################

# Default values
MEM_LIMIT="16"
TIME_LIMIT="04:00:00"
PARTITION="sched_mit_hill"
CPUS="4"
FORCE_FLAG=""
DRY_RUN=false

# Parse arguments
if [ $# -lt 1 ]; then
    echo "Error: Date path not provided"
    echo "Usage: $0 <date_path> [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --mem MEM         Memory in GB (default: 16)"
    echo "  --time TIME       Time limit (default: 04:00:00)"
    echo "  --partition NAME  SLURM partition (default: sched_mit_hill)"
    echo "  --cpus N          Number of CPUs (default: 4)"
    echo "  --force           Force recalibration"
    echo "  --dry-run         Show command without submitting"
    exit 1
fi

DATE_PATH="$1"
shift

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mem)
            MEM_LIMIT="$2"
            shift 2
            ;;
        --time)
            TIME_LIMIT="$2"
            shift 2
            ;;
        --partition)
            PARTITION="$2"
            shift 2
            ;;
        --cpus)
            CPUS="$2"
            shift 2
            ;;
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate path
if [ ! -d "$DATE_PATH" ]; then
    echo "ERROR: Date path does not exist: $DATE_PATH"
    exit 1
fi

# Extract date from path
DATE_NAME=$(basename "$DATE_PATH")

# Validate date format
if [[ ! "$DATE_NAME" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "ERROR: Path does not appear to be a date directory (YYYY-MM-DD)"
    echo "Provided: $DATE_NAME"
    exit 1
fi

# Get repository root
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Create logs directory
mkdir -p "$REPO_ROOT/logs"

# Calculate memory limit for cal.sh (use 75% of allocated)
CAL_MEM_LIMIT=$(echo "scale=1; $MEM_LIMIT * 0.75" | bc)

# Build job name
JOB_NAME="astep_cal_${DATE_NAME}"

echo "==============================================="
echo "Single Date Calibration Job Submission"
echo "==============================================="
echo "Date: $DATE_NAME"
echo "Path: $DATE_PATH"
echo "Memory: ${MEM_LIMIT}G"
echo "Time limit: $TIME_LIMIT"
echo "Partition: $PARTITION"
echo "CPUs: $CPUS"
if [ -n "$FORCE_FLAG" ]; then
    echo "Force recalibration: YES"
fi
echo "==============================================="
echo ""

# Build sbatch command
SBATCH_CMD="sbatch \
  --job-name=$JOB_NAME \
  --partition=$PARTITION \
  --nodes=1 \
  --ntasks=1 \
  --cpus-per-task=$CPUS \
  --mem=${MEM_LIMIT}G \
  --time=$TIME_LIMIT \
  --output=$REPO_ROOT/logs/cal_${DATE_NAME}_%j.out \
  --error=$REPO_ROOT/logs/cal_${DATE_NAME}_%j.err \
  --wrap=\"cd $REPO_ROOT && source \\\$(conda info --base)/etc/profile.d/conda.sh && conda activate astep && ./scripts/full_calibration.sh $DATE_PATH --mem-limit $CAL_MEM_LIMIT $FORCE_FLAG\""

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN - Would execute:"
    echo "$SBATCH_CMD"
    echo ""
else
    echo "Submitting job..."
    echo ""

    # Submit the job
    JOB_OUTPUT=$(eval $SBATCH_CMD 2>&1)
    EXIT_CODE=$?

    echo "$JOB_OUTPUT"
    echo ""

    if [ $EXIT_CODE -eq 0 ]; then
        JOB_ID=$(echo "$JOB_OUTPUT" | grep -oP '(?<=Submitted batch job )\d+')
        echo "SUCCESS: Job submitted with ID $JOB_ID"
        echo ""
        echo "Monitor job status:"
        echo "  squeue -u \$USER"
        echo "  squeue -j $JOB_ID"
        echo ""
        echo "View logs:"
        echo "  tail -f $REPO_ROOT/logs/cal_${DATE_NAME}_${JOB_ID}.out"
        echo "  tail -f $REPO_ROOT/logs/cal_${DATE_NAME}_${JOB_ID}.err"
        echo ""
        echo "Cancel job:"
        echo "  scancel $JOB_ID"
    else
        echo "ERROR: Job submission failed"
        exit 1
    fi
fi
