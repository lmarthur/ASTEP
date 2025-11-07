import pytest

# add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

def test_image_out():
    # Mock CCDData object for testing
    from astropy.nddata import CCDData
    import numpy as np
    from src.utils import image_out

    # Create a mock CCDData image
    image = CCDData(np.random.rand(100, 100), unit='adu')

    # Define a test path (this won't actually save the file in this test)
    test_path = './test/test_data/test_image_output.jpg'

    # Call the image_out function
    image_out(image, test_path)

    # Search for the file to ensure it was created
    from pathlib import Path
    assert Path(test_path).exists(), f"Image file was not created at {test_path}"

def test_convert_to_electrons():
    """Test ADU to electron conversion"""
    from src.utils import convert_to_electrons
    from astropy.nddata import CCDData
    import astropy.units as u
    import ccdproc as ccdp
    import tempfile
    import numpy as np

    # Create temporary FITS files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test images in ADU
        for i in range(3):
            img = CCDData(np.ones((10, 10)) * 100, unit='adu')
            img.write(f'{tmpdir}/test_{i}.fits', overwrite=True)

        # Create ImageFileCollection
        ic = ccdp.ImageFileCollection(tmpdir)

        # Convert with gain=2.0
        converted = convert_to_electrons(ic, gain=2.0)

        assert len(converted) == 3
        for img in converted:
            assert img.unit == u.electron
            assert np.isclose(img.data.mean(), 200)  # 100 ADU * 2.0 gain

def test_convert_to_electrons_invalid_gain():
    """Test conversion with invalid gain values"""
    from src.utils import convert_to_electrons
    from astropy.nddata import CCDData
    import ccdproc as ccdp
    import tempfile
    import numpy as np

    with tempfile.TemporaryDirectory() as tmpdir:
        img = CCDData(np.ones((10, 10)), unit='adu')
        img.write(f'{tmpdir}/test.fits', overwrite=True)
        ic = ccdp.ImageFileCollection(tmpdir)

        # Test negative gain
        with pytest.raises(ValueError, match="positive"):
            convert_to_electrons(ic, gain=-1.0)

        # Test zero gain
        with pytest.raises(ValueError, match="positive"):
            convert_to_electrons(ic, gain=0.0)

def test_histogram_creation():
    """Test histogram file creation"""
    from src.utils import histogram
    from astropy.nddata import CCDData
    import tempfile
    import os
    import numpy as np

    image = CCDData(np.random.randn(100, 100) * 100 + 500, unit='adu')

    with tempfile.TemporaryDirectory() as tmpdir:
        path = f'{tmpdir}/test_histogram.png'
        histogram(image, path)

        assert os.path.exists(path)

def test_histogram_invalid_path():
    """Test histogram with invalid path type"""
    from src.utils import histogram
    from astropy.nddata import CCDData
    import numpy as np

    image = CCDData(np.ones((10, 10)), unit='adu')

    with pytest.raises(ValueError, match="string"):
        histogram(image, 123)  # Not a string

def test_image_out_invalid_path():
    """Test image_out with invalid path type"""
    from src.utils import image_out
    from astropy.nddata import CCDData
    import numpy as np

    image = CCDData(np.ones((10, 10)), unit='adu')

    with pytest.raises(ValueError, match="string"):
        image_out(image, ['not', 'a', 'string'])

