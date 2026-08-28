"""Shared constants and utilities for all PDF generators."""

import math
import re
import unicodedata

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


def fit_seminar_title(title, max_width, note='', font_name='Helvetica',
                      base_size=TITLE_FONT_SIZE, min_size=TITLE_FONT_FLOOR):
    """Fit a seminar title into a column of max_width points.

    note is an optional parenthetical such as a co-teaching credit. It is kept
    on the title when there is room for it at a readable size, and dropped when
    there is not, so the caller can move it to a footnote instead.

    Returns (text, font_size, fits_on_one_line, note_included).
    fits_on_one_line False means even the shortened title has to wrap, and it
    should be added to TITLE_OVERRIDES.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    text = TITLE_OVERRIDES.get(title.strip(), title).strip()

    def size_for(candidate):
        width = stringWidth(candidate, font_name, base_size)
        if width <= max_width:
            return base_size
        # Font size scales linearly with width, so this is the exact size that
        # fits. Round down to a tenth so rounding never pushes it back over.
        return math.floor((base_size * max_width / width) * 10) / 10

    if note:
        annotated = f"{text} ({note})"
        size = size_for(annotated)
        if size >= min_size:
            return annotated, size, True, True

    size = size_for(text)
    if size >= min_size:
        return text, size, True, False
    return text, min_size, False, False


# ---------------------------------------------------------------------------
# Wide table fitting
# ---------------------------------------------------------------------------
# Pages 4 and 5 both put one column per academic year next to a column of text
# (rank names on page 4, faculty names on page 5). Each new year makes them a
# little wider, and a department with long faculty names already pushes page 5
# past the paper. ReportLab centres an over-wide table, so it runs off both
# edges at once: the first letter of every name and the last year column are
# physically cut off.
#
# The fix is deliberately narrow. Only the left/right overflow is handled, and
# only for the departments that actually overflow. Everyone else is untouched.


def trim_years_to_fit(year_columns, fits):
    """Drop the oldest year columns until the table fits across the page.

    Every table keeps its year headings spelled out the same way. The few that
    would be cut start a year later instead (2014-15 rather than 2013-14),
    which is then the only difference between their table and everyone else's.

    Args:
        year_columns: All academic-year columns, oldest first.
        fits: Callable taking a list of years and returning True if the table
              built from them stays on the page.

    Returns:
        The years to show, oldest first. The full list when it already fits, so
        a table that is not in trouble is never changed.
    """
    years = list(year_columns)
    while len(years) > 1 and not fits(years):
        years = years[1:]
    return years


def dropped_years(all_years, shown_years):
    """The oldest years left off a table, oldest first. Empty when none were."""
    return list(all_years[:len(all_years) - len(shown_years)])


# Footnote markers for a single page. Same glyph in different colors, so two
# footnotes on one page stay tellable apart at a glance.
FOOTNOTE_MARKERS = [
    ('*', '#000000'),
    ('*', '#A51C30'),  # crimson
    ('*', '#1F4E9C'),  # blue
    ('*', '#1B6B3A'),  # green
]


def marker_for(index):
    """(glyph, hex colour) for the index-th footnote on a page."""
    return FOOTNOTE_MARKERS[index % len(FOOTNOTE_MARKERS)]


def _ascii(text):
    """Accent-free comparison form, so Bréond and Breond key the same."""
    return unicodedata.normalize('NFKD', str(text).strip()) \
        .encode('ascii', 'ignore').decode()


def canonical_person_name(first, last):
    """Display name for an instructor, consistent across every page.

    The source spreadsheets carry a middle initial for the same person on some
    rows and not others (Logan S McCarty in spring, Logan McCarty in fall), which
    makes one person read as two. Drop a trailing lone initial from the first
    name. A first name that is only an initial ("C." Vafa) is left alone.
    """
    first = str(first).strip()
    last = str(last).strip()
    if re.search(r'\S', first):
        first = re.sub(r'\s+[A-Za-z]\.?$', '', first).strip()
    override = PERSON_NAME_OVERRIDES.get(
        (_ascii(last).lower(), _ascii(first)[:1].lower()))
    if override:
        return override
    return f"{first} {last}".strip()


# Department cells hold either one department or a joint pair ("COMPLIT / ENGL"),
# so a department matches when it equals one of the parts. Substring matching
# looked fine until a full committee name arrived: "SOC" is inside "Committee on
# Degrees in Social Studies", which put two Social Studies seminars on the
# Sociology packet.
def department_matches(cell, department):
    """True when `department` is one of the departments named in `cell`."""
    wanted = str(department).strip().lower()
    return any(part.strip().lower() == wanted
               for part in str(cell).split('/'))


# The same person is written differently by the two source spreadsheets, so one
# instructor read two ways across pages 6 and 7 ("Sun Kim" against "Sun Joo
# Kim"). Keyed by surname and first initial, never surname alone: David and
# Philip Fisher, Jessica and Stephen Marglin, Courtney and David Lamberth, and
# Anna and Benjamin Wilson are different people who share a surname.
PERSON_NAME_OVERRIDES = {
    ('kim', 's'): 'Sun Joo Kim',
    ('mankiw', 'n'): 'N. Gregory Mankiw',
    ('quast', 'k'): 'Kathleen Quast',
    ('vafa', 'c'): 'Cumrun Vafa',
}


def name_mismatches(page6_names, page7_names):
    """Instructors whose display name differs between pages 6 and 7.

    Pages 6 and 7 read different spreadsheets, so the same person can arrive
    written two ways ("Sun Kim" on one, "Sun Joo Kim" on the other) and read as
    two people. Matching is on surname plus first initial, never surname alone:
    David and Philip Fisher are different people, and so are Jessica and Stephen
    Marglin, Courtney and David Lamberth, and Anna and Benjamin Wilson.

    Takes {(surname, initial): {names seen}} for each page. Returns a sorted
    list of (page 6 name, page 7 name) still disagreeing after
    PERSON_NAME_OVERRIDES has been applied, for a person to settle.
    """
    out = []
    for key in sorted(set(page6_names) & set(page7_names)):
        left, right = page6_names[key], page7_names[key]
        if left != right:
            out.append((' / '.join(sorted(left)), ' / '.join(sorted(right))))
    return out


def name_key(first, last):
    """Surname plus first initial, the unit name_mismatches compares on."""
    return (_ascii(last).lower(), _ascii(first)[:1].lower())
