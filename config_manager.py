# config_manager.py

import json
import streamlit as st
import base64

# Define predefined configurations
PREDEFINED_CONFIGS = {
    "Roche E801": {
        "columns": ["Test", "Reason", "Available Tests", "Type", "Pos.", "Remaining", "Lot ID", "Exp. Date"],
        "quantity_column": "Remaining",
        "test_name_column": "Test",
        "lot_column": "Lot ID",
        "expiry_column": "Exp. Date",
        "is_predefined": True # Add a flag to identify predefined configs
    },
    "Beckman AU5800": {
        # NOTE: These are EXAMPLE columns for Beckman AU. Adjust as needed.
        "columns": ["Test Name", "Reagent", "Tests Remaining", "Status", "Lot Number", "Expiration", "Calib Status"],
        "quantity_column": "Tests Remaining",
        "test_name_column": "Test Name", # Or maybe "Reagent"? Depends on the report.
        "lot_column": "Lot Number",
        "expiry_column": "Expiration",
        "is_predefined": True
    }
    # Add other predefined instruments here if needed
}

# Functions now primarily operate on or return *custom* configurations

def load_custom_config_from_file(uploaded_file):
    """Loads CUSTOM configurations from an uploaded JSON file."""
    if uploaded_file is None:
        return None
    try:
        custom_config_data = json.load(uploaded_file)
        # Basic Validation: Check if it's a dictionary
        if not isinstance(custom_config_data, dict):
            st.error("Invalid format. Configuration file should contain a JSON object (dictionary).")
            return None
        # Optional: Add deeper validation for each config entry within the dict
        st.success("Custom configuration file loaded successfully!")
        return custom_config_data
    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid configuration file.")
        return None
    except Exception as e:
        st.error(f"Error loading configuration file: {e}")
        return None

def validate_config_format(new_format_dict):
     """Validates the structure of a single configuration format dictionary."""
     required_keys = ["columns", "quantity_column", "test_name_column"]
     if not all(key in new_format_dict for key in required_keys):
         st.error("Configuration is missing required keys: 'columns', 'quantity_column', 'test_name_column'.")
         return False
     if not isinstance(new_format_dict["columns"], list) or not all(isinstance(col, str) for col in new_format_dict["columns"]):
         st.error("'columns' must be a list of strings.")
         return False
     if not isinstance(new_format_dict["quantity_column"], str) or not new_format_dict["quantity_column"]:
         st.error("'quantity_column' must be a non-empty string.")
         return False
     if not isinstance(new_format_dict["test_name_column"], str) or not new_format_dict["test_name_column"]:
          st.error("'test_name_column' must be a non-empty string.")
          return False
     # Optional checks for lot/expiry columns if provided
     lot_col = new_format_dict.get("lot_column")
     exp_col = new_format_dict.get("expiry_column")
     if lot_col is not None and (not isinstance(lot_col, str) or not lot_col):
          st.error("'lot_column', if provided, must be a non-empty string.")
          return False
     if exp_col is not None and (not isinstance(exp_col, str) or not exp_col):
            st.error("'expiry_column', if provided, must be a non-empty string.")
            return False
     return True


def get_custom_config_download_link(custom_config_data):
    """Generates a download link for the current CUSTOM configurations."""
    if not custom_config_data:
        st.info("No custom configurations available to export.")
        return ""
    try:
        config_str = json.dumps(custom_config_data, indent=2)
        b64 = base64.b64encode(config_str.encode()).decode()
        # Consider timestamp in filename?
        href = f'<a href="data:application/json;base64,{b64}" download="custom_table_configurations.json">Download Custom Configurations</a>'
        return href
    except Exception as e:
        st.error(f"Failed to generate custom config download link: {e}")
        return ""