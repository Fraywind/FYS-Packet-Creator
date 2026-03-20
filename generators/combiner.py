"""Combine individual PDFs into a single merged PDF per department."""

import os
from PyPDF2 import PdfReader, PdfWriter


def combine_department_pdfs(folder_path, output_path):
    """Combine all numbered PDFs in a department folder into one file.

    Returns True on success, False otherwise.
    """
    if not os.path.exists(folder_path):
        return False

    pdf_files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith('.pdf') and not f.startswith('ALL'):
            pdf_files.append(os.path.join(folder_path, f))

    if not pdf_files:
        return False

    pdf_files.sort()

    writer = PdfWriter()
    for pdf_file in pdf_files:
        try:
            with open(pdf_file, 'rb') as fh:
                reader = PdfReader(fh)
                for page in reader.pages:
                    writer.add_page(page)
        except Exception:
            continue

    try:
        with open(output_path, 'wb') as out:
            writer.write(out)
        return True
    except Exception:
        return False
