# FraudRisk-Matcher
Identifying potential connections between employees and company owners using multiple matching criteria

This is a Python-based tool for detecting potential conflicts of interest and fraud risks by identifying links between employees and company owners.  
It uses a combination of exact matching, fuzzy string comparison, phonetic algorithms, and address normalization to find hidden connections.

## Features
- Text normalization for names and addresses
- Alphabet detection (Cyrillic, Latin, Korean)
- Transliteration of Cyrillic into Latin
- Removal of polite forms and titles (Mr, Mrs, Dr, Pan, etc.)
- Fuzzy string matching with configurable thresholds
- Phonetic comparison using **Double Metaphone**
- Address normalization (handling common abbreviations like *ul.* → *ul*, *apt.* → *apt*)
- Exact PESEL number matching
- Generation of a consolidated Excel report with reasons and similarity scores
- Excel formatting

## Installation

You can either work with the code you already have locally, or clone this repository if using GitHub.

### Option 1: Local setup (if you already have the script)
1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Linux/Mac
   venv\Scripts\activate      # on Windows
   pip install -r requirements.txt
   
### Option 2: Clone from GitHub
1. Clone the repository:
   ```bash
   git clone https://github.com/nataliagirei/FraudRisk-Matcher.git
   cd FraudRisk-Matcher
   pip install -r requirements.txt

## Example Data & Notes
- Added sample datasets with companies and employees. These were **randomly generated using the `faker` library**, and any coincidences are unintentional.  
- Included an example output file (`matches.xlsx`) to illustrate the results.  
- For large datasets, it is recommended to install **python-Levenshtein** to speed up fuzzy string matching:  
  ```bash
  pip install python-Levenshtein
