import type { SearchRequest, SearchResponse } from "~/types";

const SEARCH_TIMEOUT_MS = 180_000;

function formatSearchError(e: unknown, apiBase: string): string {
  if (e && typeof e === "object" && "data" in e) {
    const d = (e as { data?: unknown; message?: string }).data;
    if (d && typeof d === "object" && "detail" in d) {
      const det = (d as { detail: unknown }).detail;
      if (typeof det === "string") return det;
      if (Array.isArray(det))
        return det.map((x) => JSON.stringify(x)).join("; ");
    }
    const m = (e as { message?: string }).message;
    if (m) return m;
  }
  if (e instanceof Error) {
    if (e.message.includes("Failed to fetch") || e.name === "FetchError") {
      return `Cannot reach API at ${apiBase}. On Netlify set NUXT_PUBLIC_API_BASE to your Render URL (https://...) and redeploy.`;
    }
    return e.message;
  }
  return "Search failed";
}

export const useSearch = () => {
  const config = useRuntimeConfig();
  const apiBase = config.public.apiBase;

  const results = ref<SearchResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const search = async (request: SearchRequest) => {
    loading.value = true;
    error.value = null;

    try {
      const body: Record<string, unknown> = {
        query: request.query,
        doc_type: request.doc_type,
        limit: request.limit,
      };

      if (request.date_from) body.date_from = request.date_from;
      if (request.date_to) body.date_to = request.date_to;
      if (request.min_citations != null)
        body.min_citations = request.min_citations;
      if (request.tags && request.tags.length > 0) body.tags = request.tags;

      const data = await $fetch<SearchResponse>(`${apiBase}/api/search`, {
        method: "POST",
        body,
        timeout: SEARCH_TIMEOUT_MS,
      });

      results.value = data;
    } catch (e: unknown) {
      error.value = formatSearchError(e, apiBase);
      console.error("Search error:", e);
    } finally {
      loading.value = false;
    }
  };

  return {
    results,
    loading,
    error,
    search,
  };
};
