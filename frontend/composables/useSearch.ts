import type { SearchRequest, SearchResponse } from "~/types";

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
      });

      results.value = data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Search failed";
      error.value = msg;
      console.error("Search error:", e);
    } finally {
      loading.value = false;
    }
  };

  const reset = () => {
    results.value = null;
    error.value = null;
  };

  return {
    results,
    loading,
    error,
    search,
    reset,
  };
};
