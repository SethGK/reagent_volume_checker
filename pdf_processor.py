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
    """
    Parses OCR text for Beckman AU5800 layout.
    
    - Groups R1/R2 pairs by reagent name
    - Takes the lower of each R1/R2 pair
    - Sums those across sets for each reagent
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    header_idx = next((i for i, line in enumerate(lines) if "r1/r2 shots" in line.lower()), None)
    if header_idx is None:
        st.warning("Could not locate Beckman AU5800 header row. Check OCR output.")
        return {}
    
    reagent_sets = {}
    failed = []
    no_volume_entries = []
    
    for raw_line in lines[header_idx + 1:]:
        low = raw_line.lower()
        if any(kw in low for kw in ['total', 'summary', 'magazine', 'waste']):
            break
        
        # Check if line indicates "No volume in the Bottle"
        if "no volume in the bottle" in low:
            tokens = re.split(r"\s+", raw_line)
            if len(tokens) < 2:
                failed.append(raw_line)
                continue
                
            # Extract position and reagent name
            pos_token = tokens[0]
            name_token = tokens[1]
            
            # Clean up reagent name
            if '.' in name_token:
                parts = name_token.split('.')
                if len(parts) >= 2:
                    name = parts[1].lower()
                else:
                    name = name_token.lower()
            else:
                name = name_token.lower()
            
            no_volume_entries.append({
                "name": name,
                "line": raw_line
            })
            continue
        
        tokens = re.split(r"\s+", raw_line)
        if len(tokens) < 8:
            failed.append(raw_line)
            continue
        
        # 1) Extract name from token[1], handling cases with spaces
        name_token = tokens[1]
        # Handle cases like "12 .BUN" where there's a space
        if '.' in name_token:
            name = name_token.split('.', 1)[1].lower()
        elif len(tokens) > 2 and '.' in tokens[2]:
            name = tokens[2].split('.', 1)[1].lower()
            # Need to shift indices for other fields
            tokens = [tokens[0], tokens[1] + tokens[2]] + tokens[3:]
        else:
            name = name_token.lower()
        
        # 2) Shots from token[3]
        try:
            shots = int(re.sub(r"[^\d]", "", tokens[3]))
        except:
            failed.append(raw_line)
            continue
        
        # 3) Find expiry date - usually at position 7 or 8
        expiry_date = None
        for i in range(7, min(10, len(tokens))):
            try:
                expiry_date = datetime.strptime(tokens[i], "%m/%d/%Y").date()
                break
            except:
                continue
        
        if name not in reagent_sets:
            reagent_sets[name] = []
        reagent_sets[name].append({
            "line": raw_line,
            "shots": shots,
            "expiry_date": expiry_date
        })
    
    final_data = {}
    for name, entries in reagent_sets.items():
        entries = sorted(entries, key=lambda x: x["shots"])
        total_usable = 0
        expiry_dates = []
        
        i = 0
        while i < len(entries):
            if i + 1 < len(entries):
                s1, s2 = entries[i]["shots"], entries[i + 1]["shots"]
                min_shots = min(s1, s2)
                expiry_dates += [entries[i]["expiry_date"], entries[i + 1]["expiry_date"]]
                i += 2
            else:
                min_shots = entries[i]["shots"]
                expiry_dates.append(entries[i]["expiry_date"])
                i += 1
            total_usable += min_shots
        
        expiry_dates = [d for d in expiry_dates if d is not None]
        earliest_exp = min(expiry_dates) if expiry_dates else None
        
        # Calculate onboard remaining from the OCR data
        # This is a placeholder - you may need to adjust this based on your actual data
        onboard_remaining = None
        
        final_data[name] = {
            "shots": total_usable,
            "expiry_date": earliest_exp,
            "onboard_remaining": onboard_remaining
        }
    
    if failed:
        with st.expander("⚠️ AU5800 lines skipped during parsing"):
            for ln in failed:
                st.text(ln)
    
    return final_data

def parse_ocr_text(text, analyzer):
    if analyzer == "Roche e801":
        return parse_e801(text)
    if analyzer == "Beckman AU5800":
        return parse_au5800(text)
    # Generic fallback
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
def extract_reagent_data_from_pdf(uploaded_pdf_file, analyzer, pages=None):
    """
    OCR & parse only the selected pages of the PDF.

    Args:
        uploaded_pdf_file: Streamlit UploadedFile
        analyzer: one of ANALYZER_HEADERS.keys()
        pages: list of 1-based page numbers to include (None = all pages)

    Returns:
        dict: parsed reagent data for that analyzer
    """
    if uploaded_pdf_file is None:
        return None

    try:
        pdf_bytes = uploaded_pdf_file.getvalue()
        images = convert_from_bytes(pdf_bytes, dpi=150)
        total_pages = len(images)

        if pages:
            indices = [p - 1 for p in pages if 1 <= p <= total_pages]
        else:
            indices = list(range(total_pages))

        full_text = ""
        for idx in indices:
            img = images[idx]
            # Auto-rotate landscape pages for AU5800
            if analyzer == "Beckman AU5800" and img.width > img.height:
                img = img.rotate(90, expand=True)
            page_text = pytesseract.image_to_string(img, config=tesseract_config)
            full_text += page_text + "\n\n"

        st.write(f"Parsing {analyzer} PDF (pages {', '.join(map(str, pages or range(1,total_pages+1)))})…")
        return parse_ocr_text(full_text, analyzer)

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None