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

# — Sidebar —
with st.sidebar:
    st.header("1) Upload Files & Settings")
    uploaded_excel = st.file_uploader("Minimum Volumes Excel (.xlsx)", type=["xlsx"])
    uploaded_pdf   = st.file_uploader("Reagent Status PDF (.pdf)", type=["pdf"])

    # Pick analyzer
    analyzer_list    = list(ANALYZER_HEADERS.keys())
    selected_analyzer = st.selectbox("Select Analyzer Type", analyzer_list)

    # Pick module (sheet)
    modules = load_min_volumes_by_module(uploaded_excel) if uploaded_excel else {}
    selected_module, min_volumes = select_module(modules) if modules else (None, {})

    # Choose pages of PDF
    page_count = 0
    selected_pages = None
    if uploaded_pdf:
        pdf_bytes = uploaded_pdf.getvalue()
        images = convert_from_bytes(pdf_bytes, dpi=150)
        page_count = len(images)
        selected_pages = st.multiselect(
            f"Select PDF Pages (1–{page_count})", list(range(1, page_count+1)),
            default=list(range(1, page_count+1))
        )

# — Main —
st.title("Reagent Volume Checker")
st.markdown("Upload PDF & Excel, pick your analyzer, module, and which PDF pages to include.")
st.divider()

btn = st.button("Check Reagent Levels", disabled=not (uploaded_pdf and uploaded_excel and selected_module))
if btn:
    st.subheader(f"Analyzer: {selected_module}")
    col1, col2 = st.columns(2)

    with col1:
        st.write("Extracting OCR data…")
        current_data = extract_reagent_data_from_pdf(
            uploaded_pdf_file=uploaded_pdf,
            analyzer=selected_analyzer,
            pages=selected_pages
        )
        if not current_data:
            st.error("No data parsed from PDF—check your page selection & analyzer.")
            st.stop()
        st.success(f"Extracted {len(current_data)} reagents.")

    with col2:
        st.write("⚖️ Comparing to minimum volumes…")
        results_df = find_reagents_to_load(current_data, min_volumes, selected_analyzer)

    st.divider()
    st.subheader("Results: Reagents to Load or Expiring Soon")

    # Columns to Display
    primary_key = ANALYZER_FIELDS[selected_analyzer]["primary_field"]
    primary_col = primary_key.replace("_", " ").title()
    display_cols = [
        "Reagent Name",
        primary_col,
        "Minimum Volume",
        "Expiry Date",
        "Expires Within 7 Days"
    ]

    if results_df.empty:
        st.success("All reagents meet minimum requirements and none expire within 7 days.")
    else:
        st.warning("The following reagents need loading or are expiring soon:")
        st.dataframe(results_df[display_cols], use_container_width=True)

st.divider()
st.caption(f"Reagent Checker App | Date: {pd.Timestamp.now():%Y-%m-%d}")

