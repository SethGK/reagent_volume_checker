# data_analyzer.py
import pandas as pd
import streamlit as st
from datetime import date, timedelta

# --- Analyzer Configuration ---
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

ANALYZER_FIELDS = {
    "Roche e801": {
        "primary_field": "available",
        "secondary_field": "remaining",
        "expiry_date_field": "expiry_date"
    },
    "Beckman AU5800": {
        "primary_field": "shots",
        "secondary_field": "onboard_remaining",
        "expiry_date_field": "expiry_date"
    },
}


def find_reagents_to_load(current_data, min_volumes, analyzer):
    """
    Compare OCR data to minimums using the 'primary_field' (available/tests remaining) for comparison.
    If primary_field is missing, falls back to secondary_field.

    Args:
        current_data (dict): { reagent_name: {fields...} }
        min_volumes (dict):  { reagent_name: min_volume }
        analyzer (str):      Analyzer key matching ANALYZER_FIELDS

    Returns:
        pd.DataFrame: reagents needing load or expiring soon.
    """
    cfg = ANALYZER_FIELDS.get(analyzer)
    if cfg is None:
        st.error(f"Unsupported analyzer: {analyzer}")
        return pd.DataFrame()

    primary = cfg["primary_field"]
    secondary = cfg.get("secondary_field")
    expiry_key = cfg["expiry_date_field"]

    today = date.today()
    soon = timedelta(days=7)

    records = []
    unmatched = []

    for name, fields in current_data.items():
        # Choose available (primary) if present, else fallback to secondary
        current_vol = fields.get(primary)
        if current_vol is None and secondary:
            current_vol = fields.get(secondary)
        if current_vol is None:
            continue

        min_vol = min_volumes.get(name)
        if min_vol is None:
            unmatched.append(name)
            continue

        expiry = fields.get(expiry_key)
        expires_soon = False
        if isinstance(expiry, date):
            expires_soon = (expiry - today) <= soon

        # Compare based on primary field
        if current_vol <= min_vol or expires_soon:
            record = {
                "Reagent Name": name.title(),
                "Current Volume": current_vol,
                "Minimum Volume": min_vol,
                "Expiry Date": expiry,
                "Expires Within 7 Days": expires_soon
            }
            # Add both fields if needed for context
            if primary in fields:
                record[primary.replace('_',' ').title()] = fields.get(primary)
            if secondary in fields:
                record[secondary.replace('_',' ').title()] = fields.get(secondary)

            records.append(record)

    if unmatched:
        st.info("Reagents in PDF not in min-volumes list: " + ", ".join(unmatched))

    cols = [
        "Reagent Name", "Current Volume", "Minimum Volume",
        primary.replace('_',' ').title(), secondary.replace('_',' ').title() if secondary else None,
        "Expiry Date", "Expires Within 7 Days"
    ]
    # Filter out None columns
    cols = [c for c in cols if c]

    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]
