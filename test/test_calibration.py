import pytest

# add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

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

