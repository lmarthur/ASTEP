#!/bin/bash

# Check that the correct conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "astep" ]]; then
    echo "Activating astep conda environment..."
    mamba activate astep
fi

echo "Running unit tests..."
pytest -v -s ./test/
