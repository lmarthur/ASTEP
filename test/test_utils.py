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


    