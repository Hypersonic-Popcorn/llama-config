import { createContext, useContext, useState, useEffect } from "react";

/* eslint-disable react-refresh/only-export-components */
const DarkModeContext = createContext();

function getSystemPreference() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function DarkModeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(() => getSystemPreference());

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e) => setDarkMode(e.matches);
    const cleanup = () => mediaQuery.removeEventListener("change", handler);
    mediaQuery.addEventListener("change", handler);
    return cleanup;
  }, []);

  useEffect(() => {
    document.body.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const value = { darkMode, setDarkMode };

  return (
    <DarkModeContext.Provider value={value}>
      {children}
    </DarkModeContext.Provider>
  );
}

export function useDarkMode() {
  return useContext(DarkModeContext);
}
