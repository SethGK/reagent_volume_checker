# ui_components.py

import streamlit as st
import json
import base64
from datetime import datetime
from config_manager import validate_config_format, get_config_download_link

def display_sidebar(current_config_options):
    """Displays the sidebar UI elements and handles configuration logic."""
    st.sidebar.title("Configuration")
    st.sidebar.write("Upload a table format configuration or manage formats below.")

    config_file = st.sidebar.file_uploader("Upload Configuration File (JSON)", type=["json"], key="config_upload")

    # Note: Loading logic might be better handled in app.py on initial load or file upload action
    # This function focuses on displaying the UI elements for config management

    format_options = list(current_config_options.keys())
    selected_format = st.sidebar.selectbox(
        "Select Table Format",
        format_options,
        index=0, # Default to the first option
        key="format_select"
    )

    # --- Create New Configuration Section ---
    st.sidebar.divider()
    st.sidebar.subheader("Create or Update Configuration")
    with st.sidebar.form("new_config_form"):
         new_config_name = st.text_input("Configuration Name", key="new_name")
         new_config_columns = st.text_input("Column Names (comma-separated)", key="new_cols")
         new_config_qty = st.text_input("Quantity Column Name", key="new_qty")
         new_config_test = st.text_input("Test Name Column", key="new_test")
         new_config_lot = st.text_input("Lot ID Column (Optional)", key="new_lot")
         new_config_exp = st.text_input("Expiry Date Column (Optional)", key="new_exp")
         submitted = st.form_submit_button("Save Configuration")

         if submitted:
              if not all([new_config_name, new_config_columns, new_config_qty, new_config_test]):
                  st.warning("Please fill in all required fields (Name, Columns, Quantity Col, Test Col).")
                  st.stop() # Stop execution within the form context if invalid

              new_format = {
                  "columns": [col.strip() for col in new_config_columns.split(",")],
                  "quantity_column": new_config_qty.strip(),
                  "test_name_column": new_config_test.strip(),
                  # Only include optional columns if they are provided
                  **({"lot_column": new_config_lot.strip()} if new_config_lot.strip() else {}),
                  **({"expiry_column": new_config_exp.strip()} if new_config_exp.strip() else {}),
              }

              if validate_config_format(new_format):
                   # This should return the updated config to app.py to manage state
                   st.session_state['new_config_to_add'] = {new_config_name.strip(): new_format}
                   st.success(f"Configuration '{new_config_name.strip()}' ready to be saved/updated.")
                   # Clear form by rerunning? Or manage state more explicitly.
                   # A rerun is often the Streamlit way after state change.
              else:
                   st.error("Invalid configuration format. Please check the fields.")


    # --- Export Configurations ---
    st.sidebar.divider()
    st.sidebar.subheader("Export Configurations")
    if st.sidebar.button("Generate Download Link"):
         download_link = get_config_download_link(current_config_options)
         if download_link:
              st.sidebar.markdown(download_link, unsafe_allow_html=True)

    return selected_format # Return selected format for use in main app


def display_results(reagents_df, result_df, config):
    """Displays the comparison results and dataframes."""
    st.subheader("Results")

    if result_df is None:
         st.error("Comparison could not be completed.")
         return # Exit if comparison failed

    if result_df.empty:
        st.success("✅ All reagents are above the minimum volume according to the provided files and configuration.")
    else:
        st.warning(f"⚠️ {len(result_df)} reagents are below the required volume:")
        # Ensure columns from config are present before displaying
        display_cols = [config['test_name_column'], config['quantity_column'], 'MinVolume']
        if config.get('lot_column') and config['lot_column'] in result_df.columns:
            display_cols.append(config['lot_column'])
        if config.get('expiry_column') and config['expiry_column'] in result_df.columns:
             display_cols.append(config['expiry_column'])
        valid_display_cols = [col for col in display_cols if col in result_df.columns]
        st.dataframe(result_df[valid_display_cols])

    # Display all reagent data
    if reagents_df is not None:
         with st.expander("Show All Extracted Reagent Data (from PDF)"):
              display_cols_all = config['columns'] # Show columns as defined in config
              valid_display_cols_all = [col for col in display_cols_all if col in reagents_df.columns]
              st.dataframe(reagents_df[valid_display_cols_all])


def display_download_buttons(reagents_df, below_min_df):
     """Displays download buttons for reports."""
     st.subheader("Download Reports")

     report_generated = False
     full_report_bytes = None
     if reagents_df is not None:
          full_report_bytes = utils.generate_excel_report(reagents_df, below_min_df)
          if full_report_bytes:
               report_generated = True
          else:
               st.error("Failed to generate the full report.")

     if not report_generated:
          st.warning("Cannot generate reports as initial data processing failed.")
          return

     col1, col2 = st.columns(2)

     with col1:
          # Download to-load list (only if not empty and comparison was successful)
          if below_min_df is not None and not below_min_df.empty:
               # Generate a simple Excel for just the below minimum items
               to_load_excel = BytesIO()
               try:
                   # Prepare df for export (remove internal columns)
                   below_min_to_export = below_min_df.drop(columns=['Test_key', '_merge'], errors='ignore')
                   below_min_to_export.to_excel(to_load_excel, index=False, engine='openpyxl')
                   to_load_excel.seek(0)
                   st.download_button(
                       label="Download To-Load List (Excel)",
                       data=to_load_excel,
                       file_name="reagents_to_load.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                   )
               except Exception as e:
                    st.error(f"Failed to create To-Load Excel: {e}")
          else:
               st.info("No 'To-Load' list needed or comparison failed.")


     with col2:
          # Full report download button
          st.download_button(
              label="Download Full Report (Excel)",
              data=full_report_bytes,
              file_name=f"reagent_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          )


def display_instructions():
    """Displays the 'How to Use' expander."""
    with st.expander("How to Use This App", expanded=False):
        st.markdown("""
        ### Instructions

        1.  **Configure Format (Sidebar)**: Select the table format matching your PDF, or create/upload a new configuration. Ensure column names match exactly.
        2.  **Upload Reagent PDF**: Upload the PDF containing the reagent inventory table.
        3.  **Upload Min Volumes Excel**: Upload an Excel file (`.xlsx` or `.xls`) containing minimum volume requirements.
            * This file **must** have columns named exactly `Test` and `MinVolume`. Test names will be matched case-insensitively.
        4.  **Process**: The app will automatically process the files upon successful upload.
        5.  **View Results**: Check the main panel for reagents below the minimum volume.
        6.  **Download Reports**: Use the buttons to download Excel reports.

        ### Creating/Updating Table Formats

        * Use the form in the sidebar.
        * Provide a unique name for the format.
        * List the *exact* column headers from your PDF table, separated by commas.
        * Specify which of those column names correspond to the Quantity, Test Name, Lot ID (optional), and Expiry Date (optional).
        * Click "Save Configuration". The new/updated format will be available in the dropdown.
        * Configurations are stored temporarily for the current session. Use Export/Import to save/load them permanently.

        ### Troubleshooting

        * **No Tables Found**: Ensure the PDF contains detectable tables. `camelot-py` works best with clear, non-scanned tables. Try the `flavor='lattice'` option in `utils.py` if tables have clear lines.
        * **Column Mismatch**: Double-check the selected "Table Format" in the sidebar matches the actual columns in your PDF. Verify the column names in the configuration (especially Quantity and Test Name) are correct.
        * **Excel Errors**: Ensure the Excel file has sheets named `Test` and `MinVolume`. Check that `MinVolume` contains only numbers.
        * **Comparison Errors**: This usually indicates a mismatch between test names in the PDF and Excel, or incorrect column specification in the configuration. Remember test name matching ignores case but requires the text to be otherwise identical after stripping whitespace.
        """)

def display_footer():
     """Displays the application footer."""
     st.markdown("---")
     # Update year dynamically if desired
     current_year = datetime.now().year
     st.markdown(
         f"© {current_year} Reagent Volume Checker | Built with Streamlit"
         # Add contact info if needed
     )