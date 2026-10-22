"""Presentation-only installation matching and visible map centroids."""
from __future__ import annotations

import json

import pandas as pd
import pydeck as pdk
from pydeck.bindings.json_tools import default_serialize


class CompactDeck(pdk.Deck):
    """The normal native pydeck spec, without megabytes of JSON whitespace."""

    def to_json(self):
        return json.dumps(self, default=default_serialize, separators=(",", ":"))


def select_comparison_points(
    current: pd.DataFrame, optimized: pd.DataFrame, selected_routes: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match visible installations by lot + ID, never by the old route ID."""
    if not selected_routes:
        return current, optimized
    visible_optimized = optimized.loc[
        optimized["route"].astype(str).isin(selected_routes)
    ]
    keys = pd.MultiIndex.from_frame(visible_optimized[["lot", "installation"]])
    current_keys = pd.MultiIndex.from_frame(current[["lot", "installation"]])
    return current.loc[current_keys.isin(keys)], visible_optimized


def visible_centroids(points: pd.DataFrame) -> pd.DataFrame:
    """Centroids and counts describe only the points currently on the map."""
    return points.groupby("route", as_index=False).agg(
        centroid_latitude=("latitude", "mean"),
        centroid_longitude=("longitude", "mean"),
        installations=("installation", "size"),
    )
