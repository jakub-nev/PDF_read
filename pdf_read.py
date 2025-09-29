import pdfplumber
import re
import pandas as pd

def extract_measurements_from_invoice(pdf_path):
    """
    Extract measurements from the glass invoice PDF
    Returns a list of dictionaries with measurement data
    """
    results = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            # Split text into lines for processing
            lines = text.split('\n')
            
            for line_num, line in enumerate(lines):
                # Look for measurement pattern (number x number)
                measurement_pattern = r'(\d+)(\d+)\s*x\s*(\d+)'
                measurement_match = re.search(measurement_pattern, line)
                
                if measurement_match:
                    width = int(measurement_match.group(1))
                    height = int(measurement_match.group(2))
                    
                    # Extract additional context from the line
                    item_info = {
                        'page': page_num,
                        'line_number': line_num + 1,
                        'width_mm': width,
                        'height_mm': height,
                        'measurement': f"{width} x {height}",
                        'area_mm2': width * height,
                        'area_m2': round((width * height) / 1_000_000, 4),
                        'full_line': line.strip()
                    }
                    
                    # Try to extract item position/number (usually 3 digits at start)
                    pos_match = re.match(r'^(\d{3})', line)
                    if pos_match:
                        item_info['position'] = pos_match.group(1)
                    
                    # Try to extract quantity (number before the measurement)
                    qty_pattern = r'(\d+)\s+' + re.escape(f"{width} x {height}")
                    qty_match = re.search(qty_pattern, line)
                    if qty_match:
                        item_info['quantity'] = int(qty_match.group(1))
                    
                    # Extract frame type (like "16mm SWS Černý")
                    frame_match = re.search(r'(\d+mm\s+\w+\s+\w+)', line)
                    if frame_match:
                        item_info['frame_type'] = frame_match.group(1)
                    
                    # Extract prices (last two decimal numbers in the line)
                    price_pattern = r'(\d+\.?\d*)'
                    price_matches = re.findall(price_pattern, line)
                    if len(price_matches) >= 2:
                        try:
                            # Usually unit price and total price are the last two numbers
                            item_info['unit_price_czk'] = float(price_matches[-2])
                            item_info['total_price_czk'] = float(price_matches[-1])
                        except ValueError:
                            pass
                    
                    results.append(item_info)
    
    return results

def print_measurements_summary(measurements):
    """Print a nice summary of extracted measurements"""
    print(f"=== EXTRACTED MEASUREMENTS SUMMARY ===")
    print(f"Total items found: {len(measurements)}")
    print()
    
    for i, item in enumerate(measurements, 1):
        print(f"{i:2d}. {item['measurement']} mm")
        if 'position' in item:
            print(f"    Position: {item['position']}")
        if 'quantity' in item:
            print(f"    Quantity: {item['quantity']}")
        if 'frame_type' in item:
            print(f"    Frame: {item['frame_type']}")
        print(f"    Area: {item['area_m2']} m²")
        if 'total_price_czk' in item:
            print(f"    Price: {item['total_price_czk']} CZK")
        print()

def save_measurements_to_excel(measurements, filename='measurements.xlsx'):
    """Save measurements to Excel file"""
    df = pd.DataFrame(measurements)
    
    # Reorder columns for better readability
    column_order = ['position', 'measurement', 'width_mm', 'height_mm', 
                   'quantity', 'area_m2', 'frame_type', 'unit_price_czk', 
                   'total_price_czk', 'page', 'full_line']
    
    # Only include columns that exist
    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]
    
    df.to_excel(filename, index=False)
    print(f"Data saved to {filename}")
    return df

# Main execution
if __name__ == "__main__":
    # Replace with your PDF file path
    pdf_file = "faktura_sklo.pdf"  # Your invoice file
    
    try:
        # Extract measurements
        measurements = extract_measurements_from_invoice(pdf_file)
        
        # Print summary
        print_measurements_summary(measurements)
        
        # Calculate totals
        total_area = sum(item['area_m2'] for item in measurements)
        total_price = sum(item.get('total_price_czk', 0) for item in measurements)
        
        print("=== TOTALS ===")
        print(f"Total area: {total_area:.2f} m²")
        print(f"Total price: {total_price:.2f} CZK")
        
        # Save to Excel
        df = save_measurements_to_excel(measurements)
        
        # Show unique measurements
        unique_measurements = list(set(item['measurement'] for item in measurements))
        print(f"\nUnique measurements found: {len(unique_measurements)}")
        for measurement in sorted(unique_measurements):
            print(f"  {measurement}")
            
    except FileNotFoundError:
        print(f"Error: Could not find file '{pdf_file}'")
        print("Please make sure the PDF file is in the same directory as this script")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")

# Simple function to just get the measurements quickly
def get_measurements_only(pdf_path):
    """Returns just a simple list of measurements"""
    measurements = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # Find all measurement patterns
            matches = re.findall(r'(\d+)\s*x\s*(\d+)', text, re.IGNORECASE)
            measurements.extend([f"{w} x {h}" for w, h in matches])
    
    # Remove duplicates and return sorted list
    return sorted(list(set(measurements)))

# Quick usage example:
# measurements = get_measurements_only("your_file.pdf")
# print("Measurements found:", measurements)