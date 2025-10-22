#!/bin/bash

# Check that the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    mamba activate astep
fi

echo "Running unit tests..."
# run pytest

pytest -vs ./test/ --disable-warnings --log-cli-level=INFO
