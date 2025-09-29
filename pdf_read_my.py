import pdfplumber
import re
import pandas as pd

def extract_dimensions(pdf_path):

    dimensions =[]
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()

            lines = text.split('\n')

            for line_num, line in enumerate(lines):
                dimension_pattern = r'(\d+)*\s*(\d+)\s*x\s*(\d+)'
                dimension_match = re.search(dimension_pattern,line)

                if dimension_match:
                    quantity = int(dimension_match.group(1))
                    width = int(dimension_match.group(2))
                    height = int(dimension_match.group(3))

                    item_info = {
                        'width_mm': width,
                        'height_mm': height,
                        'quantity': quantity,
                        'measurement': f"{width} x {height}",
                        'area_m2': round((width * height) / 1_000_000, 4),
                        'full_line': line.strip()
                    }
                
                    position_match = re.match(r'^\d{3}\s+(.+?)\s+\d+\s+\d+\s*x', line)
                    
                    if position_match:
                            item_info['position'] = position_match.group(1).strip()
                    dimensions.append(item_info)
    return dimensions


if __name__ == "__main__":
    pdf_file_path ="faktura_sklo.pdf"
    
    try: 
        dimensions = extract_dimensions(pdf_file_path)
        print(dimensions)
    except FileNotFoundError:
        print("Soubor '{pdf_file_path}' nenalezen")