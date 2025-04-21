# main_app.py
import streamlit as st
import pandas as pd
from io import BytesIO

# Import our modules
from excel_processor import load_min_volumes
from pdf_processor import extract_reagent_data_from_pdf
from data_analyzer import find_reagents_to_load
import utils # Ensures Tesseract config runs

# --- Page Configuration ---
st.set_page_config(
    page_title="Reagent Volume Checker",
    page_icon="🧪",
    layout="wide", # Use wide layout for better spacing
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Sleek Design (Optional) ---
st.markdown("""
<style>
    /* General Styling */
    .stApp {
        /* background-color: #f0f2f6; */ /* Light gray background */
    }

    /* File Uploader Styling */
    .stFileUploader > label {
        font-size: 1.1em; /* Slightly larger label */
        font-weight: bold;
    }
    .stFileUploader > div > div > button {
         /* background-color: #4CAF50; Green */
         /* color: white; */
    }

    /* Button Styling */
    .stButton > button {
        border-radius: 20px; /* Rounded corners */
        padding: 10px 20px;
        font-weight: bold;
        border: 2px solid #007bff; /* Blue border */
        background-color: white;
        color: #007bff; /* Blue text */
        transition: all 0.3s ease; /* Smooth transition */
    }
    .stButton > button:hover {
        background-color: #007bff; /* Blue background on hover */
        color: white; /* White text on hover */
        border-color: #0056b3;
    }
    .stButton > button:active {
         background-color: #0056b3 !important; /* Darker blue when clicked */
         border-color: #004085 !important;
         color: white !important;
    }

    /* Dataframe styling */
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 5px;
    }

    /* Headers */
     h1, h2, h3 {
        color: #0056b3; /* Dark blue headers */
     }

</style>
""", unsafe_allow_html=True)


# --- Sidebar ---
with st.sidebar:
    st.image("https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png", width=100) # Placeholder logo
    st.header("📁 Upload Files")

    # File Uploader for Minimum Volumes (Excel)
    uploaded_excel = st.file_uploader(
        "1. Upload Minimum Volumes Excel File (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=False,
        help="Upload the Excel file containing minimum reagent volumes. Each sheet should represent an analyzer, with columns 'Reagent Name' and 'Minimum Volume'."
    )

    # File Uploader for Reagent Status PDF
    uploaded_pdf = st.file_uploader(
        "2. Upload Reagent Status PDF",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload the PDF printout from your analyzer showing current reagent names and volumes/tests remaining."
    )

    # Placeholder for Analyzer Selection (populated after Excel upload)
    analyzer_options = ["Please upload Excel file first"]
    selected_analyzer = None

    # Load Excel data and populate analyzer options
    min_volumes_data = None
    if uploaded_excel:
        min_volumes_data = load_min_volumes(uploaded_excel)
        if min_volumes_data:
            analyzer_options = list(min_volumes_data.keys())
            selected_analyzer = st.selectbox(
                "3. Select Analyzer",
                options=analyzer_options,
                index=0, # Default to the first analyzer
                help="Choose the analyzer corresponding to the uploaded PDF."
            )
        else:
            # Error handled in load_min_volumes
            analyzer_options = ["Error loading Excel file"]
            st.selectbox("3. Select Analyzer", options=analyzer_options, disabled=True)
    else:
         st.selectbox("3. Select Analyzer", options=analyzer_options, disabled=True)


# --- Main Area ---
st.title("🧪 Reagent Volume Checker")
st.markdown("Upload your analyzer's reagent status PDF and the minimum volumes Excel sheet to identify reagents needing replenishment.")
st.divider()

# Processing Logic
if st.sidebar.button("📊 Check Reagent Levels", use_container_width=True, disabled=(not uploaded_pdf or not uploaded_excel or not selected_analyzer or not min_volumes_data)):
    if uploaded_pdf and uploaded_excel and selected_analyzer and min_volumes_data:
        st.subheader(f"Processing for Analyzer: {selected_analyzer}")

        col1, col2 = st.columns(2)

        with col1:
            st.info("Reading PDF data (this may take a moment)...")
            # Extract data from PDF
            current_volumes = extract_reagent_data_from_pdf(uploaded_pdf)

            if current_volumes is None:
                st.error("Failed to extract data from PDF. Please check the file and try again.")
                st.stop() # Stop execution if PDF processing fails
            elif not current_volumes:
                 st.warning("No reagent data could be parsed from the PDF. Ensure the PDF format is readable by OCR and the parsing logic in `pdf_processor.py` is correct for your layout.")
                 # Optionally display raw text here if needed for debugging
                 st.stop()
            else:
                 st.success(f"Successfully extracted data for {len(current_volumes)} reagents from PDF.")
                 # Optional: Display extracted data for verification
                 # with st.expander("View Extracted PDF Data"):
                 #    st.dataframe(pd.DataFrame(list(current_volumes.items()), columns=['Reagent Name (from PDF)', 'Current Volume']))


        with col2:
             st.info("Comparing with minimum volumes...")
             # Get the minimum volumes for the selected analyzer
             min_volumes_df = min_volumes_data.get(selected_analyzer)

             if min_volumes_df is None or min_volumes_df.empty:
                 st.error(f"Could not find or load minimum volume data for analyzer '{selected_analyzer}' from the Excel file.")
                 st.stop() # Stop execution

             # Find reagents to load
             reagents_to_load_df = find_reagents_to_load(current_volumes, min_volumes_df)


        st.divider()
        st.subheader("📋 Results: Reagents to Load")

        if not reagents_to_load_df.empty:
            st.warning(f"Found {len(reagents_to_load_df)} reagent(s) below minimum levels:")
            st.dataframe(
                reagents_to_load_df,
                use_container_width=True,
                # Optional: Add styling or highlighting here if needed
                # hide_index=True # Uncomment if you don't want the DataFrame index
            )
        else:
            st.success("✅ All reagents are at or above minimum required volumes!")

    else:
        st.warning("Please upload both files and select an analyzer before checking levels.")

elif not uploaded_pdf or not uploaded_excel:
    st.info("Please upload the required files using the sidebar.")

# --- Footer Example ---
st.divider()
st.caption(f"Reagent Checker App | Current Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}")