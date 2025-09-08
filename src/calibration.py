from astropy.nddata import CCDData
from astropy.visualization import hist
from astropy import units as u
import ccdproc as ccdp

# TODO: Add ability to suppress stdout when running test suite

def image_combine(images, method='average', sigma_clip=True, sigma=3.0):
    """
    Combine a list of CCDData images using the specified method. Thin wrapper around ccdproc.combine.
    
    INPUTS:
    ------------------
    images: ccdproc.ImageFileCollection
        A collection of CCDData images to be combined.
    method: str
        The method to use for combining images. Options include 'average', 'median', etc.
    sigma_clip: bool
        Whether to apply sigma clipping during the combination.
    sigma: float
        The sigma value to use for sigma clipping if enabled.
    
    OUTPUTS:
    ------------------
    combined_image: CCDData
        The resulting combined image as a CCDData object.

    """
    mem_limit = 2 * 1024**3  # 2 GB memory limit
    combined_image = ccdp.combine(images, method=method, sigma_clip=sigma_clip, sigma_clip_high_thresh=sigma, sigma_clip_low_thresh=sigma, mem_limit=mem_limit)
    return combined_image

def generate_mask(flat_images,  path=None):
    """
    Generate a pixel mask based on the set of flat images, using the ccdproc.mask_bad_pixels function.

    INPUTS:
    ------------------
    flat_images: ccdproc.ImageFileCollection
        A list of calibrated, uncombined flat field images to analyze for pixel masking.

    path: str, optional
        The file path where the mask will be saved. If None, the mask will not be saved.

    OUTPUTS:
    ------------------
    mask: CCDData
        A mask where bad pixels are marked as 1 and good pixels as 0.
    
    """
    
    # If there are flat images with suitably different pixel values (different exposure times or different sky brightnesses), and the exposure times are long enough that read noise is not dominant, use a ratio of the images to generate a mask. 

    # If the flat images are all very similar, use one calibrated (but not combined) flat to generate a mask

    # Note that this is a temporary implementation, and should be replaced with a more robust and cleanly written solution

    # Get the image with the highest mean value
    brightest_flat = max(flat_images.hdus(ACQTYPE='SKYFLAT'), key=lambda x: x.data.mean())
    print("\nBrightest flat image:", brightest_flat.header['ORIGFILE'], "with mean", brightest_flat.data.mean())

    # Get the darkest flat image
    darkest_flat = min(flat_images.hdus(ACQTYPE='SKYFLAT'), key=lambda x: x.data.mean())
    print("Darkest flat image:", darkest_flat.header['ORIGFILE'], "with mean", darkest_flat.data.mean())

    # Divide the darkest flat by the brightest flat
    ratio = darkest_flat.data / brightest_flat.data
    print("\nRatio image mean:", ratio.mean(), "stddev:", ratio.std())

    # If the mean of the ratio is less than 0.9, use the ccdp.ccdmask() function to generate a mask from the ratio
    if ratio.mean() < 0.9:
        print("\nGenerating pixel mask from the flat ratio...")
        mask = ccdp.ccdmask(ratio)
    # Otherwise, use the brightest flat image to generate a mask
    else:
        print("\nGenerating pixel mask from the brightest flat...\n")
        mask = ccdp.ccdmask(brightest_flat.data)

    mask_as_ccd = CCDData(data=mask.astype('uint8'), unit=u.dimensionless_unscaled)
    mask_as_ccd.header['ACQTYPE'] = 'MASK'

    # Save the mask as a fits file
    if path is not None:
        print(f"Saving mask to {path}/mask.fits")
        mask_as_ccd.write(path + 'MASK.fits', overwrite=True)

    return mask_as_ccd

def remove_cosmic_rays(image, readnoise, sigclip, verbose=True):
    """
    Remove cosmic rays from a CCDData image using the ccdproc.cosmicray_lacosmic function.

    INPUTS:
    ------------------
    image: CCDData
        The CCDData image from which cosmic rays will be removed.

    readnoise: float
        The read noise of the CCD.

    sigclip: float
        The sigma clipping threshold for identifying cosmic rays.

    verbose: bool
        Whether to print verbose output during the cosmic ray removal process.

    OUTPUTS:
    ------------------
    cleaned_image: CCDData
        The CCDData image with cosmic rays removed.
    
    """

    # TODO: Add verification step to ensure the appropriate units

    # Check for BUNIT, bunit, unit in the header
    if image.header.get('BUNIT') is None and image.header.get('bunit') is None and image.unit is None:
        raise ValueError("Input image must have a unit.")

    cleaned_image = ccdp.cosmicray_lacosmic(image, readnoise=readnoise, sigclip=sigclip, verbose=verbose)
    return cleaned_image

