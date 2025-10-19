from typing import List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pydantic import BaseModel
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER


# Citation model used across all tools
class Citation(BaseModel):
    page_from: int
    line_from: int
    page_to: int
    line_to: int

    def format_citation(self) -> str:
        """Format citation as (page:line-line) or (page:line-page:line)"""
        if self.page_from == self.page_to:
            return f"({self.page_from}:{self.line_from}-{self.line_to})"
        else:
            return f"({self.page_from}:{self.line_from}-{self.page_to}:{self.line_to})"

# Helper functions for PDF generation
def _create_pdf_document(filename: str, title: str) -> tuple:
    """Create a PDF document with common styles and settings."""
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=12,
        alignment=1  # Center
    )
    body_style = ParagraphStyle(
        name='Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    styleN = styles["BodyText"]
    styleN.alignment = TA_LEFT
    styleDC = styles["Normal"]
    styleDC.alignment = TA_CENTER
    elements = [Paragraph(title, title_style)]
    return doc, elements, body_style, styleN, styleDC

def _create_table(data: List[List[Paragraph]], col_widths: List[float]) -> Table:
    """Create a styled table for PDF output."""
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Align text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold header
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Header padding
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Body background
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Grid lines
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Body font
        ('FONTSIZE', (0, 1), (-1, -1), 10),  # Body font size
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Cell padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table

# Narrative Summary Tool Models
class sentence(BaseModel):
    content: str
    citations: List[Citation]

class NParagraph(BaseModel):
    sentences: List[sentence]

class NarrativeSummary(BaseModel):
    paragraphs: List[NParagraph]

class NarrativeSummaryTool(BaseModel):
    narrative_summary: NarrativeSummary

    def to_pdf(self, filename: str = "narrative_summary.pdf") -> str:
        """Generate a PDF for NarrativeSummary with formatted paragraphs."""
        doc, elements, body_style, _, _ = _create_pdf_document(filename, "Narrative Summary")
        for para in self.narrative_summary.paragraphs:
            pcontent = ""
            for sent in para.sentences:
                content = sent.content
                citations = [c.format_citation() for c in sent.citations]
                citation_text = " ".join(citations)
                if citation_text:
                    content += f" {citation_text}"
                pcontent += content + " "
            elements.append(Paragraph(pcontent.strip(), body_style))
            elements.append(Paragraph("", body_style))
        doc.build(elements)
        return f"PDF generated: {filename}"

# Table of Contents Summary Tool Models
class TocEntry(BaseModel):
    citation: Citation
    description: str

class TocSummary(BaseModel):
    entries: List[TocEntry]

class TocSummaryTool(BaseModel):
    toc_summary: TocSummary

    def to_pdf_table(self, filename: str = "toc_summary.pdf") -> str:
        """Generate a PDF table for TocSummary."""
        doc, elements, _, styleN, styleDC = _create_pdf_document(filename, "Table of Contents")
        data = [[Paragraph("Page/Line", styleDC), Paragraph("Description", styleDC)]]
        for event in self.toc_summary.entries:
            data.append([
                Paragraph(event.citation.format_citation(), styleDC),
                Paragraph(event.description, styleN)
            ])
        table = _create_table(data, [1.5*inch, 4*inch])
        elements.append(table)
        doc.build(elements)
        return f"PDF table generated: {filename}"

# Chronological Summary Tool Models
class ChronologicalEvent(BaseModel):
    date: Optional[str] = None
    description: str
    citation: Citation

class ChronologicalSummary(BaseModel):
    chronological_events: List[ChronologicalEvent]

class ChronologicalSummaryTool(BaseModel):
    chronological_summary: ChronologicalSummary

    def to_pdf_table(self, filename: str = "chronological_summary.pdf") -> str:
        """Generate a PDF table for ChronologicalSummary."""
        doc, elements, _, styleN, styleDC = _create_pdf_document(filename, "Chronological Summary")
        data = [[Paragraph("Date", styleDC), Paragraph("Description", styleDC), Paragraph("Page/Line", styleDC)]]
        for event in self.chronological_summary.chronological_events:
            desc = Paragraph(event.description, styleN)
            cit = Paragraph(event.citation.format_citation(), styleDC)
            date = Paragraph(event.date, styleDC) if event.date else Paragraph("", styleDC)
            data.append([date, desc, cit])
        table = _create_table(data, [1.5*inch, 4*inch, 1.5*inch])
        elements.append(table)
        doc.build(elements)
        return f"PDF table generated: {filename}"

# Example usage
def main():
    # Chronological Summary
    chrono_summary = ChronologicalSummaryTool(
        chronological_summary=ChronologicalSummary(
            chronological_events=[
                ChronologicalEvent(
                    # date="--",
                    description="Dr. Zelenko has six children with his first wife, Sima",
                    citation=Citation(page_from=14, line_from=13, page_to=14, line_to=22)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Dr. Zelenko has two children with his second wife, Rinat",
                    citation=Citation(page_from=14, line_from=13, page_to=14, line_to=22)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Dr. Zelenko had retained McDermott Will & Emery to provide estate planning services",
                    citation=Citation(page_from=10, line_from=22, page_to=11, line_to=5)
                ),
                ChronologicalEvent(
                    date="2022",
                    description="Mr. Linder meets Dr. Zelenko and Mr. Linder's firm Greenspoon Marder was retained by Dr. Zelenko for estate planning services",
                    citation=Citation(page_from=9, line_from=19, page_to=10, line_to=10)
                ),
                ChronologicalEvent(
                    date="2022",
                    description="McDermott Will & Emery drafted a family trust",
                    citation=Citation(page_from=11, line_from=15, page_to=12, line_to=3)
                ),
                ChronologicalEvent(
                    date="2022",
                    description="Greenspoon Marder drafted two irrevocable trusts",
                    citation=Citation(page_from=11, line_from=15, page_to=12, line_to=3)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="The first irrevocable trust provides that upon Dr. Zelenko's death, 1) each of his six children would receive $666,666; 2) Dr. Zelenko's parents, Larisa Zelenko and Arkady Zelenko, would receive $250,000; and 3) Dr. Zelenko's brother, Frank Zelenko, would receive $250,000",
                    citation=Citation(page_from=16, line_from=16, page_to=18, line_to=10)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Mr. Linder had a zoom call with Dr. Zelenko and Rinat Zelenko related to the assignment of insurance benefits to satisfy a home mortgage",
                    citation=Citation(page_from=20, line_from=14, page_to=20, line_to=19)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Mr. Linder testified to a text message conversation with Dr. Zelenko in which Dr. Zelenko said 'I want Rinat to be [the] sole beneficiary of [the] 2.5 million policy that has no liens on it. I need her to get that money ASAP.' Dr. Zelenko also texted 'another 500 thousand to come to Rinat when all the other policies clear.'",
                    citation=Citation(page_from=31, line_from=6, page_to=31, line_to=18)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Dr. Zelenko told Mr. Linder that Sima had blocked her kids from contacting Dr. Zelenko's parents, although he does not remember if Dr. Zelenko himself was estranged from Sima's children",
                    citation=Citation(page_from=23, line_from=14, page_to=24, line_to=11)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Dr. Zelenko verbally advised Greenspoon Marder that Moshe Knobel would be the go-between for signing the change of beneficiary form",
                    citation=Citation(page_from=40, line_from=18, page_to=41, line_to=12)
                ),
                ChronologicalEvent(
                    date="2022-06-17",
                    description="Dr. Zelenko allegedly signs change of beneficiary form and assigns proceeds to Rinat Lusting",
                    citation=Citation(page_from=13, line_from=6, page_to=13, line_to=23)
                ),
                ChronologicalEvent(
                    # date="--",
                    description="Mr. Linder verbally follows up with Mr. Knobel shortly after the documents were signed",
                    citation=Citation(page_from=28, line_from=21, page_to=29, line_to=9)
                ),
                ChronologicalEvent(
                    date="2022-06-30",
                    description="Dr. Zelenko passes away",
                    citation=Citation(page_from=10, line_from=17, page_to=10, line_to=21)
                ),
                ChronologicalEvent(
                    date="2022-07-13",
                    description="Email between Mr. Knobel and Mr. Miller reflecting that life insurance document was not signed",
                    citation=Citation(page_from=51, line_from=13, page_to=53, line_to=3)
                ),
                ChronologicalEvent(
                    date="2022-09",
                    description="Rinat's attorney sends Mr. Linder a copy of a trust document reflecting that Rinat would receive $1 million and Rinat's two children would each receive $1 million",
                    citation=Citation(page_from=21, line_from=16, page_to=22, line_to=19)
                ),
            ]
        )
    )

    # Table of Contents Summary
    toc_summary = TocSummaryTool(
        toc_summary=TocSummary(
            entries=[
                TocEntry(
                    citation=Citation(page_from=9, line_from=19, page_to=11, line_to=5),
                    description="Vladimir Zelenko's hiring of Greenspoon Marder"
                ),
                TocEntry(
                    citation=Citation(page_from=11, line_from=10, page_to=12, line_to=11),
                    description="Documents drafted for Dr. Zelenko by Mr. Linder's firm"
                ),
                TocEntry(
                    citation=Citation(page_from=12, line_from=12, page_to=13, line_to=5),
                    description="Overview of dispute"
                ),
                TocEntry(
                    citation=Citation(page_from=13, line_from=6, page_to=13, line_to=23),
                    description="Circumstances relating to the change of beneficiary form allegedly signed by Dr. Zelenko"
                ),
                TocEntry(
                    citation=Citation(page_from=14, line_from=8, page_to=24, line_to=11),
                    description="Dr. Zelenko's family"
                ),
                TocEntry(
                    citation=Citation(page_from=15, line_from=2, page_to=20, line_to=6),
                    description="Ex. 1: The first irrevocable trust for the benefit of his six children with Sima"
                ),
                TocEntry(
                    citation=Citation(page_from=20, line_from=11, page_to=21, line_to=15),
                    description="Mr. Linder's zoom call with Dr. Zelenko and Rinat Zelenko"
                ),
                TocEntry(
                    citation=Citation(page_from=21, line_from=16, page_to=22, line_to=19),
                    description="Rinat's attorney sends Mr. Linder a trust previously executed by Dr. Zelenko which provides Rinat with $1 million and provides each of Rinat's two children with $1 million"
                ),
                TocEntry(
                    citation=Citation(page_from=24, line_from=12, page_to=25, line_to=12),
                    description="Dr. Zelenko's interactions with Greenspoon Marder"
                ),
                TocEntry(
                    citation=Citation(page_from=26, line_from=2, page_to=29, line_to=9),
                    description="Ex. 2: Email to Moshe Knobel"
                ),
                TocEntry(
                    citation=Citation(page_from=29, line_from=10, page_to=31, line_to=18),
                    description="Ex. 3: Text message"
                ),
                TocEntry(
                    citation=Citation(page_from=31, line_from=19, page_to=39, line_to=20),
                    description="Calculations of amounts going to various beneficiaries"
                ),
                TocEntry(
                    citation=Citation(page_from=40, line_from=9, page_to=42, line_to=10),
                    description="Testimony about Moshe Knobel"
                ),
                TocEntry(
                    citation=Citation(page_from=42, line_from=11, page_to=46, line_to=22),
                    description="Testimony about Dr. Zelenko's intent"
                ),
                TocEntry(
                    citation=Citation(page_from=46, line_from=23, page_to=49, line_to=16),
                    description="Ex. 3: Testimony about handwriting on text message"
                ),
                TocEntry(
                    citation=Citation(page_from=49, line_from=17, page_to=50, line_to=9),
                    description="Ex. 4: Email"
                ),
                TocEntry(
                    citation=Citation(page_from=50, line_from=12, page_to=51, line_to=12),
                    description="Ex. 5: Email re timing of moving policies into the trust"
                ),
                TocEntry(
                    citation=Citation(page_from=51, line_from=13, page_to=53, line_to=3),
                    description="Ex. 6: Email between Mr. Knobel and Mr. Miller"
                ),
                TocEntry(
                    citation=Citation(page_from=55, line_from=10, page_to=59, line_to=14),
                    description="Examination by Gielchinsky (Rinat's counsel)"
                ),
                TocEntry(
                    citation=Citation(page_from=59, line_from=15, page_to=59, line_to=25),
                    description="Followup by Mr. Kutner"
                ),
            ]
        )
    )


    narrative_summary = NarrativeSummaryTool(
    narrative_summary=NarrativeSummary(
        paragraphs=[
            NParagraph(
                sentences=[
                    sentence(
                        content="This deposition relates to a dispute over insurance proceeds arising from a $2.5 million Guardian insurance policy.",
                        citations=[Citation(page_from=12, line_from=16, page_to=13, line_to=5)]
                    ),
                    sentence(
                        content="The dispute arises from a change of beneficiary form allegedly signed by Dr. Zelenko.",
                        citations=[Citation(page_from=13, line_from=6, page_to=13, line_to=11)]
                    ),
                    sentence(
                        content="Greenspoon Marder facilitated the execution of the change of beneficiary form by Dr. Zelenko.",
                        citations=[Citation(page_from=13, line_from=12, page_to=13, line_to=18)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Dr. Zelenko has eight children total from two marriages.",
                        citations=[Citation(page_from=14, line_from=13, page_to=14, line_to=22)]
                    ),
                    sentence(
                        content="Dr. Zelenko has six children with his first wife, Sima, and two with his second wife, Rinat.",
                        citations=[Citation(page_from=14, line_from=13, page_to=14, line_to=22)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="In 2022, Mr. Linder’s firm, Greenspoon Marder, was retained by Dr. Zelenko to provide estate planning services.",
                        citations=[Citation(page_from=9, line_from=19, page_to=10, line_to=10)]
                    ),
                    sentence(
                        content="Dr. Zelenko had previously retained McDermott Will & Emery for estate planning services in a different state.",
                        citations=[Citation(page_from=10, line_from=22, page_to=11, line_to=5)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Mr. Linder’s firm prepared some irrevocable trusts by working with McDermott Will & Emery on their drafts of documents.",
                        citations=[Citation(page_from=11, line_from=15, page_to=11, line_to=21)]
                    ),
                    sentence(
                        content="McDermott Will & Emery drafted a family trust and Mr. Linder’s firm drafted two irrevocable trusts.",
                        citations=[Citation(page_from=11, line_from=15, page_to=12, line_to=3)]
                    ),
                    sentence(
                        content="Mr. Linder did not recall discussing the drafting of those documents with Dr. Zelenko himself.",
                        citations=[Citation(page_from=11, line_from=10, page_to=11, line_to=14)]
                    ),
                    sentence(
                        content="In total, Mr. Linder spoke with Dr. Zelenko three or four times, and Ben Miller, an associate at Greenspoon Marder, spoke to him more frequently.",
                        citations=[Citation(page_from=24, line_from=12, page_to=24, line_to=25)]
                    ),
                    sentence(
                        content="The primary purpose of drafting the irrevocable trust was to avoid an estate tax issue.",
                        citations=[Citation(page_from=43, line_from=13, page_to=43, line_to=25)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="One of the irrevocable trusts (Ex. 1) was for the benefit of Dr. Zelenko’s six oldest children that he had with his first wife, Sima.",
                        citations=[Citation(page_from=15, line_from=2, page_to=16, line_to=14)]
                    ),
                    sentence(
                        content="The irrevocable trust provided that upon Dr. Zelenko’s death, each of his six children would receive $666,666.",
                        citations=[Citation(page_from=16, line_from=16, page_to=18, line_to=10)]
                    ),
                    sentence(
                        content="The irrevocable trust provided that upon Dr. Zelenko’s death, Dr. Zelenko’s parents, Larisa Zelenko and Arkady Zelenko, would receive $250,000.",
                        citations=[Citation(page_from=16, line_from=16, page_to=18, line_to=10)]
                    ),
                    sentence(
                        content="The irrevocable trust provided that upon Dr. Zelenko’s death, Dr. Zelenko’s brother, Frank Zelenko, would receive $250,000.",
                        citations=[Citation(page_from=16, line_from=16, page_to=18, line_to=10)]
                    ),
                    sentence(
                        content="Mr. Linder testified that Dr. Zelenko was “very adamant about the transfer to Rinat” and was not sure if the trust document was finalized.",
                        citations=[Citation(page_from=18, line_from=14, page_to=18, line_to=24)]
                    ),
                    sentence(
                        content="Mr. Linder testified that although he has no reason to believe the document is not signed by Dr. Zelenko, he does not know what Dr. Zelenko’s signature looked like at the time and the document did not appear witnessed.",
                        citations=[Citation(page_from=18, line_from=25, page_to=20, line_to=3)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Mr. Linder testified that he had a zoom call with Dr. Zelenko and Rinat Zelenko related to the assignment of insurance benefits to satisfy a home mortgage.",
                        citations=[Citation(page_from=20, line_from=11, page_to=20, line_to=19)]
                    ),
                    sentence(
                        content="Dr. Zelenko wanted one of the insurance policies to benefit Rinat to satisfy the mortgage on a recent home purchase that they made in the event that Dr. Zelenko passed away.",
                        citations=[Citation(page_from=20, line_from=20, page_to=21, line_to=9)]
                    ),
                    sentence(
                        content="Mr. Linder testified that they did not discuss any of the trusts during the call.",
                        citations=[Citation(page_from=21, line_from=10, page_to=21, line_to=15)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Mr. Linder also testified to a text message conversation with Dr. Zelenko in which Dr. Zelenko said “I want Rinat to be [the] sole beneficiary of [the] 2.5 million policy that has no liens on it. I need her to get that money ASAP.”",
                        citations=[Citation(page_from=31, line_from=6, page_to=31, line_to=13)]
                    ),
                    sentence(
                        content="Dr. Zelenko also texted “another 500 thousand to come to Rinat when all the other policies clear.”",
                        citations=[Citation(page_from=31, line_from=14, page_to=31, line_to=18)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Mr. Linder testified that Dr. Zelenko told him that Sima had blocked her kids from contacting Dr. Zelenko’s parents, although he does not remember if Dr. Zelenko himself was estranged from Sima’s children.",
                        citations=[Citation(page_from=23, line_from=14, page_to=24, line_to=11)]
                    ),
                    sentence(
                        content="Mr. Linder testified that Mr. Miller never told him that Dr. Zelenko wanted to leave $2.5 million more to Rinat at the expense of his six children with Sima.",
                        citations=[Citation(page_from=25, line_from=6, page_to=25, line_to=12)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="On June 17, 2022, Dr. Zelenko allegedly signed a change of beneficiary form changing the beneficiary of the Guardian insurance policy and assigning the proceeds to Rinat Lusting.",
                        citations=[Citation(page_from=13, line_from=16, page_to=13, line_to=23)]
                    ),
                    sentence(
                        content="Moshe Knobel served as the go-between between Greenspoon Marder and Dr. Zelenko for signing the change of beneficiary form.",
                        citations=[Citation(page_from=28, line_from=9, page_to=28, line_to=15)]
                    ),
                    sentence(
                        content="Mr. Knobel was not an employee of Greenspoon Marder but was formerly affiliated with Greenspoon Marder.",
                        citations=[Citation(page_from=27, line_from=14, page_to=28, line_to=3)]
                    ),
                    sentence(
                        content="Mr. Linder testified that Dr. Zelenko said that Mr. Knobel was a “trusted confidant,” “was the only person he could trust at the time” and that Greenspoon Marder should deal through Mr. Knobel “for all things related to” Dr. Zelenko.",
                        citations=[Citation(page_from=40, line_from=18, page_to=41, line_to=12)]
                    ),
                    sentence(
                        content="Mr. Linder followed up with Mr. Knobel soon after the form was signed.",
                        citations=[Citation(page_from=28, line_from=25, page_to=29, line_to=9)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Shortly after signing the form, Dr. Zelenko passed away.",
                        citations=[Citation(page_from=10, line_from=17, page_to=10, line_to=21)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="In September 2022, Mr. Linder received an email from Rinat’s attorney, Matthew Triggs, with a copy of a previous trust executed by Dr. Zelenko which provided Rinat with $1 million and provided each of Rinat’s two children with $1 million.",
                        citations=[Citation(page_from=21, line_from=16, page_to=22, line_to=19)]
                    ),
                    sentence(
                        content="Mr. Linder testified that he first became aware of this trust when he received the email from Mr. Triggs.",
                        citations=[Citation(page_from=21, line_from=16, page_to=22, line_to=19)]
                    ),
                ]
            ),
            NParagraph(
                sentences=[
                    sentence(
                        content="Dr. Zelenko had a $10 million insurance policy.",
                        citations=[Citation(page_from=31, line_from=19, page_to=38, line_to=11)]
                    ),
                    sentence(
                        content="$2 million was given to Sima.",
                        citations=[Citation(page_from=31, line_from=19, page_to=38, line_to=11)]
                    ),
                    sentence(
                        content="$1 million went to Rinat directly and $2 million was put in a trust for Sima’s two children ($1 million to each child).",
                        citations=[Citation(page_from=31, line_from=19, page_to=38, line_to=11)]
                    ),
                    sentence(
                        content="$666,666 went to each of Sima’s six children ($4.5 million total).",
                        citations=[Citation(page_from=31, line_from=19, page_to=38, line_to=11)]
                    ),
                    sentence(
                        content="$250,000 went to Dr. Zelenko’s parents and $250,000 went to Dr. Zelenko’s brother.",
                        citations=[Citation(page_from=31, line_from=19, page_to=38, line_to=11)]
                    ),
                    sentence(
                        content="Under the original trust, Rinat’s two children were to receive around $700,000 each.",
                        citations=[Citation(page_from=57, line_from=15, page_to=57, line_to=22)]
                    ),
                ]
            ),
        ]
    )
)

    chrono_summary.to_pdf_table()
    toc_summary.to_pdf_table()
    narrative_summary.to_pdf()

if __name__=="__main__":
    main()
