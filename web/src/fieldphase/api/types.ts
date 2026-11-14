/**
 * Field Phase data contract, version 1.
 *
 * Mirrors api/repository.py exactly. Every payload is plain JSON: numbers may be null (never NaN),
 * dates are ISO strings, categorical fields are stable codes and never translated text.
 */

export type EnsoClass = "el_nino_strong" | "el_nino_moderate" | "neutral" | "la_nina";
export type Strength = "none" | "weak" | "moderate" | "strong" | "very_strong";
export type CropSeason = "summer" | "winter";
/** "suposicao" marks an unsourced assumption and must surface as a warning in the UI. */
export type SourceTag = string;

export interface Assumption {
  scope: "crop";
  crop_code: number;
  field: string;
  value: string;
  source: SourceTag;
}

export interface Meta {
  app: string;
  contract_version: string;
  /** True only for mock payloads; the UI must then show a visible "mock" badge. */
  mock: boolean;
  generated_at: string;
  baseline_crop_years: [number, number];
  current_crop_year: number | null;
  enso_classes: EnsoClass[];
  methods: Record<string, string>;
  assumptions: Assumption[];
  datasets: Record<string, Record<string, string>>;
}

export interface OutlookRow {
  lead: number;
  season: string;
  issued: string;
  p_la_nina: number;
  p_neutral: number;
  p_el_nino: number;
  "p_p0.5_p1.0": number;
  "p_p1.0_p1.5": number;
  "p_p1.5_p2.0": number;
  "p_ge_p2.0": number;
  [bin: string]: number | string;
}

export interface EnsoHistoryRow {
  season: string;
  year: number;
  center_month: number;
  crop_year: number;
  roni: number | null;
  oni: number | null;
  roni_phase: string | null;
  roni_strength: Strength | null;
}

export interface CropYearEnso {
  crop_year: number;
  enso_class: EnsoClass;
  roni_ref: number | null;
  roni_strength: Strength | null;
  provisional: boolean;
  forecast: boolean;
  forecast_probability_pct?: number | null;
  basis: string;
}

export interface EnsoPayload {
  current: {
    discussion: {
      issued: string;
      alert_status: string;
      synopsis: string;
      next_issue: string | null;
      nino34_quoted_c: number | null;
      discussion_text: string;
      source_url: string;
    };
    roni: { season: string; value: number; phase: string; strength: Strength };
    oni: { season: string; value: number };
    weekly_nino34: { week: string; anomaly: number };
    fetched_at: string;
  };
  outlook: OutlookRow[];
  weekly: { week_center: string; nino34_anom: number; nino12_anom: number }[];
  history: EnsoHistoryRow[];
  crop_years: CropYearEnso[];
  provenance: Record<string, string>;
}

export interface Municipality {
  code: number;
  /** ASCII name from config/regions.yaml. */
  name: string;
  /** IBGE's official, accented name (from SIDRA); use this for display. */
  name_official: string;
  uf: string;
  region_id: string;
  region_name: string;
  /** Direction of the El Nino rainfall signal in this region. */
  enso_signal: "excess" | "deficit";
  hazards: string[] | string;
  centroid_lon: number;
  centroid_lat: number;
  min_lon: number;
  min_lat: number;
  max_lon: number;
  max_lat: number;
  geometry_source: string;
}

export interface MunicipalitiesPayload {
  municipalities: Municipality[];
  geojson: GeoJSON.FeatureCollection | null;
  provenance: Record<string, string>;
}

export interface CompositeRow {
  enso_class: EnsoClass;
  n: number;
  mean: number | null;
  median: number | null;
  minus_neutral: number | null;
  /** Comma-separated crop years. */
  years: string;
}

export interface ClimateSeason {
  crop_year: number;
  enso_class: EnsoClass | null;
  [metric: string]: number | string | null;
}

export interface CropEvidence {
  crop_code: number;
  name_pt: string;
  name_en: string;
  season: CropSeason;
  source: SourceTag;
  assumption: boolean;
  pam_table: number;
  series: {
    crop_year: number;
    enso_crop_year: number;
    yield_kg_ha: number;
    trend_kg_ha: number;
    anomaly_pct: number;
    enso_class: EnsoClass | null;
  }[];
  composite: CompositeRow[];
}

export interface SeasonDay {
  day: number;
  date: string;
  current_mm: number | null;
  baseline_mean_mm: number | null;
  baseline_p10_mm: number | null;
  baseline_p90_mm: number | null;
  analog_mean_mm: number | null;
}

export interface MunicipalityPayload {
  municipality: Municipality & { hazards: string[] };
  current_crop_year: Partial<CropYearEnso> & { crop_year: number };
  season_progress: {
    start: string;
    last_observed: string;
    n_baseline: number;
    n_analog: number;
    analog_years: number[];
    days: SeasonDay[];
  };
  climate: {
    seasons: ClimateSeason[];
    composites: Record<string, { unit: string; by_class: CompositeRow[] }>;
  };
  yield: { crops: CropEvidence[] };
  provenance: Record<string, string>;
}
