import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import CatalogCreate from "./pages/CatalogCreate";
import CatalogPreview from "./pages/CatalogPreview";
import QualityCheck from "./pages/QualityCheck";
import PriceCalculator from "./pages/PriceCalculator";
import ExportPage from "./pages/ExportPage";
import { useAuthStore } from "./stores/authStore";

function Protected({ children }) {
  const token = useAuthStore((s) => s.token);
  return token ? children : <Navigate to="/onboarding" replace />;
}

export default function App() {
  return (
    <div className="min-h-full">
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/pricing" element={<PriceCalculator />} />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route
          path="/catalog/new"
          element={
            <Protected>
              <CatalogCreate />
            </Protected>
          }
        />
        <Route
          path="/catalog/:id"
          element={
            <Protected>
              <CatalogPreview />
            </Protected>
          }
        />
        <Route
          path="/quality/:id"
          element={
            <Protected>
              <QualityCheck />
            </Protected>
          }
        />
        <Route
          path="/export/:id"
          element={
            <Protected>
              <ExportPage />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
