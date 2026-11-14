/**
 * Every user-facing string, in Brazilian Portuguese (default) and English (for the pitch).
 *
 * Keys are grouped by component. Functions build the plain-language explanations from real
 * values; they never contain a number of their own.
 */

import type { EnsoClass, Strength } from "../api/types";

export type Locale = "pt-BR" | "en";

const ptBR = {
  app: {
    title: "Field Phase",
    tagline: "Prévia de impacto do El Niño na sua lavoura, com dados da NASA, NOAA e IBGE",
    language: "Idioma",
    theme: "Tema",
    themeAuto: "Automático",
    themeLight: "Claro",
    themeDark: "Escuro",
    loading: "Carregando dados…",
    loadError: "Não foi possível carregar os dados",
    loadErrorHint:
      "Rode o pipeline e exporte os dados: `uv run python -m api.export` (ou inicie a API com VITE_DATA_MODE=api).",
    mock: "DADOS FICTÍCIOS (mock)",
    footerSources: "Fontes e métodos",
    footerNoMock: "Nenhum dado fictício nesta página.",
  },
  sections: {
    enso: "El Niño agora",
    ensoLead: "O estado oficial do Pacífico, segundo o Climate Prediction Center da NOAA.",
    place: "Escolha o município",
    preview: "Prévia de impacto desta safra",
    evidence: "O que os anos de El Niño forte já mostraram",
    evidenceLead:
      "Comparação de cada tipo de ano com a média de 1991–2020. Cada barra mostra quantos anos (n) entraram na conta.",
    yield: "Produtividade por cultura (IBGE PAM)",
    yieldLead:
      "Desvio da produtividade em relação à tendência de longo prazo, que retira o ganho de tecnologia ao longo dos anos.",
    rotations: "Rotações recomendadas",
    rotationsTodo:
      "Ainda não implementado. A pontuação das rotações (proteger o solo, conservar água, estabilidade de renda) entra na próxima etapa; esta página mostra só as evidências em que ela vai se apoiar.",
  },
  enso: {
    alert: "Alerta",
    issued: (d: string) => `Discussão de ${d}`,
    next: (d: string) => `próxima em ${d}`,
    roni: "RONI (índice oficial)",
    roniSub: (season: string) => `trimestre ${season}`,
    weekly: "Niño-3.4 semanal",
    weeklySub: (week: string) => `semana de ${week}`,
    oni: (v: string, s: string) => `ONI ${s}: ${v} (índice antigo, para comparação)`,
    synopsisLabel: "Resumo da NOAA (texto original, em inglês)",
    outlookTitle: "Chance de cada tipo de ENSO nos próximos trimestres",
    outlookSub: (issued: string) => `Probabilidades oficiais da NOAA CPC, emitidas em ${issued}`,
    historyTitle: "RONI desde 1950",
    historySub: "Acima de +0,5 °C: El Niño. Abaixo de −0,5 °C: La Niña.",
    historic: "Evento histórico (+2,5 °C)",
  },
  classes: {
    el_nino_strong: "El Niño forte",
    el_nino_moderate: "El Niño fraco/moderado",
    neutral: "Neutro",
    la_nina: "La Niña",
  } satisfies Record<EnsoClass, string>,
  strength: {
    none: "abaixo do limiar",
    weak: "fraco",
    moderate: "moderado",
    strong: "forte",
    very_strong: "muito forte",
  } satisfies Record<Strength, string>,
  signal: {
    excess: "Excesso de chuva no El Niño",
    deficit: "Falta de chuva no El Niño",
  },
  hazards: {
    waterlogging: "encharcamento",
    erosion: "erosão",
    delayed_planting: "atraso no plantio",
    harvest_rain: "chuva na colheita",
    drought: "seca",
    veranico: "veranico",
    late_onset: "início tardio das chuvas",
    safrinha_failure: "quebra da safrinha",
  } as Record<string, string>,
  preview: {
    title: "Chuva acumulada desde o início da safra",
    sub: (start: string, last: string) => `De ${start} até ${last} (último dia publicado pela NASA POWER)`,
    current: "Esta safra",
    baseline: "Média 1991–2020",
    band: "Faixa normal (10%–90%)",
    analog: "Média dos anos de El Niño forte",
    headline: (mm: string, pct: string, normal: string) =>
      `Desde o início da safra choveram ${mm} mm — ${pct} do normal para a data (${normal} mm).`,
    analogLine: (mm: string, n: number, years: string) =>
      `Nos ${n} anos de El Niño forte (${years}), a média até esta data foi ${mm} mm.`,
    forecastClass: (cls: string, p: string, basis: string) =>
      `Esta safra está classificada como "${cls}" por previsão (${p} de chance; ${basis}).`,
    gridNote:
      "Chuva da NASA POWER: média de uma célula de ~50 km no centro do município, não de uma estação.",
    day: "Dia",
    mm: "mm",
  },
  metrics: {
    early_rain_mm_anom_pct: "Chuva set–dez",
    late_rain_mm_anom_pct: "Chuva jan–abr",
    season_rain_mm_anom_pct: "Chuva da safra (set–abr)",
    early_r20_days_anom: "Dias de chuva forte (≥20 mm), set–dez",
    late_cdd_days_anom: "Maior veranico, jan–abr",
    early_rx5_mm_anom_pct: "Maior chuva em 5 dias, set–dez",
    season_gwetroot_anom: "Umidade do solo na raiz",
    season_tmax_c_anom: "Temperatura máxima média",
  } as Record<string, string>,
  units: {
    "%": "% vs. normal",
    days: "dias vs. normal",
    C: "°C vs. normal",
    "0-1": "vs. normal (índice 0–1)",
  } as Record<string, string>,
  explain: {
    climate: (metric: string, cls: string, n: number, value: string, years: string) =>
      `${metric}: nos ${n} anos de ${cls} (${years}), ${value} em relação ao normal.`,
    noYears: (cls: string) => `Nenhum ano de ${cls} no registro deste município.`,
    yield: (crop: string, cls: string, n: number, value: string, years: string) =>
      `${crop}: nos ${n} anos de ${cls} (${years}), a produtividade ficou ${value} da tendência.`,
    smallSample: (n: number) => `Atenção: só ${n} ano(s) — trate como indício, não como regra.`,
  },
  yield: {
    tabsLabel: "Cultura",
    summer: "safra de verão",
    winter: "safra de inverno",
    winterNote:
      "Cultura de inverno: a safra colhida no ano Y é comparada com o ENSO que se forma durante seu ciclo (o do ano-safra Y+1).",
    seriesTitle: (crop: string) => `${crop}: desvio da tendência por ano`,
    compositeTitle: "Média por tipo de ano",
    kgha: "kg/ha",
    trend: "tendência",
    anomaly: "desvio",
  },
  assumption: {
    badge: "Suposição",
    text: (what: string) =>
      `${what} ainda não tem fonte citável (marcado como "suposição" na configuração). Use com cautela.`,
    cropSeason: (crop: string, season: string) => `A janela de cultivo de ${crop} (${season})`,
  },
  chart: {
    showTable: "Ver tabela",
    hideTable: "Ocultar tabela",
    year: "Ano-safra",
    value: "Valor",
    years: "Anos",
    n: "n",
    class: "Tipo de ano",
    season: "Trimestre",
    probability: "Probabilidade",
  },
  map: {
    label: "Mapa dos municípios-piloto",
    pick: "Selecionar",
  },
  provenance: "Fonte",
};

export type Strings = typeof ptBR;

const en: Strings = {
  app: {
    title: "Field Phase",
    tagline: "An El Niño impact preview for your fields, built on NASA, NOAA and IBGE data",
    language: "Language",
    theme: "Theme",
    themeAuto: "Auto",
    themeLight: "Light",
    themeDark: "Dark",
    loading: "Loading data…",
    loadError: "Could not load the data",
    loadErrorHint:
      "Run the pipeline and export the data: `uv run python -m api.export` (or start the API with VITE_DATA_MODE=api).",
    mock: "MOCK DATA",
    footerSources: "Sources and methods",
    footerNoMock: "No mock data on this page.",
  },
  sections: {
    enso: "El Niño now",
    ensoLead: "The official state of the Pacific, from NOAA's Climate Prediction Center.",
    place: "Choose a municipality",
    preview: "Impact preview for this season",
    evidence: "What past strong El Niño years showed",
    evidenceLead:
      "Each kind of year compared with the 1991–2020 average. Every bar says how many years (n) it rests on.",
    yield: "Yield by crop (IBGE PAM)",
    yieldLead: "Yield deviation from the long-term trend, which removes technology gains over the years.",
    rotations: "Recommended rotations",
    rotationsTodo:
      "Not built yet. Rotation scoring (protect soil, conserve water, income stability) is the next stage; this page shows the evidence it will rest on.",
  },
  enso: {
    alert: "Alert",
    issued: (d) => `Discussion of ${d}`,
    next: (d) => `next on ${d}`,
    roni: "RONI (official index)",
    roniSub: (season) => `season ${season}`,
    weekly: "Weekly Niño-3.4",
    weeklySub: (week) => `week of ${week}`,
    oni: (v, s) => `ONI ${s}: ${v} (legacy index, for comparison)`,
    synopsisLabel: "NOAA synopsis (original text)",
    outlookTitle: "Chance of each ENSO state in the coming seasons",
    outlookSub: (issued) => `Official NOAA CPC probabilities, issued ${issued}`,
    historyTitle: "RONI since 1950",
    historySub: "Above +0.5 °C: El Niño. Below −0.5 °C: La Niña.",
    historic: "Historic event (+2.5 °C)",
  },
  classes: {
    el_nino_strong: "Strong El Niño",
    el_nino_moderate: "Weak/moderate El Niño",
    neutral: "Neutral",
    la_nina: "La Niña",
  },
  strength: { none: "below threshold", weak: "weak", moderate: "moderate", strong: "strong", very_strong: "very strong" },
  signal: { excess: "Excess rain under El Niño", deficit: "Rain deficit under El Niño" },
  hazards: {
    waterlogging: "waterlogging",
    erosion: "erosion",
    delayed_planting: "delayed planting",
    harvest_rain: "rain at harvest",
    drought: "drought",
    veranico: "mid-season dry spell",
    late_onset: "late rainy-season onset",
    safrinha_failure: "second-crop failure",
  },
  preview: {
    title: "Rain accumulated since the start of the season",
    sub: (start, last) => `From ${start} to ${last} (latest day published by NASA POWER)`,
    current: "This season",
    baseline: "1991–2020 mean",
    band: "Normal range (10th–90th pct)",
    analog: "Strong El Niño years, mean",
    headline: (mm, pct, normal) =>
      `Since the season started, ${mm} mm of rain has fallen — ${pct} of normal for the date (${normal} mm).`,
    analogLine: (mm, n, years) => `In the ${n} strong El Niño years (${years}), the mean by this date was ${mm} mm.`,
    forecastClass: (cls, p, basis) => `This season is classed as "${cls}" by forecast (${p} chance; ${basis}).`,
    gridNote: "NASA POWER rainfall is a ~50 km grid-cell average at the municipality centre, not a station.",
    day: "Day",
    mm: "mm",
  },
  metrics: {
    early_rain_mm_anom_pct: "Rain Sep–Dec",
    late_rain_mm_anom_pct: "Rain Jan–Apr",
    season_rain_mm_anom_pct: "Season rain (Sep–Apr)",
    early_r20_days_anom: "Heavy-rain days (≥20 mm), Sep–Dec",
    late_cdd_days_anom: "Longest dry spell, Jan–Apr",
    early_rx5_mm_anom_pct: "Wettest 5 days, Sep–Dec",
    season_gwetroot_anom: "Root-zone soil wetness",
    season_tmax_c_anom: "Mean maximum temperature",
  },
  units: { "%": "% vs normal", days: "days vs normal", C: "°C vs normal", "0-1": "vs normal (0–1 index)" },
  explain: {
    climate: (metric, cls, n, value, years) => `${metric}: in the ${n} ${cls} years (${years}), ${value} vs normal.`,
    noYears: (cls) => `No ${cls} years on record for this municipality.`,
    yield: (crop, cls, n, value, years) =>
      `${crop}: in the ${n} ${cls} years (${years}), yield was ${value} from trend.`,
    smallSample: (n) => `Caution: only ${n} year(s) — treat as a hint, not a rule.`,
  },
  yield: {
    tabsLabel: "Crop",
    summer: "summer crop",
    winter: "winter crop",
    winterNote:
      "Winter crop: the harvest of year Y is compared with the ENSO that develops during its cycle (that of crop year Y+1).",
    seriesTitle: (crop) => `${crop}: deviation from trend by year`,
    compositeTitle: "Mean by kind of year",
    kgha: "kg/ha",
    trend: "trend",
    anomaly: "deviation",
  },
  assumption: {
    badge: "Assumption",
    text: (what) => `${what} has no citable source yet (marked "suposicao" in the config). Use with care.`,
    cropSeason: (crop, season) => `The growing window of ${crop} (${season})`,
  },
  chart: {
    showTable: "Show table",
    hideTable: "Hide table",
    year: "Crop year",
    value: "Value",
    years: "Years",
    n: "n",
    class: "Kind of year",
    season: "Season",
    probability: "Probability",
  },
  map: { label: "Map of pilot municipalities", pick: "Select" },
  provenance: "Source",
};

export const STRINGS: Record<Locale, Strings> = { "pt-BR": ptBR, en };
