
import sys
import os
import glob
from pathlib import Path

# Add the src directory to the Python path for sibling-module imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from vtt2md.converter import convert_vtt_to_md

def run_real_data_test():
    """Runs the conversion on actual sample files and prints the output for review."""
    sample_files = glob.glob("samples/input/*.vtt")
    if not sample_files:
        print("No sample VTT files found in samples/input/")
        return

    print(f"Found {len(sample_files)} sample files to test.\n")

    for file_path in sample_files:
        print(f"======================================================================")
        print(f">>> TESTING FILE: {file_path}")
        print(f"======================================================================\n")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                vtt_content = f.read()

            # --- Run conversion WITHOUT filler removal ---
            print("--- 1. Original Markdown (Filler Removal OFF) ---")
            md_original = convert_vtt_to_md(vtt_content, file_path, remove_fillers=False)
            print(md_original)
            print("\n" + "-"*50 + "\n")

            # --- Run conversion WITH filler removal ---
            print("--- 2. Cleaned Markdown (Filler Removal ON) ---")
            md_cleaned = convert_vtt_to_md(vtt_content, file_path, remove_fillers=True)
            print(md_cleaned)
            print("\n\n")

        except Exception as e:
            print(f"An error occurred while processing {file_path}: {e}")

if __name__ == "__main__":
    run_real_data_test()
