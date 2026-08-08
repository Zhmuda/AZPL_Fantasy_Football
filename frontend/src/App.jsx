import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Layout/Navbar";
import AuthPage from "./pages/Auth/AuthPage";
import PlayersPage from "./pages/Players/PlayersPage";
import MyTeamPage from "./pages/MyTeam/MyTeamPage";
import LeaderboardPage from "./pages/Leaderboard/LeaderboardPage";
import SettingsPage from "./pages/Settings/SettingsPage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route path="*" element={<Layout />} />
      </Routes>
    </AuthProvider>
  );
}

function Layout() {
  const { user, loading } = useAuth();

  // Ждём, пока AuthContext проверит токен из localStorage — иначе успеем
  // мигнуть редиректом на /auth даже для уже залогиненного пользователя.
  if (loading) return null;

  if (!user) return <Navigate to="/auth" replace />;

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/"            element={<Navigate to="/players" replace />} />
        <Route path="/players"     element={<PlayersPage />} />
        <Route path="/my-team"     element={<MyTeamPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/settings"    element={<SettingsPage />} />
      </Routes>
    </>
  );
}
