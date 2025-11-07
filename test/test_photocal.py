import pytest
import ccdproc as ccdp
import astropy.units as u
from astropy.nddata import CCDData
import numpy as np

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

def test_header_preservation():
    """Test that important headers are preserved through calibration"""
    from src.calibration import calibrate_science_image

    science = CCDData(np.ones((50, 50)) * 1000, unit='adu')
    science.header['EXPTIME'] = 90.0
    science.header['OBJECT'] = 'Test Object'
    science.header['RA'] = 123.456
    science.header['DEC'] = -45.678
    science.header['FILTER'] = 'V'

    master_dark = CCDData(np.ones((50, 50)) * 100, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    master_flat = CCDData(np.ones((50, 50)), unit='adu')

    calibrated = calibrate_science_image(science, None, master_dark, master_flat)

    # Important headers should be preserved
    assert 'EXPTIME' in calibrated.header

def test_calibration_workflow_consistency():
    """Test that calibration produces consistent results with same inputs"""
    from src.calibration import calibrate_science_image

    # Create reproducible test data
    np.random.seed(42)
    science = CCDData(np.random.randn(100, 100) * 10 + 1000, unit='adu')
    science.header['EXPTIME'] = 90.0

    master_dark = CCDData(np.ones((100, 100)) * 100, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    master_flat = CCDData(np.random.randn(100, 100) * 0.05 + 1.0, unit='adu')

    # Calibrate twice
    calibrated1 = calibrate_science_image(science, None, master_dark, master_flat)
    calibrated2 = calibrate_science_image(science, None, master_dark, master_flat)

    # Results should be identical
    assert np.allclose(calibrated1.data, calibrated2.data)

def test_full_pipeline_units():
    """Test that units are handled correctly through entire pipeline"""
    from src.calibration import combine_darks, calibrate_science_image
    import tempfile

    # Create dark frames
    dark_images = [CCDData(np.ones((50, 50)) * 100, unit='adu') for _ in range(3)]
    for img in dark_images:
        img.header['EXPTIME'] = 90.0

    with tempfile.TemporaryDirectory() as tmpdir:
        # Combine darks
        master_dark = combine_darks(dark_images, tmpdir)

        # Verify unit is preserved
        assert master_dark.unit == u.adu

        # Calibrate science image
        science = CCDData(np.ones((50, 50)) * 1000, unit='adu')
        science.header['EXPTIME'] = 90.0

        master_flat = CCDData(np.ones((50, 50)), unit='adu')

        calibrated = calibrate_science_image(science, None, master_dark, master_flat)

        # Unit should still be adu after calibration
        assert calibrated.unit == u.adu

def test_gain_conversion_accuracy():
    """Test that gain conversion produces correct electron counts"""
    import astropy.units as u

    # Create a science image in ADU
    science_adu = CCDData(np.ones((100, 100)) * 1000, unit='adu')
    gain = 2.5  # electrons per ADU

    # Convert to electrons
    science_electrons = science_adu.multiply(gain * u.electron / u.adu)

    # Check conversion
    assert science_electrons.unit == u.electron
    assert np.isclose(science_electrons.data.mean(), 2500)  # 1000 ADU * 2.5 gain

def test_mask_application_order():
    """Test that mask is applied after calibration, not before"""
    from src.calibration import calibrate_science_image

    science = CCDData(np.ones((50, 50)) * 1000, unit='adu')
    science.header['EXPTIME'] = 90.0

    master_dark = CCDData(np.ones((50, 50)) * 100, unit='adu')
    master_dark.header['EXPTIME'] = 90.0

    master_flat = CCDData(np.ones((50, 50)), unit='adu')

    # Create mask
    mask_data = np.zeros((50, 50), dtype='uint8')
    mask_data[25, 25] = 1
    mask = CCDData(mask_data, unit=u.dimensionless_unscaled)

    # Calibrate with mask
    calibrated = calibrate_science_image(science, None, master_dark, master_flat, mask=mask)

    # Verify calibration was applied before masking
    # Unmasked pixels should be (1000-100)/1 = 900
    assert np.isclose(calibrated.data[0, 0], 900, rtol=0.01)
    # Masked pixel should have mask flag set
    assert calibrated.mask[25, 25] == True
