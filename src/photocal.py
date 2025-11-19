"""
Photometric Calibration Pipeline for ASTEP Telescope Images

This script performs automated photometric calibration on ASTEP telescope images.
It can process either all dates found in a data directory, or a single specific
date directory. Calibration includes bias, dark, and flat field corrections,
followed by cosmic ray removal.

The script automatically discovers date directories and skips dates that have
already been calibrated (unless --force is specified).

Usage:
    python photocal.py /path/to/data                    # Process all dates
    python photocal.py /path/to/data/2024-01-15         # Process specific date
    python photocal.py /path/to/data --force            # Force reprocess all dates
    python photocal.py /path/to/data --mem-limit 16.0   # Use 16GB memory limit
"""

import astropy.units as u
from astropy.nddata import CCDData
from astropy.io import fits
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
from src.utils import print_memory_usage
import argparse

def main():
    """
    Main function to perform photometric calibration on ASTEP telescope images.

    This function:
    1. Detects if data_path is a specific date directory or parent containing dates
    2. Discovers date(s) to process (single date or all dates)
    3. For each date, checks if calibration already exists (skips if it does, unless --force)
    4. Combines bias and dark frames to create master calibration frames
    5. Generates master flat field from sky flats
    6. Applies calibration to science images
    7. Removes cosmic rays from calibrated images
    8. Saves calibrated images with '_CAL.fits' suffix

    Expected directory structure:
        data_path/
        └── YYYY-MM-DD/
            ├── YYYY-MM-DD-CAMS/          (science images and darks)
            ├── YYYY-MM-DD-CAMS_SKYFLAT/  (flat field images and darks)
            └── YYYY-MM-DD-CAMS_CAL/      (output: calibrated images)

    Command-line arguments:
        data_path: Either:
                   - Path to directory containing date subdirectories (YYYY-MM-DD)
                   - Path to a specific date directory (YYYY-MM-DD)
        --mem-limit: Memory limit in GB (default: 2.0)
        --force: Force recalibration even if output files exist
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Perform photometric calibration on ASTEP telescope images.')
    parser.add_argument('data_path', help='Path to data directory (containing date subdirectories) or specific date directory (YYYY-MM-DD)')
    parser.add_argument('--mem-limit', type=float, default=2.0, help='Memory limit in GB (default: 2.0)')
    parser.add_argument('--force', action='store_true', help='Force recalibration even if calibrated files already exist')
    args = parser.parse_args()

    start_time = time.time()
    data_path = args.data_path
    mem_limit = int(args.mem_limit * 1024**3)  # Convert GB to bytes

    print_memory_usage("Program start")

    # ========================================
    # Step 1: Auto-discover date directories
    # ========================================
    data_path_obj = Path(data_path)
    if not data_path_obj.exists():
        print(f"ERROR: Data path does not exist: {data_path}")
        return

    # Check if the provided path is itself a date directory or a parent containing date directories
    import re
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    # If the provided path itself is a date directory, process only that date
    if date_pattern.match(data_path_obj.name):
        print(f"Detected specific date directory: {data_path_obj.name}")
        dates = [data_path_obj.name]
        # Adjust data_path to be the parent directory
        data_path = str(data_path_obj.parent)
        data_path_obj = data_path_obj.parent
    else:
        # Find all directories that match the date pattern YYYY-MM-DD
        # This allows the script to automatically process all available dates
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

        # Check for SKYFLAT directory (not required, but warn if missing)
        skip_flat_correction = False
        if not flat_dir_path.exists():
            print(f"WARNING: Flat directory not found: {flat_dir}")
            print(f"Flat field correction will be SKIPPED")
            print(f"Proceeding with dark correction only")
            skip_flat_correction = True

        # Check for required files
        science_dark_files = list(science_dir_path.glob('*_DARK*.fits'))
        science_files = list(science_dir_path.glob('*_SCIENCE*.fits'))
        science_bias_files = list(science_dir_path.glob('*_BIAS*.fits'))

        # Only check flat directory if it exists
        if skip_flat_correction:
            flat_dark_files = []
            flat_bias_files = []
        else:
            flat_dark_files = list(flat_dir_path.glob('*_DARK*.fits'))
            flat_bias_files = list(flat_dir_path.glob('*_BIAS*.fits'))

        # Check if science files exist
        if not science_files:
            print(f"ERROR: No SCIENCE files found in science directory: {science_dir}")
            print(f"Skipping date {date}")
            continue

        # Determine science image exposure times (using header only for efficiency)
        science_exposure_times = set()
        for sci_file in science_files:
            try:
                header = fits.getheader(sci_file)
                exptime = header.get('EXPTIME')
                if exptime is not None:
                    science_exposure_times.add(exptime)
            except Exception as e:
                print(f"Warning: Could not read exposure time from {sci_file}: {e}")

        # Flag to track whether we can perform dark correction
        skip_science_dark_correction = False
        # Flag to track if science and flat darks are shared (to avoid duplicate work)
        shared_dark_files = False

        # Fallback logic for science dark frames
        if not science_dark_files and flat_dark_files:
            print(f"WARNING: No DARK files found in science directory: {science_dir}")
            print(f"Checking DARK files from flat directory: {flat_dir}")

            # Check flat dark exposure times (using header only for efficiency)
            flat_dark_exposure_times = set()
            for dark_file in flat_dark_files:
                try:
                    header = fits.getheader(dark_file)
                    exptime = header.get('EXPTIME')
                    if exptime is not None:
                        flat_dark_exposure_times.add(exptime)
                except Exception as e:
                    print(f"Warning: Could not read exposure time from {dark_file}: {e}")

            # Check if exposure times match
            if science_exposure_times & flat_dark_exposure_times:
                print(f"Exposure times match! Science: {science_exposure_times}s, Flat darks: {flat_dark_exposure_times}s")
                print(f"Using DARK files from flat directory for science calibration")
                science_dark_files = flat_dark_files
                shared_dark_files = True
            else:
                print(f"WARNING: Exposure time mismatch!")
                print(f"  Science exposure times: {science_exposure_times}s")
                print(f"  Flat dark exposure times: {flat_dark_exposure_times}s")
                print(f"Proceeding with calibration WITHOUT dark correction (bias and flat only)")
                skip_science_dark_correction = True
        elif not science_dark_files:
            print(f"WARNING: No DARK files found in either directory")
            print(f"Proceeding with calibration WITHOUT dark correction (bias and flat only)")
            skip_science_dark_correction = True

        # If skipping dark correction, check for bias frames as fallback
        use_bias_correction = False
        bias_files_for_science = []
        bias_dir_for_science = None  # Track which directory bias files came from
        if skip_science_dark_correction:
            print(f"\nChecking for bias frames as fallback...")

            # First check science directory for bias files
            if science_bias_files:
                bias_files_for_science = science_bias_files
                bias_dir_for_science = science_dir
                print(f"Found {len(science_bias_files)} BIAS files in science directory")
                use_bias_correction = True
            # Fall back to flat directory bias files
            elif flat_bias_files:
                bias_files_for_science = flat_bias_files
                bias_dir_for_science = flat_dir
                print(f"Found {len(flat_bias_files)} BIAS files in flat directory")
                print(f"Using BIAS files from flat directory as fallback")
                use_bias_correction = True
            else:
                print(f"No BIAS files found in either directory")
                print(f"Calibration will proceed with flat correction only (no dark, no bias)")

        # Check if we have dark files for flats
        if not flat_dark_files and science_dark_files:
            print(f"WARNING: No DARK files found in flat directory: {flat_dir}")

            # Get flat exposure times to check compatibility
            flat_files = list(flat_dir_path.glob('*_SKYFLAT*.fits')) or list(flat_dir_path.glob('*_FLAT*.fits'))
            flat_exposure_times = set()
            for flat_file in flat_files[:5]:  # Sample first 5 files for efficiency
                try:
                    header = fits.getheader(flat_file)
                    exptime = header.get('EXPTIME')
                    if exptime is not None:
                        flat_exposure_times.add(exptime)
                except Exception as e:
                    print(f"Warning: Could not read exposure time from {flat_file}: {e}")

            # Get science dark exposure times
            science_dark_exposure_times = set()
            for dark_file in science_dark_files:
                try:
                    header = fits.getheader(dark_file)
                    exptime = header.get('EXPTIME')
                    if exptime is not None:
                        science_dark_exposure_times.add(exptime)
                except Exception as e:
                    print(f"Warning: Could not read exposure time from {dark_file}: {e}")

            # Check if exposure times are compatible
            if flat_exposure_times & science_dark_exposure_times:
                print(f"Exposure times compatible! Flat: {flat_exposure_times}s, Science darks: {science_dark_exposure_times}s")
                print(f"Using DARK files from science directory for flat calibration")
                flat_dark_files = science_dark_files
                shared_dark_files = True
            else:
                print(f"WARNING: Exposure time mismatch for flat calibration")
                print(f"  Flat exposure times: {flat_exposure_times}s")
                print(f"  Science dark exposure times: {science_dark_exposure_times}s")
                print(f"Flat calibration will proceed without dark correction")
                # Leave flat_dark_files as empty list
        elif not flat_dark_files:
            print(f"WARNING: No DARK files found for flat calibration")
            print(f"Flat calibration will proceed without dark correction")

        print(f"Found {len(flat_dark_files) if flat_dark_files else 0} flat dark files")
        print(f"Found {len(science_dark_files) if science_dark_files else 0} science dark files")
        print(f"Found {len(science_files)} science files")

        # Summary of corrections to be applied
        print(f"\nCalibration plan:")
        if skip_science_dark_correction and use_bias_correction:
            print(f"  - Bias correction: YES (using fallback)")
        elif skip_science_dark_correction:
            print(f"  - Bias correction: NO (no bias frames available)")
        else:
            print(f"  - Bias correction: NO (included in dark frames)")

        if skip_science_dark_correction:
            print(f"  - Dark correction: NO (no matching dark frames)")
        else:
            print(f"  - Dark correction: YES")

        if skip_flat_correction:
            print(f"  - Flat correction: NO (no SKYFLAT directory)")
        else:
            print(f"  - Flat correction: YES")

        print(f"  - Cosmic ray removal: YES")

        Path(cal_path).mkdir(parents=True, exist_ok=True)

        # Define paths for cached master calibration frames
        master_bias_path = Path(cal_path) / f'{date}_MASTERBIAS.fits'
        master_dark_science_path = Path(cal_path) / f'{date}_MASTERDARK.fits'
        master_dark_flat_path = Path(cal_path) / f'{date}_MASTERDARK_FLAT.fits'
        master_flat_path = Path(cal_path) / f'{date}_MASTERFLAT.fits'
        mask_path = Path(cal_path) / f'{date}_MASK.fits'

        # ========================================
        # Step 3: Create master calibration frames
        # ========================================

        # Create master bias (only if using bias correction as fallback)
        science_master_bias = None
        if use_bias_correction and bias_files_for_science:
            if master_bias_path.exists() and not args.force:
                print(f"\nLoading existing master bias from {master_bias_path}")
                science_master_bias = CCDData.read(master_bias_path)
                print_memory_usage("After loading master bias")
            else:
                print(f"\nCreating master bias from {len(bias_files_for_science)} bias frames...")
                bias_images = [CCDData.read(f, unit='adu') for f in bias_files_for_science]
                science_master_bias = combine_bias(bias_images, bias_dir_for_science, mem_limit=mem_limit)
                science_master_bias.write(master_bias_path, overwrite=True)
                print(f"Master bias created and saved to {master_bias_path}")
                print_memory_usage("After master bias creation")

        # Create master dark frames
        # If dark files are shared between science and flat, create only once
        flat_master_dark = None
        science_master_dark = None

        if shared_dark_files and flat_dark_files:
            # Dark files are shared - create once and use for both
            # Check if either cached file exists
            if (master_dark_science_path.exists() or master_dark_flat_path.exists()) and not args.force:
                # Load from whichever exists
                if master_dark_science_path.exists():
                    print(f"\nLoading existing shared master dark from {master_dark_science_path}")
                    shared_master_dark = CCDData.read(master_dark_science_path)
                else:
                    print(f"\nLoading existing shared master dark from {master_dark_flat_path}")
                    shared_master_dark = CCDData.read(master_dark_flat_path)
                print_memory_usage("After loading shared master dark")
            else:
                dark_images = [CCDData.read(f, unit='adu') for f in flat_dark_files]
                dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in dark_images])
                print(f'Shared dark exposure times: {dark_exposure_times}')

                if len(dark_exposure_times) > 1:
                    print("Warning: Multiple exposure times found in dark images. Ensure they are consistent.")

                shared_master_dark = combine_darks(dark_images, flat_dir if flat_dark_files else science_dir, mem_limit=mem_limit)
                # Save to both locations
                shared_master_dark.write(master_dark_science_path, overwrite=True)
                shared_master_dark.write(master_dark_flat_path, overwrite=True)
                print(f"Shared master dark saved to {master_dark_science_path} and {master_dark_flat_path}")
                print_memory_usage("After shared master dark creation")

            # Use the same master dark for both
            flat_master_dark = shared_master_dark
            science_master_dark = shared_master_dark
        else:
            # Dark files are separate - create each independently
            # Create master dark for flats (if available)
            if flat_dark_files:
                if master_dark_flat_path.exists() and not args.force:
                    print(f"\nLoading existing flat master dark from {master_dark_flat_path}")
                    flat_master_dark = CCDData.read(master_dark_flat_path)
                    print_memory_usage("After loading flat master dark")
                else:
                    flat_dark_images = [CCDData.read(f, unit='adu') for f in flat_dark_files]
                    flat_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in flat_dark_images])
                    print(f'Flat dark exposure times: {flat_dark_exposure_times}')

                    if len(flat_dark_exposure_times) > 1:
                        print("Warning: Multiple exposure times found in flat dark images. Ensure they are consistent.")

                    flat_master_dark = combine_darks(flat_dark_images, flat_dir, mem_limit=mem_limit)
                    flat_master_dark.write(master_dark_flat_path, overwrite=True)
                    print(f"Flat master dark saved to {master_dark_flat_path}")
                    print_memory_usage("After flat master dark creation")

            # Create master dark for science images (only if not skipping dark correction)
            if not skip_science_dark_correction and science_dark_files:
                if master_dark_science_path.exists() and not args.force:
                    print(f"\nLoading existing science master dark from {master_dark_science_path}")
                    science_master_dark = CCDData.read(master_dark_science_path)
                    print_memory_usage("After loading science master dark")
                else:
                    science_dark_images = [CCDData.read(f, unit='adu') for f in science_dark_files]
                    science_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in science_dark_images])
                    print(f'Science dark exposure times: {science_dark_exposure_times}')

                    if len(science_dark_exposure_times) > 1:
                        print("Warning: Multiple exposure times found in science dark images. Ensure they are consistent.")

                    science_master_dark = combine_darks(science_dark_images, science_dir, mem_limit=mem_limit)
                    science_master_dark.write(master_dark_science_path, overwrite=True)
                    print(f"Science master dark saved to {master_dark_science_path}")
                    print_memory_usage("After science master dark creation")
            elif skip_science_dark_correction:
                print("Skipping master dark creation for science images (no matching darks available)")

        # Generate master flat field from sky flats (only if not skipping flat correction)
        flat_master = None
        mask = None
        if not skip_flat_correction:
            if master_flat_path.exists() and mask_path.exists() and not args.force:
                print(f"\nLoading existing master flat from {master_flat_path}")
                flat_master = CCDData.read(master_flat_path)
                print(f"Loading existing mask from {mask_path}")
                mask = CCDData.read(mask_path)
                print_memory_usage("After loading master flat and mask")
            else:
                flat_master = generate_flat(flat_dir, mem_limit=mem_limit)
                flat_master.write(master_flat_path, overwrite=True)
                print(f"Master flat saved to {master_flat_path}")
                # Create a pixel mask to flag bad pixels
                mask = generate_mask(flat_dir)
                mask.write(mask_path, overwrite=True)
                print(f"Mask saved to {mask_path}")
                print_memory_usage("After master flat generation")
        else:
            print("Skipping master flat generation (no SKYFLAT directory)")

        # ========================================
        # Step 4: Calibrate science images
        # ========================================
        # Process science images ONE AT A TIME to minimize memory usage
        total_images = len(science_files)

        for idx, sci_file in enumerate(science_files, start=1):
            # Load one science image at a time
            sci = CCDData.read(sci_file, unit='adu')

            # Apply bias, dark, and flat field corrections
            # Note: science_master_dark will be None if dark correction is skipped
            # Note: science_master_bias will be None unless we're using bias as fallback
            calibrated_science_image = calibrate_science_image(sci, science_master_bias, science_master_dark, master_flat=flat_master, mask=mask)

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
            print(f'({idx}/{total_images}) Saved calibrated image to {output_filename}')

            # Print memory usage periodically (every 10 images)
            if idx % 10 == 0 or idx == total_images:
                print_memory_usage(f"After processing {idx}/{total_images} images")

    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
    print_memory_usage("Program end")

# Entry point
if __name__ == '__main__':
    main()
              
            