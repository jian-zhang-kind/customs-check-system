export default defineNuxtConfig({
  compatibilityDate: "2026-10-09",
  devtools: { enabled: false },
  ssr: false,
  modules: ["@element-plus/nuxt"],
  css: ["~/assets/main.css"],
  devServer: {
    host: "127.0.0.1",
    port: 3000,
  },
  runtimeConfig: {
    public: {
      apiBase: "http://127.0.0.1:8000/api",
    },
  },
  app: {
    head: {
      title: "关务慧眼｜申报前自查",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
      ],
    },
  },
})
