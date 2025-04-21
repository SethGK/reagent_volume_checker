# excel_processor.py
import pandas as pd
import streamlit as st
from io import BytesIO

@st.cache_data(ttl=3600) # Cache data for 1 hour
def load_min_volumes(uploaded_excel_file):
    """
    Loads minimum reagent volumes from an uploaded Excel file.
    Assumes each sheet name corresponds to an analyzer.
    Assumes columns 'Reagent Name' and 'Minimum Volume'.

    Args:
        uploaded_excel_file: The uploaded file object from Streamlit.

    Returns:
        A dictionary where keys are analyzer names (sheet names)
        and values are pandas DataFrames with 'Reagent Name' and 'Minimum Volume'.
        Returns None if the file cannot be processed.
    """
    if uploaded_excel_file is None:
        return None

    try:
        # Read the file into memory (needed for caching with uploaded files)
        file_content = BytesIO(uploaded_excel_file.getvalue())
        excel_data = pd.ExcelFile(file_content)
        analyzer_sheets = excel_data.sheet_names

        min_volumes_dict = {}
        required_columns = ['Reagent Name', 'Minimum Volume']

        for sheet in analyzer_sheets:
            df = excel_data.parse(sheet_name=sheet)
            # Basic validation: Check if required columns exist
            if all(col in df.columns for col in required_columns):
                 # Ensure volume is numeric, drop rows where it's not
                df['Minimum Volume'] = pd.to_numeric(df['Minimum Volume'], errors='coerce')
                df.dropna(subset=['Minimum Volume', 'Reagent Name'], inplace=True)
                df['Minimum Volume'] = df['Minimum Volume'].astype(int)
                # Standardize reagent names (lowercase, strip whitespace) for matching
                df['Reagent Name'] = df['Reagent Name'].astype(str).str.strip().str.lower()
                min_volumes_dict[sheet] = df[['Reagent Name', 'Minimum Volume']].set_index('Reagent Name')
            else:
                st.warning(f"Sheet '{sheet}' in Excel file is missing required columns "
                           f"({', '.join(required_columns)}). Skipping this sheet.")

        if not min_volumes_dict:
            st.error("No valid sheets found in the Excel file with columns 'Reagent Name' and 'Minimum Volume'.")
            return None

        return min_volumes_dict

    except Exception as e:
        st.error(f"Error processing Excel file: {e}")
        return None