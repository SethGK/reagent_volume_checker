# pdf_processor.py
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
import re
from datetime import datetime, timedelta

# --- Configuration ---
# Analyzer-specific headers
ANALYZER_HEADERS = {
    "Roche e801": [
        "Test", "Reason", "Available Tests", "Type",
        "Pos.", "Remaining", "Lot ID", "Expiry Date"
    ],
    "Beckman AU5800": [
        "Pos.", "Test Name", "R1/R2 Shots", "Onboard Remaining",
        "RB Stability Remaining", "Cal Stability Remaining",
        "Expiration", "Lot No.", "BTL No", "Seq.", "Comment"
    ],
    # Add other analyzers and their header lists here
}
# Tesseract config (PSM 6 for uniform text)
tesseract_config = ''  # customize if needed


def parse_e801(text):
    """
    Parses OCR text for Roche e801 layout.
    Returns dict: reagent_name -> {"volume": int, "expiry": date or None}
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_tokens = ANALYZER_HEADERS["Roche e801"]
    header_idx = None
    for i, line in enumerate(lines):
        cols = re.split(r"\s{2,}", line)
        if all(any(ht.lower() in col.lower() for col in cols) for ht in header_tokens[:3]):
            header_idx = i
            headers = [c.strip() for c in cols]
            break
    if header_idx is None:
        st.warning("Could not locate Roche e801 header in OCR text.")
        return {}

    try:
        rem_idx = next(i for i, h in enumerate(headers) if 'remaining' in h.lower())
    except StopIteration:
        st.warning("'Remaining' column not found in headers.")
        return {}
    try:
        exp_idx = next(i for i, h in enumerate(headers) if 'expiry' in h.lower() or 'expiration' in h.lower())
    except StopIteration:
        exp_idx = None

    data = {}
    for line in lines[header_idx + 1:]:
        if any(kw.lower() in line.lower() for kw in ['total', 'summary']):
            break
        cols = re.split(r"\s{2,}", line)
        if len(cols) <= rem_idx:
            continue
        name = cols[0].strip().lower()
        rem_val = cols[rem_idx].strip()
        num_match = re.search(r"(\d+)", rem_val)
        if not num_match:
            continue
        volume = int(num_match.group(1))
        expiry_date = None
        if exp_idx is not None and exp_idx < len(cols):
            raw_exp = cols[exp_idx].strip()
            for fmt in ["%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    expiry_date = datetime.strptime(raw_exp, fmt).date()
                    break
                except ValueError:
                    continue
        data[name] = {"volume": volume, "expiry": expiry_date}
    return data


def parse_au5800(text):
    """
    Parses OCR text for Beckman AU5800 layout.
    Returns dict: reagent_name -> {"volume": int (min of R1/R2 Shots), "expiry": date or None}
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_tokens = ANALYZER_HEADERS["Beckman AU5800"]
    header_idx = None
    for i, line in enumerate(lines):
        cols = re.split(r"\s{2,}", line)
        # match first three headers (Pos., Test Name, R1/R2 Shots)
        if all(any(ht.lower() in col.lower() for col in cols) for ht in header_tokens[:3]):
            header_idx = i
            headers = [c.strip() for c in cols]
            break
    if header_idx is None:
        st.warning("Could not locate Beckman AU5800 header in OCR text.")
        return {}

    # Determine column indices
    try:
        name_idx = next(i for i, h in enumerate(headers) if 'test name' in h.lower())
        shots_idx = next(i for i, h in enumerate(headers) if 'shots' in h.lower())
    except StopIteration:
        st.warning("Required columns not found in headers.")
        return {}
    try:
        exp_idx = next(i for i, h in enumerate(headers) if 'expiration' in h.lower())
    except StopIteration:
        exp_idx = None

    data = {}
    for line in lines[header_idx + 1:]:
        if any(kw.lower() in line.lower() for kw in ['total', 'summary']):
            break
        cols = re.split(r"\s{2,}", line)
        if len(cols) <= shots_idx:
            continue
        name = cols[name_idx].strip().lower()
        raw_shots = cols[shots_idx].strip()
        shot_match = re.search(r"(\d+)", raw_shots)
        if not shot_match:
            continue
        shots = int(shot_match.group(1))
        expiry_date = None
        if exp_idx is not None and exp_idx < len(cols):
            raw_exp = cols[exp_idx].strip()
            for fmt in ["%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    expiry_date = datetime.strptime(raw_exp, fmt).date()
                    break
                except ValueError:
                    continue
        # Keep the lowest shots value per reagent
        if name not in data or shots < data[name]['volume']:
            data[name] = {"volume": shots, "expiry": expiry_date}
    return data


def parse_ocr_text(text, analyzer):
    """
    Dispatch parsing based on analyzer type.
    """
    text = text.replace('\r', '')
    if analyzer == "Roche e801":
        return parse_e801(text)
    if analyzer == "Beckman AU5800":
        return parse_au5800(text)

    # Fallback: generic parser
    reagent_data = {}
    pattern = re.compile(r'^([A-Za-z0-9\s\-]+?)\s{2,}.*?(\d+)\s*(?:ML|Tests|units)?$', re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.search(line.strip())
        if match:
            name = match.group(1).strip().lower()
            volume = int(match.group(2))
            if name not in reagent_data:
                reagent_data[name] = {"volume": volume, "expiry": None}
    if not reagent_data:
        st.warning(
            "Could not parse reagent data generically. "
            "Ensure PDF layout matches or add a custom parser for your analyzer."
        )
    return reagent_data


@st.cache_data(ttl=600)
def extract_reagent_data_from_pdf(uploaded_pdf_file, analyzer):
    """
    Extract reagent mapping for given analyzer from PDF via OCR.
    """
    if uploaded_pdf_file is None:
        return None
    try:
        pdf_bytes = uploaded_pdf_file.getvalue()
        images = convert_from_bytes(pdf_bytes, dpi=200)
        full_text = ''
        for img in images:
            page_text = pytesseract.image_to_string(img, config=tesseract_config)
            full_text += page_text + '\n'
        st.write(f"Parsing {analyzer} PDF...")
        return parse_ocr_text(full_text, analyzer)
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None
