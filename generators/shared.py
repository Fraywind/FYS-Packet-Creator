"""Shared constants and utilities for all PDF generators."""

import math

DEPARTMENT_MAPPING = {
    'Harvard Business School': 'HBS',
    'Harvard Divinity School': 'HDS',
    'Harvard Graduate School of Education': 'HGSE',
    'Harvard Kennedy School': 'HKS',
    'Harvard Law School': 'HLS',
    'Harvard Medical School': 'HMS',
    'Harvard T.H. Chan School of Public Health': 'HSPH',
    'Harvard John A. Paulson School of Engineering and Applied Sciences': 'SEAS',
    'African and African American Studies': 'AAAS',
    'Art, Film, and Visual Studies': 'AFVS',
    'Anthropology': 'ANTH',
    'Astronomy': 'ASTRO',
    'Celtic Languages and Literatures': 'CELTIC',
    'Chemistry and Chemical Biology': 'CHEM',
    'Classics': 'CLASS',
    'Comparative Literature': 'COMPLIT',
    'East Asian Languages and Civilizations': 'EASIAN',
    'Economics': 'ECON',
    'English': 'ENGL',
    'Earth and Planetary Sciences': 'EPS',
    'Germanic Languages and Literatures': 'GERM',
    'Government': 'GOV',
    'History of Art and Architecture': 'HAA',
    'History': 'HIST',
    'History of Science': 'HISSCI',
    'History & Literature': 'HISTLIT',
    'Human Evolutionary Biology': 'HEB',
    'Linguistics': 'LING',
    'Mathematics': 'MATH',
    'Molecular and Cellular Biology': 'MCB',
    'Music': 'MUS',
    'Near Eastern Languages and Civilizations': 'NELC',
    'Organismic and Evolutionary Biology': 'OEB',
    'Philosophy': 'PHIL',
    'Physics': 'PHYS',
    'Psychology': 'PSYCH',
    'Romance Languages and Literatures': 'RLL',
    'South Asian Studies': 'SAS',
    'Stem Cell and Regenerative Biology': 'SCRB',
    'Slavic Languages and Literatures': 'SLAV',
    'Sociology': 'SOC',
    'Committee on the Study of Religion': 'STUOFREL',
    'Theater, Dance, and Media': 'TDM',
    'Committee on Degrees in the Study of Women, Gender, and Sexuality': 'WGS',
}

# Reverse mapping: acronym -> full name
ACRONYM_TO_FULL = {v: k for k, v in DEPARTMENT_MAPPING.items()}
ACRONYM_TO_FULL.update({
    'Gov': 'Government',
    'GOV': 'Government',
    'HEB': 'Human Evolutionary Biology',
})

ALL_DEPARTMENTS = sorted(set(ACRONYM_TO_FULL.keys()))


def sanitize_department_name(dept_name):
    """Sanitize department name for file path safety."""
    sanitized = dept_name.replace('/', ' and ').replace('\\', ' and ')
    sanitized = sanitized.replace(':', ' -').replace('*', '').replace('?', '')
    sanitized = sanitized.replace('<', '').replace('>', '').replace('|', '')
    return sanitized.strip()


# ---------------------------------------------------------------------------
# Seminar title fitting
# ---------------------------------------------------------------------------
# Long seminar titles used to run past the edge of the title column and print on
# top of the professor's name. The rule, in order of preference:
#
#   1. Shrink the title's font a little so it still fits on one line. This is
#      the normal fix and handles most long titles invisibly.
#   2. If it would have to shrink past TITLE_FONT_FLOOR to fit, it is no longer
#      comfortably readable in print. Only then use a shortened title from
#      TITLE_OVERRIDES below, which keeps the seminar's real name and drops the
#      trailing subtitle.
#   3. Anything long enough to need shortening but not listed in TITLE_OVERRIDES
#      wraps onto a second line at the floor size. Nothing is ever truncated and
#      nothing ever overlaps; the run reports these so a person can add a
#      shortened form here.
#
# Used by PDF 7 and, once it is built, PDF 6.

TITLE_FONT_SIZE = 8.0    # normal size for a seminar title
TITLE_FONT_FLOOR = 6.0   # smallest size that still reads on a printed page

# Titles too long to fit on one line even at TITLE_FONT_FLOOR. Each shortened
# form is cut at the title's own colon or dash, so what remains is the seminar's
# actual name rather than a paraphrase. Add to this list only when the run
# reports a title that needs it.
TITLE_OVERRIDES = {
    'Medicine in Nazi Germany and the Holocaust—Anatomy as Example for Changes '
    'in Medical Science from Routine to Murder':
        'Medicine in Nazi Germany and the Holocaust',

    'Research at the Harvard Forest—Global Change Ecology: Forests, Ecosystem '
    'Function, the Future':
        'Research at the Harvard Forest',

    'Detention, Deportation, and Due Process: A Look at the Inner Workings of '
    'the U.S. Immigration System':
        'Detention, Deportation, and Due Process',

    'When Bad things Happen Early in Life: Effects of Early Adversity on Brain '
    '& Behavioral Development':
        'When Bad things Happen Early in Life',

    'Unlocking the Power of Immunology—From Fundamental Principles to '
    'Innovative Research Routes':
        'Unlocking the Power of Immunology',
}


def fit_seminar_title(title, max_width, font_name='Helvetica',
                      base_size=TITLE_FONT_SIZE, min_size=TITLE_FONT_FLOOR):
    """Fit a seminar title into a column of max_width points.

    Returns (text, font_size, fits_on_one_line). A False third value means even
    the shortened form needs to wrap, and the title should be added to
    TITLE_OVERRIDES.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    text = TITLE_OVERRIDES.get(title.strip(), title).strip()
    width = stringWidth(text, font_name, base_size)
    if width <= max_width:
        return text, base_size, True

    # Font size scales linearly with width, so this is the exact size that fits.
    # Round down to a tenth so rounding never pushes it back over the edge.
    needed = math.floor((base_size * max_width / width) * 10) / 10
    if needed >= min_size:
        return text, needed, True

    return text, min_size, False
