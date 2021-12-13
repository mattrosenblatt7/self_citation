# Requirements:
#   installed pybliometrics (see https://pybliometrics.readthedocs.io/en/stable/)
#   API key (see above ref)
#   must be connected to VPN associated with the Scopus account (e.g., Yale)
#   https://github.com/pybliometrics-dev/pybliometrics/issues/191
#def main():
from pybliometrics.scopus import AbstractRetrieval
import pandas as pd
from tqdm import tqdm
import time

df_journal = pd.read_csv ('./bp_2020_temp.csv')
df_journal = df_journal[df_journal['Authors'] != '[No author name available]']  # remove entried w missing authors
eids= list(df_journal['EID'])

# this one is good test: 2-s2.0-85085763458
# this one from mol psych was bad with other method: 2-s2.0-0033949096
# this one is missing author 2-s2.0-0004235298
fa_all = []
la_all = []
fa_la_all = []
any_all = []
nref_all = []
print(len(eids))
for this_eid in eids:
    print('\n***** Evaluating Manuscript eid: ' + this_eid + ' *****\n')
    ab = AbstractRetrieval(this_eid, view="FULL")
    print(ab)
    try:
        refs = ab.references
        n_authors=len(ab.authors)
        n_refs=len(refs)
        author_ids = [author.auid for author in ab.authors]
        nref_all.append(n_refs)

        # Check obtained references match num refs on record
        #if n_refs != ab.refcount:
        #    print("Inaccurate scraped reference list for eid " + this_eid)


        # Check whether any references have empty author list
        fa_count = 0
        la_count = 0
        fa_la_count = 0
        any_count = 0
        
            except:
                print('')
    except:
        print('load exception, NaN marked')
        fa_count = float("NaN")
        la_count = float("NaN")
        fa_la_count = float("NaN")
        any_count = float("NaN")

    fa_all.append(fa_count)
    la_all.append(la_count)
    fa_la_all.append(fa_la_count)
    any_all.append(any_count)

df_journal['numref'] = nref_all
df_journal['fa'] = fa_all
df_journal['la'] = la_all
df_journal['fa_la'] = fa_la_all
df_journal['any'] = any_all
df_journal.to_csv("./bp_2020_results.csv")
    # # Go through all authors and check whether they have matches in each reference's authors list
    # for i in range(0,n_authors):
    #     #this_name=[ab.authors[i].given_name,ab.authors[i].surname]
    #     this_name_refstyle=ab.authors[i].surname + ", " + ab.authors[i].given_name[0]
    #
    #     match_list=dict()
    #     #match_list_name=[]
    #     for j in range(0,n_refs):
    #         #  for each reference, record indices of all occurrences of matches
    #         this_reflist=refs[j].authors
    #
    #         #if len(this_reflist)==0:
    #             #match_list[j]="EMPTY REFLIST - must check"
    #         #else:
    #
    #         if len(this_reflist)!=0: # if not empty
    #             match_ids = [k for k in range(len(this_reflist)) if this_reflist.startswith(this_name_refstyle, k)]
    #
    #             if len(match_ids)!=0:
    #                 for k in range(0,len(match_ids)):
    #                     this_match=this_reflist[match_ids[k]:]
    #                     this_match=this_match.split()
    #                     this_match=this_match[0] + " " + this_match[1]
    #                     match_list[j]=this_match
    #                     #match_list_name.append(this_match2)
    #
    #     print(match_list)



# another option for counting w/o indexing:
# refs[j].authors.count(this_name[1])
                 




