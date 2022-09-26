#################################################
#
# Authors: Matt Rosenblatt & Stephanie Noble
#
# must be connected to VPN associated with the Scopus account (e.g., Yale)

import pybliometrics
from pybliometrics.scopus import AbstractRetrieval, AuthorRetrieval
import pandas as pd
from tqdm import tqdm
import unidecode
import numpy as np
import argparse
import matplotlib.pyplot as plt
import seaborn as sns

numref = []
refresh_rate = 30  # number of days until refreshing Scopus results

# add arguments
parser = argparse.ArgumentParser()
parser.add_argument("--ID", type=int, help="Scopus ID of author")
parser.add_argument("--allow_initial", type=int, default=0, help="whether to allow for using 'Surname, Given name initial' if IDs are not found. NOT recommended if you expect to have a relatively common Surname + Initial combination", choices=[0, 1])
parser.add_argument("--make_plots", type=int, default=1, help="whether to plot results, default will plot", choices=[0, 1])

# parse arguments
args = parser.parse_args()
ID = args.ID
allow_initial = (args.allow_initial==1)  # True if allowing initial
make_plots = (args.make_plots==1)  # True if wanting to make plots

# load author information and their documents
auth = AuthorRetrieval(ID, refresh=refresh_rate)
scopus_indexed_name = auth.indexed_name.replace(' ', ', ')
all_docs = auth.get_documents()
docs_df = pd.DataFrame(all_docs)
docs_df = docs_df[['eid', 'title', 'author_count', 'author_names', 'coverDate', 'coverDisplayDate']]
ndocs = len(docs_df)

# initialize empty arrays
auth_position = np.nan + np.zeros((ndocs, ))
sc_count = np.nan + np.zeros((ndocs, ))
sc_count_any = np.nan + np.zeros((ndocs, ))
numref = np.nan + np.zeros((ndocs, ))
missing_ref_count = np.nan + np.zeros((ndocs, ))

# loop over documents
for i, doc_eid in enumerate(tqdm(list(docs_df.eid))):
    
    try:  # try to read document based on Scopus EID
        ab = AbstractRetrieval(doc_eid, refresh=refresh_rate, view="FULL")
        
    except pybliometrics.scopus.exception.Scopus404Error:  # if Scopus failure (not available), skip this
        ab = []
        continue
    
    # get author IDs
    author_IDs = np.array([author_entry.auid for author_entry in ab.authors if author_entry.auid is not None])
    author_indexed_names = [author_entry.indexed_name.replace(' ', ', ') for author_entry in ab.authors if author_entry.indexed_name is not None]

    if ID in author_IDs:  # find author position of given author (e.g., first author)
        auth_position[i] = np.where(ID==author_IDs)[0][0] + 1

    try:  # get reference paper Scopus EIDs
        ref_EID = ['2-s2.0-' + ref_entry.id for ref_entry in ab.references if ref_entry.id is not None]
    except TypeError:  # if no references available, skip
        continue

    numref[i] = len(ab.references)
    sc_doc = 0  # number of self-citations for a given document
    sc_doc_any = 0
    missing_ref = 0  # number of references missing info for a given document
    for ref_idx, eid_to_download in enumerate(ref_EID):  # download reference papeers
        try:  # try to read document based on Scopus EID
            ref_ab = AbstractRetrieval(eid_to_download, refresh=refresh_rate, view="FULL")
        except pybliometrics.scopus.exception.Scopus404Error:  # if we cannot find article, count as a missing reference

            if allow_initial==False:  # if not allowing initial, then consider reference missing
              missing_ref+=1
            else: # if allowing to use initials, then use "Given Name, Initial" to determine self-citation
              if scopus_indexed_name in ab.references[ref_idx].authors:  
                sc_doc +=1

              if any([indexed_name_tmp in ab.references[ref_idx].authors for indexed_name_tmp in author_indexed_names]):
                sc_doc_any +=1
            
            continue  # skip loop if no abstract available for download

        try:  # try to read reference author IDs
            ref_auth_IDs = np.array([author_entry.auid for author_entry in ref_ab.authors if author_entry.auid is not None])

            if len(ref_auth_IDs)>=1:  # make sure some authors were found
                if ID in ref_auth_IDs:
                    sc_doc+=1

                if any([id_tmp in ref_auth_IDs for id_tmp in author_IDs]):
                    sc_doc_any+=1

        except TypeError:  # if no reference author IDs available, count as a missing reference

            if allow_initial==False:  # if not allowing initial, then consider reference missing
              missing_ref+=1
            else: # if allowing to use initials, then use "Given Name, Initial" to determine self-citation
              if scopus_indexed_name in ab.references[ref_idx].authors:  
                sc_doc +=1

              if any([indexed_name_tmp in ab.references[ref_idx].authors for indexed_name_tmp in author_indexed_names]):
                sc_doc_any +=1
            continue
        
        missing_ref_count[i] = missing_ref
        sc_count[i] = sc_doc
        sc_count_any[i] = sc_doc_any
       

# Save results
docs_df['Year'] = [int(date[:4]) for date in docs_df.coverDate]
docs_df['auth_position'] = auth_position
docs_df['sc_count'] = sc_count
docs_df['sc_count_any'] = sc_count_any
docs_df['numref'] = numref
docs_df['missing_ref_count'] = missing_ref_count
docs_df['sc_rate'] = docs_df['sc_count'] / docs_df['numref']
docs_df['sc_rate_any'] = docs_df['sc_count_any'] / docs_df['numref']
docs_df.to_csv('./results/results_df_' + scopus_indexed_name + '.csv')
print('Overall self-citation rate: {:.4f}'.format( np.nansum(docs_df.sc_count) / np.nansum(docs_df.numref)) )

if make_plots:
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(x='sc_rate', data=docs_df, color='#1b9e77', ax=ax)
    ax.set_xlabel('Author-Author self-citation rate')
    ax.set_ylabel('Count')
    fig.savefig('./results/' + scopus_indexed_name + '_single_author_hist.png', format="png", transparent=True, dpi=400, bbox_inches='tight')

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(x='sc_rate_any', data=docs_df, color='#d95f02', ax=ax)
    ax.set_xlabel('Any Author self-citation rate')
    ax.set_ylabel('Count')
    fig.savefig('./results/' + scopus_indexed_name + '_any_author_hist.png', format="png", transparent=True, dpi=400, bbox_inches='tight')


    fig, ax = plt.subplots(figsize=(8, 5))
    df_by_year = docs_df.groupby(['Year']).agg({'sc_count':'sum', 'numref':'sum'})
    df_by_year['sc_rate'] = df_by_year['sc_count'] / df_by_year['numref']
    ax.set_xlabel('Year')
    ax.set_ylabel('Author-Author self-citation rate')
    sns.scatterplot(data=df_by_year, x='Year', y='sc_rate', color='#1b9e77', ax=ax)
    fig.savefig('./results/' + scopus_indexed_name + '_single_author_time.png', format="png", transparent=True, dpi=400, bbox_inches='tight')



