<script setup lang="ts">
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { HeatmapChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import type { HeatmapData } from "~/types";

use([
  CanvasRenderer,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
]);

const props = defineProps<{
  heatmap: HeatmapData;
}>();

const chartOption = computed(() => {
  if (
    !props.heatmap ||
    props.heatmap.cells.length === 0 ||
    props.heatmap.years.length === 0
  ) {
    return null;
  }

  const years = props.heatmap.years.map(String);
  const topics = props.heatmap.sub_topics;

  const data = props.heatmap.cells.map((cell) => {
    const xIdx = props.heatmap.years.indexOf(cell.year);
    const yIdx = topics.indexOf(cell.sub_topic);
    return [xIdx, yIdx, cell.count];
  });

  const maxCount = Math.max(...data.map((d) => d[2] as number), 1);

  const truncatedTopics = topics.map((t) =>
    t.length > 20 ? t.slice(0, 18) + "..." : t
  );

  return {
    tooltip: {
      position: "top",
      formatter: (params: { data: number[] }) => {
        const [xIdx, yIdx, count] = params.data;
        const year = years[xIdx];
        const topic = topics[yIdx] ?? "Unknown";
        const velocity = props.heatmap.velocities[topic] ?? 0;
        const trend =
          velocity > 0 ? "Growing" : velocity < 0 ? "Declining" : "Stable";
        return `<strong>${topic}</strong><br/>Year: ${year}<br/>Count: ${count}<br/>Trend: ${trend} (${velocity > 0 ? "+" : ""}${velocity.toFixed(2)}/yr)`;
      },
    },
    grid: {
      top: 10,
      left: 120,
      right: 30,
      bottom: 50,
    },
    xAxis: {
      type: "category",
      data: years,
      splitArea: { show: true },
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: truncatedTopics,
      splitArea: { show: true },
      axisLabel: { fontSize: 10, width: 100, overflow: "truncate" },
    },
    visualMap: {
      min: 0,
      max: maxCount,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      itemHeight: 10,
      textStyle: { fontSize: 10 },
      inRange: {
        color: ["#f0f9ff", "#bae6fd", "#38bdf8", "#0284c7", "#075985"],
      },
    },
    series: [
      {
        name: "Document Count",
        type: "heatmap",
        data,
        label: {
          show: data.length <= 40,
          fontSize: 9,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0, 0, 0, 0.3)",
          },
        },
      },
    ],
  };
});

const velocityEntries = computed(() => {
  if (!props.heatmap?.velocities) return [];
  return Object.entries(props.heatmap.velocities).sort(
    (a, b) => b[1] - a[1]
  );
});
</script>

<template>
  <div class="bg-white rounded-lg border border-gray-200 p-4">
    <h3
      class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2"
    >
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
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
      Trend Heatmap
    </h3>

    <div
      v-if="!chartOption"
      class="h-40 flex items-center justify-center text-sm text-gray-400"
    >
      Not enough data for trend visualization.
    </div>

    <template v-else>
      <ClientOnly>
        <VChart
          :option="chartOption"
          style="height: 250px"
          autoresize
        />
      </ClientOnly>

      <!-- Velocity indicators -->
      <div v-if="velocityEntries.length > 0" class="mt-3">
        <p class="text-xs font-medium text-gray-500 mb-2">
          Velocity (growth rate)
        </p>
        <div class="space-y-1">
          <div
            v-for="[topic, velocity] in velocityEntries"
            :key="topic"
            class="flex items-center justify-between text-xs"
          >
            <span class="text-gray-600 truncate mr-2">{{ topic }}</span>
            <span
              :class="[
                'font-medium flex-shrink-0',
                velocity > 0
                  ? 'text-green-600'
                  : velocity < 0
                    ? 'text-red-600'
                    : 'text-gray-400',
              ]"
            >
              {{ velocity > 0 ? "+" : "" }}{{ velocity.toFixed(2) }}/yr
              <span v-if="velocity > 0">&#8599;</span>
              <span v-else-if="velocity < 0">&#8600;</span>
              <span v-else>&#8594;</span>
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
