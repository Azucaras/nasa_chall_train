/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DATA_MODE?: "static" | "api";
  readonly VITE_DATA_BASE?: string;
  readonly VITE_BASEMAP_TILES?: string;
  readonly VITE_BASEMAP_ATTRIBUTION?: string;
}
