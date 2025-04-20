# config_manager.py

import json
import streamlit as st
import base64

DEFAULT_CONFIG = {
    "default": {
        "columns": ["Test", "Reason", "Available Tests", "Type", "Pos.", "Remaining", "Lot ID", "Exp. Date"],
        "quantity_column": "Remaining",
        "test_name_column": "Test",
        "lot_column": "Lot ID",
        "expiry_column": "Exp. Date"
    }
    # Add other predefined formats here if needed
}

def load_config_from_file(uploaded_file):
    """Loads configuration from an uploaded JSON file."""
    if uploaded_file is None:
        return None
    try:
        config_data = json.load(uploaded_file)
        # Optional: Add validation here to ensure loaded config has the correct structure
        st.success("Custom configuration loaded successfully!")
        return config_data
    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid configuration file.")
        return None
    except Exception as e:
        st.error(f"Error loading configuration file: {e}")
        return None

def validate_config_format(new_format):
     """Basic validation for a new configuration format dictionary."""
     required_keys = ["columns", "quantity_column", "test_name_column"]
     if not all(key in new_format for key in required_keys):
         st.error("New configuration is missing required keys: 'columns', 'quantity_column', 'test_name_column'.")
         return False
     if not isinstance(new_format["columns"], list):
         st.error("'columns' must be a list of strings.")
         return False
     if not all(isinstance(col, str) for col in new_format["columns"]):
          st.error("All items in 'columns' must be strings.")
          return False
     if not isinstance(new_format["quantity_column"], str) or not new_format["quantity_column"]:
         st.error("'quantity_column' must be a non-empty string.")
         return False
     if not isinstance(new_format["test_name_column"], str) or not new_format["test_name_column"]:
          st.error("'test_name_column' must be a non-empty string.")
          return False
     # Optional checks for lot/expiry columns if provided
     if new_format.get("lot_column") is not None and not isinstance(new_format.get("lot_column"), str):
          st.error("'lot_column', if provided, must be a string.")
          return False
     if new_format.get("expiry_column") is not None and not isinstance(new_format.get("expiry_column"), str):
            st.error("'expiry_column', if provided, must be a string.")
            return False
     return True


def get_config_download_link(config_data):
    """Generates a download link for the current configurations."""
    try:
        config_str = json.dumps(config_data, indent=2)
        b64 = base64.b64encode(config_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="table_configurations.json">Download Current Configurations</a>'
        return href
    except Exception as e:
        st.error(f"Failed to generate config download link: {e}")
        return ""