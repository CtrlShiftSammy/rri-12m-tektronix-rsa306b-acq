#!/usr/bin/env python3
# r3a_to_csv.py - Convert .r3a files to CSV format
# Based on the Streaming IF Sample Data File Format documentation

import struct
import csv
import os
import sys

def read_r3a_to_csv(r3a_filename, output_filename=None, single_row=False):
    """
    Read a .r3a file and convert it to CSV format.
    
    Parameters:
    -----------
    r3a_filename : str
        Path to the .r3a file to convert
    output_filename : str, optional
        Path to the output CSV file. If None, uses the same name as input with .csv extension
    single_row : bool, default=False
        If True, writes all samples in a single row. If False, writes each sample with its index
        
    Returns:
    --------
    bool
        True if conversion was successful, False otherwise
        
    Notes:
    ------
    According to the documentation:
    - .r3a files contain only IF samples (raw data)
    - Samples are 16-bit signed integers in 2 bytes
    - Samples are contiguous with no transport frame information
    """
    
    # Check if file exists
    if not os.path.exists(r3a_filename):
        print(f"Error: File {r3a_filename} not found.")
        return False
    
    # Generate output CSV filename if not provided
    if output_filename is None:
        base_name = os.path.splitext(r3a_filename)[0]
        output_filename = base_name + '.csv'
    
    try:
        # Read the binary .r3a file
        with open(r3a_filename, 'rb') as r3a_file:
            # Read all data from the file
            binary_data = r3a_file.read()
            
            # Calculate number of 16-bit samples
            # Each sample is 2 bytes (16-bit signed integer)
            num_samples = len(binary_data) // 2
            
            print(f"File size: {len(binary_data)} bytes")
            print(f"Number of 16-bit samples: {num_samples}")
            
            # Unpack binary data as 16-bit signed integers
            # '<h' means little-endian signed short (16-bit)
            samples = struct.unpack(f'<{num_samples}h', binary_data)
            
            # Write samples to CSV file
            with open(output_filename, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                
                if single_row:
                    # Write all samples as a single row
                    writer.writerow(samples)
                    print(f"CSV file contains {len(samples)} samples in a single row")
                else:
                    # Write header
                    writer.writerow(['Sample_Index', 'IF_Value'])
                    
                    # Write each sample with its index
                    for i, sample in enumerate(samples):
                        writer.writerow([i, sample])
                    print(f"CSV file contains {len(samples)} samples with indices")
            
            print(f"Successfully converted {r3a_filename} to {output_filename}")
            return True
            
    except struct.error as e:
        print(f"Error unpacking binary data: {str(e)}")
        print("This may indicate the file is not in the expected format.")
        return False
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return False

def print_usage():
    """Print usage information for the script"""
    print("Usage: python r3a_to_csv.py <input_file.r3a> [output_file.csv] [-s/--single-row]")
    print("")
    print("Arguments:")
    print("  input_file.r3a       Path to the .r3a file to convert")
    print("  output_file.csv      Optional: Path to the output CSV file")
    print("                       (default: same name with .csv extension)")
    print("  -s, --single-row     Optional: Write all samples in a single row")
    print("                       (default: write each sample with its index)")
    print("")
    print("Examples:")
    print("  python r3a_to_csv.py input.r3a")
    print("  python r3a_to_csv.py input.r3a output.csv")
    print("  python r3a_to_csv.py input.r3a -s")
    print("  python r3a_to_csv.py input.r3a output.csv --single-row")

def main():
    """Command line interface for the r3a to CSV converter"""
    
    # Check arguments
    if len(sys.argv) < 2:
        print_usage()
        return
    
    # Get input filename (required)
    input_file = sys.argv[1]
    
    # Check if help was requested
    if input_file in ['-h', '--help']:
        print_usage()
        return
    
    # Check if file has .r3a extension
    if not input_file.lower().endswith('.r3a'):
        print("Warning: Input file does not have .r3a extension")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Conversion cancelled.")
            return
    
    # Parse remaining arguments
    output_file = None
    single_row = False
    
    for arg in sys.argv[2:]:
        if arg in ['-s', '--single-row']:
            single_row = True
        elif not arg.startswith('-'):
            output_file = arg
    
    # Convert file
    success = read_r3a_to_csv(input_file, output_file, single_row)
    
    if success:
        print("Conversion completed successfully.")
    else:
        print("Conversion failed.")

if __name__ == "__main__":
    # If run as a script, use the command line interface
    main()
