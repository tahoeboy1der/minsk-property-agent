from __future__ import annotations

import pytest

from minsk_agent.osm_overpass import OsmFeature, enrich_distances, haversine_m
from minsk_agent.scoring import (
    desirability_score_row,
    proximity_points,
    velocity_bonus_points,
)


def test_proximity_thresholds() -> None:
    assert proximity_points(400, 500, 25) == 25
    assert proximity_points(501, 500, 25) == 0
    assert proximity_points(300, 400, 15) == 15
    assert proximity_points(500, 400, 15) == 0


def test_velocity_bonus_monotonic() -> None:
    b1 = velocity_bonus_points(0.5, 0.2, 0.1)
    b2 = velocity_bonus_points(0.6, 0.2, 0.1)
    assert b2 >= b1
    assert velocity_bonus_points(0.1, 0.2, 0.1) == 0


def test_desirability_cap_100() -> None:
    sc, _ = desirability_score_row(100, 100, 100, 10.0, 0.01, 0.001)
    assert sc <= 100


def test_haversine_known_short_distance() -> None:
    # ~110m between two close points in Minsk (approx)
    d = haversine_m(53.915, 27.575, 53.916, 27.575)
    assert 50 < d < 200


def test_enrich_distances_zero_when_on_feature() -> None:
    osm = {
        "metro": [OsmFeature("metro", 53.915, 27.575)],
        "park": [OsmFeature("park", 53.92, 27.58)],
        "water": [OsmFeature("water", 53.91, 27.57)],
    }
    dm, dp, dw = enrich_distances(53.915, 27.575, osm)
    assert dm is not None and dm < 1.0
