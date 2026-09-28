import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { TrevoProvider } from "@trevosdk/react";
import App from "./App";
import "./App.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TrevoProvider apiKey="tsk_live_8f1ba7fb83a92ce9591066ebc9a7f860">
      <App />
    </TrevoProvider>
  </StrictMode>,
);
