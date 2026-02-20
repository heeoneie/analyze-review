import { createContext, useContext, useState } from 'react';
import { translations } from '../i18n';

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLang] = useState('ko');

  const t = (path) => {
    const keys = path.split('.');
    let val = translations[lang];
    for (const k of keys) val = val?.[k];
    return val ?? path;
  };

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
