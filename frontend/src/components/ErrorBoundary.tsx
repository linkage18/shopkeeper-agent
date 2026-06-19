import React from "react";

interface State { hasError: boolean; error?: Error }
interface Props { children: React.ReactNode; onRetry?: () => void }

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  handleRetry = () => {
    this.setState({ hasError: false });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-md rounded-lg border border-red-200 bg-red-50 px-6 py-4 text-center">
            <p className="text-sm font-medium text-red-700">页面渲染异常</p>
            <p className="mt-1 text-xs text-red-500">{this.state.error?.message}</p>
            <div className="mt-3 flex justify-center gap-2">
              <button onClick={this.handleRetry}
                className="rounded-md bg-red-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >重试</button>
              <button onClick={() => window.location.reload()}
                className="rounded-md border border-red-300 bg-white px-4 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
              >刷新页面</button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
