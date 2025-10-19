import { defineClientConfig } from 'vuepress/client'
import CurrentVersion from './components/CurrentVersion.vue'
import Features from './components/Features.vue'

export default defineClientConfig({
  enhance({ app }) {
    app.component('CurrentVersion', CurrentVersion)
    app.component('Features', Features)
  },
})
