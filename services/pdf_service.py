import os
import pypdf

def extract_text_from_pdf(file_path):
    """Extract full text from a PDF file using pypdf."""
    try:
        reader = pypdf.PdfReader(file_path)
        extracted_text = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text.append(page_text)
        
        full_text = "\n\n".join(extracted_text).strip()
        if not full_text:
            raise ValueError("No readable text found in the PDF file.")
        return full_text
    except Exception as e:
        raise ValueError(f"Error reading PDF file: {str(e)}")

def extract_text_from_txt(file_path):
    """Extract text from a plain TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_text = f.read().strip()
        if not full_text:
            raise ValueError("The text file is empty.")
        return full_text
    except Exception as e:
        raise ValueError(f"Error reading TXT file: {str(e)}")

def process_file_content(file_path, filename):
    """Process file based on extension and return extracted text."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext == 'txt':
        return extract_text_from_txt(file_path)
    elif ext == 'py':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Please upload PDF, TXT, or PY files.")
