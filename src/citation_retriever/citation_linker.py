from typing import List, Dict, Set

from .deposition_processor import DepositionProcessor
from .summary_parser import Summary

class CitationLinker:
    def __init__(self, summary: Summary, deposition_processor: DepositionProcessor):
        self.summary = summary
        self.deposition_processor = deposition_processor

    def link_citations_to_transcript(self, include_uncited: bool = True) -> List[Dict]:
        """Link summary citations to deposition transcript text, creating separate entries for each citation range."""
        summary_facts = self.summary.make_summary_facts()
        citation_data = []
        cited_ranges: Set[tuple] = set()

        # Process cited sections
        for summary_fact in summary_facts:
            # Iterate through each individual citation within this summary fact
            for citation in summary_fact.citations:  
                start_page = citation.from_page
                end_page = citation.to_page
                start_line = citation.from_line
                end_line = citation.to_line
                
                # Create citation part string for this specific citation
                if start_line is not None and end_line is not None:
                    if end_page and end_page != start_page:
                        citation_part = f"{start_page}:{start_line}-{end_page}:{end_line}"
                    else:
                        citation_part = f"{start_page}:{start_line}-{end_line}"
                else:
                    if end_page and end_page != start_page:
                        citation_part = f"{start_page}-{end_page}"
                    else:
                        citation_part = f"{start_page}"

                # Handle both page-only and page+line citations
                citation_entry = self.deposition_processor.retrieve_text_for_range(
                    start_page, end_page, start_line, end_line
                )
                citation_entry["is_cited"] = True
                citation_entry["cited"] = True  # For frontend compatibility
                citation_entry["summary_fact"] = summary_fact.text
                citation_entry["citation_str"] = summary_fact.citation_str  # Full citation string
                citation_entry["citation_part"] = citation_part  # Individual citation part
                citation_entry["page"] = start_page  # For frontend compatibility

                # Track cited ranges
                end_page = end_page or start_page
                cited_ranges.update(self.deposition_processor.get_cited_ranges(start_page, end_page, start_line, end_line))
                citation_data.append(citation_entry)

        # Add uncited sections if requested
        if include_uncited:
            uncited_sections = self.deposition_processor.get_uncited_sections(cited_ranges)
            for section in uncited_sections:
                citation_entry["is_cited"] = False
                section["cited"] = False
                section["page"] = section.get("start_page", 1)  # For frontend compatibility
            citation_data.extend(uncited_sections)

        # Sort by page and line number for consistent display
        sorted_citation_data = sorted(citation_data, key=lambda x: (x["start_page"], x["start_line"] or 0))
        
        return sorted_citation_data, citation_data