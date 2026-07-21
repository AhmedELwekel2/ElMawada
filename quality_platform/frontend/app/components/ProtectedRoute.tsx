"use client";

import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState, ReactNode } from "react";

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, user, isLoading, token, refreshAccessToken } = useAuth();
  const router = useRouter();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [hasAttemptedRefresh, setHasAttemptedRefresh] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      if (!isLoading) {
        if (!isAuthenticated || !token) {
          // Try to refresh the token if we haven't already
          if (!hasAttemptedRefresh) {
            setIsRefreshing(true);
            setHasAttemptedRefresh(true);
            const refreshSuccess = await refreshAccessToken();
            setIsRefreshing(false);
            
            if (refreshSuccess) {
              // Token refreshed successfully, don't redirect
              return;
            }
          }
          
          // Token refresh failed or no token to refresh, redirect to login
          router.push("/login");
          return;
        }
        
        if (requiredRole && user?.role !== requiredRole) {
          router.push("/dashboard");
          return;
        }
      }
    };

    checkAuth();
  }, [isAuthenticated, user, isLoading, router, requiredRole, token, refreshAccessToken, hasAttemptedRefresh]);

  if (isLoading || isRefreshing) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-red"></div>
      </div>
    );
  }

  if (!isAuthenticated || !token) {
    return null; // Will redirect to login
  }

  if (requiredRole && user?.role !== requiredRole) {
    return null; // Will redirect to dashboard
  }

  return <>{children}</>;
}
