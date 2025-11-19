# ASTEP Small-body Harvest
This repository contains code to calibrate and analyze data from the Antarctic Search for Transiting Exoplanets (ASTEP).

## Quick Start

To run the automated calibration pipeline:
```bash
mamba activate astep
./scripts/cal.sh /path/to/data
```

For detailed usage instructions, see the [Calibration Guide](docs/calibration_guide.md).

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
    5. Create a pixel mask?
        a. Note that the flat images appear to all be of the same exposure time
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

# Notes
    - None of the images appear to have overscan regions
    - There are dark images that match the exposure times for the flats (10s) and for the science images (90s), so no rescaling of the darks seems to be necessary
    - Should verify the units of the fits files to ensure that they are being handled correctly
    - Currently only have a mask for bad pixels, not for hot pixels. Hot pixel problems should be mitigated by sigma clipping, but a better method could be valuable

# TODO: 
- [ ] Check to see if the master darks, flats, biases, etc. already exist. If they do, use them.
- [X] Refactor to use the path including the date
- [X] Write example batch scripts
- [ ] Note that if the darks from the SKYFLAT directory are used, we don't need to do the dark calibration again for the SKYFLAT directory
- [ ] Assemble calibrated data into KBMOD input format
- [ ] Figure out ways to accelerate the calibration
- [ ] Run calibration locally on 2010-03-01
- [ ] Sketch out pipeline flow chart