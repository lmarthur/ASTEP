# ASTEP Calibration Scripts

This directory contains scripts for running the ASTEP calibration pipeline both locally and on SLURM clusters.

## Scripts Overview

### Core Calibration Scripts

- **`full_calibration.sh`** - Complete calibration pipeline
  - Runs both photometric and astrometric calibration
  - Can process all dates or a single specific date
  - See script header for detailed usage

- **`photocal.sh`** - Photometric calibration only
  - Dark frame combination, flat field generation
  - Science image calibration, cosmic ray removal
  - Automatically detects SLURM environment and adjusts memory limits

- **`astrocal.sh`** - Astrometric calibration only
  - Uses Astrometry.net to solve WCS for calibrated images
  - Requires photometric calibration to be completed first

- **`cal.sh`** - Legacy script (deprecated)
  - Original combined calibration script
  - Use `full_calibration.sh` instead

### SLURM Submission Scripts

- **`submit_single_date.sh`** - Submit a single date calibration job
  - Quick and easy for processing one date
  - Use when you only need to calibrate one specific observation date

- **`submit_cal_array.sh`** - Submit parallel array jobs for multiple dates
  - Automatically discovers all date directories
  - Submits one SLURM job per date for parallel processing
  - Most efficient for processing many dates

- **`submit_cal.sh`** - Template SLURM submission script
  - Manual configuration template
  - Edit configuration section for custom setups
  - Supports both single jobs and array jobs

## Quick Start Examples

### Local Execution

Process all dates in a directory (full calibration):
```bash
./scripts/full_calibration.sh /path/to/data
```

Process a single specific date:
```bash
./scripts/full_calibration.sh /path/to/data/2024-01-15
```

Run only photometric calibration:
```bash
./scripts/photocal.sh /path/to/data/2024-01-15
```

Run only astrometric calibration:
```bash
./scripts/astrocal.sh /path/to/data/2024-01-15
```

With options:
```bash
./scripts/full_calibration.sh /path/to/data --mem-limit 16.0 --force
```

### SLURM Execution

#### Single Date

Submit one date to SLURM:
```bash
./scripts/submit_single_date.sh /path/to/data/2024-01-15
```

With custom resources:
```bash
./scripts/submit_single_date.sh /path/to/data/2024-01-15 \
  --mem 32 \
  --time 08:00:00 \
  --cpus 8
```

#### Multiple Dates (Parallel)

Submit all dates as array job (most efficient):
```bash
./scripts/submit_cal_array.sh /path/to/data
```

With custom settings:
```bash
./scripts/submit_cal_array.sh /path/to/data \
  --mem 32 \
  --time 08:00:00 \
  --partition sched_mit_hill \
  --force
```

Dry run (see what would be submitted):
```bash
./scripts/submit_cal_array.sh /path/to/data --dry-run
```

#### Manual Template

For custom workflows, edit and use `submit_cal.sh`:
```bash
# 1. Edit configuration in submit_cal.sh
vim scripts/submit_cal.sh

# 2. Submit
sbatch scripts/submit_cal.sh
```

## SLURM Options Reference

Common options available in submission scripts:

| Option | Default | Description |
|--------|---------|-------------|
| `--mem` | 16G | Memory per job |
| `--time` | 04:00:00 | Time limit (HH:MM:SS) |
| `--partition` | sched_mit_hill | SLURM partition name |
| `--cpus` | 4 | CPUs per task |
| `--force` | - | Force recalibration |
| `--dry-run` | - | Show command without submitting |

## Monitoring Jobs

Check job status:
```bash
squeue -u $USER
```

View specific job:
```bash
squeue -j <job_id>
```

View logs (while running):
```bash
tail -f logs/cal_<job_id>.out
```

Cancel a job:
```bash
scancel <job_id>
```

Cancel all your jobs:
```bash
scancel -u $USER
```

## Resource Guidelines

Typical resource requirements per date:

| Dataset Size | Memory | Time | CPUs |
|--------------|--------|------|------|
| Small (<1000 images) | 8-16G | 2-4h | 4 |
| Medium (1000-5000) | 16-32G | 4-8h | 4-8 |
| Large (>5000) | 32-64G | 8-12h | 8-16 |

Memory requirements depend on:
- Number of images
- Image dimensions
- Cosmic ray removal settings
- Astrometry.net index size

## Troubleshooting

### Out of Memory Errors

Increase memory allocation:
```bash
./scripts/submit_single_date.sh /path/to/date --mem 32
```

Or use the `--mem-limit` flag to reduce memory usage (slower):
```bash
./scripts/full_calibration.sh /path/to/date --mem-limit 8.0
```

### Time Limit Exceeded

Increase time limit:
```bash
./scripts/submit_single_date.sh /path/to/date --time 12:00:00
```

### Job Won't Start

Check partition availability:
```bash
sinfo -p sched_mit_hill
```

Try different partition:
```bash
./scripts/submit_single_date.sh /path/to/date --partition sched_any
```

### Conda Environment Issues

Make sure the `astep` conda environment exists:
```bash
conda env list
```

If needed, create/activate it before submitting:
```bash
conda activate astep
```

## Directory Structure

Expected data directory structure:
```
data/
└── 2024-01-15/
    ├── 2024-01-15-CAMS/          # Science images and darks
    ├── 2024-01-15-CAMS_SKYFLAT/  # Flat field images (optional)
    └── 2024-01-15-CAMS_CAL/      # Output: calibrated images (created by pipeline)
```

Logs are written to `logs/` in the repository root.

## Advanced Usage

### Processing Subset of Dates

Create a custom script with specific dates:
```bash
# Edit submit_cal.sh and set DATES array
DATES=(
    "2024-01-15"
    "2024-01-20"
    "2024-02-01"
)

# Submit as array job
sbatch --array=0-2 scripts/submit_cal.sh
```

### Chain Jobs with Dependencies

Submit job B to start after job A completes:
```bash
JOB_A=$(sbatch scripts/submit_single_date.sh /data/2024-01-15 | grep -oP '\d+')
sbatch --dependency=afterok:$JOB_A scripts/submit_single_date.sh /data/2024-01-16
```

### Email Notifications

Add to your submission:
```bash
sbatch --mail-type=END,FAIL --mail-user=your@email.com scripts/submit_cal.sh
```
