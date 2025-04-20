# ui_components.py

import streamlit as st
import json
import base64
from datetime import datetime
# Import PREDEFINED_CONFIGS and validation functions
from config_manager import PREDEFINED_CONFIGS, validate_config_format, get_custom_config_download_link, load_custom_config_from_file
import utils # Import utils if display_download_buttons calls utils.generate_excel_report
from io import BytesIO

def display_sidebar(custom_configs):
    """Displays the sidebar UI elements and handles configuration logic.
       Args:
           custom_configs (dict): The dictionary holding user-defined custom configurations.
       Returns:
           tuple: (selected_format_name, updated_custom_configs)
    """
    st.sidebar.title("Configuration")

    # --- Load Custom Configurations ---
    st.sidebar.subheader("Load Custom Formats")
    config_file = st.sidebar.file_uploader("Upload Custom Formats File (JSON)", type=["json"], key="custom_config_upload")
    if config_file:
        loaded_configs = load_custom_config_from_file(config_file)
        if loaded_configs:
            # Decide merge strategy: Overwrite duplicates or keep existing? Overwrite is simpler.
            custom_configs.update(loaded_configs)
            st.sidebar.success(f"Loaded/updated {len(loaded_configs)} custom format(s).")
            # Reset the file uploader state after successful load to prevent reloading on every rerun
            st.session_state.custom_config_upload = None # Requires setting the key in file_uploader
            st.rerun() # Rerun to reflect changes immediately


    # --- Select Format ---
    st.sidebar.divider()
    st.sidebar.subheader("Select Table Format")
    predefined_options = list(PREDEFINED_CONFIGS.keys())
    custom_options = list(custom_configs.keys())
    format_options = predefined_options + custom_options

    # Determine default index - prioritize existing selection if valid, else default to first predefined
    current_selection = st.session_state.get('selected_format', predefined_options[0])
    try:
         default_index = format_options.index(current_selection)
    except ValueError:
         default_index = 0 # Fallback to the first option if previous selection is no longer valid

    selected_format = st.sidebar.selectbox(
        "Select Format",
        format_options,
        index=default_index,
        key="format_select" # Keep key for state persistence
    )

    # --- Manage Custom Configurations ---
    st.sidebar.divider()
    st.sidebar.subheader("Create or Update Custom Format")

    # Populate form if a custom format is selected for editing
    editing_config = custom_configs.get(selected_format, {}) if selected_format in custom_options else {}
    cols_str = ", ".join(editing_config.get("columns", []))
    qty_col = editing_config.get("quantity_column", "")
    test_col = editing_config.get("test_name_column", "")
    lot_col = editing_config.get("lot_column", "")
    exp_col = editing_config.get("expiry_column", "")
    form_name = selected_format if selected_format in custom_options else ""

    with st.sidebar.form("custom_config_form", clear_on_submit=True):
         custom_config_name = st.text_input("Custom Format Name", value=form_name, key="cust_name")
         custom_config_columns = st.text_input("Column Names (comma-separated)", value=cols_str, key="cust_cols")
         custom_config_qty = st.text_input("Quantity Column Name", value=qty_col, key="cust_qty")
         custom_config_test = st.text_input("Test Name Column", value=test_col, key="cust_test")
         custom_config_lot = st.text_input("Lot ID Column (Optional)", value=lot_col, key="cust_lot")
         custom_config_exp = st.text_input("Expiry Date Column (Optional)", value=exp_col, key="cust_exp")
         submitted = st.form_submit_button(f"Save Custom Format")

         if submitted:
              name = custom_config_name.strip()
              if not all([name, custom_config_columns, custom_config_qty, custom_config_test]):
                  st.warning("Please fill in required fields (Name, Columns, Quantity Col, Test Col).")
              elif name in PREDEFINED_CONFIGS:
                  st.warning(f"Cannot use '{name}'. It is a predefined format name.")
              else:
                  new_format = {
                      "columns": [col.strip() for col in custom_config_columns.split(",") if col.strip()],
                      "quantity_column": custom_config_qty.strip(),
                      "test_name_column": custom_config_test.strip(),
                      "is_predefined": False # Mark as custom
                  }
                  # Only include optional columns if they are provided and valid
                  if custom_config_lot.strip():
                       new_format["lot_column"] = custom_config_lot.strip()
                  if custom_config_exp.strip():
                      new_format["expiry_column"] = custom_config_exp.strip()

                  if validate_config_format(new_format):
                      # Trigger update in app.py via session state
                      st.session_state['config_to_update'] = {name: new_format}
                      st.success(f"Custom format '{name}' saved for this session.")
                      # Form clears on submit, state trigger handles update & rerun in app.py
                  else:
                      st.error("Invalid configuration format. Please check the fields.") # Validation func shows details

    # --- Delete Custom Configuration ---
    if selected_format in custom_options:
         if st.sidebar.button(f"Delete Custom Format '{selected_format}'", key=f"del_{selected_format}"):
              st.session_state['config_to_delete'] = selected_format
              st.rerun() # Rerun to process deletion in app.py


    # --- Export Custom Configurations ---
    st.sidebar.divider()
    st.sidebar.subheader("Export Custom Formats")
    download_link = get_custom_config_download_link(custom_configs)
    if download_link: # Only show markdown if link exists
        st.sidebar.markdown(download_link, unsafe_allow_html=True)


    # Return the selected format name and potentially modified custom configs
    # Let app.py handle state updates based on triggers like 'config_to_update'
    return selected_format

# (Keep other ui_components functions: display_results, display_download_buttons, display_instructions, display_footer)
# Make sure display_results and display_download_buttons receive the actual 'config' dictionary
# which app.py will fetch based on the selected_format_name.

def display_results(reagents_df, result_df, config):
    """Displays the comparison results and dataframes."""
    st.subheader("Results")

    if config is None:
         st.error("No valid configuration selected or found.")
         return
    if result_df is None and reagents_df is None: # Check if processing even started
        st.info("Upload files and select a format to see results.")
        return
    if result_df is None and reagents_df is not None: # Check if comparison failed
         # Error messages should ideally come from the processing functions (utils.py)
         st.warning("Comparison could not be completed. Check previous error messages.")
         # Still show the extracted data if available
    elif result_df is not None: # Comparison completed
        if result_df.empty:
            st.success("✅ All reagents are above the minimum volume according to the provided files and configuration.")
        else:
            st.warning(f"⚠️ {len(result_df)} reagents are below the required volume:")
            # Dynamically get columns from config, ensuring they exist in the result_df
            display_cols = [config['test_name_column'], config['quantity_column'], 'MinVolume'] # MinVolume is added during merge
            if config.get('lot_column') and config['lot_column'] in result_df.columns:
                display_cols.append(config['lot_column'])
            if config.get('expiry_column') and config['expiry_column'] in result_df.columns:
                 display_cols.append(config['expiry_column'])
            # Filter for columns actually present in the dataframe to avoid KeyErrors
            valid_display_cols = [col for col in display_cols if col in result_df.columns]
            st.dataframe(result_df[valid_display_cols])

    # Display all reagent data (extracted from PDF)
    if reagents_df is not None:
         with st.expander("Show All Extracted Reagent Data (from PDF)"):
              # Use column names from the config for display order/selection
              display_cols_all = config.get('columns', list(reagents_df.columns)) # Fallback to df columns if 'columns' missing in config
              valid_display_cols_all = [col for col in display_cols_all if col in reagents_df.columns]
              st.dataframe(reagents_df[valid_display_cols_all])
    elif pdf_file_processed: # Add a flag if needed to know if PDF processing was attempted
         st.warning("Could not display extracted reagent data due to PDF processing errors.")

# NOTE: Ensure display_download_buttons uses the correct config object if needed
# Currently it mainly uses the dataframes, which should be fine.
# Pass 'utils' if generate_excel_report is called directly (it's better practice to call via utils.generate_excel_report)
def display_download_buttons(reagents_df, below_min_df, config):
     """Displays download buttons for reports."""
     st.subheader("Download Reports")

     report_generated = False
     full_report_bytes = None
     if reagents_df is not None:
          # Pass the full config in case generate_excel_report needs it in the future
          full_report_bytes = utils.generate_excel_report(reagents_df, below_min_df) # Config not strictly needed by current implementation
          if full_report_bytes:
               report_generated = True
          else:
               st.error("Failed to generate the full report.") # Error likely shown in utils func

     if not report_generated and reagents_df is not None:
          # Don't show this if reagents_df is None (means PDF processing failed earlier)
          st.warning("Could not generate reports. Check previous errors.")
          return
     elif reagents_df is None:
           st.warning("Cannot generate reports as PDF data extraction failed.")
           return


     col1, col2 = st.columns(2)

     with col1:
          # Download to-load list (only if not empty and comparison was successful)
          if below_min_df is not None and not below_min_df.empty:
               # Generate a simple Excel for just the below minimum items
               to_load_excel = BytesIO()
               try:
                   # Prepare df for export (remove internal columns added during processing)
                   cols_to_drop = ['Test_key', '_merge'] # Internal columns used in utils.compare_reagents
                   below_min_to_export = below_min_df.drop(columns=cols_to_drop, errors='ignore')
                   below_min_to_export.to_excel(to_load_excel, index=False, engine='openpyxl')
                   to_load_excel.seek(0)
                   st.download_button(
                       label="Download To-Load List (Excel)",
                       data=to_load_excel,
                       file_name="reagents_to_load.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="download_to_load"
                   )
               except Exception as e:
                    st.error(f"Failed to create To-Load Excel: {e}")
          else:
               st.info("No 'To-Load' list to download (either none below minimum or comparison failed).")


     with col2:
          # Full report download button
          st.download_button(
              label="Download Full Report (Excel)",
              data=full_report_bytes,
              file_name=f"reagent_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              key="download_full_report"
          )

# display_instructions and display_footer likely don't need changes for this request.
def display_instructions():
    """Displays the 'How to Use' expander."""
    with st.expander("How to Use This App", expanded=False):
        st.markdown("""
        ### Instructions

        1.  **Select Format (Sidebar)**: Choose a predefined instrument format (e.g., "Roche E801") or a custom format you've created.
        2.  **Upload Reagent PDF**: Upload the PDF containing the reagent inventory table matching the selected format.
        3.  **Upload Min Volumes Excel**: Upload an Excel file (`.xlsx` or `.xls`) containing minimum volume requirements.
            * This file **must** have columns named exactly `Test` and `MinVolume`. Test names will be matched case-insensitively against the 'Test Name Column' defined in the selected format.
        4.  **Process**: The app will automatically process the files upon successful upload.
        5.  **View Results**: Check the main panel for reagents below the minimum volume.
        6.  **Download Reports**: Use the buttons to download Excel reports.

        ### Managing Custom Formats (Sidebar)

        * **Create/Update**: Use the form to define a new custom format or edit an existing *selected* custom format. Provide a unique name (cannot be the same as a predefined format). List the *exact* column headers from your PDF table, separated by commas. Specify which column names correspond to Quantity, Test Name, Lot ID (optional), and Expiry Date (optional). Click "Save Custom Format".
        * **Load**: Upload a `.json` file (previously exported using the "Export" button) containing one or more custom format definitions. Loaded formats will be added to or update existing custom formats in the current session.
        * **Delete**: Select a custom format from the dropdown list, then click the "Delete Custom Format" button that appears.
        * **Export**: Click the "Download Custom Configurations" link to save all your currently defined *custom* formats to a `.json` file. Predefined formats are not exported.

        ### Troubleshooting

        * **No Tables Found / Extraction Errors**: Ensure the PDF contains detectable tables suitable for `camelot-py`. Check that the selected "Table Format" accurately reflects the structure and column headers of the table in your PDF.
        * **Column Mismatch / KeyError**: Verify the selected format's defined columns (especially Quantity and Test Name) exactly match the headers in your PDF *for that format*. If using a custom format, edit it to ensure accuracy.
        * **Excel Errors**: Ensure the Excel file has columns named `Test` and `MinVolume`. Check that `MinVolume` contains valid numbers.
        * **Comparison Errors / Missing Tests**: This often indicates a mismatch between test names in the PDF's 'Test Name Column' and the `Test` column in the Excel file. Check for differences in spelling, abbreviations, or extra spaces. Matching ignores case. Ensure all required tests exist in the `MinVolume` Excel file.
        """)

def display_footer():
     """Displays the application footer."""
     st.markdown("---")
     current_year = datetime.now().year
     st.markdown(
         f"© {current_year} Reagent Volume Checker | Built with Streamlit"
     )