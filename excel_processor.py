import pandas as pd
import streamlit as st
from io import BytesIO

@st.cache_data(ttl=3600)
def load_min_volumes_by_module(uploaded_excel_file):
    """
    Reads an Excel file where each sheet is a module (e.g. AU1-1, AU1-2) containing
    'Reagent Name' and 'Minimum Volume'. Falls back on two-column sheets.
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

        # Ensure column names are strings
        df.columns = df.columns.map(str)

        # Normalize column names
        df.columns = (
            df.columns
              .str.strip()
              .str.lower()
              .str.replace(' ', '_')
        )

        # Identify required columns by keyword
        reagent_col = next((c for c in df.columns if 'reagent' in c), None)
        min_col     = next((c for c in df.columns if 'min' in c and 'vol' in c), None)

        # Fallback: if exactly two columns, assume first=reagent, second=min
        if (not reagent_col or not min_col) and df.shape[1] == 2:
            st.info(f"Sheet '{sheet}' has no headers; using column1 as reagent and column2 as min-volume.")
            reagent_col = reagent_col or df.columns[0]
            min_col     = min_col     or df.columns[1]

        if not reagent_col or not min_col:
            st.warning(
                f"Sheet '{sheet}' missing 'Reagent Name' or 'Minimum Volume'. Skipping."
            )
            continue

        # Clean and filter data
        sub = df[[reagent_col, min_col]].copy()
        sub[min_col] = pd.to_numeric(sub[min_col], errors='coerce')
        sub.dropna(subset=[reagent_col, min_col], inplace=True)
        sub[min_col] = sub[min_col].astype(int)
        sub[reagent_col] = (
            sub[reagent_col]
              .astype(str)
              .str.strip()
              .str.lower()
        )

        modules[sheet] = dict(zip(sub[reagent_col], sub[min_col]))

    if not modules:
        st.error("No valid sheets found in Excel file.")
    return modules


def select_module(modules_dict, default=None):
    """
    Pick exactly one sheet (module).
    """
    if not modules_dict:
        st.error("No modules available.")
        return None, {}
    sheet = st.sidebar.selectbox(
        "Select Module",
        options=list(modules_dict.keys()),
        index=(list(modules_dict.keys()).index(default) if default in modules_dict else 0),
    )
    return sheet, modules_dict[sheet]
