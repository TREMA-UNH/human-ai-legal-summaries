# import json
# from pathlib import Path
# import os

# from citation_retriever.summary_parser import Summary
# import logging

# logging_config = logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# def render_scores(criteria_scores):
#     html = ""
#     for criterion, data in criteria_scores.items():
#         html += f"<div class='score-block'>"
        
#         # Handle structure evaluation's different score format
#         if criterion.lower() == 'structure':
#             html += f"<h3>{criterion.title()}</h3>"
            
#             # Handle the new score format: [{"structured": true/false}, {"logical flow": true/false}]
#             score_data = data.get('score', [])
#             if isinstance(score_data, list):
#                 html += "<div class='structure-scores'>"
#                 for score_item in score_data:
#                     for key, value in score_item.items():
#                         status = "✓" if value else "✗"
#                         color = "#27ae60" if value else "#e74c3c"
#                         html += f"<p style='color: {color};'><strong>{key.title()}:</strong> {status}</p>"
#                 html += "</div>"
#             else:
#                 # Fallback for regular score format
#                 html += f"<span class='score'>Score: {round(data.get('score', 0), 2)}</span>"
#         else:
#             # Regular scoring for other criteria
#             html += f"<h3>{criterion.title()} <span class='score'>Score: {round(data.get('score', 0), 2)}</span></h3>"

#         explanation = data.get("explanation", "")
#         if explanation:
#             html += f"<p style='color: black'><strong>Explanation:</strong> {explanation}</p>"

#         details = data.get("details")
#         if details:
#             html += "<div class='details'><ul>"
#             if isinstance(details, list):
#                 for d in details:
#                     nugget = d.get("nugget", "")
#                     presence = d.get("presence_score", "")
#                     expl = d.get("explanation", "")
#                     html += f"""<li style='color: black;'>
#                                     <span style='color: #555;'><strong>Nugget:</strong> {nugget}</span><br>
#                                     <span style='color: #555;'><strong>Presence:</strong> {presence}</span><br>
#                                     <strong>Explanation:</strong> {expl}
#                                 </li>"""
#             elif isinstance(details, dict):
#                 for k, v in details.items():
#                     html += f"<li style='color: black;'><strong>{k}:</strong> {v}</li>"
#             html += "</ul></div>"
#         html += "</div>"
#     return html


# def render_stats(stats):
#     return f"""
#     <div class='stats'>
#         <h3>Stats</h3>
#         <p style='color: #354051;'><strong>Total Consolidated Nuggets:</strong> {stats.get('total_consolidated_nuggets')}</p>
#         <p style='color: #354051;'><strong>Total Original Nuggets:</strong> {stats.get('total_original_nuggets')}</p>
#         <p style='color: #354051;'><strong>Summary Length:</strong> {stats.get('summary_length')} words</p>
#     </div>
#     """



# def generate_side_by_side_html(data, title="Summary -- Evaluation Report"):
#     summary_text = data.get("summary", "")
#     summary_path = data.get("summary_path", "")
#     logger.info(f"summary_path:{summary_path}")
#     summary = Summary(summary_path = summary_path)
#     summary_facts = summary.make_summary_facts()
#     logger.info(f"summary_facts:{summary_facts}")
#     formatted_summary = summary_text.replace('\n', '<br>')
#     for fact in summary_facts:
#         citation_id = f"citation-{hash(fact.citation_str)}"  # Unique ID for each citation
#         clickable_citation = f"<a href='#' class='citation-link' id='{citation_id}' onclick='handleCitationClick(\"{fact.citation_str}\")'>{fact.citation_str}</a>"
#         formatted_summary = formatted_summary.replace(fact.citation_str, clickable_citation)
#     logger.info(f"formatted_summary={formatted_summary}")



#     criteria_scores = data.get("criteria_scores", {})
#     stats = data.get("stats", {})

#     score_html = render_scores(criteria_scores) + render_stats(stats)
#     html_template = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <title>{title}</title>
#         <style>
#             body {{
#                 font-family: 'Segoe UI', sans-serif;
#                 margin: 0;
#                 padding: 0;
#                 background-color: #354051;
#             }}
#             h1 {{
#                 text-align: center;
#                 background: #F04E24;
#                 color: white;
#                 padding: 20px 0;
#                 margin-bottom: 0;
#             }}
#             .container {{
#                 display: flex;
#                 padding: 30px;
#                 gap: 20px;
#             }}
#             .column {{
#                 flex: 1;
#                 background-color: #fff;
#                 padding: 20px;
#                 border-radius: 8px;
#                 box-shadow: 0 1px 5px rgba(0,0,0,0.1);
#                 overflow-wrap: break-word;
#             }}
#             .left-column {{
#                 height: 70vh;
#                 overflow-y: auto; 
#                 flex: 1.4;
#                 border-left: 6.5px solid #6F7D95;
#             }}
#             .right-column {{
#                 height: 70vh;
#                 overflow-y: auto; 
#                 flex: 0.6;
#                 border-left: 4.5px solid #364052;
#             }}
#             .score-block {{
#                 margin-bottom: 25px;
#             }}
#             .score {{
#                 color: #27ae60;
#                 float: right;
#             }}
#             .structure-scores {{
#                 margin: 10px 0;
#                 padding: 10px;
#                 background: #f8f9fa;
#                 border-radius: 5px;
#             }}
#             .details ul {{
#                 list-style: none;
#                 padding-left: 0;
#             }}
#             .details li {{
#                 background: #f0f0f0;
#                 padding: 10px;
#                 margin: 5px 0;
#                 border-radius: 5px;
#             }}
#             .stats {{
#                 margin-top: 40px;
#                 background: #ecf0f1;
#                 padding: 15px;
#                 border-radius: 6px;
#             }}
#             .citation-link {{
#                 color: #2ecc71;
#                 text-decoration: none;
#                 cursor: pointer;
#             }}
#             .citation-link:hover {{
#                 text-decoration: underline;
#             }}
#         </style>
#         <script>
#             document.addEventListener('DOMContentLoaded', function() {{
#                 const citationLinks = document.querySelectorAll('.citation-link');
#                 console.log('Found ' + citationLinks.length + ' citation links');
#                 citationLinks.forEach(link => {{
#                     link.addEventListener('click', function(event) {{
#                         event.preventDefault();
#                         const citation = this.getAttribute('data-citation');
#                         console.log('Citation clicked: ' + citation);
#                         // Add your custom functionality here
#                         alert('Citation clicked: ' + citation);
#                     }});
#                 }});
#             }});
#         </script>
#     </head>
#     <body>
#         <h1>{title}</h1>
#         <div class="container">
#             <div class="column left-column">
#                 <h2 style='color: black;'>Summary</h2>
#                 <p style='color: black;'>{formatted_summary}</p>
#             </div>
#             <div class="column right-column">
#                 <h2 style='color: black;'>Evaluation Scores</h2>
#                 {score_html}
#             </div>
#         </div>
#     </body>
#     </html>
#     """
#     return html_template


# def save_html(data, output_path="final_report.html"):
#     data = replace_newlines(data)

#     html = generate_side_by_side_html(data)
#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(html)
#     print(f"Report saved to {output_path}")


# def replace_newlines(obj):
#     if isinstance(obj, dict):
#         return {k: replace_newlines(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [replace_newlines(elem) for elem in obj]
#     elif isinstance(obj, str):
#         return obj.replace('\n', '<br>')
#     else:
#         return obj