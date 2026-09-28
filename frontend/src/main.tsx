import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { TrevoProvider } from "@trevosdk/react";
import App from "./App";
import "./App.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TrevoProvider apiKey="tsk_live_e9fab74aaa08daadb320fbe21bc6c691">
      <App />
    </TrevoProvider>
  </StrictMode>,
);
