import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../context/AuthContext";
import LanguageSwitcher from "../../components/Layout/LanguageSwitcher";
import s from "./AuthPage.module.css";

export default function AuthPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (tab === "login") {
        await login(form.email, form.password);
      } else {
        await register(form.email, form.username, form.password);
      }
      navigate("/players");
    } catch (err) {
      const detail = err.response?.data?.detail;
      // FastAPI шлёт detail строкой для наших HTTPException, но массивом
      // объектов при 422 (ошибка валидации pydantic) — рендерить массив
      // объектов напрямую роняет React ("Objects are not valid as a child").
      const message = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map(d => d.msg).filter(Boolean).join(", ")
          : "";
      setError(message || t("auth.genericError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={s.page}>
      <div className={s.card}>
        <div className={s.langRow}>
          <LanguageSwitcher />
        </div>
        <div className={s.header}>
          <span className={s.emoji}>⚽</span>
          <h1>{t("auth.title")}</h1>
          <p>{t("auth.subtitle")}</p>
        </div>

        <div className={s.tabs}>
          <button className={tab === "login" ? s.activeTab : s.tab} onClick={() => setTab("login")}>
            {t("auth.loginTab")}
          </button>
          <button className={tab === "register" ? s.activeTab : s.tab} onClick={() => setTab("register")}>
            {t("auth.registerTab")}
          </button>
        </div>

        <form className={s.form} onSubmit={submit}>
          <label className={s.field}>
            <span>{t("auth.email")}</span>
            <input type="email" value={form.email} onChange={set("email")} required placeholder={t("auth.emailPlaceholder")} />
          </label>

          {tab === "register" && (
            <label className={s.field}>
              <span>{t("auth.username")}</span>
              <input value={form.username} onChange={set("username")} required placeholder={t("auth.usernamePlaceholder")} />
            </label>
          )}

          <label className={s.field}>
            <span>{t("auth.password")}</span>
            <input type="password" value={form.password} onChange={set("password")} required placeholder="••••••••" />
          </label>

          {error && <div className={s.error}>{error}</div>}

          <button className={s.submit} disabled={loading}>
            {loading ? t("auth.loading") : tab === "login" ? t("auth.submitLogin") : t("auth.submitRegister")}
          </button>
        </form>
      </div>
    </div>
  );
}
