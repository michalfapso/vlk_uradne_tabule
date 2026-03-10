<script setup lang="ts">
import { useConvexQuery, useConvexClient } from 'convex-vue';
import { api } from '../../convex/_generated/api';
import { $isAuthenticated, $user, setAuth } from '../stores/authStore';
import { useStore } from '@nanostores/vue';
import Button from 'primevue/button';
import { watchEffect, onMounted, ref, computed } from 'vue';

const convex = useConvexClient();

// Use useStore from @nanostores/vue for reactivity in templates
const isAuthenticated = useStore($isAuthenticated);
const user = useStore($user);
const isMounted = ref(false);

const VERIFIER_STORAGE_KEY = "__convexAuthOAuthVerifier";
const JWT_STORAGE_KEY = "__convexAuthJWT";
const convexUrl = import.meta.env.PUBLIC_CONVEX_URL || "";
const storageNamespace = convexUrl.replace(/[^a-zA-Z0-9]/g, "");

// Bind query arguments to current store state
const viewerArgs = computed(() => ({
  isAuthenticated: isAuthenticated.value
}));

const { data: viewer } = useConvexQuery((api as any).users.viewer, viewerArgs, { server: false });

watchEffect(() => {
  if (!isMounted.value) return;

  if (viewer.value) {
    setAuth(true, {
      name: viewer.value.name,
      email: viewer.value.email,
    });
  } else if (viewer.value === null) {
    const storedToken = localStorage.getItem(JWT_STORAGE_KEY + "_" + storageNamespace);
    if (!storedToken) {
      setAuth(false, null);
    }
  }
});

onMounted(async () => {
  isMounted.value = true;
  
  // Handle initial auth token from storage
  const storedToken = localStorage.getItem(JWT_STORAGE_KEY + "_" + storageNamespace);
  if (storedToken) {
    (convex as any).setAuth(async () => storedToken);
    if (!$isAuthenticated.get()) {
       setAuth(true, { name: "Načítavam...", email: "" });
    }
  }

  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");
  if (code) {
    const storageKey = VERIFIER_STORAGE_KEY + "_" + storageNamespace;
    const verifier = localStorage.getItem(storageKey);
    
    if (verifier) {
      const attemptSignIn = async (retries = 3) => {
        try {
          const result = await (convex as any).action((api as any).auth.signIn, { params: { code }, verifier });
          if (result.tokens) {
            localStorage.setItem(JWT_STORAGE_KEY + "_" + storageNamespace, result.tokens.token);
            (convex as any).setAuth(async () => result.tokens.token);
            setAuth(true, { name: "Načítavam...", email: "" });
          }
          localStorage.removeItem(storageKey);
          
          const newUrl = new URL(window.location.href);
          newUrl.searchParams.delete("code");
          window.history.replaceState({}, "", newUrl.toString());
        } catch (err) {
          if (retries > 0 && err instanceof Error && (err.message.includes("Connection lost") || err.message.includes("Failed to fetch"))) {
            await new Promise(resolve => window.setTimeout(resolve, 1000));
            return attemptSignIn(retries - 1);
          }
          console.error("Sign in failed after retries", err);
        }
      };

      await attemptSignIn();
    }
  }
});

const login = async () => {
  try {
    const result = await (convex as any).action((api as any).auth.signIn, {
      provider: "google",
    });
    if (result.redirect) {
      if (result.verifier) {
        const storageKey = VERIFIER_STORAGE_KEY + "_" + storageNamespace;
        localStorage.setItem(storageKey, result.verifier);
      }
      window.location.href = result.redirect;
    }
  } catch (err) {
    console.error("Login failed", err);
  }
};

const logout = async () => {
  try {
    await (convex as any).action((api as any).auth.signOut);
    localStorage.removeItem(JWT_STORAGE_KEY + "_" + storageNamespace);
    (convex as any).setAuth(null);
    setAuth(false, null);
  } catch (err) {
    console.error("Logout failed", err);
  }
};
</script>

<template>
  <div class="auth-section min-h-[40px]">
    <template v-if="isMounted">
      <div v-if="isAuthenticated" class="flex items-center gap-3">
        <span class="text-sm font-medium text-gray-700">
          {{ user?.name || user?.email || 'Prihlásený' }}
        </span>
        <Button 
          label="Odhlásiť sa" 
          @click="logout" 
          size="small" 
          severity="secondary" 
          outlined
        />
      </div>
      <div v-else>
        <Button 
          label="Prihlásiť sa cez Google" 
          @click="login" 
          size="small" 
        />
      </div>
    </template>
    <template v-else>
      <div class="h-10"></div>
    </template>
  </div>
</template>

<style scoped>
.auth-section {
  display: flex;
  align-items: center;
}
</style>
