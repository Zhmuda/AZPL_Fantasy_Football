import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Layout/Navbar";
import Footer from "./components/Layout/Footer";
import BackgroundDecor from "./components/BackgroundDecor";
import AuthPage from "./pages/Auth/AuthPage";
import PlayersPage from "./pages/Players/PlayersPage";
import MyTeamPage from "./pages/MyTeam/MyTeamPage";
import LeaderboardPage from "./pages/Leaderboard/LeaderboardPage";
import SettingsPage from "./pages/Settings/SettingsPage";
import RulesPage from "./pages/Rules/RulesPage";
import LeaguesPage from "./pages/Leagues/LeaguesPage";

export default function App() {
  return (
    <AuthProvider>
      <BackgroundDecor />
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
      <div style={{ flex: 1 }}>
        <Routes>
          <Route path="/"            element={<Navigate to="/players" replace />} />
          <Route path="/players"     element={<PlayersPage />} />
          <Route path="/my-team"     element={<MyTeamPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/settings"    element={<SettingsPage />} />
          <Route path="/rules"       element={<RulesPage />} />
          <Route path="/leagues"     element={<LeaguesPage />} />
        </Routes>
      </div>
      <Footer />
    </>
  );
}
