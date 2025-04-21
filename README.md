# reagent_volume_checker# Reagent Volume Checker Streamlit App

This application helps laboratory staff quickly identify reagents that need to be loaded onto an analyzer based on current levels (from a PDF printout) and predefined minimum requirements (from an Excel file).

## Features

* Upload analyzer reagent status via PDF (uses OCR - requires Tesseract).
* Upload minimum reagent volume requirements via Excel (.xlsx).
* Select the specific analyzer (based on Excel sheet names).
* Compares current volumes to minimums.
* Displays a clear list of reagents to load.
* Basic caching for improved performance on repeated file uploads.
* Modular code structure.

## Prerequisites

1.  **Python:** Version 3.7+ recommended.
2.  **Tesseract OCR Engine:** This is **essential** for reading the PDF files.
    * **Installation:**
        * Windows: Download from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) or other sources. **Ensure you add Tesseract to your system PATH** during installation or note the install location.
        * macOS: `brew install tesseract`
        * Linux (Debian/Ubuntu): `sudo apt update && sudo apt install tesseract-ocr`
        * Linux (Fedora): `sudo dnf install tesseract`
    * **Configuration:** If Tesseract is not automatically found, you **must** edit the `utils.py` file and set the `tesseract_cmd_path` variable to the full path of your `tesseract.exe` (Windows) or `tesseract` (macOS/Linux) executable.
3.  **Poppler (PDF Rendering Library):** Needed by the `pdf2image` library.
    * **Installation:**
        * Windows: Download [Poppler binaries](https://github.com/oschwartz10612/poppler-windows/releases/), extract them, and add the `bin\` directory inside the extracted folder to your system PATH.
        * macOS: `brew install poppler`
        * Linux (Debian/Ubuntu): `sudo apt update && sudo apt install poppler-utils`
        * Linux (Fedora): `sudo dnf install poppler-utils`

## Setup

1.  **Clone or Download:** Get the project files.
2.  **Navigate:** Open a terminal or command prompt and navigate to the `reagent_checker` directory.
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **(Optional but Recommended):** Verify Tesseract installation by running `tesseract --version` in your terminal. If this command fails, Tesseract is not installed correctly or not in your PATH. Configure `utils.py` if needed.

## File Formats

* **Excel File (.xlsx):**
    * Each sheet should correspond to one analyzer. The sheet name will be used as the analyzer name in the app's dropdown.
    * Each sheet **must** contain at least two columns:
        * `Reagent Name`: The exact name of the reagent (case-insensitive matching is used, but consistent naming is best).
        * `Minimum Volume`: The minimum acceptable volume or number of tests/units. This **must** be a numeric value.
    * Other columns are ignored.
* **PDF File (.pdf):**
    * This should be the printout or exported file from your analyzer showing the current status of reagents.
    * The app uses OCR (Optical Character Recognition) to read this file. **Accuracy depends heavily on the PDF quality and layout.**
    * **Crucially, you will likely need to customize the `parse_ocr_text` function within `pdf_processor.py`** to correctly extract reagent names and their current volumes based on how they appear in *your specific* PDF files. The provided example parsing logic is generic and might need significant adjustment (e.g., using different regular expressions).

## How to Run

1.  Make sure you are in the `reagent_checker` directory in your terminal.
2.  Run the Streamlit app:
    ```bash
    streamlit run main_app.py
    ```
3.  The application should open in your web browser automatically.
4.  Follow the instructions in the sidebar:
    * Upload the Excel file with minimum volumes.
    * Upload the PDF reagent status file.
    * Select the correct analyzer from the dropdown (populated from Excel sheet names).
    * Click the "Check Reagent Levels" button.
5.  The results (reagents to load) will be displayed in the main area.

## Customization

* **PDF Parsing:** The most likely area needing customization is the `parse_ocr_text` function in `pdf_processor.py`. Examine the raw text output (you can uncomment the debug section in `pdf_processor.py` or `main_app.py`) and adjust the regular expressions or string manipulation logic to match your PDF's layout.
* **Tesseract Path:** Set the correct path in `utils.py` if needed.
* **Styling:** Modify the CSS in `main_app.py` for different visual themes.
* **Excel Columns:** If your Excel file uses different column names for reagent name or minimum volume, update the `excel_processor.py` module accordingly.