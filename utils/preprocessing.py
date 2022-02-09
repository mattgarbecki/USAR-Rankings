#importing necessary modules
from calendar import c
import pandas as pd
import numpy as np
import os
import glob
from fuzzywuzzy import process, fuzz
from utils.constants import *


#functinon to read in all the data to memory
def read_data(cfg):
    
    # loop over the list of csv files
    all_dfs = []
    csv_files = glob.glob(os.path.join(cfg["input_path"], f"*.{cfg['input_file_type']}"))
    for f in csv_files:
        
        # read the csv file
        new_df = pd.read_csv(f)
        all_dfs.append(new_df)

    #combine the dataframes together
    df = pd.concat(all_dfs)

    return df

#function to fix any misspellings detected in the dataset
def fix_misspelled_columns(df, cfg):

    cur_column_name = first_team_first_player

    #Create tuples of names, similar names, and scores of how similar they are
    cur_col = df[cur_column_name].dropna().unique()
    score_sort = [(x,) + i
                for x in cur_col 
                for i in process.extract(x, cur_col,     scorer=fuzz.token_sort_ratio)]

    #Create a dataframe from the tuples
    print("continuing now that thats done lol")
    similarity_sort = pd.DataFrame(score_sort, columns=['original_name','close_name','score'])

    #adding counts of how many times each name appears originally
    name_appearance = df[cur_column_name].value_counts().reset_index()
    name_appearance.columns = ["name", "count"]

    #left joining this into our similarity dataframe
    similarity_sort = pd.merge(similarity_sort, name_appearance.rename({"count":"orig_count"}, axis=1), \
                    left_on="original_name", right_on="name", how="left")
    similarity_sort = pd.merge(similarity_sort, name_appearance.rename({"count":"matched_count"}, axis=1), \
                    left_on="close_name", right_on="name", how="left").drop(columns=["name_x", "name_y"])

    #setting the default name to that which occurs more often, and the misspelling to the less often name
    similarity_sort["most_frequent_name"] = similarity_sort.apply(lambda x: \
                                    x["original_name"] if x["orig_count"] >= x["matched_count"] else\
                                         x["close_name"], axis=1)
    similarity_sort["matched_name"] = similarity_sort.apply(lambda x: \
                                    x["original_name"] if x["most_frequent_name"] == x["close_name"] else\
                                         x["close_name"], axis=1)
    similarity_sort = similarity_sort[["most_frequent_name", "matched_name", "score"]]

    #keeping the values above a minimum match threshold and removing rows that are the same two names
    high_score_sort = \
    similarity_sort[(similarity_sort['score'] >= cfg["minimum_misspelling_confidence"]) &
                    (similarity_sort['most_frequent_name'] != similarity_sort['matched_name'])]
    high_score_sort = high_score_sort.sort_values(by="score", ascending=False)

    #printing the results
    print("Original Name\tProposed Mispelling\tConfidence Score")
    for i, row in high_score_sort.iterrows():
        print(row["most_frequent_name"], "\t", row["matched_name"], "\t", row["score"])
    
    #getting user input on what confidence level to cut this off at
    confidence_thresh = input("""Please provide a threshold of confidence for misspellings. \
                                 All proposed name / misspelling combinations at or above \
                                 this numner will be used to clean the data:\n\t""")
    while True:
        try:
            confidence_thresh = int(confidence_thresh)
            if confidence_thresh >= 0 and confidence_thresh <= 100:
                break
            else:
                confidence_thresh = input("Provided input is not between 0 and 1. Please provide a decimal between 0 and 1\n\t")
        except:
            confidence_thresh = input("Provided input is not a decimal number. Please provide a decimal between 0 and 1\n\t")
        
    #removing entries below the user defined cutoff
    high_score_sort = high_score_sort[high_score_sort["score"] >= confidence_thresh].drop_duplicates()

    #converting the dataframe to a dictionary to use to clean the data
    spell_check_mapping = dict(zip(high_score_sort.most_frequent_name, high_score_sort.matched_name))

    #entering interactive mode if desired
    if cfg["interactive_spelling_correction"] is True:

        #creating an inverse dictionary for the user to edit any mistakes out of

        #gathering user input on the reverse dictionary

        #fixing any mistakes user points out

        #gathering user input to make sure all accepted names are real names

        #fixing any mistakes

        #inversing the dictionary to have a final dictionary used to clean the data with
        pass

    print("at the end of this")
    return None
    

#creating a function to do some initial data preprocessing
def preprocess_tournament_results(cfg):

    #start by reading in the data from the input directory specified in the yaml config file
    print("Reading in data")
    df = read_data(cfg)
    
    #cleaning up the string columns
    #removing traling and leading whitespace from string columns, setting to all lowercase
    str_cols = df.select_dtypes(exclude=[np.number]).columns
    for col in str_cols:
        df[col] = df[col].str.strip().str.lower()

    #removing matches with no specified winner if desired
    if cfg["remove_matches_with_unknown_winners"] is True:
        df = df[(df[first_team_score].notna()) & (df[second_team_score].notna())]

    
    #correcting any spelling mistakes
    print("Correcting any spelling errors")
    fix_misspelled_columns(df, cfg)
    
    #removing matches with no specified winner if desired

    return df