# excel_processor.py
import pandas as pd
import streamlit as st
from io import BytesIO

@st.cache_data(ttl=3600)
def load_min_volumes_by_module(uploaded_excel_file):
    """
    Reads an Excel file where each sheet is a module (e.g. AU1-1, AU1-2) containing
    'Reagent Name' and 'Minimum Volume'.

    Returns:
        dict: { sheet_name: { reagent_name: min_volume (int) } }
    """
    if uploaded_excel_file is None:
        return {}

    # Read into a BytesIO buffer for caching
    file_buffer = BytesIO(uploaded_excel_file.getvalue())
    try:
        xls = pd.ExcelFile(file_buffer)
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        return {}

    modules = {}
    for sheet in xls.sheet_names:
        try:
            df = xls.parse(sheet_name=sheet)
        except Exception as e:
            st.warning(f"Could not parse sheet '{sheet}': {e}")
            continue

        # Normalize column names
        df.columns = (
            df.columns
              .str.strip()
              .str.lower()
              .str.replace(' ', '_')
        )

        # Identify required columns
        reagent_col = next((c for c in df.columns if 'reagent' in c), None)
        min_col = next((c for c in df.columns if 'min' in c and 'vol' in c), None)
        if not reagent_col or not min_col:
            st.warning(
                f"Sheet '{sheet}' missing 'Reagent Name' or 'Minimum Volume'. Skipping."
            )
            continue

        # Clean and filter data
        df = df[[reagent_col, min_col]].copy()
        df[min_col] = pd.to_numeric(df[min_col], errors='coerce')
        df.dropna(subset=[reagent_col, min_col], inplace=True)
        df[min_col] = df[min_col].astype(int)
        df[reagent_col] = (
            df[reagent_col]
              .astype(str)
              .str.strip()
              .str.lower()
        )

        # Build module dict
        modules[sheet] = dict(zip(df[reagent_col], df[min_col]))

    if not modules:
        st.error("No valid sheets found in Excel file.")
    return modules


def select_module(modules_dict, default=None):
    """
    Streamlit helper to select a module (sheet) from loaded modules.

    Args:
        modules_dict (dict): { sheet_name: { reagent: min_vol } }
        default (str, optional): default sheet to select

    Returns:
        tuple: (selected_sheet_name, min_vol_dict)
    """
    if not modules_dict:
        st.error("No modules available to select.")
        return None, {}

    sheet = st.sidebar.selectbox(
        "Select Module", options=list(modules_dict.keys()), index=(list(modules_dict.keys()).index(default) if default in modules_dict else 0)
    )
    return sheet, modules_dict.get(sheet, {})
