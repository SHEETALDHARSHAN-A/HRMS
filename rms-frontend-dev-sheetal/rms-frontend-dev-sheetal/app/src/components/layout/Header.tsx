import { Search, Bell, ChevronDown, LogOut, Menu, X, CheckCheck, Trash2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useUser } from "../../context/UserContext";
import { useModal } from "../../context/ModalContext"; // 💡 CHANGE: Import useModal
import { useNotifications } from "../../context/NotificationContext";

interface HeaderProps {
  searchPlaceholder: string;
  onToggleSidebar?: () => void;
  sidebarOpen?: boolean;
}

export default function Header({ searchPlaceholder, onToggleSidebar, sidebarOpen }: HeaderProps) {
  const { user, logout } = useUser();
  const { showConfirm, setModalProcessing, showToast } = useModal(); // use confirm modal, processing state and toast
  const { notifications, unreadCount, markAsRead, markAllAsRead, deleteNotification } = useNotifications();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notificationRef = useRef<HTMLDivElement>(null);
  const firstDropdownItemRef = useRef<HTMLButtonElement | null>(null);

  const toggleDropdown = () => {
    setIsDropdownOpen(prev => !prev);
  };
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsNotificationOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close dropdown on Escape key for accessibility
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsDropdownOpen(false);
        setIsNotificationOpen(false);
      }
    };
    if (isDropdownOpen || isNotificationOpen) document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isDropdownOpen, isNotificationOpen]);

  const handleLogout = async () => {
      const confirmed = await showConfirm({
          title: "Confirm Logout",
          message: "Are you sure you want to end your session? You will need to sign in again.",
          confirmText: "Logout",
          isDestructive: true,
      });

      if (confirmed) {
          await logout();
      }
  }

  // Generate avatar dynamically based on initials (Logic unchanged)
  const initials = `${user?.first_name?.[0] || 'U'}${user?.last_name?.[0] || 'S'}`.toUpperCase();
  const userAvatar = `https://ui-avatars.com/api/?name=${encodeURIComponent(
          initials
        )}&background=016BAE&color=fff&size=40`; 
  
  const userName = user 
    ? `${user.first_name} ${user.last_name}`.trim() 
    : 'User';

  const formatRole = (value: unknown) => {
    if (!value) return 'Role unknown';
    const roleValue = Array.isArray(value) ? value[0] : value;
    if (typeof roleValue !== 'string') return 'Role unknown';
    return roleValue
      .split('_')
      .map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(' ');
  };

  const userRole = user?.role ?? 'Role unknown';
  const roleLabel = formatRole(userRole);
  const userEmail = user?.email ?? '';

  useEffect(() => {
    if (isDropdownOpen && firstDropdownItemRef.current) {
      firstDropdownItemRef.current.focus();
    }
  }, [isDropdownOpen]);

  return (
    <header 
        className="h-[var(--header-height)] bg-white shadow-md flex items-center justify-between px-4 sm:px-6 sticky top-0 z-10 w-full"
    >
      {/* Mobile: sidebar toggle */}
      <div className="flex items-center lg:hidden mr-2">
        <button
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          className="p-2 rounded-md hover:bg-gray-100 focus:outline-none"
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>
      {/* Left: Search Bar - Responsive width */}
      <div className="flex items-center gap-2 w-full max-w-xs md:max-w-md rounded-full py-2 px-3 focus-within:ring-2 focus-within:ring-[var(--color-primary-500)] transition-colors duration-200 bg-white shadow-sm border border-gray-100">
        <Search size={16} className="text-gray-400" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          aria-label="Search"
          className="w-full border-none outline-none text-sm text-gray-700 placeholder-gray-400 bg-transparent"
        />
      </div>

      {/* Right: User and Icons */}
      <div className="flex items-center gap-4 relative" ref={dropdownRef}>
        {/* Bell Icon with Notification */}
        <div className="relative hidden sm:block" ref={notificationRef}>
          <div 
            className="cursor-pointer p-2 rounded-full hover:bg-gray-100 transition-colors" 
            title="Notifications"
            onClick={() => setIsNotificationOpen(!isNotificationOpen)}
          >
            <Bell size={20} className="text-gray-500" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-5 w-5 bg-red-500 text-white text-xs rounded-full border border-white flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </div>

          {/* Notification Dropdown */}
          {isNotificationOpen && (
            <div className="absolute top-12 right-0 bg-white shadow-xl border border-gray-100 rounded-lg overflow-hidden z-20 w-80 max-h-96 animate-in slide-in-from-top-1">
              <div className="p-4 border-b border-gray-100">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium text-gray-900">Notifications</h3>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => markAllAsRead()}
                      className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                      <CheckCheck size={12} />
                      Mark all read
                    </button>
                  )}
                </div>
              </div>
              
              <div className="max-h-64 overflow-y-auto">
                  {notifications.length === 0 ? (
                  <div className="p-4 text-center text-gray-500">
                    <Bell size={24} className="mx-auto text-gray-300 mb-2" />
                    <p className="text-sm">No notifications yet</p>
                  </div>
                ) : (
                  notifications.slice(0, 10).map((notification) => (
                    <div
                      key={notification.notification_id}
                      className={`p-3 border-b border-gray-50 hover:bg-gray-50 cursor-pointer ${
                        !notification.is_read ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => !notification.is_read && markAsRead(notification.notification_id)}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="text-sm font-medium text-gray-900">{notification.title}</h4>
                          <p className="text-xs text-gray-600 mt-1">{notification.message}</p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(notification.created_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="ml-2 mt-1 flex items-start gap-2">
                          {!notification.is_read && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          )}
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              try {
                                const confirmed = await showConfirm({
                                  title: 'Delete Notification',
                                  message: 'Are you sure you want to delete this notification? This action cannot be undone.',
                                  confirmText: 'Delete',
                                  isDestructive: true,
                                });
                                if (!confirmed) return;
                                setModalProcessing(true);
                                const ok = await deleteNotification(notification.notification_id);
                                if (ok) {
                                  showToast('Notification deleted', 'success');
                                } else {
                                  showToast('Failed to delete notification', 'error');
                                }
                              } catch (err) {
                                console.error('Error deleting notification:', err);
                                showToast('Error deleting notification', 'error');
                              } finally {
                                setModalProcessing(false);
                              }
                            }}
                            title="Delete notification"
                            className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {notifications.length > 10 && (
                <div className="p-2 text-center border-t border-gray-100">
                  <button className="text-xs text-gray-500 hover:text-gray-700">
                    View all notifications
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Info and Dropdown Trigger */}
        <div
          className="flex items-center gap-2 cursor-pointer p-1 rounded-lg hover:bg-gray-50 transition-colors"
          onClick={toggleDropdown}
          aria-expanded={isDropdownOpen}
          aria-haspopup="menu"
          aria-controls="header-profile-menu"
        >
          {user && (
            <>
              <img
                src={userAvatar}
                alt="user avatar"
                className="w-9 h-9 rounded-full object-cover"
              />
              <div className="text-right hidden md:block">
                <span className="text-sm font-medium block text-gray-900 leading-none">{userName}</span>
                <span className="text-xs text-gray-500 capitalize">{roleLabel}</span>
              </div>
            </>
          )}
          <ChevronDown
            size={16}
            className={`text-gray-500 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`}
          />
        </div>

        {/* Profile Dropdown Menu */}
        {isDropdownOpen && (
          <div id="header-profile-menu" role="menu" aria-label="User menu" className="absolute top-14 right-0 bg-white shadow-xl border border-gray-100 rounded-lg overflow-hidden z-20 w-56 animate-in slide-in-from-top-1">
            <div className="p-3">
              <div className="flex items-start gap-3 p-2 rounded-md">
                <img src={userAvatar} alt="avatar" className="w-10 h-10 rounded-full" />
                <div className="text-sm">
                  <div className="font-medium text-gray-900">{userName}</div>
                  {userEmail && <div className="text-xs text-gray-500 truncate">{userEmail}</div>}
                  <div className="text-xs text-gray-400 mt-1">{roleLabel}</div>
                </div>
              </div>
              <div className="mt-2 border-t border-gray-100 pt-2">
                <button
                  ref={firstDropdownItemRef}
                  role="menuitem"
                  onClick={() => { /* open profile settings - hook up later */ }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-md flex items-center gap-2"
                >
                  <LogOut size={16} className="text-gray-500" /> Profile Settings
                </button>
                <button
                  role="menuitem"
                  onClick={handleLogout}
                  className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md flex items-center gap-2 mt-1"
                >
                  <LogOut size={16} className="text-red-500" /> Logout
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}