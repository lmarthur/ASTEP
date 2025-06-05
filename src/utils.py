import matplotlib.pyplot as plt
from astropy.nddata import CCDData
from astropy.visualization import hist

def image_out(image, path):
    """
    Output a CCDData object to an image file.

    INPUTS:
    ------------------
    image: CCDData
        The CCDData image to be saved.
    
    path: str
        The file path where the image will be saved.
    """

    # Ensure the path is a string
    if not isinstance(path, str):
        raise ValueError("The path must be a string.")

    # Plot the image using matplotlib
    plt.imshow(image.data, cmap='gray', origin='lower')
    plt.colorbar(label='Counts (ADU)')

    # Save the figure to the specified path
    plt.savefig(path)
    plt.close()  # Close the plot to free up memory

def histogram(image, path):
    """
    Create and save a histogram of the image data.

    INPUTS:
    ------------------
    image: CCDData
        The CCDData image for which the histogram will be created.

    path: str
        The file path where the histogram will be saved.
    """
    # Ensure the path is a string
    if not isinstance(path, str):
        raise ValueError("The path must be a string.")

    # Create a histogram of the image data
    plt.figure(figsize=(10, 6))
    hist(image.data.flatten(), bins=800, histtype='step', color='black')
    plt.xlabel('Pixel Value (ADU)')
    plt.ylabel('Frequency')
    plt.yscale('log')  # Use logarithmic scale for better visibility of low counts
    # Save the histogram to the specified path
    plt.savefig(path)
    plt.close()  # Close the plot



