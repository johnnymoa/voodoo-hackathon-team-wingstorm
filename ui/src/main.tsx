import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./index.css";
import { Layout } from "./components/Layout";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import TargetsPage from "./pages/TargetsPage";
import ReferencePage from "./pages/ReferencePage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/runs" replace />} />
          <Route path="/runs"          element={<RunsPage />} />
          <Route path="/runs/:runId"   element={<RunDetailPage />} />
          <Route path="/targets"       element={<TargetsPage />} />
          <Route path="/reference"     element={<ReferencePage />} />
          <Route path="*" element={<Navigate to="/runs" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
