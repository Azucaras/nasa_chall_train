"""Resolve pilot municipalities against the IBGE APIs and compute their centroids.

Reads the declarative list in config/regions.yaml, downloads each municipality's boundary from the
IBGE *malhas* API, and computes an area-weighted polygon centroid. The centroid is the point handed
to NASA POWER, so it is derived here rather than hand-typed anywhere.

Output: data/processed/regions.parquet
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline.common import (
    base_parser,
    fetch_json,
    load_config,
    log,
    pilot_municipalities,
    setup_logging,
    write_parquet,
)

MALHA_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}"
    "?formato=application/vnd.geo%2Bjson&qualidade=intermediaria"
)


def _ring_area_and_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Signed area and centroid of one closed linear ring, by the shoelace formula.

    Returns (signed_area, cx, cy). A negative signed area means the ring is wound the other way,
    which is how holes cancel out of the weighted sum.
    """
    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    if area2 == 0.0:
        # Degenerate ring: fall back to the mean of its vertices so a bad geometry cannot
        # silently produce a (0, 0) centroid in the Atlantic.
        n = len(ring)
        return 0.0, sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n

    return area2 / 2.0, cx / (3.0 * area2), cy / (3.0 * area2)


def _polygons(geometry: dict[str, Any]) -> list[list[list[list[float]]]]:
    """Normalise Polygon / MultiPolygon into a list of polygons (each a list of rings)."""
    kind = geometry["type"]
    if kind == "Polygon":
        return [geometry["coordinates"]]
    if kind == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"unsupported geometry type for a municipality: {kind}")


def centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    """Area-weighted centroid of a (Multi)Polygon, in degrees lon/lat.

    Computed in plain degrees, not an equal-area projection. At municipality scale the error is far
    below the resolution of anything we sample with it (NASA POWER is ~0.5 degrees), so projecting
    would add a dependency for no gain.
    """
    total = 0.0
    sx = 0.0
    sy = 0.0
    for polygon in _polygons(geometry):
        for ring in polygon:
            area, cx, cy = _ring_area_and_centroid(ring)
            total += area
            sx += cx * area
            sy += cy * area

    if total == 0.0:
        raise ValueError("geometry has zero total area; refusing to guess a centroid")

    return sx / total, sy / total


def bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) -- the bbox used later to clip gridded products."""
    xs: list[float] = []
    ys: list[float] = []
    for polygon in _polygons(geometry):
        for ring in polygon:
            xs.extend(p[0] for p in ring)
            ys.extend(p[1] for p in ring)
    return min(xs), min(ys), max(xs), max(ys)


def main() -> None:
    args = base_parser(__doc__ or "").parse_args()
    setup_logging(args.verbose)

    meta = load_config("regions.yaml")["meta"]
    rows: list[dict[str, Any]] = []

    for mun in pilot_municipalities():
        code = int(mun["code"])
        geojson = fetch_json(
            MALHA_URL.format(code=code),
            cache_name=f"ibge_malha_{code}.geojson",
            refresh=args.refresh,
        )
        geometry = geojson["features"][0]["geometry"]
        lon, lat = centroid(geometry)
        min_lon, min_lat, max_lon, max_lat = bounds(geometry)

        log.info("%s (%d): centroid %.4f, %.4f", mun["name"], code, lon, lat)
        rows.append(
            {
                "code": code,
                "name": mun["name"],
                "uf": mun["uf"],
                "mesoregion": mun["mesoregion"],
                "region_id": mun["region_id"],
                "region_name": mun["region_name"],
                "enso_signal": mun["enso_signal"],
                "hazards": ",".join(mun["hazards"]),
                "centroid_lon": round(lon, 4),
                "centroid_lat": round(lat, 4),
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            }
        )

    df = pd.DataFrame(rows)
    write_parquet(
        df,
        "regions.parquet",
        metadata={
            "source": "IBGE malhas API v3 (qualidade=intermediaria)",
            "centroid_method": "area-weighted polygon centroid, degrees lon/lat",
            "climatology_baseline": f"{meta['climatology_baseline'][0]}-{meta['climatology_baseline'][1]}",
            "generated_by": "pipeline/fetch_regions.py",
        },
    )
    print(df[["code", "name", "uf", "centroid_lon", "centroid_lat", "enso_signal"]].to_string(index=False))


if __name__ == "__main__":
    main()
