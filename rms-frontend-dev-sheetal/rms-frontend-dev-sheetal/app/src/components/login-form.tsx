import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { useCallback, useEffect, useRef, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react"
import { useAuthContext } from "./../context/AuthContext"
import { authService } from "./../services/authService"

const EMAIL_READY_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

const isEmailReadyForStatusCheck = (email: string): boolean => {
  return EMAIL_READY_REGEX.test(email.trim())
}

const useDebounce = (callback: (...args: any[]) => void, delay: number) => {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const debouncedCallback = useCallback(
    (...args: any[]) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    },
    [callback, delay]
  )

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return debouncedCallback
}

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"form">) {
  const { loading, error, signIn, userEmail } = useAuthContext()

  const [email, setEmail] = useState(userEmail || "")
  const [rememberMe, setRememberMe] = useState(localStorage.getItem("rememberMe") === "true")
  const previousUserEmailRef = useRef<string | null>(userEmail || null)
  const [emailStatus, setEmailStatus] = useState<
    "idle" | "checking" | "exists" | "invalid" | "not_registered"
  >("idle")
  const [emailCheckMessage, setEmailCheckMessage] = useState<string | null>(null)

  const checkEmailExistence = useCallback(async (value: string) => {
    const normalizedEmail = value.trim()

    if (!isEmailReadyForStatusCheck(normalizedEmail)) {
      setEmailStatus("idle")
      setEmailCheckMessage(null)
      return
    }

    setEmailStatus("checking")
    setEmailCheckMessage(null)

    try {
      const result = await authService.checkEmailStatus(normalizedEmail)
      const apiStatus = result.data?.user_status

      if (apiStatus === "EXIST") {
        setEmailStatus("exists")
        return
      }

      if (apiStatus === "NOT_EXIST") {
        setEmailStatus("not_registered")
        setEmailCheckMessage(result.message || "This email is not registered as an administrator.")
        return
      }

      if (apiStatus === "INVALID_FORMAT") {
        setEmailStatus("invalid")
        setEmailCheckMessage(result.error || result.message || "Please enter a valid email address.")
        return
      }

      if (!result.success) {
        if (result.data?.user_status === "NOT_EXIST") {
          setEmailStatus("not_registered")
          setEmailCheckMessage(result.message || "This email is not registered as an administrator.")
          return
        }

        setEmailStatus("invalid")
        setEmailCheckMessage(result.error || result.message || "Error checking email status.")
        return
      }

      setEmailStatus("idle")
      setEmailCheckMessage(null)
    } catch (err: any) {
      setEmailStatus("invalid")
      setEmailCheckMessage(err?.message || "Error checking email status.")
    }
  }, [])

  const debouncedCheck = useDebounce(checkEmailExistence, 500)

  useEffect(() => {
    if (!emailCheckMessage) {
      return
    }

    const timer = setTimeout(() => setEmailCheckMessage(null), 7000)
    return () => clearTimeout(timer)
  }, [emailCheckMessage])

  useEffect(() => {
    if (userEmail && userEmail !== previousUserEmailRef.current) {
      previousUserEmailRef.current = userEmail
      setEmail(userEmail)

      if (isEmailReadyForStatusCheck(userEmail)) {
        checkEmailExistence(userEmail)
      }
    }
  }, [userEmail, checkEmailExistence])

  const handleEmailChange = (value: string) => {
    setEmail(value)

    if (isEmailReadyForStatusCheck(value)) {
      debouncedCheck(value)
    } else {
      setEmailStatus("idle")
      setEmailCheckMessage(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    const normalizedEmail = email.trim()

    if (
      !normalizedEmail ||
      loading ||
      !isEmailReadyForStatusCheck(normalizedEmail) ||
      emailStatus === "checking" ||
      emailStatus === "invalid"
    ) {
      return
    }

    if (emailStatus === "not_registered") {
      setEmailCheckMessage("This email is not registered as an administrator. Sign-in is not allowed.")
      return
    }

    setEmailCheckMessage(null)
    if (signIn) {
      await signIn(normalizedEmail, rememberMe)
    }
  }

  const isButtonDisabled =
    loading ||
    !isEmailReadyForStatusCheck(email) ||
    emailStatus === "checking" ||
    emailStatus === "invalid" ||
    emailStatus === "not_registered"

  return (
    <form
      className={cn(
        "w-full rounded-3xl border border-border/80 bg-card/95 p-6 shadow-[0_24px_64px_-40px_rgba(15,23,42,0.45)] backdrop-blur-sm sm:p-8",
        className
      )}
      onSubmit={handleSubmit}
      {...props}
    >
      <FieldGroup className="gap-6">
        <div className="flex flex-col gap-2 text-left">
          <Badge variant="secondary" className="mb-1 w-fit rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide">
            <ShieldCheck className="mr-1 size-3.5" />
            Admin Portal
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">Login to your account</h1>
          <p className="max-w-sm text-base leading-relaxed text-muted-foreground">
            Enter your email below to login to your account
          </p>
        </div>
        <Field>
          <FieldLabel htmlFor="email" className="text-sm font-semibold tracking-wide text-foreground/90">Email</FieldLabel>
          <div className="relative">
            <Input
              id="email"
              type="email"
              placeholder="m@example.com"
              value={email}
              onChange={(e) => handleEmailChange(e.target.value)}
              className={cn(
                "h-12 rounded-2xl bg-background pr-12 text-base shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]",
                emailStatus === "exists" &&
                  "border-emerald-500/70 focus-visible:border-emerald-500 focus-visible:ring-emerald-500/20"
              )}
            />
            {emailStatus === "checking" && (
              <span className="pointer-events-none absolute inset-y-0 right-3 inline-flex items-center text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
              </span>
            )}
            {emailStatus === "exists" && (
              <span className="pointer-events-none absolute inset-y-0 right-3 inline-flex items-center text-emerald-600">
                <CheckCircle2 className="size-5" />
              </span>
            )}
          </div>
          {emailStatus === "checking" && (
            <FieldDescription className="inline-flex items-center gap-1">
              <Loader2 className="size-3 animate-spin" />
              Checking administrator access...
            </FieldDescription>
          )}
          {emailStatus === "exists" && (
            <FieldDescription className="inline-flex items-center gap-1 text-emerald-600">
 You can continue.
            </FieldDescription>
          )}
          {(emailCheckMessage || error) && (
            <FieldError>{error || emailCheckMessage}</FieldError>
          )}
        </Field>
        <Field>
          <label htmlFor="rememberMe" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <input
              id="rememberMe"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            Remember me
          </label>
          <FieldDescription className="mt-1 inline-flex items-center gap-1 text-xs">
            <ShieldCheck className="size-3.5" />
            Session stays protected with OTP verification.
          </FieldDescription>
        </Field>
        <Field>
          <Button
            type="submit"
            disabled={isButtonDisabled}
            className="h-12 w-full rounded-2xl text-base font-semibold tracking-wide"
          >
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="size-4 animate-spin" />
                Generating OTP...
              </span>
            ) : (
              "Login"
            )}
          </Button>
        </Field>
        <Field>
          <FieldDescription className="text-center text-sm">
            This login is for authorized administrators only.
          </FieldDescription>
        </Field>
      </FieldGroup>
    </form>
  )
}
