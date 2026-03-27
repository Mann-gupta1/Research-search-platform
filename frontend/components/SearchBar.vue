<script setup lang="ts">
import type { SearchRequest } from "~/types";

const props = defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  search: [request: SearchRequest];
}>();

const query = ref("");
const docType = ref<"patents" | "papers" | "both">("both");
const showFilters = ref(false);
const dateFrom = ref<string>("");
const dateTo = ref<string>("");
const minCitations = ref<string>("");
const tagsInput = ref<string>("");

const handleSubmit = () => {
  if (!query.value.trim()) return;

  const parsedTags = tagsInput.value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const request: SearchRequest = {
    query: query.value.trim(),
    doc_type: docType.value,
    limit: 50,
    date_from: dateFrom.value || null,
    date_to: dateTo.value || null,
    min_citations: minCitations.value
      ? parseInt(minCitations.value)
      : null,
    tags: parsedTags.length > 0 ? parsedTags : null,
  };

  emit("search", request);
};
</script>

<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <form @submit.prevent="handleSubmit">
      <!-- Main search row -->
      <div class="flex gap-3">
        <div class="flex-1 relative">
          <input
            v-model="query"
            type="text"
            placeholder="e.g., 'machine learning for drug discovery' or 'lithium-ion battery thermal management'"
            class="w-full pl-4 pr-10 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-gray-900 placeholder-gray-400"
          />
          <svg
            class="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
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
        <button
          type="submit"
          :disabled="loading || !query.trim()"
          class="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <svg
            v-if="loading"
            class="animate-spin w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          {{ loading ? "Searching..." : "Search" }}
        </button>
      </div>

      <!-- Doc type toggle + filter toggle -->
      <div class="mt-4 flex items-center justify-between">
        <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          <button
            v-for="option in [
              { value: 'both', label: 'All' },
              { value: 'patents', label: 'Patents' },
              { value: 'papers', label: 'Papers' },
            ]"
            :key="option.value"
            type="button"
            :class="[
              'px-4 py-1.5 text-sm font-medium rounded-md transition-colors',
              docType === option.value
                ? 'bg-white text-primary-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900',
            ]"
            @click="docType = option.value as 'both' | 'patents' | 'papers'"
          >
            {{ option.label }}
          </button>
        </div>

        <button
          type="button"
          class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          @click="showFilters = !showFilters"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          {{ showFilters ? "Hide filters" : "More filters" }}
        </button>
      </div>

      <!-- Expanded filters -->
      <div
        v-if="showFilters"
        class="mt-4 pt-4 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Date from</label
          >
          <input
            v-model="dateFrom"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Date to</label
          >
          <input
            v-model="dateTo"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Min. citations</label
          >
          <input
            v-model="minCitations"
            type="number"
            min="0"
            placeholder="0"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1"
            >Field / Tags</label
          >
          <input
            v-model="tagsInput"
            type="text"
            placeholder="e.g., batteries, ML"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
          <p class="mt-0.5 text-xs text-gray-400">Comma-separated</p>
        </div>
      </div>
    </form>
  </div>
</template>
