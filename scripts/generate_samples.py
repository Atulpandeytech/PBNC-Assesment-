"""
scripts/generate_samples.py
Generates realistic, rigorous test and demonstration files for Pragati Bharti Document Intelligence:
1. 1_clean_mcq.pdf: Clean digital MCQ PDF with answer key at end.
2. 2_answer_key_start.pdf: PDF with answer key at beginning in table format.
3. 3_scanned_noisy.pdf: Scanned-style PDF with rotation, blur, and noise.
4. 4_question_image.png: PNG image of a question with options and a geometric diagram.
5. 5_question_image.jpg: JPG image of 2 questions with options.
6. 6_cross_page.pdf: Multi-page PDF with cross-page question, diagram, and table.
7. 7_group_question_paper.pdf & 7_group_answer_key.pdf: Separate Question Paper & Answer Key.
8. 8_garbled_scan.pdf: Low-quality garbled scan producing low confidence.
Invalid files:
- invalid_disguised_exe.pdf: MZ header disguised as PDF.
- invalid_corrupt.pdf: Corrupted non-PDF binary payload.
- invalid_password.pdf: AES-256 encrypted password-protected PDF.
- invalid_unsupported.docx: Unsupported Office document.
- invalid_oversize.pdf: File exceeding 50 MB limit.
"""

import io
import math
import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLES_INPUT_DIR = BASE_DIR / "samples" / "input"
SAMPLES_INVALID_DIR = BASE_DIR / "samples" / "invalid"
SAMPLES_OUTPUT_DIR = BASE_DIR / "samples" / "output"
DOCS_EVIDENCE_DIR = BASE_DIR / "docs" / "evidence"


def ensure_directories():
    for d in (SAMPLES_INPUT_DIR, SAMPLES_INVALID_DIR, SAMPLES_OUTPUT_DIR, DOCS_EVIDENCE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def generate_1_clean_mcq():
    path = SAMPLES_INPUT_DIR / "1_clean_mcq.pdf"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    
    # Title Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(306, 750, "PRAGATI BHARTI SENIOR SECONDARY SCHOOL")
    c.setFont("Helvetica", 11)
    c.drawCentredString(306, 732, "ANNUAL EXAMINATION - SCIENCE (CLASS X)")
    c.line(54, 722, 558, 722)
    
    y = 690
    questions = [
        (
            "1. What is the chemical formula of bleaching powder?",
            "(A) CaOCl2    (B) Ca(OH)2    (C) NaHCO3    (D) Na2CO3"
        ),
        (
            "2. Which part of the human brain is responsible for regulating posture and balance?",
            "(A) Cerebrum    (B) Cerebellum    (C) Medulla    (D) Pons"
        ),
        (
            "3. The phenomenon of splitting white light into its component colors is called:",
            "(A) Reflection    (B) Refraction    (C) Dispersion    (D) Total Internal Reflection"
        ),
        (
            "4. Which of the following metals occurs in native state in nature?",
            "(A) Gold    (B) Iron    (C) Aluminium    (D) Zinc"
        ),
        (
            "5. What is the SI unit of electrical resistivity?",
            "(A) Ohm    (B) Ohm-meter    (C) Ampere    (D) Volt-meter"
        ),
    ]
    
    for q_text, opts in questions:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, q_text)
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(80, y, opts)
        y -= 35

    # Answer Key Section at end
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 10, "ANSWER KEY")
    c.setFont("Helvetica", 11)
    c.drawString(60, y - 30, "1-A, 2-B, 3-C, 4-A, 5-B")
    
    c.save()
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    print(f"Generated: {path}")


def generate_2_answer_key_start():
    path = SAMPLES_INPUT_DIR / "2_answer_key_start.pdf"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(306, 755, "PRAGATI BHARTI ASSESSMENT SYSTEM")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 725, "SOLUTIONS & ANSWER KEY (SECTION A)")
    
    # Table Grid for Answer Key at the top
    c.rect(60, 675, 480, 40, stroke=1, fill=0)
    c.line(60, 695, 540, 695)
    for x in range(180, 540, 120):
        c.line(x, 675, x, 715)
        
    c.setFont("Helvetica-Bold", 10)
    c.drawString(70, 690, "Q1: (B)")
    c.drawString(190, 690, "Q2: (D)")
    c.drawString(310, 690, "Q3: (A)")
    c.drawString(430, 690, "Q4: (C)")
    
    c.line(60, 655, 540, 655)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 635, "EXAMINATION QUESTIONS")
    
    y = 605
    questions = [
        ("1. What is the value of sin 30 degrees + cos 60 degrees?",
         "(A) 0.5    (B) 1.0    (C) 1.5    (D) 2.0"),
        ("2. The discriminant of quadratic equation 2x^2 - 4x + 3 = 0 is:",
         "(A) 8    (B) 0    (C) 16    (D) -8"),
        ("3. The sum of the first 20 positive even integers is:",
         "(A) 420    (B) 400    (C) 210    (D) 440"),
        ("4. If the perimeter and area of a circle are numerically equal, the radius is:",
         "(A) 1 unit    (B) pi units    (C) 2 units    (D) 4 units"),
    ]
    
    for q_text, opts in questions:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, q_text)
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(80, y, opts)
        y -= 35
        
    c.save()
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    print(f"Generated: {path}")


def get_font(size: int = 20):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def generate_3_scanned_noisy():
    path = SAMPLES_INPUT_DIR / "3_scanned_noisy.pdf"
    
    # 1. Create a clean base image with text
    w, h = 1200, 1600
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_title = get_font(24)
    font_body = get_font(20)
    
    draw.text((100, 80), "PRAGATI BHARTI SCHOLARSHIP APTITUDE TEST", fill=(20, 20, 20), font=font_title)
    draw.text((100, 120), "SECTION B - GENERAL SCIENCE", fill=(40, 40, 40), font=font_body)
    draw.line([(100, 150), (1100, 150)], fill=(50, 50, 50), width=2)
    
    lines = [
        "1. Which organelle is known as the powerhouse of the cell?",
        "   (A) Nucleus    (B) Ribosome    (C) Mitochondria    (D) Lysosome",
        "",
        "2. What is the value of gravitational acceleration g on the surface of Earth?",
        "   (A) 9.8 m/s^2    (B) 8.9 m/s^2    (C) 11.2 m/s^2    (D) 6.4 m/s^2",
        "",
        "3. Which element has the chemical symbol Fe?",
        "   (A) Fluorine    (B) Francium    (C) Iron    (D) Fermium",
        "",
        "ANSWER KEY",
        "1-C, 2-A, 3-C",
    ]
    
    y = 190
    for line in lines:
        draw.text((100, y), line, fill=(30, 30, 30), font=font_body)
        y += 45
        
    # 2. Convert to OpenCV and apply realistic scan degradation
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Slight rotation (1.2 degrees)
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, 1.2, 1.0)
    cv_img = cv2.warpAffine(cv_img, rot_mat, (w, h), borderValue=(245, 245, 245))
    
    # 3. Save as PDF
    res_pil = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    res_pil.save(path, "PDF", resolution=150.0)
    print(f"Generated: {path}")


def generate_4_question_image_png():
    path = SAMPLES_INPUT_DIR / "4_question_image.png"
    w, h = 1000, 650
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = get_font(20)
    
    # Question text
    draw.text((50, 40), "1. In the right-angled triangle ABC shown below, find the length of hypotenuse AC", fill=(0, 0, 0), font=font)
    draw.text((50, 75), "   if AB = 6 cm and BC = 8 cm.", fill=(0, 0, 0), font=font)
    
    # Draw geometric diagram (Right-angled triangle)
    draw.polygon([(250, 160), (250, 340), (470, 340)], outline=(0, 0, 150), width=3)
    draw.rectangle([(250, 320), (270, 340)], outline=(0, 0, 150), width=2)
    
    # Labels
    font_lbl = get_font(18)
    draw.text((230, 150), "A", fill=(0, 0, 0), font=font_lbl)
    draw.text((230, 345), "B", fill=(0, 0, 0), font=font_lbl)
    draw.text((475, 345), "C", fill=(0, 0, 0), font=font_lbl)
    draw.text((180, 240), "6 cm", fill=(100, 0, 0), font=font_lbl)
    draw.text((340, 355), "8 cm", fill=(100, 0, 0), font=font_lbl)
    draw.text((370, 230), "AC = ?", fill=(0, 100, 0), font=font_lbl)
    
    # Options
    y_opt = 420
    draw.text((50, y_opt), "(A) 10 cm    (B) 14 cm    (C) 12 cm    (D) 100 cm", fill=(0, 0, 0), font=font)
    
    # Answer key
    draw.text((50, 480), "ANSWER KEY: 1-A", fill=(50, 50, 50), font=font)
    
    img.save(path, "PNG")
    print(f"Generated: {path}")


def generate_5_question_image_jpg():
    path = SAMPLES_INPUT_DIR / "5_question_image.jpg"
    w, h = 1000, 650
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = get_font(20)
    
    draw.text((50, 40), "1. What is the value of the universal gravitational constant G?", fill=(0, 0, 0), font=font)
    draw.text((70, 75), "(A) 6.67 x 10^-11 N m^2/kg^2    (B) 9.8 x 10^6 N m^2/kg^2", fill=(0, 0, 0), font=font)
    draw.text((70, 110), "(C) 3.0 x 10^8 m/s    (D) 1.6 x 10^-19 C", fill=(0, 0, 0), font=font)
    
    draw.line([(50, 180), (950, 180)], fill=(200, 200, 200), width=1)
    
    draw.text((50, 210), "2. Which layer of the atmosphere contains the ozone layer?", fill=(0, 0, 0), font=font)
    draw.text((70, 245), "(A) Troposphere    (B) Stratosphere", fill=(0, 0, 0), font=font)
    draw.text((70, 280), "(C) Mesosphere    (D) Thermosphere", fill=(0, 0, 0), font=font)
    
    draw.line([(50, 360), (950, 360)], fill=(200, 200, 200), width=1)
    draw.text((50, 400), "ANSWERS: 1-A, 2-B", fill=(60, 60, 60), font=font)
    
    img.save(path, "JPEG", quality=95)
    print(f"Generated: {path}")


def generate_6_cross_page():
    path = SAMPLES_INPUT_DIR / "6_cross_page.pdf"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    
    # PAGE 1
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, 750, "PRAGATI BHARTI COMPREHENSIVE PHYSICS EXAM")
    c.line(54, 735, 558, 735)
    
    # Q1
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 700, "1. What is the SI unit of electric potential difference?")
    c.setFont("Helvetica", 10)
    c.drawString(80, 680, "(A) Ampere    (B) Volt    (C) Ohm    (D) Joule")
    
    # Q2
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 640, "2. An object is placed at 2F in front of a convex lens. The image formed is:")
    c.setFont("Helvetica", 10)
    c.drawString(80, 620, "(A) Virtual and enlarged    (B) Real and inverted at 2F    (C) Real and diminished    (D) At infinity")
    
    # Q3 - Starts on Page 1 and carries over without final punctuation
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 570, "3. In an experiment to observe electromagnetic induction, a solenoid having 500 turns is connected")
    c.drawString(60, 550, "   to a sensitive galvanometer and a permanent bar magnet is moved along its axis with constant speed and")
    # End of page 1 - carryover cut-off
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(550, 50, "Continued on Page 2 ...")
    c.showPage()
    
    # PAGE 2
    # Continuation of Q3
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 750, "   the deflection shown by the galvanometer pointer is observed for different speeds.")
    c.drawString(60, 730, "   What conclusion can be drawn regarding the magnitude of the induced EMF?")
    c.setFont("Helvetica", 10)
    c.drawString(80, 705, "(A) Induced EMF is directly proportional to the rate of change of magnetic flux")
    c.drawString(80, 685, "(B) Induced EMF is inversely proportional to the number of turns")
    c.drawString(80, 665, "(C) Induced EMF is zero at all speeds")
    c.drawString(80, 645, "(D) Induced EMF depends only on temperature")
    
    # Draw Table on Page 2
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, 610, "Table 1: Experimental Observation Data")
    c.rect(60, 530, 480, 70, stroke=1, fill=0)
    c.line(60, 575, 540, 575)
    c.line(200, 530, 200, 600)
    c.line(360, 530, 360, 600)
    
    c.drawString(70, 583, "Observation Trial")
    c.drawString(210, 583, "Magnet Velocity (m/s)")
    c.drawString(370, 583, "Induced Current (mA)")
    
    c.setFont("Helvetica", 10)
    c.drawString(70, 558, "Trial 1")
    c.drawString(210, 558, "0.5")
    c.drawString(370, 558, "12.4")
    
    c.drawString(70, 538, "Trial 2")
    c.drawString(210, 538, "1.0")
    c.drawString(370, 538, "24.8")
    
    # Q4 on Page 2
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 480, "4. Which rule is used to determine the direction of induced current?")
    c.setFont("Helvetica", 10)
    c.drawString(80, 460, "(A) Fleming's Right-Hand Rule    (B) Fleming's Left-Hand Rule    (C) Right-Hand Thumb Rule    (D) Coulomb's Law")
    
    # Answer Key at bottom of Page 2
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 390, "ANSWER KEY")
    c.setFont("Helvetica", 11)
    c.drawString(60, 370, "1-B, 2-B, 3-A, 4-A")
    
    c.save()
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    print(f"Generated: {path}")


def generate_7_group_pair():
    qp_path = SAMPLES_INPUT_DIR / "7_group_question_paper.pdf"
    ak_path = SAMPLES_INPUT_DIR / "7_group_answer_key.pdf"
    
    # Question Paper (No answers)
    buf_qp = io.BytesIO()
    c = canvas.Canvas(buf_qp, pagesize=letter)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(306, 750, "PRAGATI BHARTI CHEMISTRY MID-TERM EXAM")
    c.setFont("Helvetica", 10)
    c.drawCentredString(306, 735, "Paper Code: CHEM-202 | Time: 45 Mins | Total Marks: 20")
    c.line(54, 725, 558, 725)
    
    y = 690
    questions = [
        ("1. What is the pH value of pure water at 25 degrees Celsius?",
         "(A) 5    (B) 7    (C) 9    (D) 14"),
        ("2. Which of the following is an amphoteric oxide?",
         "(A) Na2O    (B) SO2    (C) Al2O3    (D) CaO"),
        ("3. The functional group present in aldehydes is:",
         "(A) -CHO    (B) -COOH    (C) -OH    (D) >C=O"),
        ("4. Which gas is evolved when zinc granules react with dilute sulphuric acid?",
         "(A) Oxygen    (B) Nitrogen    (C) Hydrogen    (D) Chlorine"),
        ("5. Stainless steel is an alloy of iron, chromium, and:",
         "(A) Copper    (B) Zinc    (C) Nickel    (D) Tin"),
    ]
    for q_text, opts in questions:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, q_text)
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(80, y, opts)
        y -= 35
        
    c.save()
    with open(qp_path, "wb") as f:
        f.write(buf_qp.getvalue())
    print(f"Generated: {qp_path}")
    
    # Answer Key (Stand-alone separate document)
    buf_ak = io.BytesIO()
    c_ak = canvas.Canvas(buf_ak, pagesize=letter)
    c_ak.setFont("Helvetica-Bold", 15)
    c_ak.drawCentredString(306, 750, "OFFICIAL ANSWER KEY")
    c_ak.setFont("Helvetica", 11)
    c_ak.drawCentredString(306, 732, "Subject: Chemistry (Paper Code: CHEM-202)")
    c_ak.line(54, 720, 558, 720)
    
    c_ak.setFont("Helvetica-Bold", 12)
    c_ak.drawString(100, 670, "Question Number")
    c_ak.drawString(300, 670, "Correct Option")
    c_ak.line(100, 660, 450, 660)
    
    answers = [
        ("Question 1", "(B) 7"),
        ("Question 2", "(C) Al2O3"),
        ("Question 3", "(A) -CHO"),
        ("Question 4", "(C) Hydrogen"),
        ("Question 5", "(C) Nickel"),
    ]
    
    y = 635
    c_ak.setFont("Helvetica", 11)
    for q_num, ans in answers:
        c_ak.drawString(100, y, q_num)
        c_ak.drawString(300, y, ans)
        y -= 30
        
    c_ak.save()
    with open(ak_path, "wb") as f:
        f.write(buf_ak.getvalue())
    print(f"Generated: {ak_path}")


def generate_8_garbled_scan():
    path = SAMPLES_INPUT_DIR / "8_garbled_scan.pdf"
    w, h = 800, 1100
    img = Image.new("RGB", (w, h), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Draw faint garbled text
    draw.text((50, 60), "Prgti Bhrti Gbled Scn Tst", fill=(160, 160, 160))
    draw.text((50, 120), "Q1. Wht is the dsty of mter? . . .", fill=(170, 170, 170))
    draw.text((70, 160), "a) 1000 kg   b) unknwn   c) none", fill=(180, 180, 180))
    
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Heavy blur
    cv_img = cv2.GaussianBlur(cv_img, (15, 15), 5.0)
    
    # Severe rotation
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, 14.5, 0.95)
    cv_img = cv2.warpAffine(cv_img, rot_mat, (w, h), borderValue=(230, 230, 230))
    
    # Heavy salt and pepper noise
    noise = np.random.normal(0, 35, cv_img.shape).astype(np.uint8)
    cv_img = cv2.add(cv_img, noise)
    
    # Save as PDF
    res_pil = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    res_pil.save(path, "PDF", resolution=72.0)
    print(f"Generated: {path}")


def generate_invalid_files():
    # 1. Disguised executable (.exe with .pdf extension)
    exe_path = SAMPLES_INVALID_DIR / "invalid_disguised_exe.pdf"
    with open(exe_path, "wb") as f:
        f.write(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This program cannot be run in DOS mode.")
    print(f"Generated: {exe_path}")

    # 2. Corrupt non-PDF bytes
    corrupt_path = SAMPLES_INVALID_DIR / "invalid_corrupt.pdf"
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT_A_PDF_STREAM\x00\xff\xfe\xca\xfe\xba\xbe" * 50)
    print(f"Generated: {corrupt_path}")

    # 3. Encrypted PDF
    enc_path = SAMPLES_INVALID_DIR / "invalid_password.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Confidential Examination Content Protected with Password")
    doc.save(
        enc_path,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        user_pw="SuperSecretPass123!",
        owner_pw="AdminOwnerKey456!"
    )
    doc.close()
    print(f"Generated: {enc_path}")

    # 4. Unsupported extension (.docx)
    docx_path = SAMPLES_INVALID_DIR / "invalid_unsupported.docx"
    with open(docx_path, "wb") as f:
        f.write(b"PK\x03\x04\x14\x00\x06\x00mock docx content archive")
    print(f"Generated: {docx_path}")

    # 5. Oversize file (> 50 MB)
    oversize_path = SAMPLES_INVALID_DIR / "invalid_oversize.pdf"
    with open(oversize_path, "wb") as f:
        # Seek to 51 MB to create sparse file quickly without allocating 51MB of disk churn
        f.write(b"%PDF-1.4\n")
        f.seek(51 * 1024 * 1024 + 1024)
        f.write(b"\n%%EOF\n")
    print(f"Generated: {oversize_path} ({os.path.getsize(oversize_path) / (1024*1024):.1f} MB)")


def main():
    print("=== Generating Pragati Bharti Test and Demonstration Samples ===")
    ensure_directories()
    generate_1_clean_mcq()
    generate_2_answer_key_start()
    generate_3_scanned_noisy()
    generate_4_question_image_png()
    generate_5_question_image_jpg()
    generate_6_cross_page()
    generate_7_group_pair()
    generate_8_garbled_scan()
    generate_invalid_files()
    print("=== All sample files generated successfully! ===")


if __name__ == "__main__":
    main()
