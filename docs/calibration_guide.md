# ASTEP Calibration Pipeline Guide

This guide explains how to use the automated calibration pipeline for ASTEP telescope images.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Directory Structure](#directory-structure)
4. [Quick Start](#quick-start)
5. [Usage](#usage)
6. [Pipeline Steps](#pipeline-steps)
7. [Command-Line Options](#command-line-options)
8. [Troubleshooting](#troubleshooting)

## Overview

The ASTEP calibration pipeline automates the process of:
1. **Photometric calibration**: Bias, dark, and flat field correction of science images
2. **Cosmic ray removal**: Detection and removal of cosmic ray artifacts
3. **Astrometric calibration**: WCS (World Coordinate System) solution using Astrometry.net

The pipeline automatically discovers all date directories in your data path and processes them sequentially. It intelligently skips dates that have already been calibrated to avoid redundant processing.

## Prerequisites

### Required Software
- Python 3.x with conda/mamba
- Conda environment named `astep` with required packages:
  - astropy
  - ccdproc
  - numpy
  - astroscrappy (for cosmic ray removal)
- Astrometry.net (`solve-field` command)

### Required Data
For each observation date, you need three directories:
- `YYYY-MM-DD-CAMS`: Science images and associated dark frames
- `YYYY-MM-DD-CAMS_SKYFLAT`: Sky flat images and associated dark frames
- Files should be named with patterns: `*_SCIENCE*.fits`, `*_DARK*.fits`, `*_BIAS*.fits`

## Directory Structure

The pipeline expects the following directory structure:

```
data/
└── YYYY-MM-DD/                    # Date directory (e.g., 2012-06-04)
    ├── YYYY-MM-DD-CAMS/           # Science images
    │   ├── *_SCIENCE*.fits        # Science exposures
    │   ├── *_DARK*.fits           # Dark frames (matching science exposure time)
    │   └── *_BIAS*.fits           # Bias frames (optional)
    ├── YYYY-MM-DD-CAMS_SKYFLAT/   # Flat field images
    │   ├── *_SKYFLAT*.fits        # Sky flat exposures
    │   └── *_DARK*.fits           # Dark frames (matching flat exposure time)
    └── YYYY-MM-DD-CAMS_CAL/       # Output directory (created automatically)
        └── *_SCIENCE_CAL.fits     # Calibrated science images
```

## Quick Start

### Basic Usage
```bash
# Activate the conda environment (if not already active)
mamba activate astep

# Run the calibration pipeline
./scripts/cal.sh /path/to/data
```

The script will automatically:
1. Find all date directories (e.g., `2012-06-04`)
2. Check if calibration already exists (skips if it does)
3. Perform photometric calibration
4. Perform astrometric calibration with Astrometry.net

### Force Recalibration
To reprocess dates even if calibration already exists:
```bash
./scripts/cal.sh /path/to/data --force
```

## Usage

### Using the Bash Script (Recommended)
The `cal.sh` script handles both photometric and astrometric calibration:

```bash
# Basic usage
./scripts/cal.sh <data_path>

# Force recalibration
./scripts/cal.sh <data_path> --force

# Example
./scripts/cal.sh /Users/username/ASTEP/data
```

### Using the Python Script Directly
For photometric calibration only:

```bash
# Activate environment first
mamba activate astep

# Basic usage
python src/photocal.py <data_path>

# With options
python src/photocal.py <data_path> --mem-limit 4.0 --force
```

## Pipeline Steps

### Step 1: Date Discovery
The pipeline scans the data directory for subdirectories matching the pattern `YYYY-MM-DD` (e.g., `2012-06-04`).

### Step 2: Calibration Check
For each date, the pipeline checks if the `YYYY-MM-DD-CAMS_CAL` directory exists and contains calibrated files (`*_SCIENCE_CAL.fits`). If found, that date is skipped unless `--force` is specified.

### Step 3: Master Calibration Frames
For dates requiring processing:
- **Master Dark (Science)**: Combines all dark frames matching science exposure times
- **Master Dark (Flat)**: Combines all dark frames matching flat exposure times
- **Master Flat**: Generates normalized master flat from sky flat images
- **Bad Pixel Mask**: Creates mask to flag problematic pixels

### Step 4: Science Image Calibration
For each science image:
1. Subtract master dark
2. Divide by master flat
3. Apply bad pixel mask
4. Convert from ADU to electrons using gain factor
5. Remove cosmic rays using L.A.Cosmic algorithm
6. Save with `_CAL.fits` suffix

### Step 5: Astrometric Calibration
For each calibrated image:
1. Run Astrometry.net's `solve-field`
2. Add WCS solution to FITS header
3. Field of view constrained to 0.9-1.1 degrees

## Command-Line Options

### cal.sh Options
```
Usage: ./scripts/cal.sh <data_path> [--force]

Arguments:
  data_path    Path to directory containing date subdirectories
  --force      Force recalibration even if output files exist
```

### photocal.py Options
```
Usage: python src/photocal.py <data_path> [OPTIONS]

Required:
  data_path           Path to directory containing date subdirectories

Optional:
  --mem-limit FLOAT   Memory limit in GB (default: 2.0)
  --force             Force recalibration even if files exist
  -h, --help          Show help message
```

## Configuration

### Memory Limit
The default memory limit is 2.0 GB. You can adjust this in two ways:

1. **In cal.sh**: Edit the `MEM_LIMIT_GB` variable (line 22)
2. **Command line**: Use the `--mem-limit` flag with photocal.py

### Astrometry.net Parameters
To modify astrometric calibration parameters, edit the `solve-field` command in `cal.sh` (lines 131-142). Current settings:
- Field width: 0.9-1.1 degrees
- No plot generation
- Minimal output files

## Output Files

### Photometric Calibration Output
```
data/YYYY-MM-DD/YYYY-MM-DD-CAMS_CAL/
├── YYYY-MM-DD_HH.MM.SS_SCIENCE_CAL.fits    # Calibrated science images
├── ...
```

Each calibrated FITS file contains:
- Calibrated image data (in electrons)
- Original header preserved
- Cosmic rays removed
- Bad pixels masked

### Astrometric Calibration Output
The astrometric calibration updates the calibrated FITS files in-place, adding WCS information to the headers. Astrometry.net may also create temporary files (`.axy`, `.corr`, etc.) which are suppressed by the `--no-plots` and related flags.

## Troubleshooting

### Conda Environment Not Activating
The automatic environment activation in `cal.sh` may not work in all shell configurations. Manually activate before running:
```bash
mamba activate astep
./scripts/cal.sh /path/to/data
```

### Missing Dependencies
If you encounter import errors, verify your environment:
```bash
mamba activate astep
python -c "import astropy, ccdproc, numpy, astroscrappy"
```

### Astrometry.net Failures
If `solve-field` fails to solve images:
- Verify field of view constraints match your telescope (currently 0.9-1.1 deg)
- Check that Astrometry.net index files are installed for your field of view
- Review solve-field output for specific error messages

### Insufficient Memory
If you encounter memory errors:
- Reduce the `--mem-limit` parameter
- Process fewer images at once
- Close other applications

### Directory Not Found Errors
Ensure your directory structure matches the expected format:
- Date directories named `YYYY-MM-DD`
- Subdirectories named `YYYY-MM-DD-CAMS` and `YYYY-MM-DD-CAMS_SKYFLAT`
- FITS files with appropriate naming patterns

### Already Calibrated
If you see "Calibration already exists" but want to reprocess:
```bash
./scripts/cal.sh /path/to/data --force
```

## Examples

### Process All Available Dates
```bash
mamba activate astep
./scripts/cal.sh /Users/username/Research/ASTEP/data
```

### Process Specific Date Range
First, manually select which date directories to keep in your data path, then:
```bash
./scripts/cal.sh /Users/username/Research/ASTEP/data_subset
```

### Photometric Calibration Only
```bash
mamba activate astep
python src/photocal.py /Users/username/Research/ASTEP/data
```

### High-Memory System
For systems with more available RAM:
```bash
python src/photocal.py /path/to/data --mem-limit 8.0
```

## Additional Resources

- Main README: `../ReadMe.md`
- Calibration source code: `../src/photocal.py`
- Pipeline functions: `../src/calibration.py`
- Bash script: `../scripts/cal.sh`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review error messages carefully
3. Verify your directory structure and file naming
4. Check that all prerequisites are installed
