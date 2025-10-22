# This script contains code to perform photometric calibration on ASTEP telescope images. 

import ccdproc as ccdp
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

# Want to pass in a date argument to specify which night's data to process

def main():
    start_time = time.time()
    dates = ['2012-06-04']  # List of dates to process
    path = '/Users/lmarthur/Documents/Research/ASTEP/data'

    for date in dates:
        # Search for subdirectories corresponding to the date
        science_dir = path + '/' + date + '-CAMS' 
        flat_dir = path + '/' + date + '-CAMS_SKYFLAT'
        cal_path = path + '/' + date + '-CAMS_CALIBRATED'
        Path(cal_path).mkdir(parents=True, exist_ok=True)

        # Calibrate the dark images
        flat_dark_images = [CCDData.read(f, unit='adu') for f in Path(flat_dir).glob('*_DARK*.fits')]
        flat_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in flat_dark_images])
        print(f'Flat dark exposure times: {flat_dark_exposure_times}')
        science_dark_images = [CCDData.read(f, unit='adu') for f in Path(science_dir).glob('*_DARK*.fits')]
        science_dark_exposure_times = np.unique([dark.header['EXPTIME'] for dark in science_dark_images])
        print(f'Science dark exposure times: {science_dark_exposure_times}')

        # Runtime checks on exposure times
        if len(science_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in science dark images. Ensure they are consistent.")
        if len(flat_dark_exposure_times) > 1:
            print("Warning: Multiple exposure times found in flat dark images. Ensure they are consistent.")

        science_master_dark = combine_darks(science_dark_images, science_dir, mem_limit=2*1024**3)
        flat_master_dark = combine_darks(flat_dark_images, flat_dir, mem_limit=2*1024**3)

        flat_master = generate_flat(flat_dir, mem_limit=2*1024**3)

        # Create a pixel mask
        mask = generate_mask(flat_dir)

        # Calibrate the science images
        science_images = [CCDData.read(f, unit='adu') for f in Path(science_dir).glob('*_SCIENCE*.fits')]
        for sci in science_images:
            calibrated_science_image = calibrate_science_image(sci, None, science_master_dark, master_flat=flat_master, mask=mask)
            # Convert to electrons
            gain = sci.header.get('GAIN', 2.0)  # Default to 2.0 if not found
            calibrated_science_image = calibrated_science_image.multiply(gain * u.electron / u.adu)
            # Remove cosmic rays from calibrated science images
            readnoise = sci.header.get('RDNOISE', 9.0)  # Default to 9.0 if not found
            calibrated_science_image = remove_cosmic_rays(calibrated_science_image, readnoise, sigclip=7.0, verbose=False)

            output_filename = cal_path + '/' + sci.header['ORIGFILE'].replace('.fits', '_CALIBRATED.fits')
            calibrated_science_image.write(output_filename, overwrite=True)
            print(f'Saved calibrated image to {output_filename}')

    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")

# Entry point
if __name__ == '__main__':
    main()
              
            