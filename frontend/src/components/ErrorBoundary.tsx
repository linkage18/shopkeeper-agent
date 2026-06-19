import React from "react";

interface State { hasError: boolean; error?: Error }
interface Props { children: React.ReactNode }

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-md rounded-lg border border-red-200 bg-red-50 px-6 py-4 text-center">
            <p className="text-sm font-medium text-red-700">页面渲染异常</p>
            <p className="mt-1 text-xs text-red-500">{this.state.error?.message}</p>
            <button
              onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}
              className="mt-3 rounded-md bg-red-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-red-700"
            >重新加载</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
