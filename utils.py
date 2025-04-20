# utils.py

import streamlit as st
import pandas as pd
import camelot
import os
import tempfile
from io import BytesIO
from datetime import datetime
import openpyxl # Explicitly import engine dependency

def extract_reagents_from_pdf(uploaded_pdf, table_format):
    """Extract reagent data from PDF using specified format"""
    # Use BytesIO directly with camelot if possible, avoids temp files
    try:
        pdf_data = uploaded_pdf.read()
        # Check if camelot can read directly from bytes
        tables = camelot.read_pdf(BytesIO(pdf_data), pages='all', flavor='stream')
        # If not, fall back to temp file (original method)
        # with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        #     tmp_file.write(pdf_data)
        #     tmp_path = tmp_file.name
        # try:
        #     tables = camelot.read_pdf(tmp_path, pages='all', flavor='stream')
        # finally:
        #     os.unlink(tmp_path) # Ensure cleanup even on error

        if len(tables) == 0:
            st.error("No tables found in the PDF. Try a different PDF or table extraction method.")
            return None

        df = tables[0].df # Assuming the first table is always the target

        config = table_format
        # Basic validation before assigning columns
        if len(df.columns) != len(config["columns"]):
            st.warning(
                f"Table column count ({len(df.columns)}) doesn't match configuration "
                f"({len(config['columns'])}). Using default column indices. Please check the selected format."
            )
            # Optional: Add logic to try and find columns by name if headers exist in PDF?
            return None # Or handle differently

        df.columns = config["columns"]

        # Validate required columns exist before processing
        required_cols = [config["quantity_column"], config["test_name_column"]]
        if not all(col in df.columns for col in required_cols):
             st.error(f"One or more required columns ({', '.join(required_cols)}) not found based on configuration.")
             return None

        # Convert quantity column to numeric, handle potential errors gracefully
        try:
            df[config["quantity_column"]] = pd.to_numeric(df[config["quantity_column"]], errors='coerce')
            # Optional: Check for NaNs introduced by coercion and warn user
            if df[config["quantity_column"]].isnull().any():
                st.warning("Some quantity values could not be converted to numbers and were ignored.")
        except KeyError:
            # This check is now less likely due to the validation above, but good practice
            st.error(f"Configuration error: Quantity column '{config['quantity_column']}' not found.")
            return None
        except Exception as e:
             st.error(f"Error converting quantity column to numbers: {e}")
             return None

        return df

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        # If using temp file, ensure cleanup here too
        # if 'tmp_path' in locals() and os.path.exists(tmp_path):
        #      os.unlink(tmp_path)
        return None


def load_min_volumes(uploaded_excel, test_column="Test", min_vol_column="MinVolume"):
    """Load minimum volume data from Excel"""
    try:
        df = pd.read_excel(uploaded_excel)
        # Validate required columns exist
        if test_column not in df.columns or min_vol_column not in df.columns:
             st.error(f"Excel file must contain columns named '{test_column}' and '{min_vol_column}'.")
             return None

        # Make test names lowercase for case-insensitive matching
        df[test_column] = df[test_column].astype(str).str.strip().str.lower()
        # Ensure MinVolume is numeric
        df[min_vol_column] = pd.to_numeric(df[min_vol_column], errors='coerce')
        if df[min_vol_column].isnull().any():
             st.warning("Some minimum volume values were not numeric and were ignored.")
             df = df.dropna(subset=[min_vol_column]) # Remove rows with invalid min volumes

        # Rename columns for consistency internally
        df = df.rename(columns={test_column: "Test_key", min_vol_column: "MinVolume"})
        return df[[ "Test_key", "MinVolume"]] # Return only necessary columns

    except Exception as e:
        st.error(f"Error loading or processing Excel file: {e}")
        return None


def compare_reagents(reagents_df, mins_df, config):
    """Compare reagent levels with minimum volumes"""
    if reagents_df is None or mins_df is None:
        return pd.DataFrame() # Return empty dataframe if inputs are invalid

    try:
        test_col = config["test_name_column"]
        qty_col = config["quantity_column"]
        lot_col = config.get("lot_column") # Use .get for optional columns
        exp_col = config.get("expiry_column")

        # Ensure quantity column is numeric (might be redundant if checked earlier, but safe)
        if not pd.api.types.is_numeric_dtype(reagents_df[qty_col]):
             st.error(f"Quantity column '{qty_col}' is not numeric. Cannot perform comparison.")
             return pd.DataFrame()

        # Create lowercase key for matching (ensure it's string first)
        reagents_df["Test_key"] = reagents_df[test_col].astype(str).str.strip().str.lower()

        # Merge dataframes using the standardized 'Test_key'
        # Use indicator=True to debug merge issues
        merged = reagents_df.merge(mins_df, on="Test_key", how="left", indicator=True)

        # Optional: Check for reagents not found in the minimums file
        not_in_mins = merged[merged['_merge'] == 'left_only']
        if not not_in_mins.empty:
            st.warning(f"The following {len(not_in_mins)} tests from the PDF were not found in the Minimum Volumes file: "
                       f"{', '.join(not_in_mins[test_col].unique())}")

        # Filter out rows where merge failed or MinVolume is NaN
        merged = merged[merged['_merge'] == 'both'].dropna(subset=["MinVolume"])

        if "MinVolume" not in merged.columns:
             st.error("Could not find 'MinVolume' column after merging. Check Excel file and configuration.")
             return pd.DataFrame()

        # Find items below minimum volume (handle potential NaN in qty_col just in case)
        merged[qty_col] = pd.to_numeric(merged[qty_col], errors='coerce')
        to_load = merged[merged[qty_col] < merged["MinVolume"]].copy() # Use .copy() to avoid SettingWithCopyWarning

        # Select and order columns for the result display
        result_columns = [test_col, qty_col, "MinVolume"]
        if lot_col and lot_col in reagents_df.columns:
            result_columns.append(lot_col)
        if exp_col and exp_col in reagents_df.columns:
            result_columns.append(exp_col)

        # Filter result dataframe to only include desired columns and handle missing ones
        final_columns = [col for col in result_columns if col in to_load.columns]
        return to_load[final_columns]

    except KeyError as e:
         st.error(f"Configuration Mismatch: Column '{e}' not found during comparison. Check PDF structure and selected format.")
         return pd.DataFrame()
    except Exception as e:
        st.error(f"Error comparing reagent data: {e}")
        return pd.DataFrame()


def generate_excel_report(df, below_min_df=None):
    """Generate a detailed Excel report in memory"""
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Main data sheet - remove internal keys if they exist
            df_to_write = df.drop(columns=['Test_key'], errors='ignore')
            df_to_write.to_excel(writer, sheet_name="All Reagents", index=False)

            # Items below minimum volume
            if below_min_df is not None and not below_min_df.empty:
                below_min_to_write = below_min_df.drop(columns=['Test_key', '_merge'], errors='ignore')
                below_min_to_write.to_excel(writer, sheet_name="Below Minimum", index=False)

            # Summary sheet
            summary_data = {
                "Metric": ["Total Reagents Found", "Reagents Below Minimum", "Report Date"],
                "Value": [
                    len(df),
                    0 if below_min_df is None else len(below_min_df),
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

    except Exception as e:
        st.error(f"Failed to generate Excel report: {e}")
        return None # Indicate failure

    output.seek(0)
    return output