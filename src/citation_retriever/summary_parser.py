
from pydantic import BaseModel, root_validator
from typing import Optional, List
import re
from transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file

class Citation(BaseModel):
    from_page: Optional[int] = None
    to_page: Optional[int] = None
    from_line: Optional[int] = None
    to_line: Optional[int] = None

class SummaryFact(BaseModel):
    text: str
    citations: List[Citation]
    fact_text_with_citation: str
    citation_str: str

class Summary(BaseModel):
    summary_path: str
    text: Optional[str] = None

    @root_validator(pre=True)
    def populate_text(cls, values):
        path = values.get('summary_path')
        if path and 'text' not in values:
            values['text'] = "\n".join(read_transcript_file(path))
        return values


    def summary_loader(self) -> str:
        """Load the content of the deposition transcript file."""
        try:
            with open(self.summary_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.summary_path}")
        except Exception as e:
            raise Exception(f"Error reading file {self.summary_path}: {str(e)}")

    def _parse_citation(self, citation_str: str, regex_type: str) -> List[Citation]:
        """Parse citation string based on which regex matched it."""
        citations = []
        
        # Remove parentheses if present
        clean_citation = citation_str.strip('()')
        
        if regex_type in ['R1', 'R2', 'R3', 'R6']:
            # Handle line-based citations (page:line format)
            # Split by comma for multiple ranges
            ranges = [r.strip() for r in clean_citation.split(',')]
            
            for range_str in ranges:
                if ':' in range_str:
                    # Line-based format: "9:1-24:11" or "37:22-24"
                    parts = range_str.split('-')
                    if len(parts) == 2:
                        start_part = parts[0].strip()
                        end_part = parts[1].strip()
                        
                        # Parse start
                        start_page, start_line = map(int, start_part.split(':'))
                        
                        # Parse end
                        if ':' in end_part:
                            end_page, end_line = map(int, end_part.split(':'))
                        else:
                            # Same page, different line: "37:22-24"
                            end_page = start_page
                            end_line = int(end_part)
                        
                        citations.append(Citation(
                            from_page=start_page,
                            to_page=end_page,
                            from_line=start_line,
                            to_line=end_line
                        ))
                else:
                    # Page-only format within mixed: "121-124"
                    parts = range_str.split('-')
                    if len(parts) == 2:
                        start_page = int(parts[0].strip())
                        end_page = int(parts[1].strip())
                        
                        citations.append(Citation(
                            from_page=start_page,
                            to_page=end_page,
                        ))
        
        elif regex_type in ['R4', 'R5']:
            # Handle page-only citations
            ranges = [r.strip() for r in clean_citation.split(',')]
            
            for range_str in ranges:
                parts = range_str.split('-')
                if len(parts) == 2:
                    start_page = int(parts[0].strip())
                    end_page = int(parts[1].strip())
                    
                    citations.append(Citation(
                        from_page=start_page,
                        to_page=end_page,
                    ))
        
        return citations

    def _identify_regex_type(self, citation_str: str) -> str:
        """Identify which regex pattern matched the citation."""
        R1 = r"\d+:\d+-\d+(?::\d+)?"  # Single range with lines
        R2 = r"\d+:\d+-\d+(?::\d+)?(?:,\s*\d+:\d+-\d+(?::\d+)?)+"  # Multiple ranges with lines
        R3 = r"\((?:\d+:\d+-\d+(?::\d+)?(?:,\s*\d+:\d+-\d+(?::\d+)?)*)\)"  # Parentheses, lines
        R4 = r"\(\d+-\d+\)"  # Single page-only range
        R5 = r"\((?:\d+-\d+(?:,\s*\d+-\d+)+)\)"  # Multiple page-only ranges
        R6 = r"(?:(?:\d+:\d+-\d+(?::\d+)?|\d+-\d+)(?:,\s*(?:\d+:\d+-\d+(?::\d+)?|\d+-\d+))+)"  # Mixed ranges
        
        # Check in order of specificity
        if re.fullmatch(R3, citation_str):
            return 'R3'
        elif re.fullmatch(R5, citation_str):
            return 'R5'
        elif re.fullmatch(R4, citation_str):
            return 'R4'
        elif re.fullmatch(R2, citation_str):
            return 'R2'
        elif re.fullmatch(R6, citation_str):
            return 'R6'
        elif re.fullmatch(R1, citation_str):
            return 'R1'
        else:
            return 'UNKNOWN'
    def make_summary_facts(self) -> List[SummaryFact]:
            """Extract citations from the transcript and create SummaryFact objects."""
            # Load the transcript content
            content = self.summary_loader()
            
            # Regex patterns
            R1 = r"\d+:\d+-\d+(?::\d+)?"  # Single range with lines, e.g., "9:1-24:11" or "37:22-24"
            R2 = r"\d+:\d+-\d+(?::\d+)?(?:,\s*\d+:\d+-\d+(?::\d+)?)+"  # Multiple ranges with lines
            R3 = r"\((?:\d+:\d+-\d+(?::\d+)?(?:,\s*\d+:\d+-\d+(?::\d+)?)*)\)"  # Parentheses, lines
            R4 = r"\(\d+-\d+\)"  # Single page-only range, e.g., "(121-124)"
            R5 = r"\((?:\d+-\d+(?:,\s*\d+-\d+)+)\)"  # Multiple page-only ranges, e.g., "(126-127, 139-142)"
            R6 = r"(?:(?:\d+:\d+-\d+(?::\d+)?|\d+-\d+)(?:,\s*(?:\d+:\d+-\d+(?::\d+)?|\d+-\d+))+)"  # Mixed ranges
            RANGE_PATTERN = r"\d+:\d+-\d+(?::\d+)?|\d+-\d+"  # Matches individual ranges (line or page-only)

            FULL_PATTERN = rf"({R1}|{R2}|{R3}|{R4}|{R5}|{R6}|{RANGE_PATTERN})"

            
            # # Find all matches with their positions
            # matches = list(re.finditer(FULL_PATTERN, content))

            # facts = re.split(FULL_PATTERN, content)
            # print(facts)

            
            summary_facts = []
            

            # Find all matches with their positions
            matches = list(re.finditer(FULL_PATTERN, content))

            # Cut off intro before first citation
            if matches:
                first_citation_start = matches[0].start()
                intro_cutoff = 0
                before_citation = content[:first_citation_start]

                # Try to find a clean break (e.g., empty line or table separator)
                for m in re.finditer(r"(?:\n\s*\n|^\|[-| ]+\|$)", before_citation, flags=re.MULTILINE):
                    intro_cutoff = m.end()

                # Trim content and re-run everything
                content = content[intro_cutoff:]
                matches = list(re.finditer(FULL_PATTERN, content))
                facts = re.split(FULL_PATTERN, content)
            else:
                facts = re.split(FULL_PATTERN, content)

            for i, match in enumerate(matches):
                citation_str = match.group(1)
                regex_type = self._identify_regex_type(citation_str)
                
                # Parse citations based on regex type
                citations = self._parse_citation(citation_str, regex_type)
                fact_text = facts[2*i]

                fact_text_with_citation = " ".join(facts[2*i:2*i+2])
                # Remove the citation from the text
                fact_text = fact_text.replace(citation_str, '').strip()
                
                if fact_text and citations:  # Only add if we have both text and citations
                    summary_facts.append(SummaryFact(
                        text=fact_text,
                        citations=citations,
                        fact_text_with_citation = fact_text_with_citation,
                        citation_str = citation_str
                    ))
                    
                    print(f"Citation: {citation_str}")
                    print(f"Regex Type: {regex_type}")
                    print(f"Parsed Citations: {citations}")
                    print(f"Text: {fact_text[:100]}...")
                    print("-" * 50)
            
            return summary_facts
    
    

