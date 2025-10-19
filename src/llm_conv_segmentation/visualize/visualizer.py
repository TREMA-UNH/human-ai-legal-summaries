import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from collections import defaultdict
import plotly.express as px
from typing import List, Dict
import gzip
import argparse
import textwrap

class SegmentVisualizer:
    def __init__(self, data_path: str = None, data: List[Dict] = None):
        if data_path:
            self.data = self._load_data(data_path)
        elif data:
            self.data = data
        else:
            self.data = self._generate_sample_data(500)

        self.segment_stats = self._analyze_segments()

    def _load_data(self, file_path: str) -> List[Dict]:
        data = []
        try:
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
        except Exception as e:
            print(f"Error loading data: {e}")
            return []
        return data

    def _generate_sample_data(self, n_samples: int) -> List[Dict]:
        np.random.seed(42)
        segment_weights = np.exp(-np.arange(25) / 8)
        segment_weights = segment_weights / segment_weights.sum()
        data = []
        for i in range(n_samples):
            segment_id = np.random.choice(range(1, 26), p=segment_weights)
            page_num = max(1, int(np.random.normal(25, 15)))
            fact_data = {
                "fact": {
                    "page_number": page_num,
                    "line_number": np.random.randint(1, 25),
                    "question_sa": "Sample question?",
                    "answer_sa": "Sample answer."
                },
                "annotation": {
                    "segment_id": segment_id,
                    "segment_topic": f"Topic for Segment {segment_id}",
                    "reasoning": f"Reasoning for this fact in segment {segment_id}."
                }
            }
            data.append(fact_data)
        return data

    def _analyze_segments(self) -> Dict:
        segment_data = defaultdict(lambda: {
            'count': 0,
            'pages': [],
            'min_page': float('inf'),
            'max_page': 0,
            'segment_topic': ''
        })

        for item in self.data:
            seg_id = item['annotation']['segment_id']
            page = item['fact']['page_number']

            segment_data[seg_id]['count'] += 1
            segment_data[seg_id]['pages'].append(page)
            segment_data[seg_id]['min_page'] = min(segment_data[seg_id]['min_page'], page)
            segment_data[seg_id]['max_page'] = max(segment_data[seg_id]['max_page'], page)
            segment_data[seg_id]['segment_topic'] = item['annotation'].get('segment_topic', '')

        for seg_id in segment_data:
            segment_data[seg_id]['page_span'] = (
                segment_data[seg_id]['max_page'] - segment_data[seg_id]['min_page'] + 1
            )

        return dict(segment_data)

    def create_segment_overview_dashboard(self, save_path: str = None):
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Deposition Segment Analysis Dashboard', fontsize=16, fontweight='bold')

        segments = sorted(self.segment_stats.keys(), key=lambda x: self.segment_stats[x]['count'], reverse=True)
        counts = [self.segment_stats[s]['count'] for s in segments]
        page_spans = [self.segment_stats[s]['page_span'] for s in segments]

        # 1. Segment Size Distribution
        ax1 = axes[0, 0]
        bars = ax1.bar(segments, counts, color='steelblue', alpha=0.7)
        ax1.set_title('Facts per Segment', fontweight='bold')
        ax1.set_xlabel('Segment ID (sorted by size)')
        ax1.set_ylabel('Number of Facts')
        ax1.grid(True, alpha=0.3)

        # for i, (bar, count) in enumerate(zip(bars, counts)):
        #     if i < 10:
        #         ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
        #                  str(count), ha='center', va='bottom', fontweight='bold')

        # # 2. Page Span Analysis
        # ax2 = axes[0, 1]
        # ax2.scatter(segments, page_spans, s=np.array(counts)*20, alpha=0.6)
        # ax2.set_title('Segment Page Span (Bubble size = Fact count)', fontweight='bold')
        # ax2.set_xlabel('Segment ID (sorted by size)')
        # ax2.set_ylabel('Page Span')
        # ax2.grid(True, alpha=0.3)

        # 3. Segment Topic Table
        ax3 = axes[0,1]
        ax3.axis('off')
        topic_text = "MOST IMPORTANT SEGMENTS (by size)\n" + "="*40 + "\n"
        for seg_id in segments[:15]:
            topic = self.segment_stats[seg_id]['segment_topic']
            # topic_text += f"Segment {seg_id}:\n{textwrap.shorten(topic, width=60)}\n"
            wrapped_topic = textwrap.wrap(topic, width=60)
            topic_text += f"Segment {seg_id}:\n" + "\n".join(wrapped_topic) + "\n"
        ax3.text(0.05, 0.95, topic_text, transform=ax3.transAxes, 
                 fontsize=10, verticalalignment='top', fontfamily='monospace')

        # 4. Top Segment Summary
        ax4 = axes[1, 0]
        ax4.axis('off')
        summary_text = "TOP SEGMENTS SUMMARY\n" + "="*30 + "\n"
        top_segments = segments[:5]
        for i, seg_id in enumerate(top_segments):
            seg = self.segment_stats[seg_id]
            summary_text += f"{i+1}. Segment {seg_id}: {seg['count']} facts, Pages {seg['min_page']}-{seg['max_page']}\n"
        ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
                 fontsize=10, verticalalignment='top', fontfamily='monospace')

        ax2 = axes[1, 1]
        ax2.axis('off')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Dashboard saved to {save_path}")
        plt.show()

    def create_interactive_segment_timeline(self, save_path: str = None):
        timeline_data = []
        for item in self.data:
            timeline_data.append({
                'segment_id': item['annotation']['segment_id'],
                'segment_topic': item['annotation'].get('segment_topic', ''),
                'reasoning': item['annotation'].get('reasoning', ''),
                'page': item['fact']['page_number'],
                'line': item['fact']['line_number'],
                'question': item['fact']['question_sa'],
                'answer': item['fact']['answer_sa']
            })

        df = pd.DataFrame(timeline_data)
        df['question'] = df['question'].apply(lambda x: '<br>'.join(textwrap.wrap(str(x), width=30)))
        df['answer'] = df['answer'].apply(lambda x: '<br>'.join(textwrap.wrap(str(x), width=30)))
        df['reasoning'] = df['reasoning'].apply(lambda x: '<br>'.join(textwrap.wrap(str(x), width=40)))

        fig = px.scatter(df,
                         x='page',
                         y='segment_id',
                         color='segment_id',
                         hover_data=['line', 'question', 'answer', 'segment_topic', 'reasoning'],
                         title=f'Segment Timeline Across Pages for {save_path}',
                         labels={
                             'page': 'Page Number',
                             'segment_id': 'Segment ID'
                         })

        fig.update_layout(
            width=1200,
            height=600,
            showlegend=True
        )

        if save_path:
            fig.write_html(save_path)
            print(f"Interactive timeline saved to {save_path}")

        fig.show()

    def print_segment_summary(self):
        print("\n" + "="*60)
        print("DEPOSITION SEGMENT ANALYSIS SUMMARY")
        print("="*60)

        segments = sorted(self.segment_stats.keys(), key=lambda x: self.segment_stats[x]['count'], reverse=True)
        total_facts = len(self.data)

        print(f"Total Facts Analyzed: {total_facts}")
        print(f"Number of Segments: {len(segments)}")
        print(f"Average Facts per Segment: {total_facts/len(segments):.1f}")

        print(f"\nTOP 5 LARGEST SEGMENTS:")
        print("-" * 40)
        for seg_id in segments[:5]:
            data = self.segment_stats[seg_id]
            print(f"Segment {seg_id:2d}: {data['count']:3d} facts | "
                  f"Topic: {data['segment_topic'][:40]} | "
                  f"Pages: {data['min_page']}-{data['max_page']} "
                  f"(span: {data['page_span']})")

# Usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize segments from a .jsonl.gz file of fact annotations")
    parser.add_argument("--input", type=str, required=True, help="Path to input .jsonl.gz file")
    parser.add_argument("-o", "--output", type = str, required = True, help = "name of the output file to generate the .png and .html of it.")
    args = parser.parse_args()

    visualizer = SegmentVisualizer(data_path=args.input)
    visualizer.print_segment_summary()
    visualizer.create_segment_overview_dashboard(save_path=f"{args.output}.png")
    visualizer.create_interactive_segment_timeline(save_path=f"{args.output}.html")
