"""Shared constants and utilities for all PDF generators."""

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
