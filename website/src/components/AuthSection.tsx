import { useAuthActions } from "@convex-dev/auth/react";
import { useConvexAuth, useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import { setAuth } from '../stores/authStore';
import { Button } from 'primereact/button';
import { useEffect, useState } from 'react';

export default function AuthSection() {
  const authActions = useAuthActions();
  const { isAuthenticated, isLoading } = useConvexAuth();
  const viewer = useQuery(api.users.viewer);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (isAuthenticated && viewer) {
      setAuth(true, {
        name: viewer.name,
        email: viewer.email,
      });
    } else if (!isLoading && !isAuthenticated) {
      setAuth(false, null);
    }
  }, [isAuthenticated, viewer, isLoading]);

  if (!isMounted || isLoading) {
    return <div className="h-10"></div>;
  }

  return (
    <div className="auth-section flex items-center min-h-[40px]">
      {isAuthenticated ? (
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">
            {viewer?.name || viewer?.email || 'Prihlásený'}
          </span>
          <Button 
            label="Odhlásiť sa" 
            onClick={() => void authActions?.signOut()} 
            size="small" 
            severity="secondary" 
            outlined
            pt={{
                root: { className: 'px-3 py-1 text-xs border border-gray-400 rounded hover:bg-gray-100 transition-colors' },
                label: { className: 'text-gray-700' }
            }}
          />
        </div>
      ) : (
        <Button 
          label="Prihlásiť sa cez Google" 
          onClick={() => void authActions?.signIn("google")} 
          size="small" 
          pt={{
            root: { className: 'px-3 py-2 text-sm bg-blue-600 text-white rounded font-medium hover:bg-blue-700 transition-colors' }
          }}
        />
      )}
    </div>
  );
}

