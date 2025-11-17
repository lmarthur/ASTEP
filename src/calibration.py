from astropy.nddata import CCDData
from astropy import units as u
from astropy.stats import mad_std
import ccdproc as ccdp
import os
import sys
import numpy as np
from pathlib import Path

# TODO: Add ability to suppress stdout when running test suite

def inv_median(data):
    """Function to compute the inverse of the median of the data."""
    return 1.0 / np.median(data)

def image_combine(images, method='average', sigma_clip=True, sigma=3.0, mem_limit=2*1024**3):
    """
    Combine a list of CCDData images using the specified method. Thin wrapper around ccdproc.combine.
    
    INPUTS:
    ------------------
    images: [CCDData]
        A list of CCDData images to be combined.
    method: str
        The method to use for combining images. Options include 'average', 'median', etc.
    sigma_clip: bool
        Whether to apply sigma clipping during the combination.
    sigma: float
        The sigma value to use for sigma clipping if enabled.
    mem_limit: int
        The memory limit in bytes for the combination process.

    OUTPUTS:
    ------------------
    combined_image: CCDData
        The resulting combined image as a CCDData object.

    """
    
    combined_image = ccdp.combine(images, method=method, sigma_clip=sigma_clip, sigma_clip_high_thresh=sigma, sigma_clip_low_thresh=sigma, mem_limit=mem_limit)
    return combined_image

def generate_flat(flat_dir, mem_limit=2*1024**3):
    """
    Generate a master flat field image from a directory of flat images.

    INPUTS:
    ------------------
    flat_dir: str
        The directory path where the flat images are located.
    mem_limit: int
        The memory limit in bytes for the combination process.

    OUTPUTS:
    ------------------
    master_flat: CCDData
        The resulting master flat field image as a CCDData object.
    
    """

    # Load in the master dark
    date = os.path.basename(flat_dir).split('-')[0:3]
    date = '-'.join(date)

    # Check to see if the master dark exists
    master_dark_path = flat_dir + '/' + date + '_MASTERDARK.fits'
    if not os.path.exists(master_dark_path):
        print(f"Master dark not found at {master_dark_path}")
        sys.exit(1)

    master_dark = CCDData.read(master_dark_path, unit='adu')

    flat_images = [CCDData.read(f, unit='adu') for f in Path(flat_dir).glob('*_SKYFLAT*.fits')]

    calibrated_flats = []
    for flat in flat_images:
        # Subtract master dark
        flat_cal = ccdp.subtract_dark(flat, master_dark, exposure_time='EXPTIME', exposure_unit=u.second)
        calibrated_flats.append(flat_cal)

    # Combine the calibrated flat images
    print(f'Combining flat images for {flat_dir}...')

    master_flat = ccdp.combine(calibrated_flats, method='median', scale=inv_median, sigma_clip=True, sigma_clip_low_thresh=3, sigma_clip_high_thresh=3, sigma_clip_func=np.nanmedian, sigma_clip_dev_func=mad_std, mem_limit=mem_limit)

    master_flat.header['ACQTYPE'] = 'MASTERFLAT'
    # Save the master flat as a fits file
    output_path = (flat_dir + '/' + f'{date}_MASTERFLAT.fits')
    master_flat.write(output_path, overwrite=True)

    return master_flat
    

def generate_mask(flat_directory):
    """
    Generate a pixel mask based on the set of flat images, using the ccdproc.mask_bad_pixels function.

    INPUTS:
    ------------------
    flat_directory: str
        The directory path where the flat images are located.

    OUTPUTS:
    ------------------
    mask: CCDData
        A mask where bad pixels are marked as 1 and good pixels as 0.
    
    """
    
    # If there are flat images with suitably different pixel values (different exposure times or different sky brightnesses), and the exposure times are long enough that read noise is not dominant, use a ratio of the images to generate a mask. 

    # If the flat images are all very similar, use one calibrated (but not combined) flat to generate a mask

    # Note that this is a temporary implementation, and should be replaced with a more robust and cleanly written solution

    # flat_images = [CCDData.read(f, unit='adu') for f in Path(flat_directory).glob('*_SKYFLAT*.fits')]
    date = os.path.basename(flat_directory).split('-')[0:3]
    date = '-'.join(date)

    # # Get the image with the highest mean value
    # brightest_flat = max(flat_images, key=lambda x: x.data.mean())
    # print("\nBrightest flat image:", brightest_flat.header['ORIGFILE'], "with mean", brightest_flat.data.mean())
# 
    # # Get the darkest flat image
    # darkest_flat = min(flat_images, key=lambda x: x.data.mean())
    # print("Darkest flat image:", darkest_flat.header['ORIGFILE'], "with mean", darkest_flat.data.mean())
# 
    # # Divide the darkest flat by the brightest flat
    # ratio = darkest_flat.data / brightest_flat.data
    # print("\nRatio image mean:", ratio.mean(), "stddev:", ratio.std())
# 
    # # If the mean of the ratio is less than 0.9, use the ccdp.ccdmask() function to generate a mask from the ratio
    # if ratio.mean() < 0.9:
    #     print("\nGenerating pixel mask from the flat ratio...")
    #     mask = ccdp.ccdmask(ratio)
    # # Otherwise, use the brightest flat image to generate a mask
    # else:
    #     print("\nGenerating pixel mask from the brightest flat...\n")
    #     mask = ccdp.ccdmask(brightest_flat.data)

    # Check to see if the master flat exists
    master_flat_path = flat_directory + '/' + date + '_MASTERFLAT.fits'
    if not os.path.exists(master_flat_path):
        print(f"Master flat not found at {master_flat_path}")
        sys.exit(1)

    print("\nGenerating pixel mask from the combined master flat...\n")
    
    master_flat = CCDData.read(flat_directory + '/' + date + '_MASTERFLAT.fits', unit='adu')
    mask = ccdp.ccdmask(master_flat.data)
    mask_as_ccd = CCDData(data=mask.astype('uint8'), unit=u.dimensionless_unscaled)
    mask_as_ccd.header['ACQTYPE'] = 'MASK'

    # Save the mask as a fits file

    print(f"Saving mask to {flat_directory}/{date}_MASK.fits\n")
    output_path = (flat_directory + '/' + f'{date}_MASK.fits')
    mask_as_ccd.write(output_path, overwrite=True)

    return mask_as_ccd

def remove_cosmic_rays(image, readnoise, sigclip, verbose=True):
    """
    Remove cosmic rays from a CCDData image using the ccdproc.cosmicray_lacosmic function.

    INPUTS:
    ------------------
    images: CCDData
        The CCDData image from which cosmic rays will be removed.

    readnoise: float
        The read noise of the CCD in electrons.

    sigclip: float
        The sigma clipping threshold for identifying cosmic rays.

    verbose: bool
        Whether to print verbose output during the cosmic ray removal process.

    OUTPUTS:
    ------------------
    cleaned_image: CCDData
        The CCDData image with cosmic rays removed.
    
    """

    # Check for BUNIT, bunit, unit in the header
    cleaned_images = []

    if image.header.get('BUNIT') is None and image.header.get('bunit') is None and image.unit is None:
        raise ValueError("Input image must have a unit.")

    cleaned_image = ccdp.cosmicray_lacosmic(image, readnoise=readnoise, sigclip=sigclip, verbose=verbose)

    return cleaned_image

def combine_bias(bias_images, path, mem_limit=2*1024**3):
    """
    Combine a list of bias images into a master bias frame.

    INPUTS:
    ------------------
    bias_images: [CCDData]
        A list of CCDData bias images to be combined.
    path: str
        The directory path where the bias images are located and where the master bias will be saved.

    OUTPUTS:
    ------------------
    master_bias: CCDData
        The resulting master bias frame as a CCDData object.
    
    """
    # Note that this assumes that there are no overscan regions in the bias images. If there are, they should be trimmed before combining.
    date = os.path.basename(path).split('-')[0:3]
    date = '-'.join(date)

    output_path = (path + '/' + f'{date}_MASTERBIAS.fits')

    master_bias = image_combine(bias_images, method='average', sigma_clip=True, sigma=3.0, mem_limit=mem_limit)
    master_bias.header['ACQTYPE'] = 'MASTERBIAS'
    # print the EXPTIME header keyword

    print(f'Master bias EXPTIME: {master_bias.header["EXPTIME"]} seconds')
    
    # Save the master bias as a fits file
    master_bias.write(output_path, overwrite=True)

    return master_bias

def combine_darks(dark_images, path, mem_limit=2*1024**3):
    """
    Combine a list of dark images into a master dark frame. Note that this function assumes that all input dark images have the same exposure time. Also note that this function does not currently scale the dark images or subtract the bias. If this is desired, it should be done prior to calling this function.

    INPUTS:
    ------------------
    dark_images: [CCDData]
        A list of CCDData dark images to be combined.
    path: str
        The directory path where the dark images are located and where the master dark will be saved.
    mem_limit: int
        The memory limit in bytes for the combination process.

    OUTPUTS:
    ------------------
    master_dark: CCDData
        The resulting master dark frame as a CCDData object.
    
    """

    # Strip the date out of the path, e.g. path = '/Users/lmarthur/Documents/Research/ASTEP/data/2012-06-04-CAMS' -> date = '2012-06-04'
    date = os.path.basename(path).split('-')[0:3]
    date = '-'.join(date)

    output_path = (path + '/' + f'{date}_MASTERDARK.fits')
    # Get the list of unique exposure times in the dark images
    exptimes = [dark.header['EXPTIME'] for dark in dark_images]
    exptimes = np.unique(exptimes)
    # if there are multiple exposure times, raise an error
    if len(exptimes) > 1:
        raise ValueError("Input dark images must all have the same exposure time.")
    
    print(f'Combining dark images with exposure time {exptimes} seconds into {output_path}...')

    master_dark = image_combine(dark_images, method='average', sigma_clip=True, sigma=3.0, mem_limit=mem_limit)

    master_dark.header['ACQTYPE'] = 'MASTERDARK'

    master_dark.write(output_path, overwrite=True)

    return master_dark

def calibrate_science_image(science_image, master_bias, master_dark, master_flat, mask=None):
    """
    Calibrate a list of science images by subtracting the master bias and master dark, and dividing by the master flat.

    INPUTS:
    ------------------
    science_images: CCDData
        A CCDData science image to be calibrated.
    master_bias: CCDData
        The master bias frame.
    master_dark: CCDData
        The master dark frame.
    master_flat: CCDData
        The master flat frame.
    mask: CCDData or None
        An optional pixel mask to apply during calibration.

    OUTPUTS:
    ------------------
    calibrated_images: [CCDData]
        A calibrated CCDData science image.
    
    """
    sci_cal = science_image

    # Subtract the master bias (if provided)
    if master_bias is not None:
        sci_cal = ccdp.subtract_bias(sci_cal, master_bias)

    # Subtract the master dark (if provided)
    if master_dark is not None:
        sci_cal = ccdp.subtract_dark(sci_cal, master_dark, exposure_time='EXPTIME', exposure_unit=u.second)

    # Divide by the master flat (if provided)
    if master_flat is not None:
        sci_cal = ccdp.flat_correct(sci_cal, master_flat)

    # Apply the mask if provided
    if mask is not None:
        sci_cal.mask = mask.data.astype(bool)

    return sci_cal