import { useTranslation } from "react-i18next";
import s from "./Footer.module.css";

const SUPPORT_EMAIL = "droninfly@gmail.com";

// VK/Telegram URLs are placeholders until the real community pages exist —
// disabled links with a tooltip instead of guessed/fake URLs.
export default function Footer() {
  const { t } = useTranslation();

  return (
    <footer className={s.footer}>
      <div className={s.inner}>
        <div className={s.brand}>
          <span className={s.logo}>⚽</span>
          <span className={s.title}>{t("nav.brand")}</span>
        </div>

        <div className={s.links}>
          <a href={`mailto:${SUPPORT_EMAIL}`} className={s.link}>
            {t("footer.support")}
          </a>
          <a href="/rules" className={s.link}>{t("nav.rules")}</a>
          <span className={s.linkDisabled} title={t("footer.comingSoon")}>
            {t("footer.vk")}
          </span>
          <span className={s.linkDisabled} title={t("footer.comingSoon")}>
            {t("footer.telegram")}
          </span>
        </div>

        <div className={s.copy}>{t("footer.copy", { year: new Date().getFullYear() })}</div>
      </div>
    </footer>
  );
}
