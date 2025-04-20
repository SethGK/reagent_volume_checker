# app.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Import functions from other modules
import utils
import config_manager
from ui_components import display_sidebar, display_results, display_download_buttons, display_instructions, display_footer

# --- App Configuration ---
st.set_page_config(page_title="Reagent Volume Checker", layout="wide")

# --- Initialize Session State ---
# Store configurations in session state to persist across reruns
if 'table_configurations' not in st.session_state:
    st.session_state['table_configurations'] = config_manager.DEFAULT_CONFIG.copy()
if 'selected_format' not in st.session_state:
     st.session_state['selected_format'] = list(st.session_state['table_configurations'].keys())[0]
if 'reagents_df' not in st.session_state:
     st.session_state['reagents_df'] = None
if 'mins_df' not in st.session_state:
     st.session_state['mins_df'] = None
if 'result_df' not in st.session_state:
     st.session_state['result_df'] = None
if 'new_config_to_add' not in st.session_state: # Used to pass data from sidebar form
     st.session_state['new_config_to_add'] = None


# --- Sidebar ---
# Load config from file *before* displaying sidebar if uploaded
uploaded_config = st.session_state.get('config_upload') # Access file uploader state
if uploaded_config:
     loaded_config = config_manager.load_config_from_file(uploaded_config)
     if loaded_config:
          # Merge or replace configurations
          # Example: Update existing, add new ones
          st.session_state['table_configurations'].update(loaded_config)
          st.info("Configurations updated from file.")
          # Reset uploader maybe? Streamlit handles this fairly well.

# Handle adding new config from sidebar form
if st.session_state['new_config_to_add']:
     st.session_state['table_configurations'].update(st.session_state['new_config_to_add'])
     st.success(f"Configuration '{list(st.session_state['new_config_to_add'].keys())[0]}' saved for this session.")
     st.session_state['new_config_to_add'] = None # Reset the trigger
     # Rerun to update sidebar dropdown immediately
     st.rerun()


# Display sidebar and get selected format
selected_format_name = display_sidebar(st.session_state['table_configurations'])
st.session_state['selected_format'] = selected_format_name # Update state if changed

# --- Main Application UI ---
st.title("Reagent Volume Checker")
st.write("Upload a PDF with reagent data and an Excel file defining minimum required volumes.")

# File upload area
col1, col2 = st.columns(2)

with col1:
    st.subheader("Step 1: Upload Reagent PDF")
    pdf_file = st.file_uploader(
         "Drop or select PDF file",
         type=["pdf"],
         key="pdf_uploader", # Use key to access state if needed elsewhere
         accept_multiple_files=False
     )

with col2:
    st.subheader("Step 2: Upload Min Volumes Excel")
    excel_file = st.file_uploader(
         "Drop or select Excel file (`Test`, `MinVolume` columns required)",
         type=["xlsx", "xls"],
         key="excel_uploader",
         accept_multiple_files=False
     )

# --- Processing Logic ---
if pdf_file and excel_file:
    st.subheader("Processing Files...")
    progress_bar = st.progress(0, text="Starting processing...")

    # Get the actual configuration dictionary for the selected format
    current_format_config = st.session_state['table_configurations'].get(st.session_state['selected_format'])

    if not current_format_config:
         st.error(f"Selected format '{st.session_state['selected_format']}' not found in configurations. Please select a valid format.")
         st.stop()

    # 1. Extract reagent data from PDF
    progress_bar.progress(25, text="Extracting data from PDF...")
    st.session_state['reagents_df'] = utils.extract_reagents_from_pdf(pdf_file, current_format_config)

    # 2. Load minimum volumes from Excel
    if st.session_state['reagents_df'] is not None:
        progress_bar.progress(50, text="Loading minimum volumes from Excel...")
        # Assuming standard column names "Test" and "MinVolume" in Excel
        st.session_state['mins_df'] = utils.load_min_volumes(excel_file, test_column="Test", min_vol_column="MinVolume")
    else:
         st.session_state['mins_df'] = None # Ensure mins_df is None if PDF failed
         st.error("Skipping Excel processing due to PDF extraction errors.")


    # 3. Compare reagents if both dataframes are valid
    if st.session_state['reagents_df'] is not None and st.session_state['mins_df'] is not None:
        progress_bar.progress(75, text="Comparing reagent levels...")
        st.session_state['result_df'] = utils.compare_reagents(
            st.session_state['reagents_df'],
            st.session_state['mins_df'],
            current_format_config
        )
    else:
         st.session_state['result_df'] = None # Ensure result is None if previous steps failed
         if st.session_state['reagents_df'] is not None: # Only show this if PDF was OK but Excel failed
              st.error("Skipping comparison due to errors loading minimum volumes.")


    progress_bar.progress(100, text="Processing complete.")

    # --- Display Results and Downloads ---
    # Pass the current config to ensure correct column names are used for display
    display_results(st.session_state['reagents_df'], st.session_state['result_df'], current_format_config)

    if st.session_state['reagents_df'] is not None: # Only show downloads if PDF processing was somewhat successful
         display_download_buttons(st.session_state['reagents_df'], st.session_state['result_df'])
    else:
         st.warning("Downloads unavailable because PDF data could not be extracted.")


else:
    st.info("Please upload both a PDF and an Excel file to begin analysis.")

# --- Instructions and Footer ---
display_instructions()
display_footer()