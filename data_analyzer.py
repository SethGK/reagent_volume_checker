# data_analyzer.py
import pandas as pd
import streamlit as st
from datetime import date, timedelta

# --- Analyzer Configuration ---
# For future analyzers, add header lists in ANALYZER_HEADERS (used elsewhere)
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
    # Add additional analyzers and their headers here
}

# Mapping of analyzers to data field keys produced by PDF processing
ANALYZER_FIELDS = {
    "Roche e801": {
        "volume_field": "remaining",
        "available_field": "available",
        "expiry_date_field": "expiry_date"
    },
    "Beckman AU5800": {
        "volume_field": "shots",
        "onboard_field": "onboard_remaining",
        "expiry_date_field": "expiry_date"
    },
    # Add new analyzer mappings here
}


def find_reagents_to_load(current_data, min_volumes, analyzer):
    """
    Compare OCR-extracted data to minimums and flag expiring reagents.

    Args:
        current_data (dict): { reagent_name: {fields...} }
        min_volumes (dict):  { reagent_name: min_volume }
        analyzer (str):      Analyzer key matching ANALYZER_FIELDS

    Returns:
        pd.DataFrame: reagents needing load or expiring soon.
    """
    # Validate analyzer support
    cfg = ANALYZER_FIELDS.get(analyzer)
    if cfg is None:
        st.error(f"Unsupported analyzer: {analyzer}")
        return pd.DataFrame()

    vol_key = cfg["volume_field"]
    avail_key = cfg.get("available_field")
    onboard_key = cfg.get("onboard_field")
    expiry_key = cfg["expiry_date_field"]

    today = date.today()
    soon = timedelta(days=7)

    records = []
    unmatched = []

    for name, fields in current_data.items():
        # Fetch current volume
        current_vol = fields.get(vol_key)
        if current_vol is None:
            continue

        # Lookup min volume
        min_vol = min_volumes.get(name)
        if min_vol is None:
            unmatched.append(name)
            continue

        # Check expiry
        expiry = fields.get(expiry_key)
        expires_soon = False
        if isinstance(expiry, date):
            expires_soon = (expiry - today) <= soon

        # Determine if reagent needs loading or is expiring
        if current_vol <= min_vol or expires_soon:
            rec = {
                "Reagent Name": name.title(),
                "Current Volume": current_vol,
                "Minimum Volume": min_vol,
                "Expiry Date": expiry,
                "Expires Within 7 Days": expires_soon
            }
            if avail_key and avail_key in fields:
                rec["Available Tests"] = fields.get(avail_key)
            if onboard_key and onboard_key in fields:
                rec["Onboard Remaining"] = fields.get(onboard_key)

            records.append(rec)

    # Notify about unmatched
    if unmatched:
        st.info(
            "Reagents in PDF not found in min-volumes list: " + ", ".join(unmatched)
        )

    # Build result DataFrame with consistent columns
    cols = [
        "Reagent Name", "Current Volume", "Minimum Volume",
        "Available Tests", "Onboard Remaining",
        "Expiry Date", "Expires Within 7 Days"
    ]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    # Ensure all columns present
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]
