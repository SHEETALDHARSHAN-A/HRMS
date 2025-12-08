// src/components/layout/PublicLayout.tsx

import React, { useState } from 'react';
import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Search } from 'lucide-react';
// --- UPDATED: Use the correct logo.svg path ---
import appLogo from '../../assets/logo.svg'; 
import AdvancedSearchBar from '../common/AdvancedSearchBar';

interface PublicLayoutProps {
  children: ReactNode;
  bannerTitle: string;
  bannerSubtitle: string;
  showHeroContent?: boolean;
}

const PublicLayout: React.FC<PublicLayoutProps> = ({
  children,
  bannerTitle,
  bannerSubtitle,
  showHeroContent = true,
}) => {
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleSearchClick = () => {
    setShowAdvancedSearch(true);
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <style>{`
        /* Import Poppins font */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
        
        .font-poppins {
          font-family: 'Poppins', sans-serif;
        }
        
        /* Custom navigation styling to match PRAYAG.AI */
        .nav-container {
          font-family: 'Poppins', sans-serif;
          font-size: 16px;
          color: #333333;
        }
        
        .nav-link-active {
          background-color: #FF4D00 !important;
          color: #FFFFFF !important;
          border-radius: 6px;
          padding: 8px 16px;
        }
        
        .nav-link-mobile-active {
          background-color: #FF4D00 !important;
          color: #FFFFFF !important;
        }
        
        .nav-link-hover:hover {
          color: #FF4D00;
          background-color: rgba(255, 77, 0, 0.1);
        }
        
        @keyframes slideIn {
          from { transform: scaleX(0); }
          to { transform: scaleX(1); }
        }
      `}</style>
      
      {/* --- ENHANCED: Header / Navbar --- */}
      {/*
        - BUG FIX: Added `sticky top-0 z-40` to fix the overlap bug.
        - DESIGN: Replaced `shadow-sm` with `border-b` for a cleaner design.
      */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50 transition-colors shadow-sm">
        <nav className="container mx-auto px-4 sm:px-6 lg:px-8 nav-container">
          <div className="flex items-center justify-between h-20 gap-6">

            {/* --- UPDATED: Logo --- */}
            <Link to="/" className="flex-shrink-0 flex items-center gap-3">
              <img className="h-10 w-auto" src={appLogo} alt="PRAYAG.AI" />
            </Link>

            {/* --- CENTERED: Main Navigation --- */}
            <div className="hidden md:flex items-center space-x-2 flex-1 justify-center">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  isActive 
                    ? 'nav-link-active px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-white shadow-sm'
                    : 'px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-gray-700 dark:text-gray-300 nav-link-hover'
                }
              >
                Home
              </NavLink>
              <NavLink
                to="/services"
                className={({ isActive }) =>
                  isActive 
                    ? 'nav-link-active px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-white shadow-sm'
                    : 'px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-gray-700 dark:text-gray-300 nav-link-hover'
                }
              >
                Services
              </NavLink>
              <NavLink
                to="/story"
                className={({ isActive }) =>
                  isActive 
                    ? 'nav-link-active px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-white shadow-sm'
                    : 'px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-gray-700 dark:text-gray-300 nav-link-hover'
                }
              >
                Story
              </NavLink>
              <NavLink
                to="/contact"
                className={({ isActive }) =>
                  isActive 
                    ? 'nav-link-active px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-white shadow-sm'
                    : 'px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-gray-700 dark:text-gray-300 nav-link-hover'
                }
              >
                Contact
              </NavLink>
              <NavLink
                to="/career-page"
                className={({ isActive }) =>
                  isActive 
                    ? 'nav-link-active px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-white shadow-sm'
                    : 'px-4 py-2 text-base font-poppins font-medium transition-all duration-200 rounded-md text-gray-700 dark:text-gray-300 nav-link-hover'
                }
              >
                Careers
              </NavLink>
            </div>

            <div className="flex items-center gap-3">
              {/* Mobile menu button */}
              <button 
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2 text-gray-700 hover:text-orange-500 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {isMobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>
          
          {/* Mobile Navigation Menu */}
          {isMobileMenuOpen && (
            <div className="md:hidden border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
              <div className="px-4 py-2 space-y-1">
                <NavLink
                  to="/"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive 
                      ? 'nav-link-mobile-active block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-white'
                      : 'block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-gray-700 dark:text-gray-300 nav-link-hover'
                  }
                >
                  Home
                </NavLink>
                <NavLink
                  to="/services"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive 
                      ? 'nav-link-mobile-active block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-white'
                      : 'block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-gray-700 dark:text-gray-300 nav-link-hover'
                  }
                >
                  Services
                </NavLink>
                <NavLink
                  to="/story"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive 
                      ? 'nav-link-mobile-active block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-white'
                      : 'block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-gray-700 dark:text-gray-300 nav-link-hover'
                  }
                >
                  Story
                </NavLink>
                <NavLink
                  to="/contact"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive 
                      ? 'nav-link-mobile-active block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-white'
                      : 'block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-gray-700 dark:text-gray-300 nav-link-hover'
                  }
                >
                  Contact
                </NavLink>
                <NavLink
                  to="/career-page"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    isActive 
                      ? 'nav-link-mobile-active block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-white'
                      : 'block px-4 py-3 text-base font-poppins font-medium rounded-lg transition-colors text-gray-700 dark:text-gray-300 nav-link-hover'
                  }
                >
                  Careers
                </NavLink>
              </div>
            </div>
          )}
        </nav>
      </header>

      {/* --- Main Content Area --- */}
      <main className="flex-grow">
        {/* Hero Section */}
        {showHeroContent && (
          <div className={`relative z-10 bg-gradient-to-r from-[var(--color-primary-600)] to-[var(--color-primary-400)] dark:from-gray-900 dark:to-gray-800 text-white ${showAdvancedSearch ? 'min-h-[500px] py-16' : 'min-h-[400px] py-12'} flex flex-col items-center justify-center px-4 transition-all duration-300`}>
            <div className={`text-center ${showAdvancedSearch ? 'mb-12' : 'mb-8'} transition-all duration-300`}>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">{bannerTitle}</h1>
              <p className="text-lg md:text-xl opacity-90 mb-6">{bannerSubtitle}</p>
              
              {/* Search Button or Advanced Search Bar */}
              {!showAdvancedSearch ? (
                <div className="animate-in fade-in duration-300">
                  <button
                    onClick={handleSearchClick}
                    className="inline-flex items-center gap-3 bg-white text-[var(--color-primary-600)] font-semibold px-8 py-4 rounded-full shadow-lg hover:bg-gray-100 transition-all transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-[var(--color-primary-500)] dark:bg-gray-100 dark:hover:bg-gray-200"
                  >
                    <Search size={20} />
                    <span>Search Open Roles</span>
                  </button>
                  
                  {/* Helper text */}
                  <p className="mt-4 text-white/80 text-sm">
                    Find opportunities by role, location, or skills
                  </p>
                </div>
              ) : (
                <div className="w-full max-w-6xl">
                  <div className="animate-in slide-in-from-top-4 fade-in duration-500">
                    <AdvancedSearchBar onCollapse={() => setShowAdvancedSearch(false)} />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Page Content (Job List) */}
        {/*
          - Fixed margin to prevent navbar overlap
          - Added proper top padding for navbar clearance
        */}
  <div className="container mx-auto px-4 sm:px-6 lg:px-8 pt-8 relative pb-24">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 min-h-[200px]">
            {children}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">&copy; {new Date().getFullYear()} PRAYAG. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default PublicLayout;