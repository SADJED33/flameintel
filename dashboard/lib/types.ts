export type Source = {
  id: string; text: string; psi: string; doc_type: string; file: string; loc: string;
  distance: number; routed?: boolean; acronym?: string; title?: string;
};
export type Warning = { text: string; numbers: string[]; issue: string };
export type Related = { psi: string; acronym: string; title: string };
export type ChatResult = {
  answer: string; sources: Source[]; outcome: "answered" | "partial" | "refused"; refused: boolean;
  warnings: Warning[]; related: Related[]; model: string | null; model_switched: boolean; cached: boolean;
  usage: { total_tokens?: number }; timing_s: number; cache_hit: boolean; scenario: string;
};

export type Rank = {
  score: number; components: Record<string, number>; why: string[]; gravity_note: string; disclaimer: string;
};
export type Investigation = {
  id: string; acronym: string; title: string; name: string; description: string; objective: string; approach: string;
  hypothesis: string; research_impacts: string; hardware: string; flight_program: string; project_type: string;
  environment: string; gravity_condition: string; managing_center: string; start_date: string; end_date: string;
  source_updated_at: string; license: string; doi: string; source_url: string; source_url_note: string;
  principal_investigator: string; topics: string[]; materials: string[]; condition_columns: string[];
  publications: { title: string; authors: string; doi: string }[];
  availability: "both" | "dataset" | "publication" | "metadata_only";
  has_dataset: boolean; has_publication: boolean; file_counts: Record<string, number>; tabular_file_count: number;
  index_chunks: Record<string, number>; index_chunk_total: number; known_gaps: { file: string; problem: string }[];
  unreadable_pdfs: number; skipped_files: number; limitations: string[];
  rank?: Rank;
};
