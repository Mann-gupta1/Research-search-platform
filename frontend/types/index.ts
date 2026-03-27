export interface SearchRequest {
  query: string;
  doc_type: "patents" | "papers" | "both";
  date_from?: string | null;
  date_to?: string | null;
  min_citations?: number | null;
  tags?: string[] | null;
  limit: number;
}

export interface DocumentResult {
  doc_id: string;
  title: string;
  abstract: string;
  doc_type: string;
  publication_date: string | null;
  citation_count: number | null;
  tags: string[];
  score: number;
  cluster_id: number | null;
}

export interface SubTopic {
  cluster_id: number;
  label: string;
  keywords: string[];
  doc_count: number;
}

export interface HeatmapCell {
  sub_topic: string;
  year: number;
  count: number;
}

export interface HeatmapData {
  cells: HeatmapCell[];
  sub_topics: string[];
  years: number[];
  velocities: Record<string, number>;
}

export interface SearchResponse {
  results: DocumentResult[];
  clusters: SubTopic[];
  heatmap: HeatmapData;
  total_time_ms: number;
}
