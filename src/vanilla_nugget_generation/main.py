# run_deposition_nuggets.py
import argparse
from .DepositionNuggetGeneration import DepositionNuggetGenerator
from transcript_analysis.models.TokenTracker import token_tracker
from config import CONFIG

def main():
    parser = argparse.ArgumentParser("Extract nuggets from deposition")
    parser.add_argument("--input", required=True, help=".txt deposition file.")
    parser.add_argument("-o", "--output", required=True, help=".json output path to stoe the nuggets and hierarchichal nuggets.")
    parser.add_argument("--chunk-size", type=int, default=10000, help = "Chunk size for chunking the input before passing it to the LLM")
    parser.add_argument("--overlap", type=int, default=5, help = "# of Q&A pairs overlapping during chunking")
    parser.add_argument("--print-usage", action="store_true", help = "logs each API call usage")
    parser.add_argument("--total-usage", action="store_true", help = "logs the total usage summary")
    parser.add_argument("--mode", type=str, default="consolidated", help = "mode for nugget generation. Can be consolidated or mapping")
    parser.add_argument("--sso-profile", type=str, required=True, help="aws sso profile set in ~/.aws/config.")
    args = parser.parse_args()

    generator = DepositionNuggetGenerator(
        input_path=args.input,
        output_path=args.output,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        print_usage=args.print_usage,
        mode=args.mode)

    generator.run()
    token_tracker.summary() if args.total_usage else None

if __name__ == "__main__":
    main()
