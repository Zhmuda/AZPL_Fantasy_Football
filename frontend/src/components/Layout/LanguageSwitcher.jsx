import { useTranslation } from "react-i18next";
import s from "./Navbar.module.css";

const LANGS = [
  { code: "ru", label: "RU" },
  { code: "en", label: "EN" },
  { code: "az", label: "AZ" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language?.split("-")[0] || "ru";

  return (
    <select
      className={s.langSelect}
      value={LANGS.some(l => l.code === current) ? current : "ru"}
      onChange={e => i18n.changeLanguage(e.target.value)}
      aria-label="Language"
    >
      {LANGS.map(l => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
