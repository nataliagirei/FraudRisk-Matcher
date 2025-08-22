import re
import pandas as pd
from unidecode import unidecode
from transliterate import translit
from metaphone import doublemetaphone
from fuzzywuzzy import fuzz


# --- Helpers: text prep ---
def detect_alphabet(text):
    if not isinstance(text, str) or not text.strip():
        return 'other'

    has_korean = any('\uac00' <= c <= '\ud7a3' for c in text)
    has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
    has_latin = any('a' <= c.lower() <= 'z' for c in text)

    if has_korean:
        return 'korean'
    elif has_cyrillic:
        return 'cyrillic'
    elif has_latin:
        return 'latin'
    else:
        return 'other'


def normalize_text(text):
    if not isinstance(text, str):
        return text

    # Deleting some polite words
    titles = {'pani', 'pan', 'mr', 'ms', 'mrs', 'mgr', 'dr', 'miss', 'sir'}
    words = text.strip().split()
    filtered_words = [w for w in words if w.lower() not in titles]
    text = ' '.join(filtered_words)

    alphabet = detect_alphabet(text)

    if alphabet == 'cyrillic':
        text = translit(text, 'ru', reversed=True)
    elif alphabet == 'latin':
        text = unidecode(text)

    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def normalize_column_names(df):
    df.columns = [
        re.sub(r'\W+', '_', col.strip().lower()).strip('_')
        for col in df.columns
    ]
    return df


def normalize_address(addr):
    if not isinstance(addr, str):
        return addr
    addr = normalize_text(addr)
    addr = re.sub(r'\bul\.?\b', 'ul', addr)
    addr = re.sub(r'\bapt\.?\b', 'apt', addr)
    addr = re.sub(r'[.,]', '', addr)
    return addr


def build_full_address(row):
    parts = [
        row.get('street', ''),
        str(row.get('building_number', '')) + (f"/{row['apartment_number']}" if pd.notna(row.get('apartment_number')) else ""),
        row.get('city', '')
    ]
    return ", ".join([p for p in parts if pd.notna(p)])


# --- Phonetics prep ---
def double_metaphone_similarity(word1, word2):
    if not word1 or not word2:
        return 0
    code1a, code1b = doublemetaphone(word1)
    code2a, code2b = doublemetaphone(word2)

    codes1 = [c for c in [code1a, code1b] if c]
    codes2 = [c for c in [code2a, code2b] if c]

    max_ratio = 0
    for c1 in codes1:
        for c2 in codes2:
            ratio = fuzz.ratio(c1, c2)
            if ratio > max_ratio:
                max_ratio = ratio
    return max_ratio


def extract_likely_surname(name):
    tokens = name.strip().split()
    if len(tokens) == 0:
        return ''
    return max(tokens, key=len) if len(tokens) > 1 else tokens[0]


# --- Main matchers ---
def pesel_matcher(pesel1, pesel2):
    matched = pesel1 == pesel2
    return matched, 'pesel' if matched else None


def address_matcher(addr1, addr2):
    threshold = 80
    addr1_norm = normalize_address(addr1)
    addr2_norm = normalize_address(addr2)
    ratio = fuzz.token_sort_ratio(addr1_norm, addr2_norm)
    matched = ratio >= threshold
    return matched, 'address' if matched else None, ratio


def name_and_phonetic_matcher(name1, name2):
    fuzzy_threshold = 85
    min_fuzz_for_surname_initial = 60
    min_fuzz_for_surname_only = 80
    phonetic_threshold = 50
    min_fuzz_for_phonetic = 60

    name1_norm = normalize_text(name1)
    name2_norm = normalize_text(name2)
    fuzz_ratio = fuzz.token_sort_ratio(name1_norm, name2_norm)

    parts1 = name1_norm.split()
    parts2 = name2_norm.split()

    surname1 = extract_likely_surname(name1_norm)
    surname2 = extract_likely_surname(name2_norm)

    if fuzz_ratio >= fuzzy_threshold:
        return True, 'fuzz', fuzz_ratio, 0

    if len(parts1) >= 2 and len(parts2) >= 2:
        initial_match = parts1[0][0] == parts2[0][0]
        if surname1 == surname2 and initial_match and fuzz_ratio >= min_fuzz_for_surname_initial:
            return True, 'surname+initial', fuzz_ratio, 0

    if surname1 == surname2 and fuzz_ratio >= min_fuzz_for_surname_only:
        return True, 'surname_only', fuzz_ratio, 0

    phonetic_ratio = 0
    if detect_alphabet(name1_norm) == detect_alphabet(name2_norm) == 'latin':
        phonetic_ratio = double_metaphone_similarity(name1_norm, name2_norm)

    if phonetic_ratio >= phonetic_threshold and fuzz_ratio >= min_fuzz_for_phonetic:
        return True, 'phonetic', fuzz_ratio, phonetic_ratio

    return False, 'no_match', fuzz_ratio, phonetic_ratio


def matcher(emp, comp, matching_criteria: list):
    reasons = []
    fuzz_ratio = 0
    phonetic_ratio = 0
    address_ratio = 0

    if 'pesel' in matching_criteria:
        matched, reason = pesel_matcher(emp['pesel'], comp['pesel'])
        if matched:
            reasons.append(reason)

    if 'name' in matching_criteria or 'phonetic' in matching_criteria:
        matched, reason, fr, pr = name_and_phonetic_matcher(
            emp['employee_full_name_clean'],
            comp['company_owner_name_clean']
        )
        fuzz_ratio = max(fuzz_ratio, fr)
        phonetic_ratio = max(phonetic_ratio, pr)
        if matched:
            reasons.append(reason)

    if 'address' in matching_criteria:
        matched, reason, addr_ratio = address_matcher(
            emp['employee_address_clean'],
            comp['company_address_clean']
        )
        address_ratio = addr_ratio
        if matched:
            reasons.append(reason)

    return {
        'is_match': bool(reasons),
        'match_reasons': ', '.join(reasons) if reasons else 'no_match',
        'fuzz_ratio': fuzz_ratio,
        'phonetic_ratio': phonetic_ratio,
        'address_ratio': address_ratio
    }


def generate_matches(df_employees, df_companies, matching_criteria):
    matches = []

    for _, emp in df_employees.iterrows():
        for _, comp in df_companies.iterrows():
            result = matcher(emp, comp, matching_criteria)

            if not result['is_match']:
                continue

            match_entry = {
                'company_name': comp['company_name'],
                'company_owner_name': comp['owner_name'],
                'employee_name': emp['name'],
                'employee_surname': emp['surname'],
                'match_reason': result['match_reasons']
            }

            if 'pesel' in matching_criteria:
                match_entry['company_owner_PESEL'] = comp['pesel']
                match_entry['employee_PESEL'] = emp['pesel']
                match_entry['matching_PESEL_flag'] = (emp['pesel'] == comp['pesel'])

            if 'address' in matching_criteria:
                match_entry['company_address'] = comp['address']
                match_entry['employee_address'] = emp['full_address']
                match_entry['matching_address_ratio'] = result['address_ratio']

            if 'name' in matching_criteria or 'phonetic' in matching_criteria:
                match_entry['matching_name_ratio'] = result['fuzz_ratio']
                match_entry['phonetic_match_ratio'] = result['phonetic_ratio']

            matches.append(match_entry)

    return matches
