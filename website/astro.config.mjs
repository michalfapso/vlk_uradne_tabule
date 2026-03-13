import { defineConfig } from 'astro/config';
import tailwind from "@astrojs/tailwind";
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

import react from '@astrojs/react';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// https://astro.build/config
export default defineConfig({
  // Set the site property to your full GitHub Pages URL
  // Replace with your actual username if different
  site: 'https://michalfapso.github.io',
  // Set the base path to your repository name
  // Make sure this matches your repository name!
  base: '/vlk_uradne_tabule/',
  integrations: [tailwind(), react()],
  devToolbar: {
    enabled: false
  },
  vite: {
    ssr: {
      noExternal: ['primereact']
    }
  }
});

