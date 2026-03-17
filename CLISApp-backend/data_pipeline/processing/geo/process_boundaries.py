#!/usr/bin/env python3
"""Boundary preprocessing utilities.

Reads the client-provided SSC shapefile and exports simplified GeoJSON files
that the mobile frontend can bundle as static assets.

Outputs:
    CLISApp-frontend/assets/geo/boundaries/
        ├─ ssc_coarse.json               # Merged parent-group boundaries
        └─ ssc/
             └─ <group_id>.json          # SSC features grouped per parent

    CLISApp-frontend/src/services/boundaries/
        └─ sscManifest.ts                # Auto-generated SSC asset manifest

The exporter performs light geometry simplification to keep payload size
manageable on devices while preserving topology.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import geopandas as gpd
from shapely.geometry import mapping
from shapely.ops import unary_union


LOGGER = logging.getLogger("process_boundaries")

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "CLISApp-backend"
FRONTEND_ROOT = REPO_ROOT / "CLISApp-frontend"

DATA_ROOT = BACKEND_ROOT / "data_pipeline" / "data"
RAW_GEO_ROOT = DATA_ROOT / "raw" / "geo"

FRONTEND_BOUNDARIES_ROOT = FRONTEND_ROOT / "assets" / "geo" / "boundaries"
SSC_DETAIL_DIR = FRONTEND_BOUNDARIES_ROOT / "ssc"
SSC_COARSE_PATH = FRONTEND_BOUNDARIES_ROOT / "ssc_coarse.json"
SSC_MANIFEST_PATH = FRONTEND_ROOT / "src" / "services" / "boundaries" / "sscManifest.ts"

SSC_SHP = REPO_ROOT / "additional-data" / "D_lowPopMap_A" / "D_lowPopMap_A.shp"
LGA_SHP = RAW_GEO_ROOT / "LGA_boundaries" / "Local_Government_Areas.shp"

# Empirically tuned tolerance: ~50 metres in degrees (~0.0005)
SIMPLIFY_TOLERANCE = 0.0005

SSC_CODE_CANDIDATES = (
    "merged_i",
    "ssc_code",
    "ssc_code16",
    "ssc_code21",
    "ssc_code23",
    "loc_code",
    "code",
)
SSC_NAME_CANDIDATES = (
    "merged_n",
    "ssc_name",
    "ssc_name16",
    "ssc_name21",
    "ssc_name23",
    "locality",
    "name",
)
SSC_GROUP_CANDIDATES = (
    "sa3_name",
    "sa4_name",
    "lga_name",
    "lga",
    "parent_region",
    "group_name",
    "region_name",
    "region",
)
SSC_STATE_CANDIDATES = (
    "state",
    "state_name",
    "state_abbr",
    "ste_name16",
    "ste_name21",
    "ste_name23",
)
SSC_AREA_CANDIDATES = (
    "area_sqkm",
    "area_km2",
    "ca_area_sq",
    "shape_area",
)


@dataclass(frozen=True)
class SscFieldMapping:
    code: str
    name: str
    group: str | None
    state: str | None
    area: str | None


def load_shapefile(path: Path) -> gpd.GeoDataFrame:
    """Load a shapefile and normalize it to EPSG:4326."""

    if not path.exists():
        raise FileNotFoundError(
            f"Shapefile not found: {path}. Provide the D_lowPopMap_A shapefile with --shapefile."
        )
    if not path.is_file():
        raise FileNotFoundError(f"Shapefile path is not a file: {path}")

    LOGGER.info("Reading %s", path)
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:  # pragma: no cover - depends on geopandas backend exception types
        raise RuntimeError(
            f"Unable to read shapefile {path}. Ensure the .shp, .shx, .dbf, and .prj files are all present and readable."
        ) from exc

    LOGGER.info("Loaded %d raw features", len(gdf))
    LOGGER.info("Shapefile columns: %s", ", ".join(str(column) for column in gdf.columns))

    if gdf.crs is None:
        raise ValueError(
            f"Shapefile {path} does not define a CRS. Reproject it to EPSG:4326 or add a valid .prj file."
        )

    LOGGER.info("Detected CRS: %s", gdf.crs)
    normalized_gdf = gdf if gdf.crs.to_epsg() == 4326 else gdf.to_crs(epsg=4326)
    if normalized_gdf.crs.to_epsg() != 4326:
        raise ValueError(f"Failed to normalize {path} to EPSG:4326. Current CRS: {normalized_gdf.crs}")

    non_null_gdf = normalized_gdf[normalized_gdf.geometry.notna()].copy()
    dropped_count = len(normalized_gdf) - len(non_null_gdf)
    if dropped_count:
        LOGGER.info("Dropped %d features with null geometry", dropped_count)
    if non_null_gdf.empty:
        raise ValueError(f"Shapefile {path} contains no usable features after removing null geometry.")

    LOGGER.info("Using %d features after geometry validation", len(non_null_gdf))
    return non_null_gdf


def simplify_geometry(geom, tolerance: float = SIMPLIFY_TOLERANCE) -> dict:
    """Simplify a geometry while preserving topology."""

    simplified = geom.simplify(tolerance, preserve_topology=True)
    return mapping(simplified)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert SSC shapefiles into frontend GeoJSON assets.")
    parser.add_argument(
        "--shapefile",
        type=Path,
        default=SSC_SHP,
        help=f"Path to the SSC shapefile (default: {SSC_SHP})",
    )
    parser.add_argument(
        "--group-field",
        default=None,
        help="Optional parent region column override if auto-detection picks the wrong grouping field.",
    )
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=SIMPLIFY_TOLERANCE,
        help=f"Topology-preserving simplification tolerance in degrees (default: {SIMPLIFY_TOLERANCE})",
    )
    return parser.parse_args(argv)


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _clean_text(value: Any, *, field_label: str, column_name: str) -> str:
    if value is None:
        raise ValueError(f"Column '{column_name}' contains null values for required {field_label}.")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError(f"Column '{column_name}' contains NaN values for required {field_label}.")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Column '{column_name}' contains blank values for required {field_label}.")
    return text


def _format_code(value: Any, column_name: str) -> str:
    cleaned = _clean_text(value, field_label="SSC code", column_name=column_name)
    numeric_value = cleaned[:-2] if cleaned.endswith(".0") else cleaned
    return numeric_value


def _format_title_case(value: Any, column_name: str, field_label: str) -> str:
    return _clean_text(value, field_label=field_label, column_name=column_name).title()


def _format_state(value: Any, column_name: str | None) -> str:
    if column_name is None:
        return "QLD"
    if value is None:
        return "QLD"
    if isinstance(value, float) and math.isnan(value):
        return "QLD"
    text = str(value).strip().upper()
    return text or "QLD"


def _format_area(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_area_sqkm(gdf: gpd.GeoDataFrame) -> list[float | None]:
    """Compute area in km² by projecting to an equal-area CRS (EPSG:3577 GDA94 Australian Albers)."""
    try:
        projected = gdf.to_crs(epsg=3577)
        return [round(geom.area / 1_000_000, 2) if geom is not None else None for geom in projected.geometry]
    except Exception:
        LOGGER.warning("Could not compute area from geometry; area_sqkm will be null")
        return [None] * len(gdf)


def _column_lookup(columns: Iterable[str]) -> dict[str, str]:
    return {normalize_identifier(column): column for column in columns}


def _find_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lookup = _column_lookup(columns)
    for candidate in candidates:
        actual = lookup.get(normalize_identifier(candidate))
        if actual is not None:
            return actual
    return None


def resolve_field_mapping(columns: Iterable[str], group_field: str | None = None) -> SscFieldMapping:
    column_list = [str(column) for column in columns]
    code_field = _find_column(column_list, SSC_CODE_CANDIDATES)
    if code_field is None:
        raise ValueError(
            "Missing required SSC code column. "
            f"Expected one of {SSC_CODE_CANDIDATES}. Available columns: {', '.join(column_list)}."
        )

    name_field = _find_column(column_list, SSC_NAME_CANDIDATES)
    if name_field is None:
        raise ValueError(
            "Missing required SSC name column. "
            f"Expected one of {SSC_NAME_CANDIDATES}. Available columns: {', '.join(column_list)}."
        )

    if group_field:
        resolved_group = _find_column(column_list, [group_field])
        if resolved_group is None:
            raise ValueError(
                f"Requested parent group field '{group_field}' was not found. "
                f"Available columns: {', '.join(column_list)}."
            )
        group_field_name = resolved_group
    else:
        group_field_name = _find_column(column_list, SSC_GROUP_CANDIDATES)
        if group_field_name is None:
            LOGGER.info(
                "No parent group column found in shapefile. Available columns: %s. Falling back to LGA-derived grouping.",
                ", ".join(column_list),
            )
            group_field_name = None

    mapping = SscFieldMapping(
        code=code_field,
        name=name_field,
        group=group_field_name,
        state=_find_column(column_list, SSC_STATE_CANDIDATES),
        area=_find_column(column_list, SSC_AREA_CANDIDATES),
    )
    LOGGER.info(
        "Resolved SSC fields: code=%s name=%s group=%s state=%s area=%s",
        mapping.code,
        mapping.name,
        mapping.group or "<derived from LGA boundaries>",
        mapping.state or "<default: QLD>",
        mapping.area or "<none>",
    )
    return mapping


def _derive_group_fields_from_lga_boundaries(ssc_gdf: gpd.GeoDataFrame) -> tuple[Any, Any]:
    lga_gdf = load_shapefile(LGA_SHP)
    required_columns = {"lga_code", "lga"}
    if not required_columns.issubset(set(lga_gdf.columns)):
        raise ValueError(
            f"LGA fallback shapefile is missing required columns {sorted(required_columns)}. "
            f"Available columns: {', '.join(str(column) for column in lga_gdf.columns)}."
        )

    point_frame = gpd.GeoDataFrame(
        ssc_gdf.drop(columns="geometry"),
        geometry=ssc_gdf.geometry.representative_point(),
        crs=ssc_gdf.crs,
    )
    joined = gpd.sjoin(
        point_frame,
        lga_gdf[["lga_code", "lga", "geometry"]],
        how="left",
        predicate="within",
    )

    unmatched_mask = joined["lga"].isna()
    if unmatched_mask.any():
        missing_count = int(unmatched_mask.sum())
        LOGGER.warning(
            "%d SSC features did not fall within any LGA boundary; attempting nearest-join fallback",
            missing_count,
        )
        unmatched_points = point_frame.loc[unmatched_mask.index[unmatched_mask]]
        nearest_joined = gpd.sjoin_nearest(
            unmatched_points,
            lga_gdf[["lga_code", "lga", "geometry"]],
            how="left",
        )
        joined.loc[unmatched_mask, "lga"] = nearest_joined["lga"].values
        joined.loc[unmatched_mask, "lga_code"] = nearest_joined["lga_code"].values

        still_missing = joined["lga"].isna().sum()
        if still_missing:
            LOGGER.warning(
                "%d SSC features remain ungrouped after nearest-join; assigning to 'ungrouped'",
                int(still_missing),
            )
            joined["lga"] = joined["lga"].fillna("ungrouped")

    group_names = joined["lga"].map(lambda value: _format_title_case(value, "lga", "derived parent group"))
    group_ids = group_names.map(lambda value: f"group_{normalize_identifier(value)}")
    LOGGER.info("Derived parent groups for %d SSC features using spatial LGA fallback", len(joined))
    return group_names, group_ids


def prepare_ssc_records(gdf: gpd.GeoDataFrame, field_mapping: SscFieldMapping) -> gpd.GeoDataFrame:
    """Create a normalized, immutable working set for export."""

    if field_mapping.group is None:
        derived_group_names, derived_group_ids = _derive_group_fields_from_lga_boundaries(gdf)
    else:
        derived_group_names = gdf[field_mapping.group].map(
            lambda value: _format_title_case(value, field_mapping.group or "<group>", "parent group")
        )
        derived_group_ids = gdf[field_mapping.group].map(
            lambda value: f"group_{normalize_identifier(_clean_text(value, field_label='parent group', column_name=field_mapping.group or '<group>'))}"
        )

    prepared = gdf.assign(
        _ssc_code=gdf[field_mapping.code].map(lambda value: _format_code(value, field_mapping.code)),
        _ssc_id=gdf[field_mapping.code].map(lambda value: f"ssc_{_format_code(value, field_mapping.code)}"),
        _name=gdf[field_mapping.name].map(
            lambda value: _format_title_case(value, field_mapping.name, "SSC name")
        ),
        _group_name=derived_group_names,
        _group_id=derived_group_ids,
        _state=(
            gdf[field_mapping.state].map(lambda value: _format_state(value, field_mapping.state))
            if field_mapping.state
            else "QLD"
        ),
        _area_sqkm=(
            gdf[field_mapping.area].map(_format_area)
            if field_mapping.area
            else _compute_area_sqkm(gdf)
        ),
    )

    if prepared["_group_id"].eq("group_").any():
        raise ValueError(
            f"Column '{field_mapping.group}' contains values that cannot be converted into a valid group_id."
        )

    return prepared


def _build_feature(
    feature_id: str,
    name: str,
    state: str,
    group_id: str,
    area_sqkm: float | None,
    geometry: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {
            "id": feature_id,
            "name": name,
            "state": state,
            "group_id": group_id,
            "area_sqkm": area_sqkm,
        },
        "geometry": geometry,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    size_bytes = path.stat().st_size
    LOGGER.info("Output file %s (%d bytes)", path, size_bytes)
    return size_bytes


def _prepare_output_dir(out_dir: Path) -> None:
    """Clear previous SSC output (idempotent re-run) but keep legacy assets.

    Legacy assets (lga_boundaries.json, suburbs/) are intentionally preserved
    so that BoundaryStore.ts continues to work until Story 1.2 switches
    the frontend to the new SSC bundle.
    """
    detail_dir = out_dir / "ssc"
    if detail_dir.exists():
        shutil.rmtree(detail_dir)
        LOGGER.info("Cleared existing SSC detail directory %s", detail_dir)


def export_ssc_coarse_boundaries(
    ssc_gdf: gpd.GeoDataFrame,
    out_path: Path,
    simplify_tolerance: float = SIMPLIFY_TOLERANCE,
) -> int:
    features: list[dict[str, Any]] = []
    grouped = ssc_gdf.sort_values(["_group_id", "_ssc_code"]).groupby(
        ["_group_id", "_group_name"], sort=True
    )

    for (group_id, group_name), group_rows in grouped:
        merged_geometry = unary_union(list(group_rows.geometry))
        area_values = [value for value in group_rows["_area_sqkm"].tolist() if value is not None]
        area_sqkm = float(sum(area_values)) if area_values else None
        state = next((str(value) for value in group_rows["_state"].tolist() if value), "QLD")
        features.append(
            _build_feature(
                feature_id=group_id,
                name=group_name,
                state=state,
                group_id=group_id,
                area_sqkm=area_sqkm,
                geometry=simplify_geometry(merged_geometry, tolerance=simplify_tolerance),
            )
        )

    collection = {"type": "FeatureCollection", "features": features}
    _write_json(out_path, collection)
    LOGGER.info("Exported %d coarse group features -> %s", len(features), out_path)
    return len(features)


def export_ssc_detail_boundaries(
    ssc_gdf: gpd.GeoDataFrame,
    detail_dir: Path,
    simplify_tolerance: float = SIMPLIFY_TOLERANCE,
) -> list[str]:
    detail_dir.mkdir(parents=True, exist_ok=True)

    grouped_features: dict[str, list[dict[str, Any]]] = {}
    ordered_records = ssc_gdf.sort_values(["_group_id", "_ssc_code"])
    for row in ordered_records.to_dict("records"):
        feature = _build_feature(
            feature_id=str(row["_ssc_id"]),
            name=str(row["_name"]),
            state=str(row["_state"]),
            group_id=str(row["_group_id"]),
            area_sqkm=row["_area_sqkm"],
            geometry=simplify_geometry(row["geometry"], tolerance=simplify_tolerance),
        )
        grouped_features.setdefault(str(row["_group_id"]), []).append(feature)

    for group_id, features in grouped_features.items():
        collection = {"type": "FeatureCollection", "features": features}
        out_path = detail_dir / f"{group_id}.json"
        _write_json(out_path, collection)
        LOGGER.info("Exported %d SSC features for %s -> %s", len(features), group_id, out_path)

    return sorted(grouped_features)


def generate_ssc_manifest(group_ids: Iterable[str], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "// Auto-generated by process_boundaries.py - DO NOT EDIT",
        'import { FeatureCollection } from "geojson";',
        "",
        "export const sscCollections: Record<string, FeatureCollection> = {",
    ]
    for group_id in sorted(group_ids):
        lines.append(
            f'  "{group_id}": require("../../../assets/geo/boundaries/ssc/{group_id}.json"),'
        )
    lines.append("};")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    size_bytes = manifest_path.stat().st_size
    LOGGER.info("Output file %s (%d bytes)", manifest_path, size_bytes)


def process_ssc_boundaries(
    shapefile_path: Path,
    out_dir: Path = FRONTEND_BOUNDARIES_ROOT,
    manifest_path: Path = SSC_MANIFEST_PATH,
    *,
    group_field: str | None = None,
    simplify_tolerance: float = SIMPLIFY_TOLERANCE,
) -> dict[str, Any]:
    """Process the SSC shapefile into frontend boundary assets."""

    start_time = time.perf_counter()
    ssc_gdf = load_shapefile(shapefile_path)
    field_mapping = resolve_field_mapping(ssc_gdf.columns, group_field=group_field)
    prepared_ssc_gdf = prepare_ssc_records(ssc_gdf, field_mapping)

    out_dir.mkdir(parents=True, exist_ok=True)
    _prepare_output_dir(out_dir)

    coarse_feature_count = export_ssc_coarse_boundaries(
        prepared_ssc_gdf,
        out_path=out_dir / SSC_COARSE_PATH.name,
        simplify_tolerance=simplify_tolerance,
    )
    group_ids = export_ssc_detail_boundaries(
        prepared_ssc_gdf,
        detail_dir=out_dir / SSC_DETAIL_DIR.name,
        simplify_tolerance=simplify_tolerance,
    )
    generate_ssc_manifest(group_ids, manifest_path)

    elapsed_seconds = time.perf_counter() - start_time
    if elapsed_seconds <= 300:
        LOGGER.info("Processing stayed within the 5 minute target (%.2f seconds)", elapsed_seconds)
    else:
        LOGGER.warning("Processing exceeded the 5 minute target (%.2f seconds)", elapsed_seconds)
    LOGGER.info(
        "Processing completed in %.2f seconds for %d SSC features across %d groups",
        elapsed_seconds,
        len(prepared_ssc_gdf),
        len(group_ids),
    )

    return {
        "feature_count": len(prepared_ssc_gdf),
        "group_count": len(group_ids),
        "coarse_feature_count": coarse_feature_count,
        "elapsed_seconds": elapsed_seconds,
        "output_dir": out_dir,
        "manifest_path": manifest_path,
    }


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    process_ssc_boundaries(
        shapefile_path=args.shapefile,
        out_dir=FRONTEND_BOUNDARIES_ROOT,
        manifest_path=SSC_MANIFEST_PATH,
        group_field=args.group_field,
        simplify_tolerance=args.simplify_tolerance,
    )


if __name__ == "__main__":
    main()
