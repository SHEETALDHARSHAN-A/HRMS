// rms-frontend-dev-sheetal/app/src/pages/Public/AboutUsPage.tsx
import React from 'react';
import PublicLayout from '../../components/layout/PublicLayout';
import { Building, Target, Eye } from 'lucide-react';

const AboutUsPage: React.FC = () => {
  return (
    <PublicLayout
      // 💡 Title/Subtitle are now passed but will be hidden
      bannerTitle="About "
      bannerSubtitle="Innovation and Excellence in Recruitment Technology"
      // 💡 NEW: This prop hides the hero text for a cleaner static page
      showHeroContent={false} 
    >
      {/* 💡 We add our own card and title *inside* the main content */}
      <div className="bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden">
        {/* Hero Image Section (Placeholder) */}
        <div className="h-64 bg-gradient-to-r from-blue-100 via-indigo-100 to-blue-200 flex items-center justify-center">
          <Building size={64} className="text-[var(--color-primary-500)] opacity-50" />
        </div>
        
        <div className="p-8 md:p-12">
          {/* Page Title */}
          <section className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">About Us</h1>
            <p className="text-lg text-gray-500">Innovation and Excellence in Recruitment Technology</p>
          </section>

          {/* Our Story Section */}
          <section>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Our Story</h2>
            <p className="text-gray-600 leading-relaxed mb-4">
              Founded on the principle of innovation, Our company was born from a desire to solve the most persistent challenges in talent acquisition. We saw brilliant candidates getting lost in outdated systems and talented recruiters spending more time on administrative tasks than on human connection.
            </p>
            <p className="text-gray-600 leading-relaxed">
              We set out to build an intelligent, AI-powered platform that streamlines the entire recruitment lifecycle—from smart sourcing and automated screening to seamless onboarding. Our mission is to empower organizations to hire top talent faster, with greater precision, and a better experience for everyone involved.
            </p>
          </section>

          {/* (Rest of the content is the same) */}
          <section className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <div className="flex items-center gap-3 mb-3">
                <Target size={24} className="text-[var(--color-accent-orange)]" />
                <h3 className="text-xl font-semibold text-gray-800">Our Mission</h3>
              </div>
              <p className="text-gray-600 text-sm">
                To revolutionize recruitment by seamlessly integrating artificial intelligence, creating an efficient, fair, and human-centric hiring process for companies and candidates worldwide.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
              <div className="flex items-center gap-3 mb-3">
                <Eye size={24} className="text-[var(--color-primary-500)]" />
                <h3 className="text-xl font-semibold text-gray-800">Our Vision</h3>
              </div>
              <p className="text-gray-600 text-sm">
                To be the world's most intelligent and trusted platform for connecting exceptional talent with outstanding opportunities, fostering growth for individuals and organizations alike.
              </p>
            </div>
          </section>
        </div>
      </div>
    </PublicLayout>
  );
};

export default AboutUsPage;