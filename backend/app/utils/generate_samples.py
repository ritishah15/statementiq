import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import fitz

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_statements"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def create_hdfc_digital_pdf(output_path: Path):
    """Generates a realistic 2-page digital HDFC Bank statement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor('#172B4D'))
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12)
    header_style = ParagraphStyle('HeaderBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12)

    elements = []

    # Bank Header
    elements.append(Paragraph("<b>HDFC BANK LIMITED</b>", title_style))
    elements.append(Paragraph("Branch: KORAMANGALA 4TH BLOCK, BANGALORE | Phone: 080-61234567", normal_style))
    elements.append(Spacer(1, 10))

    # Account Details Table
    acc_data = [
        [Paragraph("<b>Customer Name:</b>", header_style), Paragraph("VIKRAMADITYA SINGHANIA", normal_style),
         Paragraph("<b>Statement Period:</b>", header_style), Paragraph("01/05/2024 to 31/05/2024", normal_style)],
        [Paragraph("<b>Account Number:</b>", header_style), Paragraph("50100492817291", normal_style),
         Paragraph("<b>IFSC Code:</b>", header_style), Paragraph("HDFC0001234", normal_style)],
        [Paragraph("<b>Opening Balance:</b>", header_style), Paragraph("INR 45,200.00", normal_style),
         Paragraph("<b>Closing Balance:</b>", header_style), Paragraph("INR 1,28,450.00", normal_style)]
    ]
    t_acc = Table(acc_data, colWidths=[110, 160, 110, 160])
    t_acc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_acc)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>TRANSACTION ACTIVITY (PAGE 1)</b>", header_style))
    elements.append(Spacer(1, 6))

    # Page 1 Transactions
    headers = ["Date", "Narration / Description", "Withdrawal (Dr)", "Deposit (Cr)", "Closing Balance"]
    txn_data_p1 = [
        headers,
        ["01/05/2024", "ACH CREDIT TECHCORP SALARY MAY 2024", "", "1,20,000.00", "1,65,200.00"],
        ["02/05/2024", "UPI/RENT/MR SHARMA/HDFC BANK", "25,000.00", "", "1,40,200.00"],
        ["03/05/2024", "POS SWIGGY BANGALORE IN", "650.00", "", "1,39,550.00"],
        ["05/05/2024", "ELECTRICITY BILL BESCOM BANGALORE", "2,400.00", "", "1,37,150.00"],
        ["08/05/2024", "AMAZON PAY INDIA MUMBAI RETAIL", "4,200.00", "", "1,32,950.00"],
        ["10/05/2024", "ATM CASH WDL HDFC INDIRANAGAR", "10,000.00", "", "1,22,950.00"],
        ["12/05/2024", "UBER INDIA RIDES BANGALORE TRIP", "450.00", "", "1,22,500.00"],
        ["14/05/2024", "ZERODHA BROKING LTD EQUITY ADD FUNDS", "15,000.00", "", "1,07,500.00"],
        ["15/05/2024", "SMS ALERT CHARGES Q1 2024", "17.70", "", "1,07,482.30"]
    ]

    t_p1 = Table(txn_data_p1, colWidths=[70, 240, 80, 80, 80])
    t_p1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#172B4D')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_p1)

    elements.append(PageBreak())

    # Page 2 Transactions
    elements.append(Paragraph("<b>TRANSACTION ACTIVITY (PAGE 2) - CONTINUED</b>", header_style))
    elements.append(Spacer(1, 6))

    txn_data_p2 = [
        headers,
        ["18/05/2024", "DIVIDEND CR ITC LIMITED 500 SHARES", "", "3,125.00", "1,10,607.30"],
        ["20/05/2024", "APOLLO PHARMACY MEDICAL STORE BLR", "1,850.00", "", "1,08,757.30"],
        ["22/05/2024", "DELHI PUBLIC SCHOOL TERM 1 FEE", "18,500.00", "", "90,257.30"],
        ["24/05/2024", "IMPS-P2A-491028301-TRANSFER TO PRIYA S", "5,000.00", "", "85,257.30"],
        ["26/05/2024", "ZOMATO ORDER #49102 GURGAON", "820.00", "", "84,437.30"],
        ["28/05/2024", "FLIPKART INTERNET BANGALORE ORDER", "3,490.00", "", "80,947.30"],
        ["29/05/2024", "BPCL PETROL PUMP WHITEFIELD FUEL", "2,497.30", "", "78,450.00"],
        ["31/05/2024", "NEFT CR-CONSULTING BONUS PAYMENT", "", "50,000.00", "1,28,450.00"]
    ]

    t_p2 = Table(txn_data_p2, colWidths=[70, 240, 80, 80, 80])
    t_p2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#172B4D')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_p2)

    doc.build(elements)
    print(f"Generated digital PDF at: {output_path}")

def create_scanned_pdf_from_digital(digital_pdf_path: Path, scanned_pdf_path: Path):
    """Converts a digital PDF into a true scanned/rasterized PDF with visual artifacts."""
    doc = fitz.open(str(digital_pdf_path))
    new_doc = fitz.open()

    for page in doc:
        # Render at 180 DPI
        pix = page.get_pixmap(dpi=180)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)

        # Convert to grayscale
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        # Add subtle scanner noise & contrast variation
        noise = np.random.normal(0, 3, gray.shape).astype(np.int16)
        noisy = np.clip(gray.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Convert back to PIL image and save as 1-page PDF
        processed_pil = Image.fromarray(noisy)
        temp_img_path = str(SAMPLE_DIR / "temp_scan.png")
        processed_pil.save(temp_img_path, "PNG")

        img_pdf = fitz.open()
        img_pdf_page = img_pdf.new_page(width=page.rect.width, height=page.rect.height)
        img_pdf_page.insert_image(page.rect, filename=temp_img_path)

        new_doc.insert_pdf(img_pdf)
        img_pdf.close()
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

    doc.close()
    new_doc.save(str(scanned_pdf_path))
    new_doc.close()
    print(f"Generated scanned image-only PDF at: {scanned_pdf_path}")

if __name__ == "__main__":
    dig_path = SAMPLE_DIR / "hdfc_digital_statement.pdf"
    scan_path = SAMPLE_DIR / "scanned_statement.pdf"
    create_hdfc_digital_pdf(dig_path)
    create_scanned_pdf_from_digital(dig_path, scan_path)
