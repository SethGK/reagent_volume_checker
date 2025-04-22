# pdf_processor.py
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
import re
from datetime import datetime, date

# --- Configuration ---
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

tesseract_config = ''

def parse_e801(text):
    """
    Parses OCR text for Roche e801 layout.
    Strips any trailing version numbers (e.g. '-3' or ' 3') from the Test name
    so that 'FT3-3' or 'E2 3' both map back to 'FT3' and 'E2'.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Find the header that contains both 'Test' and 'Remaining'
    header_idx = None
    for idx, line in enumerate(lines):
        if 'test' in line.lower() and 'remaining' in line.lower():
            header_idx = idx
            break
    if header_idx is None:
        st.warning("Could not locate Roche e801 header row. Check OCR output.")
        return {}

    data = {}
    for line in lines[header_idx+1:]:
        low = line.lower()
        # stop at summary lines
        if any(term in low for term in ['total', 'summary', 'magazine', 'waste']):
            break

        # Grab the Test name (with possible suffix), the Available count, then ASSAY/PRE/DIL
        m = re.match(r"^(.+?)\s+(\d+)\s+(ASSAY|PRE|DIL)", line, re.IGNORECASE)
        if not m:
            continue
        raw_name, avail_str, _ = m.groups()

        # strip off any trailing '‑<digit>' or ' <digit>' so e.g. "FT3‑3" → "FT3"
        base = re.sub(r"[-\s]\d+$", "", raw_name)

        try:
            available = int(avail_str)
        except:
            available = None

        # split on whitespace
        tokens = line.split()
        try:
            remaining = int(tokens[4])
        except:
            remaining = None

        # parse expiry token (second‑to‑last) and days in parentheses (last)
        expiry_date = None
        expiry_days = None
        if len(tokens) >= 2:
            # e.g. tokens[-2] == "2025/09"
            ym = re.match(r"(\d{4})/(\d{2})", tokens[-2])
            if ym:
                y, mth = ym.groups()
                try:
                    expiry_date = date(int(y), int(mth), 1)
                except:
                    pass
            dm = re.search(r"\((\d+)\)", tokens[-1])
            if dm:
                expiry_days = int(dm.group(1))

        data[base.strip().lower()] = {
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
    exp_idx = next((i for i,h in enumerate(headers) if 'expir' in h.lower()), None)
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
        m = re.search(r"(\d+)", cols[shots_idx])
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
    text = text.replace('\r', '')
    if analyzer == "Roche e801":
        return parse_e801(text)
    if analyzer == "Beckman AU5800":
        return parse_au5800(text)

    reagent_data = {}
    pattern = re.compile(r'^([A-Za-z0-9\s\-]+?)\s{2,}.*?(\d+)\s*(?:ML|Tests|units)?$', re.IGNORECASE)
    for line in text.splitlines():
        m = pattern.search(line.strip())
        if m:
            name = m.group(1).strip().lower()
            val = int(m.group(2))
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
        images = convert_from_bytes(pdf_bytes, dpi=150)
        full_text = ''
        for img in images:
            full_text += pytesseract.image_to_string(img, config=tesseract_config) + '\n'
        st.write(f"Parsing {analyzer} PDF...")
        return parse_ocr_text(full_text, analyzer)
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None
