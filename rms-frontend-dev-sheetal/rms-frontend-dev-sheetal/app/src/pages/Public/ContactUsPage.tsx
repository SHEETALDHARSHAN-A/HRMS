// rms-frontend-dev-sheetal/app/src/pages/Public/ContactUsPage.tsx
import React, { useState } from 'react';
import PublicLayout from '../../components/layout/PublicLayout';
import Button from '../../components/common/Button';
import { Mail, Phone, MapPin, Send, Loader2, CheckCircle } from 'lucide-react';

const ContactUsPage: React.FC = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // Placeholder submit handler
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSubmitted(true);
    }, 1500);
  };

  return (
    <PublicLayout
      bannerTitle="Contact Us"
      bannerSubtitle="We're here to help."
      // 💡 Hide the hero content to use a card-based layout
      showHeroContent={false} 
    >
      <div className="bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12">
          
          {/* Column 1: Contact Info */}
          <div className="lg:col-span-5 bg-gray-50 p-8 md:p-12">
            {/* 💡 Added a page title here */}
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Contact Us</h1>
            <p className="text-lg text-gray-500 mb-8">We're here to help. Reach out with any questions.</p>
            
            <div className="space-y-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-100 text-[var(--color-primary-500)] rounded-full flex items-center justify-center">
                  <Mail size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800">Email</h4>
                  <p className="text-gray-600 text-sm">contact@prayag.ai</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-100 text-[var(--color-primary-500)] rounded-full flex items-center justify-center">
                  <Phone size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800">Phone</h4>
                  <p className="text-gray-600 text-sm">+91 123 456 7890</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-100 text-[var(--color-primary-500)] rounded-full flex items-center justify-center">
                  <MapPin size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-800">Office</h4>
                  <p className="text-gray-600 text-sm">123 Innovation Drive, Tech Park, Bangalore, 560100</p>
                </div>
              </div>
            </div>
          </div>

          {/* Column 2: Contact Form */}
          <div className="lg:col-span-7 p-8 md:p-12">
            {isSubmitted ? (
              <div className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <CheckCircle size={48} className="text-green-500" />
                <h3 className="text-2xl font-semibold text-gray-800 mt-4">Thank You!</h3>
                <p className="text-gray-600 mt-2">Your message has been sent. We'll get back to you soon.</p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                 <h2 className="text-2xl font-bold text-gray-900 mb-6">Send us a message</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                    <input type="text" id="name" name="name" required className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
                  </div>
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input type="email" id="email" name="email" required className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
                  </div>
                </div>
                <div>
                  <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                  <input type="text" id="subject" name="subject" required className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
                </div>
                <div>
                  <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-1">Message</label>
                  <textarea id="message" name="message" rows={5} required className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"></textarea>
                </div>
                <div>
                  <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto py-3 px-8 text-base">
                    {isSubmitting ? (
                      <Loader2 size={20} className="animate-spin" />
                    ) : (
                      <Send size={18} />
                    )}
                    <span>{isSubmitting ? 'Sending...' : 'Send Message'}</span>
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};

export default ContactUsPage;