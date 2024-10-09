import zipfile
import argparse
import os

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="Unzip a zip file.")
parser.add_argument("zip_file", help="Path to the zip file to unzip")
parser.add_argument("extract_to", nargs='?', default='.', help="Directory to extract the contents to (default: current directory)")
args = parser.parse_args()

# Check if the zip file exists
if not os.path.isfile(args.zip_file):
  print(f"Error: {args.zip_file} does not exist.")
  exit(1)

# Open the zip file and extract its contents
with zipfile.ZipFile(args.zip_file, 'r') as zip_ref:
  zip_ref.extractall(args.extract_to)

print(f"Extracted all files to {args.extract_to}")
