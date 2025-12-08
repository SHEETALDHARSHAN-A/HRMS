export const AUTH_CONFIG = {
  BRAND: {
    name: "PRAYAG.AI",
    tagline: "Recruitment Management",
    subtitle: "INNOVATION AND EXCELLENCE"
  },
  CONTENT: {
    signInTitle: "Sign in",
    signUpTitle: "Sign up",
    verifyTitle: "Verify your email",
    emailLabel: "Enter your email address",
    firstNameLabel: "First name",
    lastNameLabel: "Last name",
    emailPlaceholder: "Email address",
    firstNamePlaceholder: "First name",
    lastNamePlaceholder: "Last name",
    rememberMe: "Remember me",
    signInButton: "Sign In",
    signUpButton: "Sign up",
    continueButton: "Continue",
    noAccountText: "If you don't have an account?",
    alreadyAccountText: "If you already have an account?",
    registerHere: "Register here !",
    loginHere: "Login here !",
    didntGetCode: "Didn't get code?",
    resendIt: "Resend it.",
    otpInstruction: "Enter the code we've sent to your email address",
    description: "An intelligent recruitment platform designed to streamline every stage of hiring—from candidate sourcing and smart shortlisting to automated screening and seamless onboarding—embodying Dev Dhara's commitment to quality and efficiency."
  },
    OTP_EXPIRY_SECONDS: 240, 
    RESEND_COOLDOWN_SECONDS: 60, 
  ERROR_MESSAGES: {
    USER_EXISTS: "User already exists. Please use the 'Login here' tab.", 
    NETWORK_ERROR: "Cannot connect to the server. Please check your network connection.",
    INVALID_OTP: "Invalid OTP. Please check the code or request a new one.",
    NOT_REGISTERED: "You haven't registered yet. Please use the 'Sign up here' tab.",
    GENERIC_ERROR: "An unexpected error occurred. Please try again."
  },
  API_ENDPOINTS: {
    SIGN_IN_OTP: "/auth/send-otp",
    SIGN_UP_OTP: "/auth/sign-up/send-otp",
    VERIFY_OTP: "/auth/verify-otp",
  CHECK_COOKIE: "/auth/check-cookie",
    CHECK_EMAIL_STATUS: "/auth/check-email-status",
    RESEND_OTP: "/auth/resend-otp",
    LOGOUT: "/auth/logout"
  },
  AUTH_STEPS: {
    SIGN_IN: 'sign_in',
    SIGN_UP: 'sign_up',
    VERIFY_OTP: 'verify_otp'
  }
};