import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import ru from "./locales/ru.json";
import en from "./locales/en.json";
import az from "./locales/az.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ru: { translation: ru },
      en: { translation: en },
      az: { translation: az },
    },
    fallbackLng: "ru",
    supportedLngs: ["ru", "en", "az"],
    nonExplicitSupportedLngs: true,
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "lang",
      caches: ["localStorage"],
    },
    interpolation: { escapeValue: false },
  })
  .then(() => {
    document.documentElement.lang = i18n.language?.split("-")[0] || "ru";
  });

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng?.split("-")[0] || "ru";
});

export default i18n;
