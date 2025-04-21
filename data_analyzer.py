# data_analyzer.py
import pandas as pd
import streamlit as st

def find_reagents_to_load(current_volumes_dict, min_volumes_df):
    """
    Compares current reagent volumes with minimum required volumes.

    Args:
        current_volumes_dict (dict): Dictionary from PDF: {'reagent_name_lower': current_volume}
        min_volumes_df (pd.DataFrame): DataFrame from Excel with index 'Reagent Name' (lowercased)
                                        and column 'Minimum Volume'.

    Returns:
        pd.DataFrame: A DataFrame containing reagents to load with columns
                      ['Reagent Name', 'Current Volume', 'Minimum Volume'].
                      Returns an empty DataFrame if inputs are invalid or no reagents are needed.
    """
    if not current_volumes_dict or min_volumes_df is None or min_volumes_df.empty:
        st.warning("Cannot perform analysis: Missing current volumes or minimum volume data.")
        return pd.DataFrame(columns=['Reagent Name', 'Current Volume', 'Minimum Volume'])

    reagents_to_load = []
    unmatched_reagents = []

    # Convert min_volumes_df index (Reagent Name) to lower case if not already done
    min_volumes_df.index = min_volumes_df.index.str.lower()

    for reagent_name_lower, current_volume in current_volumes_dict.items():
        try:
            # Look up minimum volume using the lowercased reagent name
            min_volume_row = min_volumes_df.loc[reagent_name_lower]
            minimum_volume = int(min_volume_row['Minimum Volume']) # Ensure it's int

            if current_volume < minimum_volume:
                # Find original capitalization from the index for display purposes
                original_reagent_name = min_volume_row.name # This might still be lowercase if loaded that way
                # Try to find a better capitalized version if possible (might need improvement)
                display_name = next((idx for idx in min_volumes_df.index if idx.lower() == reagent_name_lower), reagent_name_lower)

                reagents_to_load.append({
                    'Reagent Name': display_name.title(), # Capitalize for display
                    'Current Volume': current_volume,
                    'Minimum Volume': minimum_volume
                })
        except KeyError:
            # Reagent found in PDF but not in the minimums list for this analyzer
            unmatched_reagents.append(reagent_name_lower)
        except (TypeError, ValueError) as e:
            st.warning(f"Data type error for reagent '{reagent_name_lower}': {e}. Skipping.")
            continue

    if unmatched_reagents:
        st.info(f"Note: The following reagents were found in the PDF but not in the minimums list "
                f"for the selected analyzer: {', '.join(unmatched_reagents)}")

    if not reagents_to_load:
        return pd.DataFrame(columns=['Reagent Name', 'Current Volume', 'Minimum Volume'])
    else:
        return pd.DataFrame(reagents_to_load)