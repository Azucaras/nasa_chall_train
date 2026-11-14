import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./fieldphase/theme/fieldphase.css";
import "./app/page.css";
import App from "./app/App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="fp-root">
      <App />
    </div>
  </StrictMode>,
);
