# ASTEP Small-body Harvest
This repository contains code to calibrate and analyze data from the Antarctic Search for Transiting Exoplanets (ASTEP).

# Calibration
The CCD calibration process follows these steps:

    1. Calibrate the bias images
        a. If you choose to, subtract the overscan from the bias images
        b. Trim the overscan regions, if present
    2. Combine the calibrated bias images
    3. Calibrate the dark images
        a. If you are subtracting overscan, do this for the dark images
        b. Trim the overscan regions, if present
        c. If necessary, scale the dark images to match the exposure times (requires subtracting the bias)
    4. Combine the calibrated dark images
    5. Create a pixel mask
    6. Calibrate the flat images
        a. If you are subtracting overscan, do this for the flat images
        b. Trim the overscan regions, if present
        c. Subtract bias (if dark exposure times haven't been rescaled, this step may be combined with subtracting dark current)
        d. Subtract dark current, scaling if necessary
    7. Combine the flat images
        a. Normalize the flat images to a common value (if there are multiple filters, this is done separately for each filter)
        b. Combine the normalized flat images (also done separately for each filter)
    8. Calibrate the science images
        a. If you are subtracting overscan, do this for the science images
        b. Trim the overscan regions, if present
        c. Subtract the bias, if the bias is not contained in the dark current
        d. Subtract the dark current
        e. Divide by the combined flat for the corresponding filter
        f. Apply pixel mask
        g. Remove cosmic rays
    

# TODO: 
    - [X] Determine whether there is an overscan region
    - [X] Create conda env
    - [X] Write tests for image combination
    - [X] Implement image combination function
    - [X] Implement image_out() function
    - [ ] Determine whether dark images need rescaling
    - [ ] Write tests for dark image rescaling
    - [ ] Implement dark image rescaling function
    - [ ] Implement image histogram plotting function
    - [ ] Write tests for cosmic ray removal?
    - [ ] Implement cosmic ray removal function
    - [ ] Write integration tests
    - [ ] Calibrate first batch of science images
    - [ ] Find potential object detection algorithms
    - [ ] Write synthetic tracking package?