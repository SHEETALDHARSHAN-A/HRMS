import React from 'react'
import { useNavigate } from 'react-router-dom'
import type { NavigateFunction } from 'react-router-dom'

type Props = { children: React.ReactNode }
type ErrorBoundaryInnerProps = Props & { navigate: NavigateFunction }

type State = { hasError: boolean }

class ErrorBoundaryInner extends React.Component<ErrorBoundaryInnerProps, State> {
  navigate: NavigateFunction
  constructor(props: ErrorBoundaryInnerProps) {
    super(props)
    this.state = { hasError: false }
    this.navigate = props.navigate
  }

  static getDerivedStateFromError(_: Error): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Log the error somewhere (console for now)
    // In future, wire into your analytics/telemetry
     
    console.error('ErrorBoundary caught', error, info)
  }
  componentDidMount() {
    if (this.state.hasError) {
      // Defer navigation to after render to avoid setState-in-render errors
      try {
        setTimeout(() => {
          try {
            this.navigate('/interview/thank-you')
          } catch {
            // ignore
          }
        }, 0)
      } catch {
        // ignore
      }
    }
  }

  componentDidUpdate(_prevProps: ErrorBoundaryInnerProps, prevState: State) {
    if (!prevState.hasError && this.state.hasError) {
      // Navigate once after the error state is set to avoid updating during render
      try {
        setTimeout(() => {
          try {
            this.navigate('/interview/thank-you')
          } catch {
            // ignore
          }
        }, 0)
      } catch {
        // ignore
      }
    }
  }

  render() {
    if (this.state.hasError) {
      // Render a simple fallback UI; navigation will occur shortly after render.
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-semibold">An error occurred</h2>
            <p className="text-gray-600 mb-4">The interview session could not be displayed. Thank you for your time.</p>
            <button
              className="px-4 py-2 bg-indigo-600 text-white rounded"
              onClick={() => {
                try {
                  this.navigate('/interview/thank-you')
                } catch {
                  // ignore
                }
              }}
            >
              Continue
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const ErrorBoundary: React.FC<Props> = ({ children }) => {
  const navigate = useNavigate()
  return <ErrorBoundaryInner navigate={navigate}>{children}</ErrorBoundaryInner>
}

export default ErrorBoundary
