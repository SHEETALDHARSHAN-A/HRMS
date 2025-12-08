import React from 'react'
import { useNavigate } from 'react-router-dom'
import type { NavigateFunction } from 'react-router-dom'

type Props = { children: React.ReactNode }

type State = { hasError: boolean }

class ErrorBoundaryInner extends React.Component<Props, State> {
  navigate: NavigateFunction
  constructor(props: Props & { navigate: NavigateFunction }) {
    super(props)
    this.state = { hasError: false }
    this.navigate = (props as any).navigate
  }

  static getDerivedStateFromError(_: Error): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: any) {
    // Log the error somewhere (console for now)
    // In future, wire into your analytics/telemetry
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught', error, info)
  }
  componentDidMount() {
    if (this.state.hasError) {
      // Defer navigation to after render to avoid setState-in-render errors
      try {
        setTimeout(() => {
          try {
            this.navigate('/interview/thank-you')
          } catch (e) {
            // ignore
          }
        }, 0)
      } catch (_) {
        // ignore
      }
    }
  }

  componentDidUpdate(_prevProps: any, prevState: State) {
    if (!prevState.hasError && this.state.hasError) {
      // Navigate once after the error state is set to avoid updating during render
      try {
        setTimeout(() => {
          try {
            this.navigate('/interview/thank-you')
          } catch (e) {
            // ignore
          }
        }, 0)
      } catch (_) {
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
                } catch (e) {
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
  // @ts-ignore - passing navigate into class constructor
  return <ErrorBoundaryInner navigate={navigate}>{children}</ErrorBoundaryInner>
}

export default ErrorBoundary
