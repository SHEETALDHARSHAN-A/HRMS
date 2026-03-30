// src/context/ThemeContext.tsx

import React, { createContext, useContext, useEffect } from 'react';

interface ThemeContextType {
  isDarkMode: boolean;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

interface ThemeProviderProps {
  children: React.ReactNode;
}

// Dark mode has been intentionally removed. This provider keeps the
// Theme API surface but forces light mode and a no-op toggle so existing
// imports/components won't break.
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const isDarkMode = false;
  const toggleTheme = () => {
    // no-op: dark mode disabled
    return;
  };

  useEffect(() => {
    // Ensure any leftover class or color-scheme is cleared on mount
    try {
      document.documentElement.classList.remove('dark');
      document.documentElement.style.colorScheme = 'light';
    } catch {
      // ignore (server-side rendering or restricted env)
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};