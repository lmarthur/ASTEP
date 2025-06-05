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

