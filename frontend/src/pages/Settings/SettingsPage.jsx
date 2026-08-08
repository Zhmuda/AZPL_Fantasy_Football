import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../context/AuthContext";
import s from "./SettingsPage.module.css";

export default function SettingsPage() {
  const { t } = useTranslation();
  const { user, changePassword } = useAuth();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => { setForm(f => ({ ...f, [k]: e.target.value })); setSuccess(false); };

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess(false);

    if (form.next.length < 8) {
      setError(t("settings.tooShort"));
      return;
    }
    if (form.next !== form.confirm) {
      setError(t("settings.mismatch"));
      return;
    }

    setLoading(true);
    try {
      await changePassword(form.current, form.next);
      setSuccess(true);
      setForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : t("auth.genericError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={s.page}>
      <div className={s.card}>
        <h1 className={s.heading}>{t("settings.title")}</h1>
        <p className={s.sub}>@{user?.username}</p>

        <form className={s.form} onSubmit={submit}>
          <label className={s.field}>
            <span>{t("settings.currentPassword")}</span>
            <input type="password" value={form.current} onChange={set("current")} required />
          </label>
          <label className={s.field}>
            <span>{t("settings.newPassword")}</span>
            <input type="password" value={form.next} onChange={set("next")} required minLength={8} />
          </label>
          <label className={s.field}>
            <span>{t("settings.confirmPassword")}</span>
            <input type="password" value={form.confirm} onChange={set("confirm")} required minLength={8} />
          </label>

          {error && <div className={s.error}>{error}</div>}
          {success && <div className={s.success}>{t("settings.success")}</div>}

          <button className={s.submit} disabled={loading}>
            {loading ? t("auth.loading") : t("settings.save")}
          </button>
        </form>
      </div>
    </div>
  );
}
