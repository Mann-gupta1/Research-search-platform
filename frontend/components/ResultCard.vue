<script setup lang="ts">
import type { DocumentResult } from "~/types";

const props = defineProps<{
  result: DocumentResult;
}>();

const isExpanded = ref(false);

const truncatedAbstract = computed(() => {
  if (isExpanded.value || props.result.abstract.length <= 250) {
    return props.result.abstract;
  }
  return props.result.abstract.slice(0, 250) + "...";
});

const formattedDate = computed(() => {
  if (!props.result.publication_date) return "N/A";
  try {
    return new Date(props.result.publication_date).toLocaleDateString(
      "en-US",
      { year: "numeric", month: "short", day: "numeric" }
    );
  } catch {
    return props.result.publication_date;
  }
});

const scorePercent = computed(() => {
  return Math.round(props.result.score * 100);
});
</script>

<template>
  <div
    class="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-md transition-shadow"
  >
    <!-- Header row -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-1">
          <span
            :class="[
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
              result.doc_type === 'patent'
                ? 'bg-amber-100 text-amber-800'
                : 'bg-blue-100 text-blue-800',
            ]"
          >
            {{ result.doc_type === "patent" ? "Patent" : "Paper" }}
          </span>
          <span class="text-xs text-gray-400">{{ result.doc_id }}</span>
        </div>
        <h3 class="text-base font-semibold text-gray-900 leading-snug">
          {{ result.title }}
        </h3>
      </div>
      <div
        class="flex-shrink-0 text-right"
      >
        <div
          class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
          :class="
            scorePercent >= 70
              ? 'bg-green-50 text-green-700'
              : scorePercent >= 40
                ? 'bg-yellow-50 text-yellow-700'
                : 'bg-gray-50 text-gray-600'
          "
        >
          {{ scorePercent }}% match
        </div>
      </div>
    </div>

    <!-- Abstract -->
    <p class="mt-3 text-sm text-gray-600 leading-relaxed">
      {{ truncatedAbstract }}
    </p>
    <button
      v-if="result.abstract.length > 250"
      class="mt-1 text-xs text-primary-600 hover:text-primary-800"
      @click="isExpanded = !isExpanded"
    >
      {{ isExpanded ? "Show less" : "Show more" }}
    </button>

    <!-- Metadata row -->
    <div class="mt-3 flex items-center gap-4 text-xs text-gray-500">
      <span class="flex items-center gap-1">
        <svg
          class="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        {{ formattedDate }}
      </span>

      <span
        v-if="result.citation_count != null"
        class="flex items-center gap-1"
      >
        <svg
          class="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
        {{ result.citation_count }} citations
      </span>
    </div>

    <!-- Tags -->
    <div v-if="result.tags.length > 0" class="mt-2 flex flex-wrap gap-1">
      <span
        v-for="tag in result.tags.slice(0, 5)"
        :key="tag"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
      >
        {{ tag }}
      </span>
    </div>
  </div>
</template>
