import matplotlib.pyplot as plt

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


