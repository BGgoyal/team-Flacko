import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import Layout from "./components/Layout";
import Assets from "./pages/Assets";
import Auth from "./pages/Auth";
import Budget from "./pages/Budget";
import Coach from "./pages/Coach";
import Goals from "./pages/Goals";
import Overview from "./pages/Overview";
import Profile from "./pages/Profile";
import Welcome from "./pages/Welcome";

export type SessionUser = {
  id: number;
  email: string | null;
  phone: string | null;
  name: string;
  has_profile: boolean;
};

export default function App() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);
  const location = useLocation();

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, [location.pathname]);

  if (!ready) {
    return (
      <div className="app-shell">
        <p className="kicker">FinCoach</p>
        <p>Loading session…</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.has_profile ? "/overview" : "/welcome"} replace /> : <Auth onAuthed={setUser} />} />
      <Route
        path="/"
        element={
          user ? (
            <Layout user={user} onLogout={() => setUser(null)} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      >
        <Route index element={<Navigate to={user?.has_profile ? "/overview" : "/welcome"} replace />} />
        <Route path="welcome" element={<Welcome onSaved={() => setUser((u) => (u ? { ...u, has_profile: true } : u))} />} />
        <Route path="overview" element={<Overview />} />
        <Route path="budget" element={<Budget />} />
        <Route path="goals" element={<Goals />} />
        <Route path="assets" element={<Assets />} />
        <Route path="coach" element={<Coach />} />
        <Route path="profile" element={<Profile user={user!} onUpdated={setUser} />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
