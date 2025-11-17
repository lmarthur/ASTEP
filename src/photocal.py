# This script contains code to perform photometric calibration on ASTEP telescope images. 

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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Perform photometric calibration on ASTEP telescope images.')
    parser.add_argument('data_path', help='Path to the data directory containing date subdirectories')
    parser.add_argument('--mem-limit', type=float, default=2.0, help='Memory limit in GB (default: 2.0)')
    parser.add_argument('--force', action='store_true', help='Force recalibration even if calibrated files already exist')
    args = parser.parse_args()

    start_time = time.time()
    data_path = args.data_path
    mem_limit = int(args.mem_limit * 1024**3)  # Convert GB to bytes

    # Auto-discover dates by searching for date directories
    data_path_obj = Path(data_path)
    if not data_path_obj.exists():
        print(f"ERROR: Data path does not exist: {data_path}")
        return

    # Find all directories that look like dates (YYYY-MM-DD format)
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
    for date in dates:
        print(f"\n{'='*60}")
        print(f"Processing date: {date}")
        print(f"{'='*60}")

        # Search for subdirectories corresponding to the date
        date_dir = data_path + '/' + date
        science_dir = date_dir + '/' + date + '-CAMS'
        flat_dir = date_dir + '/' + date + '-CAMS_SKYFLAT'
        cal_path = date_dir + '/' + date + '-CAMS_CAL'

        # Check if calibration already exists (unless --force is specified)
        cal_path_obj = Path(cal_path)
        if not args.force and cal_path_obj.exists():
            # Check if there are already calibrated files
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

        if not flat_dark_files:
            print(f"ERROR: No DARK files found in flat directory: {flat_dir}")
            print(f"Skipping date {date}")
            continue

        if not science_dark_files:
            print(f"ERROR: No DARK files found in science directory: {science_dir}")
            print(f"Skipping date {date}")
            continue

        if not science_files:
            print(f"ERROR: No SCIENCE files found in science directory: {science_dir}")
            print(f"Skipping date {date}")
            continue

        print(f"Found {len(flat_dark_files)} flat dark files")
        print(f"Found {len(science_dark_files)} science dark files")
        print(f"Found {len(science_files)} science files")

        Path(cal_path).mkdir(parents=True, exist_ok=True)

        # Calibrate the dark images
        flat_dark_images = [CCDData.read(f, unit='adu') for f in flat_dark_files]
        flat_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in flat_dark_images])
        print(f'Flat dark exposure times: {flat_dark_exposure_times}')
        science_dark_images = [CCDData.read(f, unit='adu') for f in science_dark_files]
        science_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in science_dark_images])
        print(f'Science dark exposure times: {science_dark_exposure_times}')

        # Runtime checks on exposure times
        if len(science_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in science dark images. Ensure they are consistent.")
        if len(flat_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in flat dark images. Ensure they are consistent.")

        science_master_dark = combine_darks(science_dark_images, science_dir, mem_limit=mem_limit)
        flat_master_dark = combine_darks(flat_dark_images, flat_dir, mem_limit=mem_limit)

        flat_master = generate_flat(flat_dir, mem_limit=mem_limit)

        # Create a pixel mask
        mask = generate_mask(flat_dir)

        # Calibrate the science images
        science_images = [CCDData.read(f, unit='adu') for f in science_files]
        for sci in science_images:
            calibrated_science_image = calibrate_science_image(sci, None, science_master_dark, master_flat=flat_master, mask=mask)
            # Convert to electrons
            gain = sci.header.get('GAIN', 2.0)  # Default to 2.0 if not found
            calibrated_science_image = calibrated_science_image.multiply(gain * u.electron / u.adu)
            # Remove cosmic rays from calibrated science images
            readnoise = sci.header.get('RDNOISE', 9.0)  # Default to 9.0 if not found
            calibrated_science_image = remove_cosmic_rays(calibrated_science_image, readnoise, sigclip=7.0, verbose=False)

            output_filename = cal_path + '/' + sci.header['ORIGFILE'].replace('.fits', '_CAL.fits')
            # Copy the header from the original image
            calibrated_science_image.header = sci.header
            calibrated_science_image.write(output_filename, overwrite=True)
            print(f'Saved calibrated image to {output_filename}')

    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")

# Entry point
if __name__ == '__main__':
    main()
              
            