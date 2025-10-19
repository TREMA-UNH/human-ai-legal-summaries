
from citation_retriever.citation_linker import CitationLinker
from citation_retriever.deposition_processor import DepositionProcessor
from citation_retriever.summary_parser import Summary
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-deposition", type=str, help = "path to deposition file.")
    parser.add_argument("--input-summary", type=str, help="path to summary file.")
    args = parser.parse_args()
    summary_path, deposition_path = args.input_summary, args.input_deposition
    
    summary = Summary(summary_path=summary_path)
    deposition_processor = DepositionProcessor(deposition_path=deposition_path)
    linker = CitationLinker(summary, deposition_processor)
    
    sorted_citation_data, _ = linker.link_citations_to_transcript(include_uncited=True)
    new_line = "\n"

    for entry in sorted_citation_data[::500]:
        print(f"ID: {entry['citation_id']}")
        print(f"Citation str in the summary: {entry['citation_str']}")
        print(f"Page {entry['start_page']}:{entry['start_line'] or 'N/A'}-{entry['end_page']}:{entry['end_line'] or 'N/A'}")
        print(f"Text: {entry['text'][:100]}...") if entry['is_cited']==False else print(f"Text: {new_line.join(entry['text'].split(new_line)[::5])}...")
        print(f"Link: {entry['link']}")
        print(f"Cited: {entry['is_cited']}")
        print(f"Summary Fact: {entry.get('summary_fact', 'N/A')}")
        print("-" * 50)

    return sorted_citation_data

if __name__ == "__main__":
    main()