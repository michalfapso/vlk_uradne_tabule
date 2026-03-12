import { ConvexAuthProvider } from "@convex-dev/auth/react";
import { ConvexReactClient, ConvexProvider } from "convex/react";
import type { ReactNode } from "react";

const convexUrl = import.meta.env.PUBLIC_CONVEX_URL;
if (!convexUrl) {
  throw new Error("PUBLIC_CONVEX_URL is not defined");
}

// Create a singleton client instance to be shared across islands
const convex = new ConvexReactClient(convexUrl);

/**
 * Provider that includes Authentication handling.
 * Only ONE of these should be present on a page to avoid auth state conflicts.
 */
export default function ConvexClientProvider({ children }: { children: ReactNode }) {
  return (
    <ConvexAuthProvider client={convex}>
      {children}
    </ConvexAuthProvider>
  );
}

/**
 * A "bare" provider that just provides the Convex client without auth management.
 * Use this for additional islands on the same page.
 */
export function ConvexClientBareProvider({ children }: { children: ReactNode }) {
  return (
    <ConvexProvider client={convex}>
      {children}
    </ConvexProvider>
  );
}


