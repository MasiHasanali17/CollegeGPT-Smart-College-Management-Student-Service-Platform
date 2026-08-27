"""
loader.py

Loads all JSON datasets from data/raw only once.

This module is the single source of truth for loading
structured university datasets.
"""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

ANALYTICS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ANALYTICS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

# ---------------------------------------------------------
# Cache
# ---------------------------------------------------------

_DATASETS = {}
_LOADED = False


# ---------------------------------------------------------
# Loader
# ---------------------------------------------------------

def load_all(force_reload: bool = False):
    """
    Load every JSON file from data/raw.

    Returns
    -------
    dict

    {
        "academic_details_parul": {...},
        "hostel_residential_life_parul_details": {...},
        ...
    }
    """

    global _DATASETS
    global _LOADED

    if _LOADED and not force_reload:
        return _DATASETS

    _DATASETS = {}

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw directory not found:\n{RAW_DIR}"
        )

    files = sorted(RAW_DIR.glob("*.json"))

    logger.info("Loading %d datasets...", len(files))

    for file in files:

        try:

            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            _DATASETS[file.stem] = data

        except Exception as e:

            logger.exception(
                "Unable to load %s : %s",
                file.name,
                e
            )

    _LOADED = True

    logger.info(
        "Loaded %d datasets successfully.",
        len(_DATASETS)
    )

    return _DATASETS


# ---------------------------------------------------------
# Get one dataset
# ---------------------------------------------------------

def get(name: str):

    if not _LOADED:
        load_all()

    return _DATASETS.get(name)


# ---------------------------------------------------------
# Get all datasets
# ---------------------------------------------------------

def all_datasets():

    if not _LOADED:
        load_all()

    return _DATASETS


# ---------------------------------------------------------
# Dataset names
# ---------------------------------------------------------

def dataset_names():

    if not _LOADED:
        load_all()

    return sorted(_DATASETS.keys())


# ---------------------------------------------------------
# Reload
# ---------------------------------------------------------

def reload():

    return load_all(force_reload=True)


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    data = load_all()

    print("=" * 60)
    print("Datasets Loaded :", len(data))
    print("=" * 60)

    for name in dataset_names():
        print(name)