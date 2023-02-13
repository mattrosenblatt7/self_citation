# Set up a python 3 environment

* Set up a python 3 environment. Note: this code was primarily tested with Python 3.8 but should work with other versions
* Install the following packages:
  * numpy: conda install numpy
  * pandas: conda install pandas
  * matplotlib: conda install matplotlib
  * seaborn: conda install seaborn
  * tqdm: conda install tqdm
  * unidecode: conda install unidecode
  * pybliometrics
    * this package is more easily installed with pip. 
    * If you are using conda, we suggest first doing "conda install pip" and then "pip install pybliometrics"
 
# Self-citation code to evaluate your own self-citation rate

Please email matthew.rosenblatt@yale.edu if you have trouble running this or do not have institutional access. We can help you run the code and/or run it for you and share your self-citation trends.

## Getting Scopus data
* Connect to your institution's VPN
* Go to scopus.com
* Search within authors (e.g., Scheinost, D)
* Click the appropriate result
* On the next screen, record the ID of the author (below, boxed in red). You will later input this to the python script

![search_results](/imgs/scheinost_scopus.png)
* Generate API keys
* Go to https://dev.elsevier.com/
* Click "I want an API key"
* Generate up to 10 keys
* You will enter these into python code
 

## Running the python code
* Important: you must be connected to your institution's VPN to run the code
* cd to a directory containing the attached .py file
* Run python script
* Arguments:
  * --ID: Scopus ID of author
  * allow_initial: [0, 1], whether to allow for less exact matching using "Surname, First Initial". 
    * This helps reduce the amount of missing data, but is NOT recommended for very a common "Surname, First Initial"
  * make_plots: [0, 1], whether to generate the plots
```
python self_citation_author.py --ID 25628822400 --allow_initial 1 --make_plots 1
```

## Outputs
The above code will print the following to the terminal after succesfully running:

![terminal](/imgs/terminal_output.png)

Other outputs include:
* './results/results_df_' + scopus_indexed_name + '.csv'
  * This includes an entry for each of the author's articles with the following notable columns:
    * sc_count: number of self-citations for author of interest
    * sc_count_any: number of Any Author self-citation
    * numref: number of references
    * sc_rate: sc_count / numref
    * sc_rate_any: sc_count_any / numref
    * missing_ref_count: number of references we could not get data for. Ensure that this number is not too high
    
* './results/' + scopus_indexed_name + '_single_author_hist.png'
  * This shows a histogram of self-citation rates across all papers for the author of interest

![single_hist](/results/single_hist.png)

* './results/' + scopus_indexed_name + '_any_author_hist.png'
  * This shows the Any Author self-citation rates for all the author of interest's papers

![any_hist](/results/any_hist.png)  
  
* './results/' + scopus_indexed_name + '_single_author_time.png'
  * This plots the author of interest's self-citation rate by year
 
![single_year](/results/single_time.png)

# Analysis of raw data for figures presented in paper

See raw_data_analysis folder and instructions inside.

# Analysis of model data for table presented in paper

See model_data_analysis folder and instructions inside. 
