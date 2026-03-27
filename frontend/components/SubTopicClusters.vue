<script setup lang="ts">
import type { SubTopic } from "~/types";

defineProps<{
  clusters: SubTopic[];
  activeCluster: number | null;
}>();

const emit = defineEmits<{
  select: [clusterId: number | null];
}>();

const clusterColors = [
  "bg-blue-100 text-blue-800 border-blue-200",
  "bg-emerald-100 text-emerald-800 border-emerald-200",
  "bg-violet-100 text-violet-800 border-violet-200",
  "bg-amber-100 text-amber-800 border-amber-200",
  "bg-rose-100 text-rose-800 border-rose-200",
  "bg-cyan-100 text-cyan-800 border-cyan-200",
  "bg-orange-100 text-orange-800 border-orange-200",
  "bg-indigo-100 text-indigo-800 border-indigo-200",
];

const getColorClass = (index: number) =>
  clusterColors[index % clusterColors.length];
</script>

<template>
  <div class="bg-white rounded-lg border border-gray-200 p-4">
    <h3 class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
      <svg
        class="w-4 h-4 text-gray-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
        />
      </svg>
      Discovered Sub-Topics
    </h3>

    <div v-if="clusters.length === 0" class="text-sm text-gray-400">
      No clusters available.
    </div>

    <div v-else class="space-y-2">
      <button
        v-for="(cluster, i) in clusters"
        :key="cluster.cluster_id"
        :class="[
          'w-full text-left px-3 py-2 rounded-lg border text-sm transition-all',
          activeCluster === cluster.cluster_id
            ? 'ring-2 ring-primary-500 ring-offset-1 ' + getColorClass(i)
            : getColorClass(i) + ' hover:shadow-sm',
        ]"
        @click="emit('select', cluster.cluster_id)"
      >
        <div class="flex items-center justify-between">
          <span class="font-medium truncate">{{ cluster.label }}</span>
          <span
            class="ml-2 flex-shrink-0 text-xs opacity-70"
          >
            {{ cluster.doc_count }} docs
          </span>
        </div>
        <div
          v-if="cluster.keywords.length > 0"
          class="mt-1 flex flex-wrap gap-1"
        >
          <span
            v-for="kw in cluster.keywords.slice(0, 4)"
            :key="kw"
            class="text-xs opacity-60"
          >
            #{{ kw }}
          </span>
        </div>
      </button>
    </div>
  </div>
</template>
