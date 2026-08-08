import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Layout/Navbar";
import AuthPage from "./pages/Auth/AuthPage";
import PlayersPage from "./pages/Players/PlayersPage";
import MyTeamPage from "./pages/MyTeam/MyTeamPage";
import LeaderboardPage from "./pages/Leaderboard/LeaderboardPage";

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
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/"            element={<Navigate to="/players" replace />} />
        <Route path="/players"     element={<PlayersPage />} />
        <Route path="/my-team"     element={<MyTeamPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
      </Routes>
    </>
  );
}
