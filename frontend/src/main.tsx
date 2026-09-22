import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { TrevoProvider } from "@trevosdk/react";
import App from "./App";
import "./App.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TrevoProvider apiKey={import.meta.env.VITE_TREVO_API_KEY}>
      <App />
    </TrevoProvider>
  </StrictMode>,
);
