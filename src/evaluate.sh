python -m vanilla_nugget_generation.main --input /Users/nfarzi/Documents/nextpoint/Summarization-SHARED-EXTERNALLY/data/001-Original9/transcripts/text/20240102/01.txt -o /Users/nfarzi/Documents/nextpoint/results/nuggets/01-nuggets.json   --sso-profile nfarzi-dev


python -m vanilla_nuggetbased_evaluation.main --nuggets "./results/nuggets/01-nuggets_hierarchical.json" --summary "Summarization-SHARED-EXTERNALLY/data/001-Original9/summaries/nextpoint-generated/20241119a/chron_stage1/01_results_chron_20241119_1.txt"