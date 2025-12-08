// rms-frontend-dev-sheetal/app/src/components/auth/AuthLeftPanel.tsx
// No structural changes needed for responsiveness, but added comments

import React from 'react';
import leftPanelBackground from '../../assets/leftPanelBackground.png';

const AuthLeftPanel: React.FC = () => {
  return (
    <div
      // --- RESPONSIVENESS ---
      // `hidden`: Hidden by default (on mobile).
      // `lg:flex`: Becomes a flex container ONLY on large screens and up.
      // `lg:flex-1`: Takes up available space on large screens.
      className="lg:flex-1 p-8 sm:p-12 flex flex-col justify-center relative overflow-hidden hidden lg:flex"
      style={{
        minHeight: '100vh', // Ensures it takes full viewport height when visible
        backgroundImage: `url(${leftPanelBackground})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        // Rounded corners only visible on larger screens where the panel appears
        borderTopRightRadius: '15px',
        borderBottomRightRadius: '15px',
      }}
    >
      {/* Background Overlay */}
      <div
        className="absolute inset-0 opacity-70"
        style={{
          backgroundImage: 'linear-gradient(360deg, rgba(30, 28, 38, 1) 23%, rgba(30, 28, 38, 0.5) 85%, rgba(30, 28, 38, 0) 100%), radial-gradient(at 10% 90%, #58468C 0%, transparent 50%), radial-gradient(at 90% 10%, #929BFF 0%, transparent 50%)',
          backgroundColor: 'rgba(30, 28, 38, 0.5)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 w-full max-w-xl mx-auto xl:mx-0">
        <div className="mb-8 sm:mb-10 w-full">
            {/* Text sizes adjusted slightly with sm: prefix for consistency */}
            <h1 className="font-extrabold text-white leading-tight text-3xl sm:text-4xl md:text-5xl" style={{ fontFamily: 'Raleway' }}>
                AI-Powered
            </h1>
            <h1
                className="font-extrabold leading-tight mt-1 text-gradient-hero text-3xl sm:text-4xl md:text-5xl"
                style={{ fontFamily: 'Raleway' }}
            >
                Recruitment Management System
            </h1>
        </div>

        {/* Text sizes adjusted slightly with sm: prefix */}
        <p className="text-white font-normal leading-relaxed text-sm sm:text-base mt-6 sm:mt-8 w-full max-w-lg" style={{ fontFamily: 'Poppins' }}>
          An intelligent recruitment platform designed to streamline every stage of hiring—from candidate sourcing and smart shortlisting to automated screening and seamless onboarding—empowering organizations to hire top talent faster and with greater precision.
        </p>
      </div>
    </div>
  );
};

export default AuthLeftPanel;