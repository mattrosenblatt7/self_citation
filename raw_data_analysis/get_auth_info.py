# Code to acquire author information
# Requirements:
#   installed unidecode and pybliometrics (see https://pybliometrics.readthedocs.io/en/stable/)
#   and requested API key (see above ref)
#   must be connected to VPN associated with the Scopus account (e.g., Yale)
#   https://github.com/pybliometrics-dev/pybliometrics/issues/191

from pybliometrics.scopus import AbstractRetrieval, AuthorRetrieval
import pandas as pd
from tqdm import tqdm
from util_functions import clean_author_str
import unidecode
import numpy as np
import os
import glob
import re


refresh_days = 365 

dir_list = []
for field_name in ['Neuro', 'Neurology', 'Psychiatry']:
    tmp = [f.path for f in os.scandir('../All_' + field_name + '/') if f.is_dir()]
    dir_list.extend(tmp)

# set journal parameters
for dir_name in dir_list:
    all_csv = glob.glob(dir_name + '/*_ref.csv')

    field_name = dir_name.split('/')[-2]
    journal_name = dir_name.split('/')[-1]

    regex = re.compile('%s(.*?)_ref'%journal_name)
    years=[int(re.findall(regex, tmp.split('/')[-1])[0]) for tmp in all_csv]
    print(years)

    for year in years:
        fa_given_update=[]; la_given_update=[]
        fa_start_date = []; la_start_date = []
        fa_academic_age = []; la_academic_age = []
        fa_papers_before = []; la_papers_before = []
        # read in main set of articles
        df_results = pd.read_excel('../' + field_name + '/' + journal_name + '/results_' + journal_name + str(year) + '.xlsx')
        nentries = df_results.shape[0]
        print('Total entries: ' + '{:d}'.format(nentries))

        for entry_idx in tqdm(range(nentries)):

            # print('\n***** Evaluating Manuscript eid: ' + this_eid + ' *****\n')
            auth_ids = df_results.iloc[entry_idx]['Author(s) ID']
            auth_ids = auth_ids.split(';')[:-1]  # removes final semicolon

            try:
                a_f=AuthorRetrieval(int(auth_ids[0]), refresh=refresh_days)
                a_l=AuthorRetrieval(int(auth_ids[-1]), refresh=refresh_days)

                fa_given_tmp = a_f.given_name
                la_given_tmp = a_l.given_name

                fa_tmp_starting_date = a_f.publication_range[0]
                fa_tmp_academic_age = year - fa_tmp_starting_date

                all_docs = a_f.get_documents()
                docs = pd.DataFrame(a_f.get_documents())
                pub_years = docs['coverDate'].str[:4]
                pub_years = np.array([int(y) for y in pub_years])
                fa_papers_before.append(len(pub_years[pub_years<year]))

                la_tmp_starting_date = a_l.publication_range[0]
                la_tmp_academic_age = year - la_tmp_starting_date
                docs = pd.DataFrame(a_l.get_documents())
                pub_years = docs['coverDate'].str[:4]
                pub_years = np.array([int(y) for y in pub_years])
                la_papers_before.append(len(pub_years[pub_years<year]))

                fa_given_update.append(fa_given_tmp)
                la_given_update.append(la_given_tmp)
                fa_start_date.append(fa_tmp_starting_date)
                fa_academic_age.append(fa_tmp_academic_age)
                la_start_date.append(la_tmp_starting_date)
                la_academic_age.append(la_tmp_academic_age)

            except:
                fa_given_update.append('Error')
                la_given_update.append('Error')
                fa_start_date.append(np.nan)
                fa_academic_age.append(np.nan)
                la_start_date.append(np.nan)
                la_academic_age.append(np.nan)
                fa_papers_before.append(np.nan)
                la_papers_before.append(np.nan)

        # Save results
        df_results['fa_given_update'] = fa_given_update
        df_results['la_given_update'] = la_given_update
        df_results['fa_start_date'] = fa_start_date
        df_results['fa_academic_age'] = fa_academic_age
        # df_results['fa_papers_before'] = fa_papers_before
        df_results['la_start_date'] = la_start_date
        df_results['la_academic_age'] = la_academic_age
        df_results['fa_papers_before'] = fa_papers_before
        df_results['la_papers_before'] = la_papers_before
        # df_results['la_papers_before'] = la_papers_before
        df_results.to_csv('../' + field_name + '/' + journal_name + '/results_gendernames_' + journal_name + str(year) + '.csv')

