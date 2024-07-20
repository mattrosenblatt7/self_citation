'''
Authors: Matt Rosenblatt 
This code was used to create the citation pairs dataset. You can just use the dataset that has been uploaded to GitHub
Requirements:
installed pybliometrics (see https://pybliometrics.readthedocs.io/en/stable/) and requested API key 
must be connected to VPN associated with the Scopus account (e.g., Yale)
'''

from pybliometrics.scopus import AbstractRetrieval, AuthorRetrieval, AffiliationRetrieval
import pandas as pd
from tqdm import tqdm
import os
import glob
import re
import numpy as np
from datetime import date
from pybliometrics.scopus.exception import Scopus404Error, Scopus500Error
import argparse
from json.decoder import JSONDecodeError

import urllib3, socket
from urllib3.connection import HTTPConnection

HTTPConnection.default_socket_options = ( 
    HTTPConnection.default_socket_options + [
    (socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000), #1MB in byte
    (socket.SOL_SOCKET, socket.SO_RCVBUF, 1000000)
])


# add arguments
parser = argparse.ArgumentParser()
parser.add_argument("--field", type=str, help="which field(s) to run for")
parser.add_argument("--years", type=str, help="which years to run for")


# parse arguments
args = parser.parse_args()
# field_arg = args.field
field_list_arg = [item for item in args.field.split(',')]
print(field_list_arg)
select_years = [int(item) for item in args.years.split(',')]
print(select_years)

refresh_days = 10000
# Overall summary
# Download all relevant articles in both FULL and REF view
# Three self-citation values for each reference
# 1) fa_sc: First author - binary, is it a self-citation?
# 2) la_sc: Last author - binary, is it a self-citation?
# 3) any_sc: Any author - count, how many any author self-citations?
# Article-level metrics to include:
    # Title: citing and cited article titles
    # Journal: citing and cited journals
    # Year: citing and cited years
    # Time lag: days passed between cited and citing
    # Number of authors: citing and cited
    # Number of ref: citing
    # Self-cite poisiton: for FA and LA only
    # (Missing) Document type: citing and cited doc types
    
# Things requiring author view/download (FA and LA only):
    # AUID - FA and LA author IDs
    # Name - FA and LA name
    # Academic age - FA and LA academic age
    # Affiliation country
    # Num previous papers:
        # Overall, FA only, LA only
    # Specialization: all prev paper keywords?
    # Gender - need Genderize.io
# In REF view check for matching EID or fully matching name to count as self-citation


dir_list = []
base_path = '/data_dustin/store3/training/matt/self_citation'
for field_folder in field_list_arg:  # 'Neuro', 'Neurology', 'Psychiatry'
    tmp = [f.path for f in os.scandir( os.path.join(base_path, 'All_' + field_folder + '/' ) ) if f.is_dir()]
    dir_list.extend(tmp)

# set journal parameters
for dir_name in dir_list:
    
    # (TEMPORARY) Only for testing specific journal
    # dir_name = '/data_dustin/store3/training/matt/self_citation/All_Neuro/Neuron'
    
    field_name = dir_name.split('/')[-2]
    all_csv = glob.glob( os.path.join(dir_name, '*_ref.csv') )
    journal_name = dir_name.split('/')[-1]
    
    
    regex = re.compile('%s(.*?)_ref'%journal_name)
    years=[int(re.findall(regex, tmp.split('/')[-1])[0]) for tmp in all_csv]
    years = [y for y in years if y in select_years]  # include only 2016-2020 (if available)
    
    for year in years:
        # read in main set of articles
        df_journal = pd.read_csv (  os.path.join(base_path, field_name, journal_name, journal_name + str(year) + '.csv')  )
        df_journal = df_journal[df_journal['Authors'] != '[No author name available]']  # remove entried w missing authors
        EIDs= list(df_journal['EID'])
        doc_types_for_year = list(df_journal['Document Type'])
        nentries = df_journal.shape[0]
        print('Total entries: ' + '{:d}'.format(nentries))
        
        df_year = pd.DataFrame()
        
        if os.path.exists(os.path.join('/data_dustin/store3/training/matt/self_citation/results_1_2024/', journal_name + str(year) + '.csv')):
            print('Skipping because file exists: ' + os.path.join('/data_dustin/store3/training/matt/self_citation/results_1_2024/', journal_name + str(year) + '.csv'))
            continue
        
        for entry_idx, this_eid in tqdm(enumerate(EIDs)):       
            
            # Full view
            try:
                ab_full = AbstractRetrieval(this_eid, view='FULL', refresh=refresh_days)
            except JSONDecodeError:
                continue  # skip to next loop (next article entry)
            except Scopus404Error:
                continue
            except Scopus500Error:
                continue
                
            # Reference view
            try:
                ab_ref = AbstractRetrieval(this_eid, view='REF', refresh=refresh_days)
            except JSONDecodeError:
                continue  # skip to next loop (next article entry)
            except Scopus404Error:
                continue
            except Scopus500Error:
                continue
                
                
            if ab_full.references is not None:
                numref = len(ab_full.references)
            else:
                continue  # skip to next loop (next article entry)
    
            
    
            ######################## Article level traits ########################

            # initialize empty lists
            eid_citing = [this_eid]*numref
            title_cited = [None]*numref
            title_citing = [ab_full.title]*numref
            journal_cited = [None]*numref
            journal_citing = [ab_full.publicationName]*numref
            date_cited = [None]*numref
            date_citing = [ab_full.coverDate]*numref
            year_cited = [None]*numref
            year_citing = [int(ab_full.coverDate[:4])]*numref
            num_auth_cited = [None]*numref
            num_auth_citing = [len(ab_full.authors)]*numref
            sc_fa = [None]*numref
            sc_la = [None]*numref
            sc_any = [None]*numref
            position_fa_sc = [None]*numref
            position_la_sc = [None]*numref
            num_ref_citing = [numref]*numref
            document_type = [doc_types_for_year[entry_idx]]*numref
            
            # Note: not present
            eid_full = [ab.id for ab in ab_full.references]
            eid_ref = [ab.id for ab in ab_ref.references]
            missing_ref_eid = [ eid for eid in eid_full if eid not in eid_ref]
            for ref_idx, ref_full in enumerate(ab_full.references):
                
                if ref_full.id in missing_ref_eid:  # in this case, try to download reference in a different way
                    missing_key = True
                    try:
                        ref_ref = AbstractRetrieval('2-s2.0-' + ref_full.id, refresh=refresh_days, view='FULL')
                        ref_auid = [ref_auth.auid for ref_auth in ref_ref.authors]
                    except Scopus404Error:  # either ID is not known by scopus
                        continue  # skip to next loop (next reference)
                    except Scopus500Error:
                        continue
                    except TypeError:  # ID not present
                        continue
                    except JSONDecodeError:
                        continue
                    except Exception as e:  # try to find what type of exception
                        print(e)
                        print(type(e))

                else:  # otherwise, if reference info is already present, just use this
                    missing_key = False
                    ref_ref = ab_ref.references[eid_ref.index(ref_full.id)]
                    if ref_ref.authors_auid is not None:
                        ref_auid = ref_ref.authors_auid.split(';')
                    else:
                        ref_auid = None

                # print(ref_full.title)
                title_cited[ref_idx] = ref_full.title
                
                if missing_key:
                    journal_cited[ref_idx] = ref_ref.title  
                    
                    if ref_ref.authors is not None:
                        num_auth_cited[ref_idx] = len(ref_ref.authors)
                    
                    if ref_ref.coverDate is not None:
                        year_cited[ref_idx] = int(ref_ref.coverDate[:4])
                else:
                    journal_cited[ref_idx] = ref_ref.sourcetitle
                    
                    num_auth_cited[ref_idx] = ref_ref.authors.count(';') + 1
                    
                    year_cited[ref_idx] = ref_full.publicationyear
                
                date_cited[ref_idx] = ref_ref.coverDate
                    

                
                

                #********************** Self-citation - by AUID **********************
                citing_auid = [int(citing_auth.auid) for citing_auth in ab_full.authors]
                try:
                    cited_auid = [int(cited_auid) for cited_auid in ref_auid]
                    sc_by_auth = [1*(citing_auid_entry in cited_auid) for citing_auid_entry in citing_auid]          
                    
                    if sc_by_auth[0]==1:
                        position_fa_sc[ref_idx] = np.where(np.array(cited_auid)==citing_auid[0])[0][0]
                        
                    if sc_by_auth[-1]==1:
                        position_la_sc[ref_idx] = np.where(np.array(cited_auid)==citing_auid[-1])[0][0]
                       
                    sc_fa[ref_idx] = sc_by_auth[0]
                    sc_la[ref_idx] = sc_by_auth[-1]
                    sc_any[ref_idx] = sum(sc_by_auth)
                    
                
                except AttributeError:
                    pass  # if can't find any info, just leave as None
                except TypeError:  # if no auid
                    pass
            
                
            
            ######################## Author level traits ########################
            auid_fa = [citing_auid[0]]*numref
            auid_la = [citing_auid[-1]]*numref
            
            name_fa = [str(ab_full.authors[0].surname) + ', ' + str(ab_full.authors[0].given_name)]*numref  # do str() in case of None
            name_la = [str(ab_full.authors[-1].surname) + ', ' + str(ab_full.authors[-1].given_name)]*numref
            
            
            ######## get author data (first author)
            try:
                a_f = AuthorRetrieval(citing_auid[0], refresh=refresh_days)
                a_f_retrieved_key = True
                
                # names (more detailed)
                if a_f.given_name is not None:
                    given_name_fa = [a_f.given_name]*numref
                else:
                    given_name_fa = [None]*numref
                if a_f.surname is not None:
                    surname_fa = [a_f.surname]*numref
                else:
                    surname_fa = [None]*numref
            except Scopus404Error:  # skip
                a_f_retrieved_key = False
                given_name_fa = [None]*numref
                surname_fa = [None]*numref
            except Scopus500Error:
                a_f_retrieved_key = False
                given_name_fa = [None]*numref
                surname_fa = [None]*numref
                
            try:
                a_l = AuthorRetrieval(citing_auid[-1], refresh=refresh_days)
                a_l_retrieved_key = True
                
                # names (more detailed)   
                if a_l.given_name is not None:
                    given_name_la = [a_l.given_name]*numref
                else:
                    given_name_la = [None]*numref
                if a_l.surname is not None:
                    surname_la = [a_l.surname]*numref
                else:
                    surname_la = [None]*numref              
            except Scopus404Error:  # skip
                a_l_retrieved_key = False
                given_name_la = [None]*numref
                surname_la = [None]*numref
            except Scopus500Error:
                a_l_retrieved_key = False
                given_name_la = [None]*numref
                surname_la = [None]*numref
                

                
            ######## affiliation country - if multiple, take first (split by ; line)
            if ab_full.authors[0].affiliation is not None:
                try:
                    affil_fa = AffiliationRetrieval(ab_full.authors[0].affiliation.split(';')[0], refresh=refresh_days)
                    affil_name_fa = [affil_fa.affiliation_name]*numref
                    affil_country_fa = [affil_fa.country]*numref
                except Scopus404Error:
                    affil_name_fa = [None]*numref
                    affil_country_fa = [None]*numref
                except Scopus500Error:
                    affil_name_fa = [None]*numref
                    affil_country_fa = [None]*numref
            else:
                affil_fa = [None]*numref
                affil_name_fa = [None]*numref
                affil_country_fa = [None]*numref
            
            
            if ab_full.authors[-1].affiliation is not None:
                try:
                    affil_la = AffiliationRetrieval(ab_full.authors[-1].affiliation.split(';')[0], refresh=refresh_days)
                    affil_name_la = [affil_la.affiliation_name]*numref
                    affil_country_la = [affil_la.country]*numref
                except Scopus404Error:
                    affil_name_la = [None]*numref
                    affil_country_la = [None]*numref
                except Scopus500Error:
                    affil_name_la = [None]*numref
                    affil_country_la = [None]*numref
            else:
                affil_la = [None]*numref
                affil_name_la = [None]*numref
                affil_country_la = [None]*numref
            
            ######## academic age and previous papers
            
            # for first author
            if a_f_retrieved_key:
                if a_f.publication_range is not None:
                    fa_tmp_starting_date = a_f.publication_range[0]
                    fa_tmp_academic_age = int(ab_full.coverDate[:4]) - fa_tmp_starting_date
                    try:
                        docs = pd.DataFrame(a_f.get_documents())

                        if docs.empty:  # if nothing found on author search
                            kw_recent_fa_save = [None]*numref
                            academic_age_fa = [None]*numref
                            num_prev_papers_fa = [None]*numref
                        else:
                            # find keywords of 10 papers closest in time to published one
                            d0 = date(int(ab_full.coverDate.split('-')[0]), int(ab_full.coverDate.split('-')[1]), int(ab_full.coverDate.split('-')[1]))
                            # some months say 00 or days say 00 - replace with 01
                            d1_all = [ date(int(coverDate.replace('-00', '-01').split('-')[0]),
                                            int(coverDate.replace('-00', '-01').split('-')[1]),
                                            int(coverDate.replace('-00', '-01').split('-')[1]))
                                        for coverDate in docs['coverDate'] ]
                            days_between = [(d1-d0).days for d1 in d1_all]
                            sorted_date_idx = np.argsort(np.abs(days_between))  # sort closest articles to current (by date)
                            kw_recent_fa = []
                            kw_all = docs['authkeywords']
                            for sorted_date_idx_tmp in sorted_date_idx:
                                if kw_all[sorted_date_idx_tmp] is not None:
                                    kw_recent_fa.append(kw_all[sorted_date_idx_tmp])
                                if len(kw_recent_fa)==10:
                                    break
                            kw_recent_fa_save = [None]*numref
                            kw_recent_fa_save[0] = ';;;;'.join(kw_recent_fa)
                            academic_age_fa = [fa_tmp_academic_age]*numref
                            # now find number of previous papers
                            eids_fa = list(docs['eid'])
                            try:
                                matching_eid_idx = eids_fa.index(ab_full.eid)
                                num_prev_papers_fa = [len( eids_fa[1+matching_eid_idx:] ) ]*numref
                            except ValueError:  # if can't find matching eid (e.g., maybe inconsitencies in author id on scopus)
                                num_prev_papers_fa = [np.sum(np.array(days_between)<0)]*numref
                    except JSONDecodeError: 
                        kw_recent_fa_save = [None]*numref
                        academic_age_fa = [None]*numref
                        num_prev_papers_fa = [None]*numref
                    except Scopus500Error: 
                        kw_recent_fa_save = [None]*numref
                        academic_age_fa = [None]*numref
                        num_prev_papers_fa = [None]*numref   
                else:
                    kw_recent_fa_save = [None]*numref
                    academic_age_fa = [None]*numref
                    num_prev_papers_fa = [None]*numref
            else:
                kw_recent_fa_save = [None]*numref
                academic_age_fa = [None]*numref
                num_prev_papers_fa = [None]*numref
 
            # for last author
            if a_f_retrieved_key:
                if a_l.publication_range is not None:
                    la_tmp_starting_date = a_l.publication_range[0]
                    la_tmp_academic_age = int(ab_full.coverDate[:4]) - la_tmp_starting_date
                    try:
                        docs = pd.DataFrame(a_l.get_documents())

                        if docs.empty:
                            kw_recent_la_save = [None]*numref
                            academic_age_la = [None]*numref
                            num_prev_papers_la = [None]*numref
                        else:
                            # find keywords of 10 papers closest in time to published one
                            d0 = date(int(ab_full.coverDate.split('-')[0]), int(ab_full.coverDate.split('-')[1]), int(ab_full.coverDate.split('-')[1]))
                            # some months say 00 or days say 00 - replace with 01
                            d1_all = [ date(int(coverDate.replace('-00', '-01').split('-')[0]),
                                            int(coverDate.replace('-00', '-01').split('-')[1]),
                                            int(coverDate.replace('-00', '-01').split('-')[1]))
                                    for coverDate in docs['coverDate'] ]

                            days_between = [(d1-d0).days for d1 in d1_all]
                            sorted_date_idx = np.argsort(np.abs(days_between))  # sort closest articles to current (by date)
                            kw_recent_la = []
                            kw_all = docs['authkeywords']
                            for sorted_date_idx_tmp in sorted_date_idx:
                                if kw_all[sorted_date_idx_tmp] is not None:
                                    kw_recent_la.append(kw_all[sorted_date_idx_tmp])
                                if len(kw_recent_la)==10:
                                    break
                            kw_recent_la_save = [None]*numref
                            kw_recent_la_save[0] = ';;;;'.join(kw_recent_la)
                            academic_age_la = [la_tmp_academic_age]*numref
                            # now find number of previous papers
                            eids_la = list(docs['eid'])
                            try:
                                matching_eid_idx = eids_la.index(ab_full.eid)
                                num_prev_papers_la = [len( eids_la[1+matching_eid_idx:] ) ]*numref
                            except ValueError:  # if can't find matching eid (e.g., maybe inconsitencies in author id on scopus)
                                num_prev_papers_la = [np.sum(np.array(days_between)<0)]*numref
                    except JSONDecodeError:
                        kw_recent_la_save = [None]*numref
                        academic_age_la = [None]*numref
                        num_prev_papers_la = [None]*numref
                    except Scopus500Error:
                        kw_recent_la_save = [None]*numref
                        academic_age_la = [None]*numref
                        num_prev_papers_la = [None]*numref   

                else:  # if no author dates
                    kw_recent_la_save = [None]*numref
                    academic_age_la = [None]*numref
                    num_prev_papers_la = [None]*numref   
            else:
                kw_recent_la_save = [None]*numref
                academic_age_la = [None]*numref
                num_prev_papers_la = [None]*numref   
            
            
            ######################## Update dataframe ########################
            df_entry = pd.DataFrame({'eid_citing':eid_citing,
                                     'title_citing':title_citing,'title_cited':title_cited,
                                     'document_type':document_type,
                                     'journal_citing':journal_citing, 'journal_cited':journal_cited, 
                                     'date_citing':date_citing, 'date_cited':date_cited, 
                                     'year_citing':year_citing, 'year_cited':year_cited,
                                     'num_auth_citing':num_auth_citing, 'num_auth_cited':num_auth_cited, 
                                     'num_ref_citing':num_ref_citing,
                                     'sc_fa':sc_fa,'sc_la':sc_la, 'sc_any':sc_any,
                                     'position_fa_sc':position_fa_sc, 'position_la_sc':position_la_sc,
                                     'affil_name_fa':affil_name_fa, 'affil_name_la':affil_name_la,
                                     'affil_country_fa':affil_country_fa, 'affil_country_la':affil_country_la,
                                     'academic_age_fa':academic_age_fa, 'academic_age_la':academic_age_la,
                                     'num_prev_papers_fa':num_prev_papers_fa, 'num_prev_papers_la':num_prev_papers_la,
                                     'kw_recent_fa':kw_recent_fa_save, 'kw_recent_la':kw_recent_la_save,
                                     'auid_fa':auid_fa , 'auid_la':auid_la ,
                                     'name_fa':name_fa , 'name_la':name_la,
                                     'surname_fa':surname_fa, 'surname_la':surname_la,
                                     'given_name_fa':given_name_fa, 'given_name_la':given_name_la})
            df_year = df_year.append(df_entry, ignore_index=True)
        
        df_year.to_csv(os.path.join('/data_dustin/store3/training/matt/self_citation/results_1_2024/', journal_name + str(year) + '.csv'),
                                    index=False)
        
    





