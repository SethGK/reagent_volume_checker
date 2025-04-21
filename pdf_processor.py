# pdf_processor.py
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
import re
from datetime import datetime, date

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
}

# Tesseract config (PSM 6 for uniform text)
tesseract_config = ''


def parse_e801(text):
    """
    Parses OCR text for Roche e801 layout.
    Returns dict: reagent -> {
        available: int, remaining: int, expiry_date: date or None, expiry_days: int or None
    }
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hdr_tokens = ANALYZER_HEADERS["Roche e801"]
    header_idx = None
    for i, line in enumerate(lines):
        cols = re.split(r"\s{2,}", line)
        if all(any(tok.lower() in col.lower() for col in cols) for tok in hdr_tokens[:3]):
            header_idx = i
            headers = [c.strip() for c in cols]
            break
    if header_idx is None:
        st.warning("Could not locate Roche e801 header.")
        return {}

    available_idx = next((i for i, h in enumerate(headers) if 'available' in h.lower()), None)
    remaining_idx = next((i for i, h in enumerate(headers) if 'remaining' in h.lower()), None)
    expiry_idx = next((i for i, h in enumerate(headers) if 'expiry' in h.lower()), None)
    if available_idx is None or remaining_idx is None:
        st.warning("Roche e801: 'Available Tests' or 'Remaining' column not found.")
        return {}

    data = {}
    for line in lines[header_idx+1:]:
        if any(kw in line.lower() for kw in ['total', 'summary']):
            break
        cols = re.split(r"\s{2,}", line)
        if len(cols) <= max(available_idx, remaining_idx):
            continue
        name = cols[0].strip().lower()

        # parse available tests
        avail_match = re.search(r"(\d+)", cols[available_idx])
        available = int(avail_match.group(1)) if avail_match else None

        # parse remaining tests (this wedge)
        rem_match = re.search(r"(\d+)", cols[remaining_idx])
        remaining = int(rem_match.group(1)) if rem_match else None

        # parse expiry
        expiry_date = None
        expiry_days = None
        if expiry_idx is not None and expiry_idx < len(cols):
            raw = cols[expiry_idx].strip()
            m = re.match(r"(\d{4})/(\d{2})\s*\((\d+)\)", raw)
            if m:
                yr, mo, days = m.groups()
                try:
                    expiry_date = date(int(yr), int(mo), 1)
                    expiry_days = int(days)
                except:
                    pass

        data[name] = {
            "available": available,
            "remaining": remaining,
            "expiry_date": expiry_date,
            "expiry_days": expiry_days
        }
    return data


def parse_au5800(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hdr_tokens = ANALYZER_HEADERS["Beckman AU5800"]
    header_idx = None
    for i, line in enumerate(lines):
        cols = re.split(r"\s{2,}", line)
        if all(any(tok.lower() in col.lower() for col in cols) for tok in hdr_tokens[:3]):
            header_idx = i
            headers = [c.strip() for c in cols]
            break
    if header_idx is None:
        st.warning("Could not locate Beckman AU5800 header.")
        return {}

    name_idx = next((i for i,h in enumerate(headers) if 'test name' in h.lower()), None)
    shots_idx = next((i for i,h in enumerate(headers) if 'shots' in h.lower()), None)
    on_idx = next((i for i,h in enumerate(headers) if 'onboard remaining' in h.lower()), None)
    exp_idx = next((i for i,h in enumerate(headers) if 'expiration' in h.lower()), None)
    if None in (name_idx, shots_idx):
        st.warning("AU5800: Required columns missing.")
        return {}

    data = {}
    for line in lines[header_idx+1:]:
        if any(kw in line.lower() for kw in ['total','summary']):
            break
        cols = re.split(r"\s{2,}", line)
        if len(cols) <= shots_idx:
            continue
        name = cols[name_idx].strip().lower()
        sht = cols[shots_idx].strip()
        m = re.search(r"(\d+)", sht)
        if not m:
            continue
        shots = int(m.group(1))
        onboard = cols[on_idx].strip() if on_idx is not None and on_idx < len(cols) else None
        expiry_date = None
        if exp_idx is not None and exp_idx < len(cols):
            raw = cols[exp_idx].strip()
            for fmt in ["%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    expiry_date = datetime.strptime(raw, fmt).date()
                    break
                except:
                    continue
        entry = {"shots": shots, "expiry_date": expiry_date, "onboard_remaining": onboard}
        if name not in data or shots < data[name]['shots']:
            data[name] = entry
    return data


def parse_ocr_text(text, analyzer):
    text = text.replace('\r','')
    if analyzer == "Roche e801":
        return parse_e801(text)
    if analyzer == "Beckman AU5800":
        return parse_au5800(text)
    # fallback
    reagent_data = {}
    pattern = re.compile(r'^([A-Za-z0-9\s\-]+?)\s{2,}.*?(\d+)\s*(?:ML|Tests|units)?$', re.IGNORECASE)
    for line in text.splitlines():
        m = pattern.search(line.strip())
        if m:
            name = m.group(1).strip().lower()
            val = int(m.group(2))
            if name not in reagent_data:
                reagent_data[name] = {"volume": val, "expiry_date": None}
    if not reagent_data:
        st.warning("Could not parse reagent data generically.")
    return reagent_data


@st.cache_data(ttl=600)
def extract_reagent_data_from_pdf(uploaded_pdf_file, analyzer):
    if uploaded_pdf_file is None:
        return None
    try:
        pdf_bytes = uploaded_pdf_file.getvalue()
        images = convert_from_bytes(pdf_bytes, dpi=200)
        full_text = ''
        for img in images:
            full_text += pytesseract.image_to_string(img, config=tesseract_config) + '\n'
        st.write(f"Parsing {analyzer} PDF...")
        return parse_ocr_text(full_text, analyzer)
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None
