# main_app.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Import our modules
from excel_processor import load_min_volumes_by_module, select_module
from pdf_processor import extract_reagent_data_from_pdf
from data_analyzer import find_reagents_to_load
import utils  # Ensures Tesseract path/config is set

# --- Page Configuration ---
st.set_page_config(
    page_title="Reagent Volume Checker",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Sleek Design ---
st.markdown("""
<style>
  /* Sidebar header */
  .sidebar .css-1d391kg { padding-top: 1rem; }

  /* File uploader labels */
  .stFileUploader > label {
    font-size: 1rem;
    font-weight: 600;
  }

  /* Button styling */
  .stButton > button {
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    font-weight: 600;
    border: 1px solid #0056b3;
    background-color: #ffffff;
    color: #0056b3;
    transition: background-color 0.2s ease;
  }
  .stButton > button:hover {
    background-color: #0056b3;
    color: #ffffff;
  }

  /* Dataframe styling */
  .stDataFrame {
    border: 1px solid #ddd;
    border-radius: 0.25rem;
  }

  /* Headers */
  h1, h2, h3 {
    color: #0056b3;
  }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Files")

    uploaded_excel = st.file_uploader(
        "Minimum Volumes Excel (.xlsx)",
        type=["xlsx"],
        help="Excel with sheets for each analyzer module: 'Reagent Name' and 'Minimum Volume'."
    )

    uploaded_pdf = st.file_uploader(
        "Reagent Status PDF (.pdf)",
        type=["pdf"],
        help="PDF printout from analyzer showing current reagent volumes/tests."
    )

    modules = {}  # sheet_name -> {reagent: min_vol}
    selected_module = None

    if uploaded_excel:
        modules = load_min_volumes_by_module(uploaded_excel)
        if modules:
            selected_module, min_volumes = select_module(modules)
        else:
            st.error("Failed to load minimum volumes. Check Excel format.")
    else:
        st.info("Upload Excel to select module.")

# --- Main Area ---
st.title("Reagent Volume Checker")
st.markdown(
    "Upload your analyzer PDF and the Excel of minimum volumes to identify reagents needing replenishment."
)
st.divider()

# Button to trigger analysis
enabled = all([uploaded_pdf, uploaded_excel, modules, selected_module])
if st.button("Check Reagent Levels", disabled=not enabled):
    if not enabled:
        st.warning("Please upload both files and select an analyzer module.")
    else:
        st.subheader(f"Analyzer: {selected_module}")
        col1, col2 = st.columns(2)

        # PDF OCR Extraction
        with col1:
            st.write("**Extracting OCR data...**")
            current_data = extract_reagent_data_from_pdf(uploaded_pdf, selected_module)
            if current_data is None:
                st.error("OCR extraction failed. Ensure Tesseract is configured and PDF is clear.")
                st.stop()
            if not current_data:
                st.warning("No reagents parsed from PDF. Check parsing logic for your analyzer.")
                st.stop()
            st.success(f"Extracted data for {len(current_data)} reagents.")

        # Comparison against minimums
        with col2:
            st.write("**Comparing to minimum volumes...**")
            min_volumes = modules.get(selected_module, {})
            results_df = find_reagents_to_load(current_data, min_volumes, selected_module)

        # Display Results
        st.divider()
        st.subheader("Results: Reagents to Load or Expiring Soon")
        if results_df.empty:
            st.success("All reagents meet minimum requirements and none expire within 7 days.")
        else:
            st.dataframe(results_df, use_container_width=True)

# Footer
st.divider()
st.caption(f"Reagent Checker App | Date: {pd.Timestamp.now():%Y-%m-%d}")
