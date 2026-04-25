import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./index.css";
import { Layout } from "./components/Layout";
import HomePage from "./pages/HomePage";
import RunsPage from "./pages/RunsPage";
import RunDetailPage from "./pages/RunDetailPage";
import TargetsPage from "./pages/TargetsPage";
import PipelinesPage from "./pages/PipelinesPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index               element={<HomePage />} />
          <Route path="/targets"     element={<TargetsPage />} />
          <Route path="/pipelines"   element={<PipelinesPage />} />
          <Route path="/runs"        element={<RunsPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
