<script setup lang="ts">
import type { SearchRequest } from "~/types";

const config = useRuntimeConfig();
const apiBase = computed(() => String(config.public.apiBase || ""));

const apiLooksLocal = computed(() => {
  const b = apiBase.value.toLowerCase();
  return b.includes("localhost") || b.includes("127.0.0.1");
});

const { results, loading, error, search, reset } = useSearch();

const activeCluster = ref<number | null>(null);

const filteredResults = computed(() => {
  if (!results.value) return [];
  if (activeCluster.value === null) return results.value.results;
  return results.value.results.filter(
    (r) => r.cluster_id === activeCluster.value
  );
});

const handleSearch = async (request: SearchRequest) => {
  activeCluster.value = null;
  await search(request);
};

const handleClusterClick = (clusterId: number | null) => {
  activeCluster.value =
    activeCluster.value === clusterId ? null : clusterId;
};
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center"
          >
            <svg
              class="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold text-gray-900">
              Research Search Platform
            </h1>
            <p class="text-sm text-gray-500">
              Semantic search across patents and research papers
            </p>
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Misconfigured production API (Netlify build missing env) -->
      <div
        v-if="apiLooksLocal"
        class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-sm"
      >
        <p class="font-medium">API URL is still set to localhost</p>
        <p class="mt-1">
          In Netlify → Site settings → Environment variables, set
          <code class="bg-amber-100 px-1 rounded">NUXT_PUBLIC_API_BASE</code>
          to your Render backend (e.g.
          <code class="bg-amber-100 px-1 rounded"
            >https://research-search-platform.onrender.com</code
          >), then trigger a new deploy. Current value:
          <code class="bg-amber-100 px-1 rounded">{{ apiBase }}</code>
        </p>
      </div>

      <!-- Search Section -->
      <SearchBar :loading="loading" @search="handleSearch" />

      <!-- Error -->
      <div
        v-if="error"
        class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
      >
        {{ error }}
      </div>

      <!-- Results Section -->
      <div v-if="results" class="mt-6">
        <!-- Stats bar -->
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-gray-600">
            <span class="font-semibold">{{ results.results.length }}</span>
            results found in
            <span class="font-semibold"
              >{{ results.total_time_ms.toFixed(0) }}ms</span
            >
            <span v-if="activeCluster !== null" class="ml-2 text-primary-600">
              (filtered to cluster)
            </span>
          </p>
          <button
            v-if="activeCluster !== null"
            class="text-sm text-primary-600 hover:text-primary-800 underline"
            @click="activeCluster = null"
          >
            Clear filter
          </button>
        </div>

        <div
          v-if="results.results.length === 0"
          class="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-900 text-sm"
        >
          <p class="font-medium">Search ran successfully but returned no documents</p>
          <p class="mt-1">
            The index is probably empty. Run ingestion against the same Zilliz +
            Postgres (or SQLite) your Render service uses, then search again.
          </p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Left: Results List -->
          <div class="lg:col-span-2">
            <ResultsList :results="filteredResults" />
          </div>

          <!-- Right: Clusters + Heatmap -->
          <div class="space-y-6">
            <SubTopicClusters
              :clusters="results.clusters"
              :active-cluster="activeCluster"
              @select="handleClusterClick"
            />
            <TrendHeatmap :heatmap="results.heatmap" />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading"
        class="mt-20 text-center text-gray-400"
      >
        <svg
          class="w-16 h-16 mx-auto mb-4 text-gray-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p class="text-lg font-medium">Enter a technical query to begin</p>
        <p class="text-sm mt-1">
          Search across patents and research papers using natural language
        </p>
      </div>
    </main>
  </div>
</template>
