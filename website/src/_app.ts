import type { App } from 'vue';
import PrimeVue from 'primevue/config';
import Aura from '@primevue/themes/aura';
import { convexVue } from 'convex-vue';

export default (app: App) => {
    app.use(PrimeVue, {
        theme: {
            preset: Aura,
            options: {
                darkModeSelector: '.dark',
            }
        }
    });

    const convexUrl = import.meta.env.PUBLIC_CONVEX_URL;
    if (convexUrl) {
        app.use(convexVue, {
            url: convexUrl,
        });
    }
};

