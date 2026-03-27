<script setup lang="ts">
import type { DocumentResult } from "~/types";

const props = defineProps<{
  results: DocumentResult[];
}>();

const currentPage = ref(1);
const perPage = 10;

const totalPages = computed(() =>
  Math.ceil(props.results.length / perPage)
);

const pagedResults = computed(() => {
  const start = (currentPage.value - 1) * perPage;
  return props.results.slice(start, start + perPage);
});

watch(
  () => props.results,
  () => {
    currentPage.value = 1;
  }
);
</script>

<template>
  <div>
    <div v-if="results.length === 0" class="text-center py-8 text-gray-400">
      No results match the current filters.
    </div>

    <div v-else class="space-y-3">
      <ResultCard
        v-for="result in pagedResults"
        :key="result.doc_id"
        :result="result"
      />
    </div>

    <!-- Pagination -->
    <div
      v-if="totalPages > 1"
      class="mt-6 flex items-center justify-center gap-2"
    >
      <button
        :disabled="currentPage <= 1"
        class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="currentPage--"
      >
        Previous
      </button>
      <span class="text-sm text-gray-600">
        Page {{ currentPage }} of {{ totalPages }}
      </span>
      <button
        :disabled="currentPage >= totalPages"
        class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        @click="currentPage++"
      >
        Next
      </button>
    </div>
  </div>
</template>
