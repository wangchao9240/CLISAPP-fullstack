#!/usr/bin/env python3
"""
Queensland grid configuration for climate data sampling.

This module defines the grid points for sampling climate data across Queensland.
Using 25km resolution (~0.225 degrees) to improve sampling density while
remaining within API limits.
"""

from __future__ import annotations

import numpy as np
from typing import List, Dict

# Queensland state boundaries
QLD_BOUNDS = {
    "north": -10.0,   # Cape York
    "south": -29.0,   # NSW border
    "east": 154.0,    # Pacific coast
    "west": 138.0     # SA/NT border
}

# Grid resolution settings
GRID_RESOLUTION_KM = 25  # 25km between sample points
GRID_RESOLUTION_DEG = 0.225  # Approximately 25km at Queensland latitudes

# Data layers to fetch
CLIMATE_LAYERS = [
    "temperature",
    "humidity",
    "precipitation",
    "uv_index",
    "pm25"
]

# Layer metadata for processing
LAYER_CONFIG = {
    "temperature": {
        "unit": "°C",
        "min_value": -10,
        "max_value": 50,
        "precision": 1,
        "color_breaks": [0, 10, 20, 30, 40],
        "data_source": "Open-Meteo",
        "openmeteo_param": "temperature_2m",
    },
    "humidity": {
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "precision": 0,
        "color_breaks": [0, 30, 50, 70, 90],
        "data_source": "Open-Meteo",
        "openmeteo_param": "relative_humidity_2m",
    },
    "precipitation": {
        "unit": "mm",
        "min_value": 0,
        "max_value": 100,
        "precision": 1,
        "color_breaks": [0, 0.5, 2, 10, 50],
        "data_source": "Open-Meteo",
        "openmeteo_param": "precipitation"
    },
    "uv_index": {
        "unit": "UVI",
        "min_value": 0,
        "max_value": 15,
        "precision": 1,
        "color_breaks": [0, 3, 6, 8, 11],
        "data_source": "Open-Meteo",
        "openmeteo_param": "uv_index"
    },
    "pm25": {
        "unit": "µg/m³",
        "min_value": 0,
        "max_value": 500,
        "precision": 1,
        "color_breaks": [0, 12, 35, 55, 150],
        "data_source": "Open-Meteo",
        "openmeteo_param": "pm2_5"
    }
}

# Update intervals (in minutes)
UPDATE_INTERVALS = {
    "temperature": 60,
    "humidity": 60,
    "precipitation": 60,
    "uv_index": 60,
    "pm25": 60,
}

# Default update interval
DEFAULT_UPDATE_INTERVAL = 60  # minutes


def generate_grid_points() -> List[Dict[str, float]]:
    """
    Generate sampling grid points for Queensland.

    Returns:
        List of dictionaries with 'latitude' and 'longitude' keys.
        Each point represents a 25km x 25km cell center.

    Example:
        >>> points = generate_grid_points()
        >>> len(points)
        6278
        >>> points[0]
        {'latitude': -29.0, 'longitude': 138.0}
    """
    # Generate latitude and longitude arrays
    lats = np.arange(
        QLD_BOUNDS["south"],
        QLD_BOUNDS["north"] + GRID_RESOLUTION_DEG,
        GRID_RESOLUTION_DEG
    )
    lons = np.arange(
        QLD_BOUNDS["west"],
        QLD_BOUNDS["east"] + GRID_RESOLUTION_DEG,
        GRID_RESOLUTION_DEG
    )

    # Create grid points
    points = []
    for lat in lats:
        for lon in lons:
            points.append({
                "latitude": round(float(lat), 2),
                "longitude": round(float(lon), 2)
            })

    return points


def get_grid_dimensions() -> Dict[str, int]:
    """
    Get the dimensions of the sampling grid.

    Returns:
        Dictionary with 'rows' (latitude) and 'cols' (longitude) counts.
    """
    lats = np.arange(
        QLD_BOUNDS["south"],
        QLD_BOUNDS["north"] + GRID_RESOLUTION_DEG,
        GRID_RESOLUTION_DEG
    )
    lons = np.arange(
        QLD_BOUNDS["west"],
        QLD_BOUNDS["east"] + GRID_RESOLUTION_DEG,
        GRID_RESOLUTION_DEG
    )

    return {
        "rows": len(lats),
        "cols": len(lons),
        "total_points": len(lats) * len(lons)
    }


# Pre-generate grid points for import
GRID_POINTS = generate_grid_points()
GRID_DIMENSIONS = get_grid_dimensions()


if __name__ == "__main__":
    # Test the configuration
    print(f"Queensland Bounds: {QLD_BOUNDS}")
    print(f"Grid Resolution: {GRID_RESOLUTION_KM}km ({GRID_RESOLUTION_DEG}°)")
    print(f"Grid Dimensions: {GRID_DIMENSIONS}")
    print(f"Total Sample Points: {len(GRID_POINTS)}")
    print(f"\nFirst 5 points:")
    for point in GRID_POINTS[:5]:
        print(f"  {point}")
    print(f"\nLast 5 points:")
    for point in GRID_POINTS[-5:]:
        print(f"  {point}")
