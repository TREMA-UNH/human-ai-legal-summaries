from typing import List, Dict, Tuple, Optional
import re
from transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file

class DepositionProcessor:
    def __init__(self, deposition_path: str):
        self.deposition_path = deposition_path
        self.lines_with_metadata: List[Tuple[int, Optional[int], str]] = []

    def load_transcript(self):
        """Load deposition transcript and store lines with page and line metadata."""
        lines = read_transcript_file(self.deposition_path)
        current_page = 0
        for i, line in enumerate(lines, 1):
            if '\f' in line:
                number_match = re.search(r'(\d+)', line.split('\f', 1)[-1])
                if number_match:
                    current_page = int(number_match.group(1))
            elif re.match(r"^\s*\d+\s+", line.strip()):
                line_number_match = re.match(r"^\s*(\d+)", line.strip())
                if line_number_match:
                    line_number = int(line_number_match.group(1))
                    self.lines_with_metadata.append((current_page, line_number, line.strip()))
            else:
                self.lines_with_metadata.append((current_page, None, line.strip()))

    def retrieve_text_for_range(self, start_page: int, end_page: Optional[int], start_line: Optional[int], end_line: Optional[int]) -> Dict:
        """Retrieve transcript text for a given page/line range."""
        if not self.lines_with_metadata:
            self.load_transcript()

        end_page = end_page or start_page
        citation_id = f"citation_{start_page}_{start_line if start_line is not None else 'page'}_{end_page}_{end_line if end_line is not None else 'page'}"

        def in_line_range(pg, ln):
            if ln is None:
                return False
            if pg == start_page and start_line is not None and ln < start_line:
                return False
            if pg == end_page and end_line is not None and ln > end_line:
                return False
            return True

        matching_lines = []
        for pg, ln, line in self.lines_with_metadata:
            if not (start_page <= pg <= end_page):
                continue

            if start_line is not None or end_line is not None:
                if in_line_range(pg, ln):
                    matching_lines.append((pg, ln, line))
            else:
                matching_lines.append((pg, ln, line))

        formatted_text = "\n".join(line for _, _, line in matching_lines) if matching_lines else "No text found for this range."

        return {
            "citation_id": citation_id,
            "citation_str": None,
            "start_page": start_page,
            "end_page": end_page,
            "start_line": start_line,
            "end_line": end_line,
            "text": formatted_text,
            "link": f"#{citation_id}",
            "lines": [(pg, ln) for pg, ln, _ in matching_lines]
        }




    def get_cited_ranges(self, from_page: int, to_page: int, from_line: Optional[float], to_line: Optional[float]) -> set[Tuple]:
        if not self.lines_with_metadata:
            self.load_transcript()

        cited_ranges: set[Tuple] = set()
        use_lines = from_line is not None or to_line is not None

        for pg, ln, _ in self.lines_with_metadata:
            if not (from_page <= pg <= to_page) or ln is None:
                continue
            if use_lines:
                if pg == from_page and from_line is not None and from_line > 0 and ln < from_line:
                    continue
                if pg == to_page and to_line is not None and to_line > 0 and ln > to_line:
                    continue
            cited_ranges.add((pg, ln))

        return set(sorted(cited_ranges, key=lambda x: (x[0], x[1] or 0)))



    def get_uncited_sections(self, cited_ranges: set) -> List[Dict]:
        """Identify and group uncited transcript sections."""
        if not self.lines_with_metadata:
            self.load_transcript()

        uncited_sections = []
        current_section = []
        current_page = None
        current_start_line = None

        for pg, ln, line in self.lines_with_metadata:
            if (pg, ln) not in cited_ranges and line.strip():
                if current_page != pg or (ln is not None and current_start_line is not None and ln != current_start_line + 1):
                    if current_section:
                        uncited_sections.append({
                            "citation_id": None,
                            "citation_str": None,
                            "start_page": current_page,
                            "end_page": current_page,
                            "start_line": current_start_line,
                            "end_line": current_start_line + len(current_section) - 1 if current_start_line is not None else None,
                            "text": "\n".join(current_section),
                            "link": None,
                            "is_cited": False,
                            "lines": [(current_page, current_start_line + i if current_start_line is not None else None) for i in range(len(current_section))]
                        })
                    current_section = [line]
                    current_page = pg
                    current_start_line = ln
                else:
                    current_section.append(line)
            elif current_section:
                uncited_sections.append({
                    "citation_id": None,
                    "citation_str": None,   
                    "start_page": current_page,
                    "end_page": current_page,
                    "start_line": current_start_line,
                    "end_line": current_start_line + len(current_section) - 1 if current_start_line is not None else None,
                    "text": "\n".join(current_section),
                    "link": None,
                    "is_cited": False,
                    "lines": [(current_page, current_start_line + i if current_start_line is not None else None) for i in range(len(current_section))]
                })
                current_section = []

        if current_section:
            uncited_sections.append({
                "citation_id": None,
                "citation_str": None,
                "start_page": current_page,
                "end_page": current_page,
                "start_line": current_start_line,
                "end_line": current_start_line + len(current_section) - 1 if current_start_line is not None else None,
                "text": "\n".join(current_section),
                "link": None,
                "is_cited": False,
                "lines": [(current_page, current_start_line + i if current_start_line is not None else None) for i in range(len(current_section))]
            })

        return uncited_sections