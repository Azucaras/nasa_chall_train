import { useEffect, useMemo, useState } from "react";
import {
  AnomalyTimeline,
  CompositeBars,
  EnsoOutlookChart,
  EnsoStatus,
  ForecastPanel,
  LandCoverTile,
  I18nProvider,
  MockBanner,
  MunicipalityMap,
  MunicipalityPicker,
  RoniHistoryChart,
  RotationPanel,
  SeasonProgressChart,
  TerrainBars,
  VegetationPanel,
  YieldEvidence,
  clientFromEnv,
  useI18n,
  useLoad,
  type Locale,
  type Meta,
  type MunicipalityPayload,
} from "../fieldphase";

const client = clientFromEnv();
const basemap = {
  tiles: import.meta.env.VITE_BASEMAP_TILES ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution: import.meta.env.VITE_BASEMAP_ATTRIBUTION ?? "© OpenStreetMap contributors",
};

type Theme = "auto" | "light" | "dark";

function stored<T extends string>(key: string, fallback: T): T {
  try {
    return (localStorage.getItem(key) as T | null) ?? fallback;
  } catch {
    return fallback;
  }
}
function store(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode: preference is just not remembered */
  }
}

export default function App() {
  const [locale, setLocale] = useState<Locale>(() => stored<Locale>("fp-locale", "pt-BR"));
  const [theme, setTheme] = useState<Theme>(() => stored<Theme>("fp-theme", "auto"));

  useEffect(() => {
    document.documentElement.lang = locale;
    store("fp-locale", locale);
  }, [locale]);
  useEffect(() => {
    if (theme === "auto") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    store("fp-theme", theme);
  }, [theme]);

  return (
    <I18nProvider locale={locale}>
      <Page locale={locale} setLocale={setLocale} theme={theme} setTheme={setTheme} />
    </I18nProvider>
  );
}

function Page({
  locale,
  setLocale,
  theme,
  setTheme,
}: {
  locale: Locale;
  setLocale: (l: Locale) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
}) {
  const { t } = useI18n();
  const meta = useLoad(client.meta, "meta");
  const enso = useLoad(client.enso, "enso");
  const muns = useLoad(client.municipalities, "muns");
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (muns.status === "ready" && selected == null && muns.data.municipalities.length) {
      setSelected(muns.data.municipalities[0].code);
    }
  }, [muns, selected]);

  const detail = useLoad(() => (selected == null ? Promise.reject("none") : client.municipality(selected)), selected);

  const failed = [meta, enso, muns].find((s) => s.status === "error");

  return (
    <>
      {meta.status === "ready" && meta.data.mock && <MockBanner />}
      <div className="fp-shell">
        <header className="fp-header">
          <div>
            <h1>{t.app.title}</h1>
            <p>{t.app.tagline}</p>
          </div>
          <div className="fp-controls">
            <div className="fp-seg" role="group" aria-label={t.app.language}>
              {(["pt-BR", "en"] as Locale[]).map((l) => (
                <button key={l} type="button" aria-pressed={locale === l} onClick={() => setLocale(l)}>
                  {l === "pt-BR" ? "PT" : "EN"}
                </button>
              ))}
            </div>
            <div className="fp-seg" role="group" aria-label={t.app.theme}>
              {(["auto", "light", "dark"] as Theme[]).map((th) => (
                <button key={th} type="button" aria-pressed={theme === th} onClick={() => setTheme(th)}>
                  {th === "auto" ? t.app.themeAuto : th === "light" ? t.app.themeLight : t.app.themeDark}
                </button>
              ))}
            </div>
          </div>
        </header>

        {failed && failed.status === "error" ? (
          <section className="fp-section fp-card" role="alert">
            <h3>{t.app.loadError}</h3>
            <p className="fp-sub">{failed.error}</p>
            <p className="fp-note">{t.app.loadErrorHint}</p>
          </section>
        ) : null}

        <section className="fp-section" aria-labelledby="s-enso">
          <h2 id="s-enso">{t.sections.enso}</h2>
          <p className="fp-lead">{t.sections.ensoLead}</p>
          {enso.status === "ready" ? (
            <>
              <EnsoStatus enso={enso.data} />
              <div className="fp-grid fp-grid-2" style={{ marginTop: 16 }}>
                <EnsoOutlookChart outlook={enso.data.outlook} />
                <RoniHistoryChart enso={enso.data} />
              </div>
            </>
          ) : (
            enso.status === "loading" && <p className="fp-note">{t.app.loading}</p>
          )}
        </section>

        {muns.status === "ready" && (
          <section className="fp-section" aria-labelledby="s-place">
            <h2 id="s-place">{t.sections.place}</h2>
            <div className="fp-grid fp-grid-2">
              <MunicipalityPicker municipalities={muns.data.municipalities} selected={selected} onSelect={setSelected} />
              <MunicipalityMap
                geojson={muns.data.geojson}
                municipalities={muns.data.municipalities}
                selected={selected}
                onSelect={setSelected}
                basemap={basemap}
              />
            </div>
          </section>
        )}

        {detail.status === "ready" && <MunicipalitySections d={detail.data} />}
        {detail.status === "loading" && selected != null && <p className="fp-note">{t.app.loading}</p>}

        {meta.status === "ready" && <Footer meta={meta.data} />}
      </div>
    </>
  );
}

const CLIMATE_PANELS = ["early_rain_mm_anom_pct", "late_rain_mm_anom_pct", "early_r20_days_anom", "late_cdd_days_anom"];

function MunicipalitySections({ d }: { d: MunicipalityPayload }) {
  const { t } = useI18n();
  const [metric, setMetric] = useState(CLIMATE_PANELS[0]);
  const comps = d.climate.composites;
  const name = d.municipality.name_official ?? d.municipality.name;
  const timeline = useMemo(
    () =>
      d.climate.seasons.map((s) => ({
        year: s.crop_year,
        value: (s[metric] as number | null) ?? null,
        enso_class: s.enso_class,
      })),
    [d, metric],
  );

  return (
    <>
      <section className="fp-section" aria-labelledby="s-preview">
        <h2 id="s-preview">
          {t.sections.preview} — {name}
        </h2>
        <SeasonProgressChart progress={d.season_progress} currentYear={d.current_crop_year} />
      </section>

      {d.forecast && (
        <section className="fp-section" aria-labelledby="s-forecast">
          <h2 id="s-forecast">{t.forecast.title}</h2>
          <p className="fp-lead">{t.forecast.lead}</p>
          <ForecastPanel forecast={d.forecast} />
        </section>
      )}

      <section className="fp-section" aria-labelledby="s-rot">
        <h2 id="s-rot">
          {t.sections.rotations} — {name}
        </h2>
        {d.rotations ? (
          <RotationPanel rotations={d.rotations} regionLabel={d.municipality.region_name} />
        ) : (
          <div className="fp-card fp-todo">{t.sections.rotationsTodo}</div>
        )}
      </section>

      <section className="fp-section" aria-labelledby="s-evidence">
        <h2 id="s-evidence">{t.sections.evidence}</h2>
        <p className="fp-lead">{t.sections.evidenceLead}</p>
        <div className="fp-grid fp-grid-2">
          {CLIMATE_PANELS.filter((m) => comps[m]).map((m) => (
            <CompositeBars
              key={m}
              title={t.metrics[m] ?? m}
              sub={t.units[comps[m].unit] ?? comps[m].unit}
              rows={comps[m].by_class}
              unit={comps[m].unit}
              explainSubject={t.metrics[m] ?? m}
            />
          ))}
        </div>
        <div style={{ marginTop: 16 }}>
          <div className="fp-seg" role="tablist" style={{ flexWrap: "wrap", marginBottom: 12 }}>
            {CLIMATE_PANELS.map((m) => (
              <button key={m} type="button" role="tab" aria-selected={metric === m} onClick={() => setMetric(m)}>
                {t.metrics[m]}
              </button>
            ))}
          </div>
          <AnomalyTimeline
            title={t.metrics[metric]}
            sub={`${t.units[comps[metric]?.unit] ?? ""} · NASA POWER`}
            unit={comps[metric]?.unit ?? "%"}
            points={timeline}
          />
        </div>
      </section>

      <section className="fp-section" aria-labelledby="s-yield">
        <h2 id="s-yield">{t.sections.yield}</h2>
        <p className="fp-lead">{t.sections.yieldLead}</p>
        <YieldEvidence crops={d.yield.crops} provenance={d.provenance.yield} />
      </section>

      {(d.vegetation || d.terrain || d.land_cover) && (
        <section className="fp-section" aria-labelledby="s-veg">
          <h2 id="s-veg">{t.vegetation.title}</h2>
          <p className="fp-lead">{t.vegetation.lead}</p>
          {(d.land_cover || d.terrain) && (
            <div className="fp-grid fp-grid-2" style={{ marginBottom: 16, alignItems: "start" }}>
              {d.land_cover && <LandCoverTile landCover={d.land_cover} />}
              {d.terrain && <TerrainBars terrain={d.terrain} />}
            </div>
          )}
          {d.vegetation && <VegetationPanel vegetation={d.vegetation} />}
        </section>
      )}
    </>
  );
}

function Footer({ meta }: { meta: Meta }) {
  const { t, date } = useI18n();
  return (
    <footer className="fp-footer">
      <strong>{t.app.footerSources}</strong>
      <dl>
        {Object.entries(meta.methods).map(([k, v]) => (
          <div key={k} style={{ display: "contents" }}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
        {Object.entries(meta.datasets).map(([k, v]) => (
          <div key={k} style={{ display: "contents" }}>
            <dt>{k}</dt>
            <dd>{v.source ?? v.source_index ?? v.generated_by}</dd>
          </div>
        ))}
      </dl>
      <p className="fp-note">
        {meta.mock ? t.app.mock : t.app.footerNoMock} · contract v{meta.contract_version} · {date(meta.generated_at)}
      </p>
    </footer>
  );
}
