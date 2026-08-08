import { NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../context/AuthContext";
import LanguageSwitcher from "./LanguageSwitcher";
import s from "./Navbar.module.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleLogout = () => { logout(); navigate("/auth"); };

  return (
    <nav className={s.nav}>
      <div className={s.brand}>
        <span className={s.logo}>⚽</span>
        <span className={s.title}>{t("nav.brand")}</span>
      </div>

      <div className={s.links}>
        <NavLink to="/players" className={({ isActive }) => isActive ? s.active : ""}>
          {t("nav.players")}
        </NavLink>
        {user && (
          <NavLink to="/my-team" className={({ isActive }) => isActive ? s.active : ""}>
            {t("nav.myTeam")}
          </NavLink>
        )}
        <NavLink to="/leaderboard" className={({ isActive }) => isActive ? s.active : ""}>
          {t("nav.leaderboard")}
        </NavLink>
      </div>

      <div className={s.right}>
        <LanguageSwitcher />
        {user ? (
          <>
            <NavLink to="/settings" className={s.username}>@{user.username}</NavLink>
            <button className={s.btn} onClick={handleLogout}>{t("nav.logout")}</button>
          </>
        ) : (
          <button className={s.btnPrimary} onClick={() => navigate("/auth")}>{t("nav.login")}</button>
        )}
      </div>
    </nav>
  );
}
