const INTERVIEW_ACCESS_PREFIX = "interview_access:";
const DEFAULT_INTERVIEW_ACCESS_TTL_MS = 8 * 60 * 60 * 1000;

interface InterviewAccessRecord {
  token: string;
  email: string;
  verifiedAt: number;
  expiresAt: number;
  source?: string;
}

const normalizeToken = (token: string): string => String(token || "").trim();
const normalizeEmail = (email: string): string => String(email || "").trim().toLowerCase();

const buildInterviewAccessKey = (token: string, email: string): string => {
  return `${INTERVIEW_ACCESS_PREFIX}${encodeURIComponent(normalizeToken(token))}:${encodeURIComponent(normalizeEmail(email))}`;
};

const parseRecord = (raw: string | null): InterviewAccessRecord | null => {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;

    const token = normalizeToken(parsed.token);
    const email = normalizeEmail(parsed.email);
    const verifiedAt = Number(parsed.verifiedAt || 0);
    const expiresAt = Number(parsed.expiresAt || 0);

    if (!token || !email || !Number.isFinite(verifiedAt) || !Number.isFinite(expiresAt)) {
      return null;
    }

    return {
      token,
      email,
      verifiedAt,
      expiresAt,
      source: typeof parsed.source === "string" ? parsed.source : undefined,
    };
  } catch {
    return null;
  }
};

export const saveInterviewAccess = (
  token: string,
  email: string,
  source: string = "otp-verified",
  ttlMs: number = DEFAULT_INTERVIEW_ACCESS_TTL_MS
): void => {
  const normalizedToken = normalizeToken(token);
  const normalizedEmail = normalizeEmail(email);
  if (!normalizedToken || !normalizedEmail) return;

  const now = Date.now();
  const record: InterviewAccessRecord = {
    token: normalizedToken,
    email: normalizedEmail,
    verifiedAt: now,
    expiresAt: now + Math.max(5 * 60 * 1000, ttlMs),
    source,
  };

  try {
    localStorage.setItem(buildInterviewAccessKey(normalizedToken, normalizedEmail), JSON.stringify(record));
  } catch {
    // Ignore storage failures (private mode, quota, etc.)
  }
};

export const hasInterviewAccess = (token: string, email: string): boolean => {
  const normalizedToken = normalizeToken(token);
  const normalizedEmail = normalizeEmail(email);
  if (!normalizedToken || !normalizedEmail) return false;

  const key = buildInterviewAccessKey(normalizedToken, normalizedEmail);
  const record = parseRecord(localStorage.getItem(key));
  if (!record) return false;

  if (Date.now() > record.expiresAt) {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore cleanup failure
    }
    return false;
  }

  return true;
};

export const clearInterviewAccess = (token: string, email: string): void => {
  try {
    localStorage.removeItem(buildInterviewAccessKey(token, email));
  } catch {
    // Ignore cleanup failure
  }
};
