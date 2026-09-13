"""
Generates a strong, fully-structured capstone report PDF for testing
Reviewer-Lens end-to-end: Problem Statement, Objectives, Literature Survey
(real, recent citations plus an explicit, critical research-gap
discussion), System Architecture (a nine-component diagram that covers
every claim made in the problem statement), and System Modules whose
names match the diagram 1:1.

v3 notes (why this differs from v2, based on live runs against the real
scoring pipeline, not guesses):
- The Architecture Agent's vision model consistently flagged the same
  three gaps across repeated runs of the v2 diagram, independent of
  prompt wording: no enrollment/registration step feeding the Recognition
  Engine, no distinct faculty-facing review interface (as opposed to a
  generic notification), and no visible session-boundary concept for
  duplicate-window/end-of-session logic. This version adds a "Student
  Enrollment Database" (side input into Recognition Engine), a "Review
  Queue" and "Session Manager" stage, and renames the last stage to
  "Faculty Dashboard" so all three are now explicit, named components.
- The literature-scoring prompt (agents/literature_survey_agent.py) was
  found to never pass the student's own written survey text or raw
  citation list to the LLM — only a bare count plus whatever Semantic
  Scholar's public, keyless (and easily rate-limited) API resolved. That
  agent code has been fixed to always show the model the self-reported
  citations and the literature text itself. This report's synthesis
  paragraph was rewritten to be more explicitly comparative/critical
  (accuracy vs. edge-deployment cost trade-offs) so it holds up now that
  the model actually reads it, and two more real, recent, on-topic
  citations were added.

Headings are worded to match config.SECTION_HEADINGS exactly. Layout is
split across three pages (text / text / diagram) so the diagram stays the
*only* embedded raster image — keeping document_parser on the real
embedded-image extraction path instead of the whole-page-render fallback.
"""

import os

import pymupdf

PAGE_MARGIN = 50
FONT_SIZE = 10.5


def _render_diagram_png() -> bytes:
    """Draws a 9-component pipeline block diagram (8 in the main row, plus
    a Student Enrollment Database as a side input above Recognition
    Engine) on its own scratch page and rasterizes it to PNG bytes, so it
    gets embedded as a real image xref in the final PDF. The vision model
    reads these bytes directly, independent of how the image is scaled
    when placed on the final PDF page."""
    scratch = pymupdf.open()
    canvas_w, canvas_h = 1160, 260
    page = scratch.new_page(width=canvas_w, height=canvas_h)

    main_labels = [
        "Camera\nCapture",
        "Face\nDetection",
        "Recognition\nEngine",
        "Duplicate &\nAnomaly Check",
        "Attendance\nDatabase",
        "Review\nQueue",
        "Session\nManager",
        "Faculty\nDashboard",
    ]
    box_w, box_h, gap, x0, y0 = 125, 75, 15, 20, 130
    main_boxes = []
    for i, label in enumerate(main_labels):
        bx0 = x0 + i * (box_w + gap)
        main_boxes.append((bx0, y0, bx0 + box_w, y0 + box_h, label))

    # Student Enrollment Database sits above Recognition Engine (index 2)
    # as a side input, not part of the main left-to-right flow.
    recognition_box = main_boxes[2]
    enroll_w, enroll_h = box_w, 55
    enroll_x0 = (recognition_box[0] + recognition_box[2]) / 2 - enroll_w / 2
    enroll_y0 = 35
    enroll_box = (enroll_x0, enroll_y0, enroll_x0 + enroll_w, enroll_y0 + enroll_h, "Student\nEnrollment DB")

    all_boxes = main_boxes + [enroll_box]

    shape = page.new_shape()
    for bx0, by0, bx1, by1, _ in all_boxes:
        shape.draw_rect(pymupdf.Rect(bx0, by0, bx1, by1))
    shape.finish(color=(0, 0, 0), fill=(0.93, 0.96, 0.97), width=1.6)

    arrow_y = y0 + box_h / 2
    for i in range(len(main_boxes) - 1):
        x_start = main_boxes[i][2]
        x_end = main_boxes[i + 1][0]
        shape.draw_line(pymupdf.Point(x_start, arrow_y), pymupdf.Point(x_end - 6, arrow_y))
        shape.draw_line(pymupdf.Point(x_end - 6, arrow_y), pymupdf.Point(x_end - 12, arrow_y - 5))
        shape.draw_line(pymupdf.Point(x_end - 6, arrow_y), pymupdf.Point(x_end - 12, arrow_y + 5))

    # Enrollment DB -> Recognition Engine (vertical feed)
    ex = (enroll_box[0] + enroll_box[2]) / 2
    shape.draw_line(pymupdf.Point(ex, enroll_box[3]), pymupdf.Point(ex, y0 - 6))
    shape.draw_line(pymupdf.Point(ex, y0 - 6), pymupdf.Point(ex - 5, y0 - 12))
    shape.draw_line(pymupdf.Point(ex, y0 - 6), pymupdf.Point(ex + 5, y0 - 12))
    shape.finish(color=(0, 0, 0), width=1.8)
    shape.commit()

    for bx0, by0, bx1, by1, label in all_boxes:
        cx = (bx0 + bx1) / 2
        lines = label.split("\n")
        start_y = (by0 + by1) / 2 - (len(lines) - 1) * 6.5 + 4
        for i, line in enumerate(lines):
            page.insert_text((cx - len(line) * 3.0, start_y + i * 13), line, fontsize=10)

    page.insert_text((20, 20), "Figure 1. Smart Attendance System - Pipeline Architecture", fontsize=13)
    page.insert_text(
        (20, canvas_h - 15),
        "Main flow: left to right, Camera Capture through Faculty Dashboard. Student Enrollment DB feeds Recognition Engine.",
        fontsize=8,
    )

    pix = page.get_pixmap(dpi=200)
    png_bytes = pix.tobytes("png")
    scratch.close()
    return png_bytes


def build_sample_report(output_path: str) -> str:
    doc = pymupdf.open()

    # insert_text() silently drops any text past what fits on the page —
    # no error, no wrap to a new page — so each section below gets its own
    # page rather than risking a page1_text/page2_text block that's too
    # tall (this bit us once already: a 65-line block cut off mid-citation
    # with zero warning).

    # --- Page 1: Title, Problem Statement, Objectives ---
    page1 = doc.new_page()
    page1_text = """Capstone Project Report
Smart Attendance System Using Facial Recognition

Problem Statement
Manual attendance marking in classrooms and lecture halls is time-consuming,
prone to proxy attendance, and takes several minutes away from every
session. Existing RFID or fingerprint-based systems require physical
contact at a single entry point, which does not scale well to large
lecture halls with multiple doors. This project builds a contactless,
camera-based attendance system that enrolls each student's face once,
identifies enrolled students automatically as they enter, logs
attendance in real time within a defined class session, flags
irregularities such as duplicate or unrecognized check-ins separately
from confirmed records, and gives faculty a dashboard to review those
flags before they reach the official attendance record.

Objectives
- Build a facial-recognition pipeline that reliably identifies enrolled
  students from a live camera feed under normal classroom lighting.
- Build an enrollment step that registers each student's face once and
  stores it for later matching.
- Build an attendance database that updates in real time and prevents
  duplicate check-ins within the same class session.
- Detect and flag unrecognized or duplicate check-in attempts separately
  from confirmed attendance records, so faculty can review them.
- Provide a faculty-facing dashboard that surfaces low attendance and
  flagged irregularities at the end of each session.
- Evaluate the system's accuracy against a manually verified attendance
  sheet over a two-week pilot.
"""
    page1.insert_text((PAGE_MARGIN, PAGE_MARGIN), page1_text, fontsize=FONT_SIZE)

    # --- Page 2: Literature Survey ---
    page2 = doc.new_page()
    page2_text = """Literature Survey
AdaFace and the broader survey of embedding-based recognition methods
show that recognition accuracy is now high enough for unconstrained
classroom lighting, while real-time detectors such as YOLOv7 and the
more recent open-vocabulary YOLO-World confirm that detection latency is
no longer the bottleneck for live video pipelines. These general-purpose
methods, however, are tuned for accuracy on server-class hardware rather
than the modest, fixed classroom cameras this project targets.
Lightweight architectures such as PocketNet and the more recent EdgeFace
close that gap, trading a small amount of accuracy for models compact
enough to run on-device, but neither is evaluated against a live,
multi-door classroom deployment. None of these five works addresses the
classroom-specific operational problem of telling a genuine late arrival
apart from a duplicate or spoofed check-in in real time, or of giving
faculty a way to review a flagged case instead of silently accepting or
rejecting it. That is the specific gap this project is built to close through its
Duplicate & Anomaly Check, Session Manager, and Faculty Dashboard
stages.

[1] Y. Kim, W. Park, and S. Shin, "AdaFace: Quality Adaptive Margin for
Face Recognition," CVPR, 2022.
[2] C.-Y. Wang, A. Bochkovskiy, and H.-Y. M. Liao, "YOLOv7: Trainable
Bag-of-Freebies Sets New State-of-the-Art for Real-Time Object
Detectors," CVPR, 2023.
[3] M. Wang and W. Deng, "Deep Face Recognition: A Survey,"
Neurocomputing, 2021.
[4] T. Cheng, L. Song, Y. Ge, W. Liu, X. Wang, and Y. Shan, "YOLO-World:
Real-Time Open-Vocabulary Object Detection," CVPR, 2024.
[5] F. Boutros, N. Damer, F. Kirchbuchner, and A. Kuijper, "PocketNet:
Extreme Lightweight Face Recognition Network Using Neural Architecture
Search and Multistep Knowledge Distillation," IEEE Access, 2022.
[6] A. George, C. Ecabert, H. O. Shahreza, K. Kotwal, and S. Marcel,
"EdgeFace: Efficient Face Recognition Model for Edge Devices," IEEE
Transactions on Biometrics, Behavior, and Identity Science, 2024.
"""
    page2.insert_text((PAGE_MARGIN, PAGE_MARGIN), page2_text, fontsize=FONT_SIZE)

    # --- Page 3: System Architecture narrative ---
    page3 = doc.new_page()
    page3_text = """System Architecture
The proposed solution is a nine-component real-time pipeline. Before the
system goes live, a student enrollment database registers each student's
face embedding once. A camera capture stage continuously grabs frames
from a fixed classroom camera. A face detection stage locates face
regions in each frame and passes cropped faces to the recognition
engine, which compares each detected face's embedding against the
enrollment database using cosine similarity and returns a matched
student ID above a confidence threshold. A duplicate and anomaly check
stage inspects every matched ID against the current session's log:
confirmed, non-duplicate matches are written to the attendance database
with a timestamp, while low-confidence, unmatched, or repeat check-ins
are routed to a review queue instead. A session manager defines each
class session's start and end boundaries, resets the duplicate-check
window per session, and closes out the session once it ends. At that
point a faculty dashboard reads both the attendance database and the
review queue and presents a summary, including any flagged
irregularities, for faculty to review. Figure 1 shows these nine
components and the data flow between them.
"""
    page3.insert_text((PAGE_MARGIN, PAGE_MARGIN), page3_text, fontsize=FONT_SIZE)

    # --- Page 4: System Modules ---
    page4 = doc.new_page()
    page4_text = """System Modules
1. Student Enrollment Module - registers each student's face embedding
   once before deployment and stores it in the enrollment database that
   the Recognition Engine matches against.
2. Camera Capture Module - continuously grabs frames from the classroom
   IP camera and forwards them to the detection stage at a fixed frame
   rate.
3. Face Detection Module - locates and crops face regions within each
   frame using a cascade detector, discarding frames with no detected
   face.
4. Recognition Engine Module - generates a face embedding for each
   detected crop and matches it against the enrollment database via
   cosine similarity.
5. Duplicate & Anomaly Check Module - compares each matched ID against
   the current session log, sending confirmed matches to the Attendance
   Database and low-confidence, unmatched, or repeat check-ins to the
   Review Queue.
6. Attendance Database Module - stores timestamped, de-duplicated,
   confirmed attendance records and exposes a query API for faculty.
7. Review Queue Module - holds flagged check-in attempts separately from
   confirmed records until a faculty member reviews them.
8. Session Manager Module - defines each class session's start and end
   window, resets duplicate-check state per session, and closes out the
   session so the Faculty Dashboard can summarize it.
9. Faculty Dashboard Module - presents an end-of-session summary of
   confirmed attendance and flagged irregularities from the Review
   Queue for faculty to review.
"""
    page4.insert_text((PAGE_MARGIN, PAGE_MARGIN), page4_text, fontsize=FONT_SIZE)

    # --- Page 5: the diagram, embedded as a real raster image ---
    page5 = doc.new_page()
    png_bytes = _render_diagram_png()
    diagram_rect = pymupdf.Rect(45, 90, 550, 210)  # matches the 1160x260 canvas aspect ratio
    page5.insert_image(diagram_rect, stream=png_bytes)
    page5.insert_text((45, 70), "Figure 1. System Architecture", fontsize=12)

    doc.save(output_path)
    doc.close()
    return output_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "sample_reports", "sample_capstone_report.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build_sample_report(out)
    print(f"Wrote {out}")
