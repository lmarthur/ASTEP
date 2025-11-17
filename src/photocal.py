"""
Photometric Calibration Pipeline for ASTEP Telescope Images

This script performs automated photometric calibration on ASTEP telescope images.
It processes all dates found in the data directory, performing bias, dark, and flat
field calibration, followed by cosmic ray removal.

The script automatically discovers date directories and skips dates that have
already been calibrated (unless --force is specified).
"""

import astropy.units as u
from astropy.nddata import CCDData
import numpy as np
# import cpu time module to monitor performance
import time

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Suppress Astropy warnings for cleaner output
import warnings
from astropy.utils.exceptions import AstropyWarning
warnings.simplefilter('ignore', category=AstropyWarning)

from src.calibration import image_combine, generate_mask, remove_cosmic_rays, combine_bias, combine_darks, generate_flat, calibrate_science_image
import argparse

def main():
    """
    Main function to perform photometric calibration on ASTEP telescope images.

    This function:
    1. Discovers all date directories in the provided data path
    2. For each date, checks if calibration already exists (skips if it does, unless --force)
    3. Combines bias and dark frames to create master calibration frames
    4. Generates master flat field from sky flats
    5. Applies calibration to science images
    6. Removes cosmic rays from calibrated images
    7. Saves calibrated images with '_CAL.fits' suffix

    Expected directory structure:
        data_path/
        └── YYYY-MM-DD/
            ├── YYYY-MM-DD-CAMS/          (science images and darks)
            ├── YYYY-MM-DD-CAMS_SKYFLAT/  (flat field images and darks)
            └── YYYY-MM-DD-CAMS_CAL/      (output: calibrated images)

    Command-line arguments:
        data_path: Path to directory containing date subdirectories
        --mem-limit: Memory limit in GB (default: 2.0)
        --force: Force recalibration even if output files exist
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Perform photometric calibration on ASTEP telescope images.')
    parser.add_argument('data_path', help='Path to the data directory containing date subdirectories')
    parser.add_argument('--mem-limit', type=float, default=2.0, help='Memory limit in GB (default: 2.0)')
    parser.add_argument('--force', action='store_true', help='Force recalibration even if calibrated files already exist')
    args = parser.parse_args()

    start_time = time.time()
    data_path = args.data_path
    mem_limit = int(args.mem_limit * 1024**3)  # Convert GB to bytes

    # ========================================
    # Step 1: Auto-discover date directories
    # ========================================
    data_path_obj = Path(data_path)
    if not data_path_obj.exists():
        print(f"ERROR: Data path does not exist: {data_path}")
        return

    # Find all directories that match the date pattern YYYY-MM-DD
    # This allows the script to automatically process all available dates
    import re
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    dates = []
    for item in sorted(data_path_obj.iterdir()):
        if item.is_dir() and date_pattern.match(item.name):
            dates.append(item.name)

    if not dates:
        print(f"No date subdirectories found in {data_path}")
        print("Expected directories matching pattern: YYYY-MM-DD")
        return

    print(f"\nData path: {data_path}")
    print(f"Memory limit: {mem_limit}")
    print(f"Found {len(dates)} date(s) to process: {', '.join(dates)}")

    # ========================================
    # Step 2: Process each date
    # ========================================
    for date in dates:
        print(f"\n{'='*60}")
        print(f"Processing date: {date}")
        print(f"{'='*60}")

        # Construct paths to expected subdirectories for this date
        date_dir = data_path + '/' + date
        science_dir = date_dir + '/' + date + '-CAMS'           # Contains science images and darks
        flat_dir = date_dir + '/' + date + '-CAMS_SKYFLAT'      # Contains flat field images and darks
        cal_path = date_dir + '/' + date + '-CAMS_CAL'          # Output directory for calibrated images

        # Check if calibration already exists (unless --force is specified)
        # This allows resuming interrupted processing and avoids redundant work
        cal_path_obj = Path(cal_path)
        if not args.force and cal_path_obj.exists():
            existing_cal_files = list(cal_path_obj.glob('*_SCIENCE_CAL.fits'))
            if existing_cal_files:
                print(f"Calibration already exists for {date} ({len(existing_cal_files)} calibrated files found)")
                print(f"Skipping date {date} (use --force to recalibrate)")
                continue

        # Check if required directories exist
        science_dir_path = Path(science_dir)
        flat_dir_path = Path(flat_dir)

        if not science_dir_path.exists():
            print(f"ERROR: Science directory not found: {science_dir}")
            print(f"Skipping date {date}")
            continue

        if not flat_dir_path.exists():
            print(f"ERROR: Flat directory not found: {flat_dir}")
            print(f"Skipping date {date}")
            continue

        # Check for required files
        flat_dark_files = list(flat_dir_path.glob('*_DARK*.fits'))
        science_dark_files = list(science_dir_path.glob('*_DARK*.fits'))
        science_files = list(science_dir_path.glob('*_SCIENCE*.fits'))

        # Check if science files exist
        if not science_files:
            print(f"ERROR: No SCIENCE files found in science directory: {science_dir}")
            print(f"Skipping date {date}")
            continue

        # Fallback logic for dark frames
        # If no dark frames in science directory, use the ones from flat directory
        if not science_dark_files and flat_dark_files:
            print(f"WARNING: No DARK files found in science directory: {science_dir}")
            print(f"Using DARK files from flat directory as fallback: {flat_dir}")
            science_dark_files = flat_dark_files
        elif not science_dark_files:
            print(f"ERROR: No DARK files found in either directory")
            print(f"Skipping date {date}")
            continue

        # Check if we have dark files for flats (or use science darks as fallback)
        if not flat_dark_files and science_dark_files:
            print(f"WARNING: No DARK files found in flat directory: {flat_dir}")
            print(f"Using DARK files from science directory as fallback: {science_dir}")
            flat_dark_files = science_dark_files
        elif not flat_dark_files:
            print(f"ERROR: No DARK files found in either directory")
            print(f"Skipping date {date}")
            continue

        print(f"Found {len(flat_dark_files)} flat dark files")
        print(f"Found {len(science_dark_files)} science dark files")
        print(f"Found {len(science_files)} science files")

        Path(cal_path).mkdir(parents=True, exist_ok=True)

        # ========================================
        # Step 3: Create master calibration frames
        # ========================================

        # Load and combine dark frames for both flat and science images
        flat_dark_images = [CCDData.read(f, unit='adu') for f in flat_dark_files]
        flat_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in flat_dark_images])
        print(f'Flat dark exposure times: {flat_dark_exposure_times}')

        science_dark_images = [CCDData.read(f, unit='adu') for f in science_dark_files]
        science_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in science_dark_images])
        print(f'Science dark exposure times: {science_dark_exposure_times}')

        # Verify exposure time consistency
        if len(science_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in science dark images. Ensure they are consistent.")
        if len(flat_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in flat dark images. Ensure they are consistent.")

        # Combine dark frames to create master darks
        science_master_dark = combine_darks(science_dark_images, science_dir, mem_limit=mem_limit)
        flat_master_dark = combine_darks(flat_dark_images, flat_dir, mem_limit=mem_limit)

        # Generate master flat field from sky flats
        flat_master = generate_flat(flat_dir, mem_limit=mem_limit)

        # Create a pixel mask to flag bad pixels
        mask = generate_mask(flat_dir)

        # ========================================
        # Step 4: Calibrate science images
        # ========================================
        science_images = [CCDData.read(f, unit='adu') for f in science_files]
        for sci in science_images:
            # Apply bias, dark, and flat field corrections
            calibrated_science_image = calibrate_science_image(sci, None, science_master_dark, master_flat=flat_master, mask=mask)

            # Convert from ADU to electrons using the gain factor
            gain = sci.header.get('GAIN', 2.0)  # Default to 2.0 if not found
            calibrated_science_image = calibrated_science_image.multiply(gain * u.electron / u.adu)

            # Remove cosmic rays using the L.A.Cosmic algorithm
            readnoise = sci.header.get('RDNOISE', 9.0)  # Default to 9.0 if not found
            calibrated_science_image = remove_cosmic_rays(calibrated_science_image, readnoise, sigclip=7.0, verbose=False)

            # Save the calibrated image with '_CAL.fits' suffix
            output_filename = cal_path + '/' + sci.header['ORIGFILE'].replace('.fits', '_CAL.fits')
            calibrated_science_image.header = sci.header  # Preserve original header
            calibrated_science_image.write(output_filename, overwrite=True)
            print(f'Saved calibrated image to {output_filename}')

    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")

# Entry point
if __name__ == '__main__':
    main()
              
            