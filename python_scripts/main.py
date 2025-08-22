from comparator import *
from excel_formatter import *
import pandas as pd


# --- Data loading (you should input your data here) ---
df_employees = pd.read_excel('employees.xlsx')
df_companies = pd.read_excel('companies.xlsx')

# --- Data prep ---
df_employees = normalize_column_names(df_employees)
df_companies = normalize_column_names(df_companies)
df_employees['full_address'] = df_employees.apply(build_full_address, axis=1)
df_employees['employee_address_clean'] = df_employees['full_address'].apply(normalize_address)
df_employees['employee_name_clean'] = df_employees['name'].apply(normalize_text)
df_employees['employee_surname_clean'] = df_employees['surname'].apply(normalize_text)
df_employees['employee_full_name_clean'] = df_employees['employee_name_clean'] + ' ' + df_employees['employee_surname_clean']

df_companies['company_owner_name_clean'] = df_companies['owner_name'].apply(normalize_text)
df_companies['company_address_clean'] = df_companies['address'].apply(normalize_address)


# --- Matching ---
matching_criteria = ['name', 'phonetic', 'address', 'pesel']
matches = generate_matches(df_employees, df_companies, matching_criteria)

# --- Creating a final data frame and sorting ---
df_matches = pd.DataFrame(matches)
df_matches = df_matches.sort_values(by='matching_name_ratio', ascending=False)
df_matches = df_matches.drop_duplicates(subset=['employee_PESEL'], keep='first')


# Saving data (input a file name and a file path)
if __name__ == "__main__":
    format_excel_from_df(df_matches, "matches.xlsx")

