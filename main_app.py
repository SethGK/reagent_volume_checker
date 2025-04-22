# main_app.py
import streamlit as st
import pandas as pd
from io import BytesIO
from pdf2image import convert_from_bytes
import pytesseract

# Import modules
from excel_processor import load_min_volumes_by_module, select_module
from pdf_processor import extract_reagent_data_from_pdf, ANALYZER_HEADERS, tesseract_config
from data_analyzer import find_reagents_to_load, ANALYZER_FIELDS
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
  .stFileUploader > label {
    font-size: 1rem;
    font-weight: 600;
  }
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
  .stDataFrame {
    border: 1px solid #ddd;
    border-radius: 0.25rem;
  }
  h1, h2, h3 {
    color: #0056b3;
  }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Files & Select Settings")

    uploaded_excel = st.file_uploader("1. Minimum Volumes Excel (.xlsx)", type=["xlsx"])
    uploaded_pdf = st.file_uploader("2. Reagent Status PDF (.pdf)", type=["pdf"])

    analyzer_list = list(ANALYZER_HEADERS.keys())
    selected_analyzer = st.selectbox("3. Select Analyzer Type", analyzer_list)

    modules = {}
    selected_module = None
    if uploaded_excel:
        modules = load_min_volumes_by_module(uploaded_excel)
        if modules:
            selected_module, min_volumes = select_module(modules)
        else:
            st.error("Failed to load minimum volumes. Check Excel format.")

# --- Main Area ---
st.title("Reagent Volume Checker")
st.markdown("Upload your analyzer PDF and the Excel of minimum volumes to identify reagents needing replenishment.")
st.divider()

if st.button("Check Reagent Levels", disabled=not (uploaded_pdf and uploaded_excel and selected_module)):
    st.subheader(f"Analyzer: {selected_module}")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Extracting OCR data...**")
        try:
            pdf_bytes = uploaded_pdf.getvalue()
            images = convert_from_bytes(pdf_bytes, dpi=150)
            full_text = ''.join(pytesseract.image_to_string(img, config=tesseract_config) + '\n' for img in images)
            current_data = extract_reagent_data_from_pdf(uploaded_pdf, selected_analyzer)
        except Exception as e:
            st.error(f"OCR extraction failed: {e}")
            st.stop()

        if not current_data:
            with st.expander("View Raw OCR Output for Debugging"):
                st.text(full_text)
            st.warning("No reagents parsed from PDF. Check analyzer type and OCR accuracy.")
            st.stop()

        st.success(f"Extracted data for {len(current_data)} reagents using {selected_analyzer} parser.")

    with col2:
        st.write("**Comparing to minimum volumes...**")
        min_volumes = modules.get(selected_module, {})
        results_df = find_reagents_to_load(current_data, min_volumes, selected_analyzer)

    st.divider()
    st.subheader("Results: Reagents to Load or Expiring Soon")

    # Determine the user‐friendly name of the primary field (e.g. "available" → "Available")
    primary_key = ANALYZER_FIELDS[selected_analyzer]["primary_field"]
    primary_col = primary_key.replace("_", " ").title()

    if results_df.empty:
        st.success("All reagents meet minimum requirements and none expire within 7 days.")
    else:
        st.warning("The following reagents are below minimum volume or expiring soon:")
        # Only show the five desired columns:
        display_cols = [
            "Reagent Name",
            primary_col,            # Available or Shots
            "Minimum Volume",
            "Expiry Date",
            "Expires Within 7 Days"
        ]
        # Some analyzers label the expiry field differently; ensure it exists
        st.dataframe(results_df[display_cols], use_container_width=True)



st.divider()
st.caption(f"Reagent Checker App | Date: {pd.Timestamp.now():%Y-%m-%d}")
