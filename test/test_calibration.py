import pytest
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

def test_combine_bias():
    """Test bias frame combination"""
    from src.calibration import combine_bias
    import tempfile
    import os
    import numpy as np

    # Create mock bias images with consistent values
    bias_images = [CCDData(np.ones((100, 100)) * 100 + np.random.randn(100, 100),
                          unit='adu') for _ in range(5)]
    for img in bias_images:
        img.header['EXPTIME'] = 0.0

    with tempfile.TemporaryDirectory() as tmpdir:
        master_bias = combine_bias(bias_images, tmpdir)

        # Verify output
        assert isinstance(master_bias, CCDData)
        assert master_bias.header['ACQTYPE'] == 'MASTERBIAS'
        assert np.isclose(master_bias.data.mean(), 100, atol=5)

        # Verify file was saved
        date = os.path.basename(tmpdir)
        assert os.path.exists(f'{tmpdir}/{date}_MASTERBIAS.fits')

def test_combine_darks():
    """Test dark frame combination with exposure time validation"""
    from src.calibration import combine_darks
    import tempfile
    import numpy as np

    # Test successful combination with matching exposure times
    dark_images = [CCDData(np.ones((100, 100)) * 50, unit='adu') for _ in range(3)]
    for img in dark_images:
        img.header['EXPTIME'] = 90.0

    with tempfile.TemporaryDirectory() as tmpdir:
        master_dark = combine_darks(dark_images, tmpdir)

        assert isinstance(master_dark, CCDData)
        assert master_dark.header['ACQTYPE'] == 'MASTERDARK'
        assert np.isclose(master_dark.data.mean(), 50, atol=2)

def test_combine_darks_mismatched_exposure():
    """Test that combine_darks raises error for mismatched exposure times"""
    from src.calibration import combine_darks
    import tempfile
    import numpy as np

    dark_images = [CCDData(np.ones((100, 100)), unit='adu') for _ in range(3)]
    dark_images[0].header['EXPTIME'] = 10.0
    dark_images[1].header['EXPTIME'] = 90.0  # Different!
    dark_images[2].header['EXPTIME'] = 10.0

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="same exposure time"):
            combine_darks(dark_images, tmpdir)

def test_calibrate_science_image():
    """Test full science image calibration pipeline"""
    from src.calibration import calibrate_science_image
    import numpy as np

    # Create synthetic calibration frames
    science = CCDData(np.ones((100, 100)) * 1000, unit='adu')
    science.header['EXPTIME'] = 90.0

    master_bias = CCDData(np.ones((100, 100)) * 100, unit='adu')
    master_bias.header['EXPTIME'] = 0.0

    master_dark = CCDData(np.ones((100, 100)) * 150, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    master_flat = CCDData(np.ones((100, 100)) * 0.8, unit='adu')

    # Calibrate
    calibrated = calibrate_science_image(science, master_bias, master_dark, master_flat)

    # Verify calibration applied correctly
    # assert isinstance(calibrated[0], CCDData)

    assert np.isclose(calibrated.data.mean(), 850, rtol=0.01)

def test_calibrate_science_image_with_mask():
    """Test science calibration with pixel mask"""
    from src.calibration import calibrate_science_image
    import numpy as np

    science = CCDData(np.ones((100, 100)) * 1000, unit='adu')
    science.header['EXPTIME'] = 90.0

    master_dark = CCDData(np.ones((100, 100)) * 100, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    master_flat = CCDData(np.ones((100, 100)), unit='adu')

    # Create mask with some bad pixels
    mask_data = np.zeros((100, 100), dtype='uint8')
    mask_data[10:20, 10:20] = 1  # Mark region as bad
    mask = CCDData(mask_data, unit=u.dimensionless_unscaled)

    calibrated = calibrate_science_image(science, None, master_dark, master_flat, mask=mask)

    # Verify mask was applied
    assert calibrated.mask is not None
    assert np.sum(calibrated.mask) == 100  # 10x10 region masked

def test_calibrate_science_image_no_flat():
    """Test calibration when no flat is available"""
    from src.calibration import calibrate_science_image
    import numpy as np

    science = CCDData(np.ones((100, 100)) * 1000, unit='adu')
    science.header['EXPTIME'] = 90.0

    master_dark = CCDData(np.ones((100, 100)) * 100, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    calibrated = calibrate_science_image(science, None, master_dark, master_flat=None)

    assert isinstance(calibrated, CCDData)
    assert np.isclose(calibrated.data.mean(), 900, rtol=0.01)

def test_inv_median():
    """Test inverse median calculation"""
    from src.calibration import inv_median
    import numpy as np

    data = np.array([1, 2, 3, 4, 5])
    result = inv_median(data)

    assert np.isclose(result, 1.0/3.0)

    # Test with different data
    data2 = np.ones((100, 100)) * 50
    result2 = inv_median(data2)
    assert np.isclose(result2, 1.0/50.0)

def test_image_combine_sigma_clipping():
    """Test that sigma clipping removes outliers"""
    from src.calibration import image_combine
    import numpy as np

    # Create images with one outlier
    images = [CCDData(np.ones((100, 100)) * 100, unit='adu') for _ in range(5)]

    # Add cosmic ray to one image
    images[2].data[50, 50] = 10000

    # Combine with sigma clipping
    combined = image_combine(images, method='average', sigma_clip=True, sigma=1.0)

    # The outlier should be clipped, result should be close to 100
    combined.data[50, 50]
    assert np.isclose(combined.data[50, 50], 100, atol=10)

def test_image_combine_empty_list():
    """Test combining with empty image list"""
    from src.calibration import image_combine

    with pytest.raises(Exception):  # May be IndexError or ValueError
        image_combine([], method='average')

def test_image_combine_single_image():
    """Test combining single image"""
    from src.calibration import image_combine
    import numpy as np

    images = [CCDData(np.ones((10, 10)) * 50, unit='adu')]
    combined = image_combine(images, method='average')

    assert np.allclose(combined.data, 50)

def test_generate_mask_missing_masterflat():
    """Test mask generation when master flat doesn't exist"""
    from src.calibration import generate_mask
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(SystemExit):
            generate_mask(tmpdir)

def test_cosmic_ray_removal_performance():
    """Test cosmic ray detection on synthetic data"""
    from src.calibration import remove_cosmic_rays
    import numpy as np

    # Create image with known cosmic ray
    image = CCDData(np.ones((200, 200)) * 100, unit=u.electron)
    image.data[100, 100] = 5000  # Cosmic ray spike

    cleaned = remove_cosmic_rays(image, readnoise=10.0, sigclip=5.0, verbose=False)

    # Cosmic ray should be reduced
    assert cleaned.data[100, 100] < image.data[100, 100]
