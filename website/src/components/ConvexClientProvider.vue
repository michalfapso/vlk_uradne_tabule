<script setup lang="ts">
import { convexVue } from 'convex-vue';
import { getCurrentInstance } from 'vue';

const convexUrl = import.meta.env.PUBLIC_CONVEX_URL;

const instance = getCurrentInstance();
if (instance && convexUrl) {
  const convex = convexVue;
  instance.appContext.app.use(convex, {
    url: convexUrl,
  });

  // Handle initial auth token from storage
  const JWT_STORAGE_KEY = "__convexAuthJWT";
  const storageNamespace = convexUrl.replace(/[^a-zA-Z0-9]/g, "");
  const token = typeof window !== 'undefined' ? localStorage.getItem(JWT_STORAGE_KEY + "_" + storageNamespace) : null;
  
  if (token) {
    // We need to wait for the next tick or just access the client after use()
    // Actually, we can just use the client directly if we have it
    // In convex-vue 0.1.5, we might need to get the client from the app
    const convexClient = instance.appContext.config.globalProperties.$convex; // Just a guess
    // But since we are inside the setup of a component that might be too early.
  }
} else if (!convexUrl) {
  console.error("PUBLIC_CONVEX_URL is not defined");
}
</script>

<template>
  <slot />
</template>

