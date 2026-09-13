"""
Generates a small synthetic capstone-style PDF for end-to-end testing:
a Problem Statement, a Literature Survey with a couple of bracketed
citations, and a System Modules section with a simple embedded diagram
image (so both the raster-image path and the section-splitting path get
exercised).
"""

import os

import pymupdf


def build_dummy_pdf(output_path: str) -> str:
    doc = pymupdf.open()
    page = doc.new_page()

    text = """Capstone Project Report

Problem Statement
Many small colleges still evaluate student capstone reports entirely by
hand, which is slow and inconsistent across faculty reviewers. This
project proposes an AI-assisted pre-review tool that checks a report's
literature survey, architecture diagram, and module alignment before a
human reviewer sees it, so faculty time is spent on judgment rather than
bookkeeping.

Literature Survey
[1] A. Kumar, "Automated Essay Scoring Using Transformer Models," IEEE
Access, 2022.
[2] R. Chen and T. Osei, "A Survey of LLM-Based Document Review Systems,"
ACM Computing Surveys, 2023.
Prior work in automated review has focused mostly on essay scoring rather
than multi-part technical reports, leaving a gap this project addresses.

System Modules
The system consists of a Document Parsing module that extracts sections
and diagrams from the uploaded PDF, a Literature Survey module that
checks citation relevance and recency, an Architecture Structure module
that reads the submitted diagram, an Alignment module that compares the
diagram against the module text, and a Report Aggregator module that
produces the final composite score and downloadable report.

System Architecture
A block diagram below shows the flow between modules.
"""
    page.insert_text((50, 50), text, fontsize=11)

    # A tiny synthetic "diagram" image so the raster-image extraction path
    # (not just the page-render fallback) gets exercised.
    diagram_page = doc.new_page()
    shape = diagram_page.new_shape()
    shape.draw_rect(pymupdf.Rect(50, 50, 200, 100))
    shape.draw_rect(pymupdf.Rect(250, 50, 400, 100))
    shape.draw_rect(pymupdf.Rect(150, 150, 300, 200))
    shape.finish()
    shape.commit()
    diagram_page.insert_text((60, 80), "Parser", fontsize=10)
    diagram_page.insert_text((260, 80), "Scoring Engine", fontsize=10)
    diagram_page.insert_text((160, 180), "Report Output", fontsize=10)

    doc.save(output_path)
    doc.close()
    return output_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "sample_reports", "dummy_report.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_dummy_pdf(out)
    print(f"Wrote {out}")
