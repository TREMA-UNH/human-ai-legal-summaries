export interface Citation {
  from_page: number | null;
  to_page: number | null;
  from_line: number | null;
  to_line: number | null;
}

export interface SummaryFact {
  text: string;
  citations: Citation[];
  citation_str: string;
}

export interface CitationData {
  citation_id: string | null;
  start_page: number | null;
  end_page: number | null;
  start_line: number | null;
  end_line: number | null;
  text: string;
  link: string | null;
  is_cited: boolean;
  summary_fact?: string;
  lines: Array<[number | null, number | null]>;
}