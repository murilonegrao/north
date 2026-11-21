import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'
import '@fontsource/spectral/400.css'
import '@fontsource/spectral/400-italic.css'
import './styles/tokens.css'
import './styles/base.css'

import { createApp } from 'vue'
import App from './App.vue'
import { i18n } from './i18n'
import { router } from './router'

createApp(App).use(i18n).use(router).mount('#app')
