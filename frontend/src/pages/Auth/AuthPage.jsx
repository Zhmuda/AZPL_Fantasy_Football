import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../context/AuthContext";
import LanguageSwitcher from "../../components/Layout/LanguageSwitcher";
import s from "./AuthPage.module.css";

function extractError(err, t) {
  const detail = err.response?.data?.detail;
  // FastAPI шлёт detail строкой для наших HTTPException, но массивом
  // объектов при 422 (ошибка валидации pydantic) — рендерить массив
  // объектов напрямую роняет React ("Objects are not valid as a child").
  const message = typeof detail === "string"
    ? detail
    : Array.isArray(detail)
      ? detail.map(d => d.msg).filter(Boolean).join(", ")
      : "";
  return message || t("auth.genericError");
}

export default function AuthPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("login");
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register, requestPasswordReset, confirmPasswordReset } = useAuth();
  const navigate = useNavigate();

  const [resetForm, setResetForm] = useState({ email: "", code: "", newPassword: "" });
  const [resetRequestMsg, setResetRequestMsg] = useState("");
  const [resetRequestLoading, setResetRequestLoading] = useState(false);
  const [resetError, setResetError] = useState("");
  const [resetSuccess, setResetSuccess] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));
  const setReset = (k) => (e) => setResetForm(f => ({ ...f, [k]: e.target.value }));

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
      setError(extractError(err, t));
    } finally {
      setLoading(false);
    }
  };

  const openForgot = () => {
    setResetForm({ email: form.email, code: "", newPassword: "" });
    setResetRequestMsg(""); setResetError(""); setResetSuccess(false);
    setTab("forgot");
  };

  const requestCode = async () => {
    setResetError(""); setResetRequestMsg(""); setResetRequestLoading(true);
    try {
      await requestPasswordReset(resetForm.email);
      setResetRequestMsg(t("auth.requestSent"));
    } catch (err) {
      setResetError(extractError(err, t));
    } finally {
      setResetRequestLoading(false);
    }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    setResetError(""); setResetLoading(true);
    try {
      await confirmPasswordReset(resetForm.email, resetForm.code, resetForm.newPassword);
      setResetSuccess(true);
    } catch (err) {
      setResetError(extractError(err, t));
    } finally {
      setResetLoading(false);
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
          <p>{tab === "forgot" ? t("auth.forgotTitle") : t("auth.subtitle")}</p>
        </div>

        {tab !== "forgot" ? (
          <>
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

              {tab === "login" && (
                <button type="button" className={s.linkBtn} onClick={openForgot}>
                  {t("auth.forgotLink")}
                </button>
              )}
            </form>
          </>
        ) : (
          <div className={s.form}>
            <p className={s.hint}>{t("auth.forgotSubtitle")}</p>

            <label className={s.field}>
              <span>{t("auth.email")}</span>
              <input type="email" value={resetForm.email} onChange={setReset("email")} required placeholder={t("auth.emailPlaceholder")} />
            </label>

            <button type="button" className={s.submit} disabled={resetRequestLoading || !resetForm.email} onClick={requestCode}>
              {resetRequestLoading ? t("auth.loading") : t("auth.requestCode")}
            </button>
            {resetRequestMsg && <div className={s.success}>{resetRequestMsg}</div>}

            {resetSuccess ? (
              <div className={s.success}>{t("auth.resetSuccess")}</div>
            ) : (
              <form className={s.form} onSubmit={submitReset}>
                <label className={s.field}>
                  <span>{t("auth.code")}</span>
                  <input value={resetForm.code} onChange={setReset("code")} required placeholder={t("auth.codePlaceholder")} />
                </label>

                <label className={s.field}>
                  <span>{t("auth.newPassword")}</span>
                  <input type="password" value={resetForm.newPassword} onChange={setReset("newPassword")} required placeholder="••••••••" />
                </label>

                {resetError && <div className={s.error}>{resetError}</div>}

                <button className={s.submit} disabled={resetLoading}>
                  {resetLoading ? t("auth.loading") : t("auth.confirmReset")}
                </button>
              </form>
            )}

            <button type="button" className={s.linkBtn} onClick={() => setTab("login")}>
              {t("auth.backToLogin")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
