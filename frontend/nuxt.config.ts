export default defineNuxtConfig({
  devtools: { enabled: true },

  modules: ["@nuxtjs/tailwindcss"],

  runtimeConfig: {
    public: {
      // Dev: talk to local FastAPI. Prod build: empty → same-origin /api/* (use Netlify/Vercel
      // proxy to Render — see netlify.toml). Override anytime with NUXT_PUBLIC_API_BASE.
      apiBase:
        process.env.NUXT_PUBLIC_API_BASE ??
        (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000"),
    },
  },

  app: {
    head: {
      title: "Research Search Platform",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        {
          name: "description",
          content:
            "Semantic search over patents and research papers with sub-topic discovery",
        },
      ],
      link: [
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
        },
      ],
    },
  },

  compatibilityDate: "2024-07-01",
});
