# Welcome to YEP (Your European Parliament), a project meant to vulgarize the legislative texts the Members of European Parliaments work on.

### To see the project’s final form, visit my website : https://neliabouzid.github.io/your_european_parliament/

### To read more about the project, visit the “About” section of my website : https://neliabouzid.github.io/your_european_parliament/about.html

### The following information is aimed at reproducing and understanding the Notebooks (which can be found in the folder Notebooks 2025) and the CSVs (which can be found in the folder CSVs 2025), as well as all other files that can be found in this repository:

# 1. Instructions for replicating results

To reproduce the results, it is important to execute the notebooks in the order indicated in their titles. Before running them, you must carefully read notebooks 9 and 10, which I have already executed on Kaggle, as they use an LLM for generation. There are a few specific manipulations to follow:
- Correctly upload the input CSV files into Kaggle.
- Since summary generation is time-consuming, Notebook 9 was executed in several sessions to annotate a few rows of my CSV. The steps to execute the notebook in multiple passes are detailed within it.

Once the notebooks are executed, you must create a database with PostgreSQL and import the procedures_2025.csv data, then link it with Flask in the app.py file, which creates the website. If you run app.py in the terminal (by launching the flask run command), you can open the site locally. For publication, I made the site completely static using the freeze_website.py file (making it static makes it free to publish with Github, as there is no need to use Render).

# 2. Which file corresponds to what?

docs folder: includes the files used by Github to publish my site. static folder: includes the files for the styling of my site (js, css, images). templates folder: contains the code for the html pages of my site.

Notebooks (the listed items under the Notebooks' explanations indicate which CSVs are produced by the execution of the Notebook):

1_url_scraper: scrapes the URLs of the legislative procedures listed in the Legislative Observatory
- list_urls_2025.csv

2_scraper: scrapes the information directly available on a page describing an ordinary legislative procedure.
- urls_not_found_2025.csv
- urls_no_title_2025.csv
- urls_missing_title_span_2025.csv
- final_scrape_2025.csv

3_data_manip_technical_info: data manipulation on the 'technical_info' column to extract data and store it in new variables.
- final_sample_cod_manip_2025.csv

4_legislative_proposal_scraper: scrapes the texts of the legislative proposals.
- lp_url_not_found_2025.csv
- final_sample_cod_legislative_scrape_2025.csv

5_lp_scraped_verifier: identifies which procedures did not allow the text of the legislative proposal to be scraped.

6_text_adopted_scraper: scrapes the adopted texts of completed procedures.
- final_sample_cod_TA_2025.csv

7_final_act_scraper: scrapes the final acts of completed procedures.
- final_sample_cod_TA_final_act_2025.csv

8_splitting_datasets: separates the database into 4 databases, each grouping procedures belonging to one of these categories: completed procedures, rejected procedures, ongoing procedures, lapsed or withdrawn procedures.
- sample_cod_completed_2025.csv
- sample_cod_rejected_2025.csv
- sample_cod_lapsed_2025.csv
- sample_cod_ongoing_2025.csv

9_summarization_proposals: summarizes several legislative proposals from April to December 2025.
- cod_completed_proposal_general_summary_0_5.csv
- cod_completed_proposal_general_summary_5_10.csv
- cod_completed_proposal_general_summary_10_15.csv
- cod_completed_proposal_general_summary_15_17.csv
- cod_proposal_general_summary_0_5.csv
- cod_proposal_general_summary_5_10.csv
- cod_proposal_general_summary_10_20.csv
- cod_completed_proposal_general_summary_20_25.csv

10_summarization_final_acts: summarizes the final acts adopted by the European Parliament in 2025.
- cod_final_act_general_summary.csv

11_final_manipulation_for_sql: aggregates ongoing and completed procedures and cleans them for import into PostgreSQL.
- completed_proc_clean_2025.csv
- ongoing_proc_clean_2025.csv
- procedures_2025.csv

