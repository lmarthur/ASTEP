import pytest
import ccdproc as ccdp
import astropy.units as u
from astropy.nddata import CCDData

# add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Suppress Astropy warnings for cleaner output
import warnings
from astropy.utils.exceptions import AstropyWarning
warnings.simplefilter('ignore', category=AstropyWarning)

# suppress all logging messages during tests
import logging
logging.disable(logging.CRITICAL)

def test_image_combine():
    # Mock CCDData images for testing
    from astropy.nddata import CCDData
    import numpy as np
    from src.calibration import image_combine

    # Create mock CCDData images
    images = [CCDData(np.random.rand(100, 100), unit='adu') for _ in range(5)]

    # Test combining images with average method
    combined_image = image_combine(images, method='average', sigma_clip=True, sigma=3.0)
    
    # Check if the output is a CCDData object
    assert isinstance(combined_image, CCDData)
    
    # Check if the shape of the combined image is correct
    assert combined_image.shape == (100, 100)

    # Check if the unit is preserved
    assert combined_image.unit == 'adu'

    # Test combining images with median method
    combined_image_median = image_combine(images, method='median', sigma_clip=True, sigma=3.0)

    # Check if the output is a CCDData object
    assert isinstance(combined_image_median, CCDData)

    # Check if the shape of the combined image is correct
    assert combined_image_median.shape == (100, 100)

    # Check if the unit is preserved
    assert combined_image_median.unit == 'adu'

def test_generate_mask():
    from src.calibration import generate_mask

    # Generate a pixel mask from example flat field images
    pixel_mask = generate_mask('data/2012-06-04-CAMS_SKYFLAT')

    # Check if the output is a CCDData object
    assert isinstance(pixel_mask, CCDData)

    # TODO: Add more thorough checks to the pixel mask

def test_remove_cosmic_rays():
    # Note that to effectively test this function, the images must first be calibrated and masks must be applied. 
    from src.calibration import remove_cosmic_rays

    # Load an example image
    science_image = CCDData.read('data/2012-06-04-CAMS/2012-06-04_17.23.54_SCIENCE.fits', unit=u.adu)

    # Remove cosmic rays from the science image
    cleaned_image = remove_cosmic_rays(science_image, readnoise=10.0, sigclip=5.0)

    # Check if the output is a CCDData object
    assert isinstance(cleaned_image, CCDData)

    # TODO: Add more thorough checks to the cosmic ray removal
