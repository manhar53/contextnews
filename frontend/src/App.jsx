import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Auth from "./pages/Auth.jsx";
import Onboarding from "./pages/Onboarding.jsx";
import Home from "./pages/Home.jsx";
import NewsDetail from "./pages/NewsDetail.jsx";

export default function App() {
  const { user, ready, setOnboarded } = useAuth();

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted">
        Loading ContextNews…
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<Auth />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route
        path="/"
        element={user.onboarded ? <Home /> : <Navigate to="/onboarding" replace />}
      />
      <Route
        path="/onboarding"
        element={<Onboarding onDone={() => setOnboarded(true)} />}
      />
      <Route path="/news/:id" element={<NewsDetail />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
