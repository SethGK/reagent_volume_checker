# app.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Import functions from other modules
import utils
import config_manager # Import the whole module to access PREDEFINED_CONFIGS
from ui_components import (
    display_sidebar,
    display_results,
    display_download_buttons,
    display_instructions,
    display_footer
)

# --- App Configuration ---
st.set_page_config(page_title="Reagent Volume Checker", layout="wide")

# --- Initialize Session State ---
# Use more descriptive names in session state
if 'custom_configurations' not in st.session_state:
    # Store only CUSTOM configurations here
    st.session_state['custom_configurations'] = {}
if 'selected_format_name' not in st.session_state:
     # Initialize selection, default to first predefined
     st.session_state['selected_format_name'] = list(config_manager.PREDEFINED_CONFIGS.keys())[0]
# Initialize data state variables
if 'reagents_df' not in st.session_state:
     st.session_state['reagents_df'] = None
if 'mins_df' not in st.session_state:
     st.session_state['mins_df'] = None
if 'result_df' not in st.session_state:
     st.session_state['result_df'] = None
# State triggers for sidebar actions
if 'config_to_update' not in st.session_state:
     st.session_state['config_to_update'] = None
if 'config_to_delete' not in st.session_state:
     st.session_state['config_to_delete'] = None
if 'pdf_processed' not in st.session_state: # Flag to track if PDF processing was attempted
     st.session_state['pdf_processed'] = False


# --- Handle Sidebar Actions affecting State ---
# Update custom configs based on form submission
if st.session_state['config_to_update']:
     name, config_data = list(st.session_state['config_to_update'].items())[0]
     st.session_state['custom_configurations'][name] = config_data
     # Optionally, set the newly added/updated config as selected
     st.session_state['selected_format_name'] = name
     st.session_state['config_to_update'] = None # Reset trigger
     st.rerun() # Rerun to reflect changes in sidebar selectbox

# Delete custom config
if st.session_state['config_to_delete']:
     name_to_delete = st.session_state['config_to_delete']
     if name_to_delete in st.session_state['custom_configurations']:
          del st.session_state['custom_configurations'][name_to_delete]
          st.success(f"Custom format '{name_to_delete}' deleted.")
          # Reset selection to default if the deleted one was selected
          if st.session_state['selected_format_name'] == name_to_delete:
               st.session_state['selected_format_name'] = list(config_manager.PREDEFINED_CONFIGS.keys())[0]
     else:
          st.warning(f"Could not delete '{name_to_delete}', format not found.")
     st.session_state['config_to_delete'] = None # Reset trigger
     st.rerun() # Rerun to update sidebar


# --- Sidebar ---
# Pass the current custom configs to the sidebar function
# It now returns only the selected format name; state updates are handled above
selected_format_name = display_sidebar(st.session_state['custom_configurations'])
# Update state if selection changed in the sidebar
if st.session_state['selected_format_name'] != selected_format_name:
    st.session_state['selected_format_name'] = selected_format_name
    # Clear old results when format changes? Optional, but often good UX.
    st.session_state['reagents_df'] = None
    st.session_state['mins_df'] = None
    st.session_state['result_df'] = None
    st.session_state['pdf_processed'] = False
    st.rerun() # Rerun to reflect the change


# --- Main Application UI ---
st.title("Reagent Volume Checker")
st.write(f"Selected Format: **{st.session_state['selected_format_name']}**") # Show selected format
st.write("Upload a PDF (matching the selected format) and an Excel file (`Test`, `MinVolume` columns).")


# File upload area
col1, col2 = st.columns(2)
with col1:
    st.subheader("Step 1: Upload Reagent PDF")
    pdf_file = st.file_uploader(
         "Drop or select PDF file", type=["pdf"], key="pdf_uploader", accept_multiple_files=False
     )
with col2:
    st.subheader("Step 2: Upload Min Volumes Excel")
    excel_file = st.file_uploader(
         "Drop or select Excel file", type=["xlsx", "xls"], key="excel_uploader", accept_multiple_files=False
     )

# --- Processing Logic ---
# Find the actual configuration dictionary based on the selected name
current_format_config = None
selected_name = st.session_state['selected_format_name']
if selected_name in config_manager.PREDEFINED_CONFIGS:
    current_format_config = config_manager.PREDEFINED_CONFIGS[selected_name]
elif selected_name in st.session_state['custom_configurations']:
    current_format_config = st.session_state['custom_configurations'][selected_name]


if pdf_file and excel_file:
    if not current_format_config:
         # This case should be less likely now with default selection handling
         st.error(f"Configuration error: Cannot find definition for selected format '{selected_name}'.")
         st.stop()

    st.subheader("Processing Files...")
    progress_bar = st.progress(0, text="Starting processing...")
    st.session_state['pdf_processed'] = False # Reset flag


    # 1. Extract reagent data from PDF
    progress_bar.progress(25, text=f"Extracting data from PDF using '{selected_name}' format...")
    # Pass the actual config dictionary to the extraction function
    st.session_state['reagents_df'] = utils.extract_reagents_from_pdf(pdf_file, current_format_config)
    st.session_state['pdf_processed'] = True # Mark that processing was attempted


    # 2. Load minimum volumes from Excel (only if PDF extraction succeeded)
    if st.session_state['reagents_df'] is not None:
        progress_bar.progress(50, text="Loading minimum volumes from Excel...")
        st.session_state['mins_df'] = utils.load_min_volumes(excel_file, test_column="Test", min_vol_column="MinVolume")
    else:
         st.session_state['mins_df'] = None
         st.error("Skipping Excel processing due to PDF extraction errors.")


    # 3. Compare reagents if both dataframes are valid
    if st.session_state['reagents_df'] is not None and st.session_state['mins_df'] is not None:
        progress_bar.progress(75, text="Comparing reagent levels...")
        # Pass the actual config dictionary to the comparison function
        st.session_state['result_df'] = utils.compare_reagents(
            st.session_state['reagents_df'],
            st.session_state['mins_df'],
            current_format_config # Pass the actual config dictionary
        )
    else:
         st.session_state['result_df'] = None
         if st.session_state['reagents_df'] is not None:
              st.error("Skipping comparison due to errors loading minimum volumes.")


    progress_bar.progress(100, text="Processing complete.")


    # --- Display Results and Downloads ---
    # Pass the actual config dictionary for display formatting
    display_results(st.session_state['reagents_df'], st.session_state['result_df'], current_format_config, st.session_state['pdf_processed'])

    # Pass config to download buttons too, in case it's needed later
    display_download_buttons(st.session_state['reagents_df'], st.session_state['result_df'], current_format_config)


elif pdf_file or excel_file:
     # Only one file uploaded
     st.info("Please upload both a PDF and an Excel file to begin analysis.")
else:
    # No files uploaded yet (initial state)
    st.info("Upload files using the sections above.")


# --- Instructions and Footer ---
display_instructions()
display_footer()