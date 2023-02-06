# Requirements:
#   see get_eids.py
import unidecode

def clean_author_str(authors):

    if isinstance(authors, str):
        author_list = authors.split('.,')
    elif isinstance(authors, list):
        author_list = authors

    author_list = [unidecode.unidecode(author_entry).replace('-', ' ') for author_entry in author_list]

    # deal with II, III, IV
    for author_index, authname in enumerate(author_list):
      if len(authname.split(' '))>2:
        author_list[author_index] = authname.replace(' III,', ',').replace(' IV,', ',').replace(' II,', ',')

    author_list = [author_list_entry.strip() + '.' for author_list_entry in author_list]  # add in period after initial

    if isinstance(authors, str):  # only if Surname, Initial format
        author_list[-1]=author_list[-1][:-1]  # remove extra period from final author

    # remove consortia
    author_list = [s for s in author_list if "consortium" not in s.lower()
      and "initiative" not in s.lower() and "investigators" not in s.lower()
      and "group" not in s.lower() and "network" not in s.lower()
      and "center" not in s.lower() and "psych" not in s.lower()
      and "GEMRIC" not in s and 'Million Veteran Program' not in s
      and 'Pediatric Imaging' not in s and 'Neurocognition' not in s
      and 'schizophrenia' not in s.lower() and 'research team' not in s.lower()
      and 'ADNI and PPMI' not in s and 'Council' not in s
      and 'Collaborator' not in s and 'DDD study' not in s
      and 'NBB-Psy' not in s and 'VA Cooperative Studies Program Study Team' not in s
      and 'Collaborative Members' not in s and 'University' not in s
      and 'Imaging' not in s and 'Biomarkers' not in s]

    # get first initial only
    author_list = [article_author_entry[:article_author_entry.find('.')] for article_author_entry in author_list]

    return author_list

