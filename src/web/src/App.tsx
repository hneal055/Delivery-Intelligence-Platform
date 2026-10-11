import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DriversPage } from "./pages/DriversPage";
import { PackagesPage } from "./pages/PackagesPage";
import { SchedulingPage } from "./pages/SchedulingPage";
import { ProofGalleryPage } from "./pages/ProofGalleryPage";
import { TrackingPage } from "./pages/TrackingPage";

// Analytics and Equipment pages are not routed: they have no backend
// endpoints yet and fell back to invented numbers. Re-add them with real data.
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/drivers" element={<DriversPage />} />
          <Route path="/packages" element={<PackagesPage />} />
          <Route path="/scheduling" element={<SchedulingPage />} />
          <Route path="/proofs" element={<ProofGalleryPage />} />
          <Route path="/tracking" element={<TrackingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
