import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { TrevoProvider } from "@trevosdk/react";
import App from "./App";
import "./App.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TrevoProvider apiKey="tsk_live_668841ab3e40f69e96051f8c29cf3af0">
      <App />
    </TrevoProvider>
  </StrictMode>,
);
