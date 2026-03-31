import type { Ref } from "vue";

export function useEmbeddingWarmup(
  apiBase: Ref<string>,
  apiLooksLocal: Ref<boolean>,
) {
  const embeddingReady = ref(true);
  const warmupMessage = ref<string | null>(null);
  const warmupError = ref<string | null>(null);

  onMounted(async () => {
    if (apiLooksLocal.value) {
      return;
    }
    const root = apiBase.value.replace(/\/$/, "");
    const readyUrl = root ? `${root}/api/ready` : "/api/ready";
    const warmUrl = root ? `${root}/api/warm` : "/api/warm";

    embeddingReady.value = false;
    warmupMessage.value = "Connecting to search API…";

    const longTimeout = 120_000;
    const pollIntervalMs = 8000;
    const maxWaitMs = 20 * 60 * 1000;

    try {
      const first = await $fetch<{ embedding_ready: boolean }>(readyUrl, {
        timeout: longTimeout,
      });
      if (first.embedding_ready) {
        embeddingReady.value = true;
        warmupMessage.value = null;
        return;
      }

      warmupMessage.value =
        "Loading the AI model (first visit can take several minutes on small servers)…";

      await $fetch(warmUrl, {
        method: "POST",
        timeout: 60_000,
      });

      const deadline = Date.now() + maxWaitMs;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, pollIntervalMs));
        const r = await $fetch<{ embedding_ready: boolean }>(readyUrl, {
          timeout: longTimeout,
        });
        if (r.embedding_ready) {
          embeddingReady.value = true;
          warmupMessage.value = null;
          return;
        }
      }

      warmupError.value =
        "The model is still loading. Wait a minute, refresh the page, or upgrade your Render plan (512MB often cannot run PyTorch + search reliably).";
      embeddingReady.value = true;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      warmupError.value = msg;
      embeddingReady.value = true;
      warmupMessage.value = null;
    }
  });

  return { embeddingReady, warmupMessage, warmupError };
}
