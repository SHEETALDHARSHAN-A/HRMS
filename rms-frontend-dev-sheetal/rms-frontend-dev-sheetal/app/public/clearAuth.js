/**
 * Emergency Auth Reset Script
 * 
 * Run this in the browser console if you need to manually clear all authentication data
 * 
 * Usage:
 * 1. Open browser DevTools (F12)
 * 2. Go to Console tab
 * 3. Copy and paste this entire script
 * 4. Press Enter
 * 
 * Or simply call: window.clearAuthData()
 */

(function() {
  // Make it globally available
  window.clearAuthData = function() {
    console.log('🔄 Starting authentication data cleanup...');
    
    // Clear localStorage
    console.log('📦 Clearing localStorage...');
    const localStorageKeys = ['user', 'authToken', 'refreshToken'];
    localStorageKeys.forEach(key => {
      if (localStorage.getItem(key)) {
        localStorage.removeItem(key);
        console.log(`  ✅ Removed: ${key}`);
      }
    });
    
    // Clear sessionStorage
    console.log('📦 Clearing sessionStorage...');
    const sessionStorageKeys = ['authEmail', 'authStep', 'rememberMe'];
    sessionStorageKeys.forEach(key => {
      if (sessionStorage.getItem(key)) {
        sessionStorage.removeItem(key);
        console.log(`  ✅ Removed: ${key}`);
      }
    });
    
    // Clear all cookies
    console.log('🍪 Clearing all cookies...');
    const cookies = document.cookie.split(";");
    cookies.forEach((cookie) => {
      const cookieName = cookie.split("=")[0].trim();
      // Set cookie to expire in the past to delete it
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
      console.log(`  ✅ Removed cookie: ${cookieName}`);
    });
    
    console.log('✨ All authentication data cleared!');
    console.log('🔄 Redirecting to login page...');
    
    // Redirect after a short delay
    setTimeout(() => {
      window.location.href = '/auth';
    }, 1000);
  };
  
  console.log('✅ Emergency auth reset function loaded!');
  console.log('💡 To clear all auth data, run: window.clearAuthData()');
})();

// Auto-run if you want immediate cleanup
// Uncomment the line below to auto-execute on paste
// window.clearAuthData();
