# Requirements:
#   installed unidecode and pybliometrics (see https://pybliometrics.readthedocs.io/en/stable/)
#   and requested API key (see above ref)
#   must be connected to VPN associated with the Scopus account (e.g., Yale)
#   https://github.com/pybliometrics-dev/pybliometrics/issues/191
#def main():
from pybliometrics.scopus import AbstractRetrieval, AuthorRetrieval
import pandas as pd
from tqdm import tqdm
from util_functions import clean_author_str
import unidecode

# set journal parameters
journal_name = 'Nature'
for year in range(2020, 2021):

    # read in main set of articles
    df_journal = pd.read_csv ('../' + journal_name + '/' + journal_name + str(year) + '.csv')
    df_journal = df_journal[df_journal['Authors'] != '[No author name available]']  # remove entried w missing authors
    EIDs= list(df_journal['EID'])
    nentries = df_journal.shape[0]
    print('Total entries: ' + '{:d}'.format(nentries))

    # read in reference database
    df_ref = pd.read_csv('../' + journal_name + '/' + journal_name + str(year) + '_ref.csv')
    df_ref['Title'] = [str(title) for title in df_ref['Title']]  # some weird non-string issue
    print(df_ref.keys())
    EID_str_database = ';;;;'.join(df_ref['EID'])  # make string of all EIDs for faster searching

    # initialize lists for author ID and string methods
    fa = []; la = []; fa_la = []; any_author = []
    fa_str = []; la_str = []; fa_la_str = []; any_str = []
    fa_EIDs = []; la_EIDs = []; fa_la_EIDs = []; any_EIDs = []
    numref = []

    for entry_idx, this_eid in tqdm(enumerate(EIDs)):
        # get authors, excluding some consortia
        article_authors = clean_author_str(df_journal.iloc[entry_idx]['Authors'])
        first_author = article_authors[0]
        last_author = article_authors[-1]

        # print('\n***** Evaluating Manuscript eid: ' + this_eid + ' *****\n')
        ab = AbstractRetrieval(this_eid, view="FULL")

        # get author and reference IDs
        author_IDs = [author_entry.auid for author_entry in ab.authors if author_entry.auid is not None]
        author_names = [author_entry.surname + ', ' + author_entry.given_name.split(' ')[0] for author_entry in ab.authors
                                           if author_entry.surname is not None and author_entry.given_name is not None]
        author_names = clean_author_str(author_names)

        try:
            ref_EID = ['2-s2.0-' + ref_entry.id for ref_entry in ab.references if ref_entry.id is not None]
            ref_count = len(ref_EID)
            # finding matching references based on IDs
            matching_eid_loc = []
            for EID in ref_EID:
              title_end_loc = EID_str_database.find(EID)
              if title_end_loc>0:
                matching_eid_loc.append(EID_str_database[:title_end_loc].count(';;;;'))
            df_ref_trimmed = df_ref.iloc[matching_eid_loc]

            # find which references to download based on matching of last name + first initial
            count_fa_str=0; count_la_str=0; count_fa_la_str=0; count_any_str=0
            ref_EID_to_download = []  # download these to then check author IDs
            for idx in range(df_ref_trimmed.shape[0]):
                ref_trimmed_str = unidecode.unidecode(str(df_ref_trimmed.iloc[idx]['Authors']).replace('-', ''))  # str() in case it was not string
                # NOTE to self: can probably just do any here, then look at author IDs
                if first_author in ref_trimmed_str and last_author in ref_trimmed_str:
                    count_fa_str+=1; count_la_str+=1; count_fa_la_str+=1; count_any_str+=1
                    ref_EID_to_download.append(df_ref_trimmed.iloc[idx]['EID'])
                elif first_author in ref_trimmed_str and not last_author in ref_trimmed_str:
                    count_fa_str+=1; count_fa_la_str+=1; count_any_str+=1
                    ref_EID_to_download.append(df_ref_trimmed.iloc[idx]['EID'])
                elif not first_author in ref_trimmed_str and last_author in ref_trimmed_str:
                    count_la_str+=1; count_fa_la_str+=1; count_any_str+=1
                    ref_EID_to_download.append(df_ref_trimmed.iloc[idx]['EID'])
                elif any([article_authors_entry in ref_trimmed_str for article_authors_entry in article_authors]):
                    count_any_str+=1
                    ref_EID_to_download.append(df_ref_trimmed.iloc[idx]['EID'])



            # load authors for EIDs
            if len(author_IDs)>0:
                count_fa=0; count_la=0; count_fa_la=0; count_any=0
                EID_matching_fa = []; EID_matching_la = []; EID_matching_fa_la = []; EID_matching_any = []
                for download_EID in ref_EID_to_download:

                    #  for each reference, find author IDs
                    try:
                        ref_ab = AbstractRetrieval(download_EID, view="FULL")
                        ref_author_IDs = [ref_author_entry.auid for ref_author_entry in ref_ab.authors if ref_author_entry.auid is not None]
                    except:
                        ref_author_IDs = []

                    #  for each reference, find author names
                    try:
                        ref_author_names = [ref_author_entry.surname + ', ' + ref_author_entry.given_name.split(' ')[0]for ref_author_entry in ref_ab.authors
                                            if ref_author_entry.surname is not None and ref_author_entry.given_name is not None]
                        ref_author_names = clean_author_str(ref_author_names)
                        ref_author_names = ';;'.join(ref_author_names)
                    except:
                        ref_author_names = ''

                    if len(ref_author_IDs)==0 and ref_author_names=='':  # if no info is available, just default to initials
                        # match on initials (in case where author ID/full names not present)
                        ref_trimmed_str = unidecode.unidecode(str(df_ref_trimmed[df_ref_trimmed.EID==download_EID]['Authors']).replace('-', ''))  # str() in case it was not string
                        print('here now')
                        print(ref_trimmed_str)
                        if first_author in ref_trimmed_str and last_author in ref_trimmed_str:
                            count_fa+=1; count_la+=1; count_fa_la+=1; count_any+=1
                        elif first_author in ref_trimmed_str and not last_author in ref_trimmed_str:
                            count_fa+=1; count_fa_la+=1; count_any+=1
                        elif not first_author in ref_trimmed_str and last_author in ref_trimmed_str:
                            count_la+=1; count_fa_la+=1; count_any+=1
                        elif any([article_authors_entry in ref_trimmed_str for article_authors_entry in article_authors]):
                            count_any+=1

                    else:
                        # match on author IDs or *full* author names (surname + given name) in case of multiple IDs per author
                        if (author_IDs[0] in ref_author_IDs and author_IDs[-1] in ref_author_IDs) or\
                            (author_names[0] in ref_author_names and author_names[-1] in ref_author_names):
                            count_fa+=1; count_la+=1; count_fa_la+=1; count_any+=1
                            EID_matching_fa_la.append(download_EID); EID_matching_fa.append(download_EID)
                            EID_matching_la.append(download_EID); EID_matching_any.append(download_EID)
                        elif author_IDs[0] in ref_author_IDs and not author_IDs[-1] in ref_author_IDs or\
                            (author_names[0] in ref_author_names and not author_names[-1] in ref_author_names):
                            count_fa+=1; count_fa_la+=1; count_any+=1
                            EID_matching_fa_la.append(download_EID); EID_matching_fa.append(download_EID)
                        elif not author_IDs[0] in ref_author_IDs and author_IDs[-1] in ref_author_IDs or\
                            (not author_names[0] in ref_author_names and author_names[-1] in ref_author_names):
                            count_la+=1; count_fa_la+=1; count_any+=1
                            EID_matching_fa_la.append(download_EID); EID_matching_la.append(download_EID)
                        elif any([author_ID_entry in ref_author_IDs for author_ID_entry in author_IDs]) or\
                            any([author_names_entry in ref_author_names for author_names_entry in author_names]):
                            count_any+=1
                            EID_matching_any.append(download_EID)

            else:
                count_fa = 'No IDs'; count_la = 'No IDs'
                count_fa_la = 'No IDs'; count_any = 'No IDs'
                EID_matching_fa_la.append('No IDs'); EID_matching_fa.append('No IDs')
                EID_matching_la.append('No IDs'); EID_matching_any.append('No IDs')


        except:
            # if failure above
            count_fa = 'Error'; count_la = 'Error'
            count_fa_la = 'Error'; count_any = 'Error'
            EID_matching_fa_la = 'Error'; EID_matching_fa = 'Error'
            EID_matching_la = 'Error'; EID_matching_any = 'Error'

            count_fa_str='Error'; count_la_str='Error'
            count_fa_la_str='Error'; count_any_str='Error'

            ref_count = 'Error'


        numref.append(ref_count)
        fa.append(count_fa); la.append(count_la)
        fa_la.append(count_fa_la); any_author.append(count_any)
        fa_EIDs.append(';'.join(EID_matching_fa)); la_EIDs.append(';'.join(EID_matching_la))
        fa_la_EIDs.append(';'.join(EID_matching_fa_la)); any_EIDs.append(';'.join(EID_matching_any))

        fa_str.append(count_fa_str)
        la_str.append(count_la_str)
        fa_la_str.append(count_fa_la_str)
        any_str.append(count_any_str)

    # Save results
    print(len(numref))
    print(len(fa))
    df_journal['numref'] = numref

    df_journal['fa'] = fa; df_journal['la'] = la
    df_journal['fa_la'] = fa_la; df_journal['any'] = any_author

    df_journal['fa_str'] = fa_str; df_journal['la_str'] = la_str
    df_journal['fa_la_str'] = fa_la_str; df_journal['any_str'] = any_str

    df_journal['fa_EIDs'] = fa_EIDs; df_journal['la_EIDs'] = la_EIDs
    df_journal['fa_la_EIDs'] = fa_la_EIDs; df_journal['any_EIDs'] = any_EIDs
    print('saving')
    df_journal.to_excel('../' + journal_name + '/results_' + journal_name + str(year) + '.xlsx')
