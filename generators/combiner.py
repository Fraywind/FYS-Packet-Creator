"""Combine individual PDFs into a single merged PDF per department."""

import os
from PyPDF2 import PdfWriter


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

    # append() rather than add_page(): add_page copies a page without fully
    # bringing across the resources it points at, which silently dropped fonts
    # from the merged packet. The page 5 marker table lost ZapfDingbats and
    # printed its checks and half circles as literal "3" and "w", and a page 6
    # heading lost Helvetica-Bold along with an en dash. Which department it hit
    # varied from run to run, so it was easy to miss. Measured over the whole
    # set: add_page loses fonts, append loses none.
    #
    # Errors are raised rather than swallowed: a packet quietly missing a page
    # is worse than a failed run, and app.py records the error per department.
    writer = PdfWriter()
    for pdf_file in pdf_files:
        writer.append(pdf_file)

    with open(output_path, 'wb') as out:
        writer.write(out)

    return True
