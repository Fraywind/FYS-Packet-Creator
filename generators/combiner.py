"""Combine individual PDFs into a single merged PDF per department."""

import os
from PyPDF2 import PdfReader, PdfWriter


def combine_department_pdfs(folder_path, output_path):
    """Combine all numbered PDFs in a department folder into one file.

    Returns True on success, False otherwise.
    """
    if not os.path.exists(folder_path):
        return False

    pdf_files = sorted(
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if f.lower().endswith('.pdf') and not f.startswith('ALL'))

    if not pdf_files:
        return False

    # Every source file has to stay open until write() finishes. PyPDF2
    # resolves indirect objects lazily, so a page added from a file that is
    # already closed can silently lose resources it still points at. That is
    # what dropped ZapfDingbats from the page 5 marker table (checks and half
    # circles printed as "3" and "w") and Helvetica-Bold from a page 6 heading.
    #
    # Errors are raised rather than swallowed: a packet quietly missing a page
    # is worse than a failed run, and app.py records the error per department.
    handles = []
    try:
        writer = PdfWriter()
        for pdf_file in pdf_files:
            handle = open(pdf_file, 'rb')
            handles.append(handle)
            for page in PdfReader(handle).pages:
                writer.add_page(page)

        with open(output_path, 'wb') as out:
            writer.write(out)
    finally:
        for handle in handles:
            handle.close()

    return True
