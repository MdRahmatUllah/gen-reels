import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { config } from "../lib/config";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (config.disableBrowserAuth) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center overflow-hidden bg-base px-4 text-primary antialiased">
        <div className="w-full max-w-sm rounded-2xl border border-border-card bg-card p-6 shadow-card shimmer" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
