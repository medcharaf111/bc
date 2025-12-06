"""
Career Plans PDF Parser
Extracts workforce data from "أصحاب الخطط الوظيفية.pdf"
"""
import pdfplumber
import os
from django.conf import settings
import re
import sys
import io


def parse_career_plans_pdf():
    """
    Parse the Career Plans PDF and extract job positions and titles
    Returns dict with positions, job titles, and descriptions
    """
    # Path to the PDF file
    pdf_path = os.path.join(settings.BASE_DIR, 'Resource', 'أصحاب الخطط الوظيفية.pdf')
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found at: {pdf_path}")
        return None
    
    data = {
        'positions': [],
        'categories': {
            'primary_education': [],
            'secondary_education': [],
            'technical_education': [],
            'administration': [],
            'inspection': [],
            'support_services': []
        },
        'summary': {
            'total_positions': 0,
            'by_sector': {}
        },
        'metadata': {
            'source_file': 'أصحاب الخطط الوظيفية.pdf',
            'pages_processed': 0,
            'extraction_date': None
        }
    }
    
    try:
        from datetime import datetime
        data['metadata']['extraction_date'] = datetime.now().isoformat()
        
        with pdfplumber.open(pdf_path) as pdf:
            data['metadata']['pages_processed'] = len(pdf.pages)
            
            # Extract text and tables from all pages
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Process each row (skip header)
                    for row in table[1:]:
                        if len(row) < 1 or not row[0]:
                            continue
                        
                        # Parse the combined first column that contains all info
                        cell_content = str(row[0])
                        
                        # Extract Arabic title (first line usually)
                        lines = [line.strip() for line in cell_content.split('\n') if line.strip()]
                        
                        if len(lines) >= 3:
                            position = {
                                'arabic_title': lines[0] if len(lines) > 0 else '',
                                'french_title': lines[1] if len(lines) > 1 else '',
                                'english_title': lines[2] if len(lines) > 2 else '',
                                'sector': lines[3] if len(lines) > 3 else '',
                                'type': lines[4] if len(lines) > 4 else '',
                                'legal_basis': '',
                                'requirements': ''
                            }
                            
                            # Extract legal basis (Décret numbers)
                            decret_match = re.search(r'(Décret|Arrêté).*?(\d{4}[-/]\d+)', cell_content)
                            if decret_match:
                                position['legal_basis'] = decret_match.group(0)
                            
                            # Determine category
                            sector = position['sector'].lower()
                            arabic = position['arabic_title'].lower()
                            
                            if 'primary' in position['english_title'].lower() or 'يئادتبا' in arabic:
                                data['categories']['primary_education'].append(position)
                            elif 'secondary' in position['english_title'].lower() or 'يوناث' in arabic:
                                data['categories']['secondary_education'].append(position)
                            elif 'technical' in position['english_title'].lower() or 'ينقت' in arabic:
                                data['categories']['technical_education'].append(position)
                            elif 'director' in position['english_title'].lower() or 'ريدم' in arabic:
                                data['categories']['administration'].append(position)
                            elif 'inspector' in position['english_title'].lower() or 'شتفم' in arabic:
                                data['categories']['inspection'].append(position)
                            elif 'psycholog' in position['english_title'].lower() or 'nurse' in position['english_title'].lower():
                                data['categories']['support_services'].append(position)
                            
                            data['positions'].append(position)
            
            # Calculate summary statistics
            data['summary']['total_positions'] = len(data['positions'])
            data['summary']['by_sector'] = {
                'primary_education': len(data['categories']['primary_education']),
                'secondary_education': len(data['categories']['secondary_education']),
                'technical_education': len(data['categories']['technical_education']),
                'administration': len(data['categories']['administration']),
                'inspection': len(data['categories']['inspection']),
                'support_services': len(data['categories']['support_services']),
            }
            
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    return data


def get_career_plans_summary():
    """
    Quick summary of career plans data
    """
    data = parse_career_plans_pdf()
    if not data:
        return "No data available"
    
    summary = f"""
Career Plans Summary (Job Positions):
- Total Job Positions: {data['summary']['total_positions']}
- Primary Education: {data['summary']['by_sector']['primary_education']}
- Secondary Education: {data['summary']['by_sector']['secondary_education']}
- Technical Education: {data['summary']['by_sector']['technical_education']}
- Administration: {data['summary']['by_sector']['administration']}
- Inspection: {data['summary']['by_sector']['inspection']}
- Support Services: {data['summary']['by_sector']['support_services']}
- Pages Processed: {data['metadata']['pages_processed']}
"""
    return summary


if __name__ == '__main__':
    # Test the parser
    print("Testing Career Plans PDF Parser...")
    data = parse_career_plans_pdf()
    
    if data:
        print(f"\n✓ Successfully parsed PDF!")
        print(f"✓ Total positions defined: {data['summary']['total_positions']}")
        print(f"✓ Pages processed: {data['metadata']['pages_processed']}")
        print("\nPositions by category:")
        for category, positions in data['categories'].items():
            print(f"  {category}: {len(positions)} positions")
            for pos in positions[:2]:  # Show first 2 from each category
                print(f"    - {pos['arabic_title']} / {pos['english_title']}")
    else:
        print("\n✗ Failed to parse PDF")
