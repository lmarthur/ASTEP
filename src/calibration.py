from astropy.nddata import CCDData
from astropy.visualization import hist
import ccdproc as ccdp

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

def generate_mask(flat_images, path=None):
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