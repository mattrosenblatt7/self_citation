'''
Use this code to model the data with logistic regression
Arguments include:
--transform [0, 1], whether or not to apply inverse hyperbolic sin transform (as in paper)
--y [pairs, extreme], whether to model self-citation pairs or highly self-citing articles
--auth [fa, la, all], whether to use first authors, last authors, or both first and last authors (default)
'''
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from tqdm import tqdm
import argparse

# add arguments
parser = argparse.ArgumentParser()
parser.add_argument("--transform", type=int, default=1, help="whether to transform data", choices=[0, 1])
parser.add_argument("--y", type=str, default='pairs', help="y term in model", choices=['pairs', 'extreme'])
parser.add_argument("--auth", type=str, default='all', help="y term in model", choices=['fa', 'la', 'all'])


# parse arguments
args = parser.parse_args()
transform = args.transform
y = args.y
auth_type = args.auth


# read in data
df = pd.read_csv('./data/citation_pairs.csv')
print(df.head())
df['time_lag'] = df['year_citing'] - df['year_cited']  # time lag between cited/citing
df = df[ (df.time_lag>=0) & (df.time_lag<=150) ]    # remove potentially incorrect time lags
df = df[ (df.academic_age>=0) & (df.academic_age<=90) ]  # remove potentially incorrect academic ages
print(len(df))
df = df.drop(columns='num_auth_cited')  # column no longer needed

# apply some filters and change years
if y=='extreme':  # before transform, include only articles with 30+ refs for extreme self-citation case
    df = df[df.num_ref_citing>=30]
df['year_citing'] = df['year_citing'] - 2000  # adjust years to be 0-20


# default is all authors. if included in argument, filter to just first or last
if auth_type=='fa':
    df = df[df.auth_type=='fa']
elif auth_type=='la':
    df = df[df.auth_type=='la']

   
print(df.keys())
# ******** Model for citing/cited pairs ********
if y=='pairs':  # citing/cited pairs model
    df_mdl = df[df.num_auth_citing!=1]
    if transform==1:  # transform continuous vars
        for k in ['num_auth_citing', 'num_ref_citing', 'num_prev_papers', 'time_lag', 'academic_age']:
            df_mdl[k]= np.arcsinh(df_mdl[k])
    
    # can change formula as necessary
    formula = 'sc ~ document_type + year_citing + time_lag + num_auth_citing + num_ref_citing + academic_age + num_prev_papers + field + C(affil_continent, Treatment(reference="Asia")) + gender + auth_type + year_citing:auth_type + gender:academic_age'   #  + gender:academic_age

    # fit model
    model = smf.logit(formula = formula, data=df_mdl, missing='drop')
    model_fit = model.fit(disp=1)
    p_val_df = pd.DataFrame()
    coef_df = pd.DataFrame(model_fit.params)

# ******** Model for highly self-citing articles ********
elif y=='extreme':  # highly self-citing model
    
    # group dataframe by paper (was previously grouped as each citing/cited pair)
    df_summary = df.groupby(['Article_num', 'auth_type'], as_index=False).agg({'sc':'sum'})
    df_summary = df_summary.rename(columns={'sc':'sc_total'})
    df = pd.merge(df_summary, df.drop_duplicates(subset=['Article_num', 'auth_type']),  how='left', left_on=['Article_num', 'auth_type'], right_on = ['Article_num', 'auth_type'])
    print(len(df))
    
    # calculate self-citation rate and highly self-citing articles
    df['sc_rate'] = df.sc_total / df.num_ref_citing
    extreme_thresh = 0.25  # threshold of 25% self-citation rate or greater
    df['highly_citing'] = 1.0*(df.sc_rate>=extreme_thresh)
    df.loc[ ((df.sc_rate>.15)&(df.sc_rate<extreme_thresh)), 'highly_citing'] = np.nan
    
    print(df.groupby(['gender'])['highly_citing'].value_counts())
    
    df_mdl = df[df.num_auth_citing!=1]
    if transform==1:  # transform continuous vars
        for k in ['num_auth_citing', 'num_ref_citing', 'num_prev_papers', 'time_lag', 'academic_age']:  
            df_mdl[k]= np.arcsinh(df_mdl[k])
    
    # can change formula as necessary
    formula = 'highly_citing ~ document_type + year_citing +  + num_auth_citing + num_ref_citing + academic_age + num_prev_papers + field + C(affil_continent, Treatment(reference="Asia")) + gender + auth_type + year_citing:auth_type + gender:academic_age'  # + gender:academic_age 
    
    # fit model
    model = smf.logit(formula = formula, data=df_mdl, missing='drop')
    model_fit = model.fit(disp=1)
    p_val_df = pd.DataFrame()
    coef_df = pd.DataFrame(model_fit.params)
 

# print model fit
print(formula)
print(model_fit.summary())
print(model_fit.pvalues)
print(model_fit.tvalues)
print(model_fit.bse)

# save dataframe
data = {'coef': model_fit.params,
        'odds':np.exp(model_fit.params),
        'std err': model_fit.bse,
        't': model_fit.tvalues,
        'P>|t|': model_fit.pvalues,
        '[0.025': model_fit.conf_int()[0],
        '0.975]': model_fit.conf_int()[1]}
full_df = pd.DataFrame(data)

# set save name 
if 'gender:academic_age' in formula:
    fname = formula.split('~')[0] + '_with_interaction.csv'
else:
    fname = formula.split('~')[0] + '_no_interaction.csv'

full_df.to_csv('./data/model_results/' + fname)


