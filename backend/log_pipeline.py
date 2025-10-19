import csv
from datetime import datetime
import os 


def log_pipeline_run(deposition_name, summary_name, depo_word_count, summary_word_count, step1_run, step2_run, CSV_LOG_PATH):
    log_exists = os.path.exists(CSV_LOG_PATH)
    with open(CSV_LOG_PATH, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not log_exists:
            writer.writerow([
                "Date and Time",
                "Deposition Name",
                "Summary Name",
                "Depo Length (words)",
                "Summary Length (words)",
                "Step 1 Run (Nugget Generation)",
                "Step 2 Run (Evaluation)",
            ])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            deposition_name,
            summary_name,
            depo_word_count,
            summary_word_count,
            step1_run,
            step2_run,
        ])
        writer.writerow([
            "Date and Time",
            "call description",
            "number of calls",
            "calls input tokens",
            "calls output tokens",
            "calls cost",
            "total calls time"
        ])

def log_each_generation(call_description, number_of_calls, calls_input_tokens, calls_output_tokens, calls_cost, total_calls_time, CSV_LOG_PATH):
    log_exists = os.path.exists(CSV_LOG_PATH)
    if log_exists:
        with open(CSV_LOG_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            call_description,
            number_of_calls,
            calls_input_tokens,
            calls_output_tokens,
            calls_cost,
            total_calls_time
            
        ])

