# utils.py
import platform
import os

def configure_tesseract():
    """Configures the path to the Tesseract executable if needed."""
    # --- IMPORTANT: Configure Tesseract Path ---
    # If Tesseract is not in your system's PATH, uncomment and set the path below.
    # Example Windows:
    # tesseract_cmd_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    # Example macOS/Linux (if not found automatically):
    # tesseract_cmd_path = '/usr/local/bin/tesseract' # Or /usr/bin/tesseract

    # --- Automatic Detection (Try this first) ---
    try:
        import pytesseract
        # If path is already set, don't override unless necessary
        # You might need to uncomment the line below if auto-detection fails
        # and you've set tesseract_cmd_path above.
        # pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path
        print("Tesseract path potentially configured.")
        # You can add a check here to see if tesseract runs
        # os.system(f"{pytesseract.pytesseract.tesseract_cmd} --version")
    except ImportError:
        print("Pytesseract library not found.")
    except Exception as e:
        print(f"Error configuring Tesseract: {e}")
        print("Ensure Tesseract OCR Engine is installed and accessible.")
        print("You might need to manually set the path in utils.py.")

# Call configuration function when the module is imported
configure_tesseract()

def clean_text(text):
    """Basic text cleaning."""
    # Remove extra whitespace, handle potential OCR noise
    text = ' '.join(text.split())
    # Add more specific cleaning rules based on observed OCR output if needed
    return text

def extract_number(text):
    """Extracts the first sequence of digits from a string."""
    import re
    match = re.search(r'\d+', text)
    return int(match.group(0)) if match else None