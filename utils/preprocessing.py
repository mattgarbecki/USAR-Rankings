#importing necessary modules
import pandas as pd
import numpy as np
import os
import glob
from fuzzywuzzy import process, fuzz
from copy import deepcopy
from utils.constants import *

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
    print("Detecting any spelling errors")
    df = fix_misspelled_columns(df, cfg)

    #saving the preprocessed dataframe
    df.to_csv(f"{cfg['preprocessed_data_path']}preprocessed_tourney_results.csv", header=True, index=False)
    
    return df

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

    #fixing all text columns
    str_cols_to_check = [tournament, division, first_team, first_team_first_player]
    for cur_column_name in str_cols_to_check:

        if cur_column_name in [first_team, second_team]:
            cur_column_name = [first_team, second_team]
        elif cur_column_name in [first_team_first_player, first_team_second_player, second_team_first_player, second_team_second_player]:
            cur_column_name = [first_team_first_player, first_team_second_player, second_team_first_player, second_team_second_player]

        print(f"\n\nChecking {cur_column_name} for spelling errors")

        #Create tuples of names, similar names, and scores of how similar they are
        if isinstance(cur_column_name, list):
            #if thiis is alist of multiple columns, combine them to spell check
            all_cols = []
            for col in cur_column_name:
                all_cols.append(pd.DataFrame(df[col].dropna().unique()))
            cur_col = pd.concat(all_cols, axis=0)
            cur_col = cur_col.iloc[:,0].dropna().unique() #getting only unique names
        else:
            cur_col = df[cur_column_name].dropna().unique()
        score_sort = [(x,) + i
                    for x in cur_col 
                    for i in process.extract(x, cur_col,     scorer=fuzz.token_sort_ratio)]

        #Create a dataframe from the tuples
        similarity_sort = pd.DataFrame(score_sort, columns=['original_name','close_name','score'])

        #adding counts of how many times each name appears originally
        name_appearance = pd.DataFrame(cur_col).value_counts().rename_axis('unique_values').reset_index(name='counts')
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

        if high_score_sort.shape[0] == 0:
            print("No spelling mistakes detected, moving on to the next column if applicable")
            continue
        
        #removing duplicate rows that have reversed names
        high_score_sort['check_string'] = high_score_sort.apply(lambda row: ''.join(sorted([row['most_frequent_name'], row['matched_name']])), axis=1)
        high_score_sort = high_score_sort.drop_duplicates('check_string')

        #printing the results
        print("Original Name\tProposed Mispelling\tConfidence Score")
        for i, row in high_score_sort.iterrows():
            print(row["most_frequent_name"], "\t", row["matched_name"], "\t", row["score"])
        
        #getting user input on what confidence level to cut this off at
        confidence_thresh = input(("Please provide a threshold of confidence for misspellings."
                                    " All proposed name / misspelling combinations at or above"
                                    " this number will be used to clean the data:\n\t"))
        while True:
            try:
                confidence_thresh = int(confidence_thresh)
                if confidence_thresh >= 0 and confidence_thresh <= 100:
                    break
                else:
                    confidence_thresh = input("Provided input is not between 0 and 100. Please provide a decimal between 0 and 1\n\t")
            except:
                confidence_thresh = input("Provided input is not a number. Please provide a decimal between 0 and 100\n\t")
            
        #removing entries below the user defined cutoff
        high_score_sort = high_score_sort[high_score_sort["score"] >= confidence_thresh].drop_duplicates()

        #converting the dataframe to a dictionary to use to clean the data
        spell_check_mapping = dict()
        for i, row in high_score_sort.iterrows():
            if row["most_frequent_name"] in spell_check_mapping:
                spell_check_mapping[row["most_frequent_name"]].append(row["matched_name"])
            else:
                spell_check_mapping[row["most_frequent_name"]] = [row["matched_name"]]

        #entering interactive mode if desired
        if cfg["interactive_spelling_correction"] is True:

            #gathering user input on the reverse dictionary
            while True:
                final_spell_mapping = dict() #creating a final dict to store the correct spellings
                for key, value in spell_check_mapping.items():
                    print("\nThe correctly spelled name is:\t", key)
                    print("The proposed misspellings are:\t", value)
                    correct_map = input("Is this correct? (y/n):\t")
                    while True:
                        #if its already correct, save it
                        if correct_map == "y":
                            if key in final_spell_mapping:
                                final_spell_mapping[key].extend(value)
                            else:
                                final_spell_mapping[key] = value
                            break
                        elif correct_map == "n":
                            #fix the issues if it isnt correct
                            potential_spellings = deepcopy(value)
                            potential_spellings.append(key)
                            #allow the user to specify which is the correct spelling and which are typos 
                            correct_spelling = input(("Which of the spellings are correct from the following"
                                                    " (enter 'different names' if they are not the same person)"
                                                    f":\n{potential_spellings}\n\n\t"))
                            while True:
                                if correct_spelling in potential_spellings:
                                    all_mispellings = deepcopy(potential_spellings)
                                    all_mispellings.remove(correct_spelling)
                                    if correct_spelling in final_spell_mapping:
                                        print("Found previous entry of this name. Appended new misspellings to it")
                                        for x in all_mispellings:
                                            #making sure this misspelling isnt already there
                                            if x not in final_spell_mapping[correct_spelling]:
                                                final_spell_mapping[correct_spelling].extend(all_mispellings)
                                    else:
                                        final_spell_mapping[correct_spelling] = all_mispellings
                                    break
                                elif correct_spelling == "different names":
                                    #not saving to correction dictionary
                                    break
                                else:
                                    correct_spelling = input((f"Please provide a valid spelling from"
                                                            " the proposed list or type 'different names'"
                                                            f":\n{potential_spellings}\n\n\t"))  
                            break              
                        else:
                            correct_map = input("Please provide either 'y' or 'n' to indicate if this is correct\t")

                #stopping interactive mode if user approves of the mapping
                #redoing it otherwise
                print(f"Finished interactive mode with the following correct names and their misspellings:\n{final_spell_mapping}")
                finished_loop = input("Are these spelling mistakes correct (y/n)?:\t")
                while True:
                    if finished_loop == "y" or finished_loop == "n":
                        break
                    else:
                        finished_loop = input("please provide either 'y' or 'n' to indicate if the spellings are correct:\t")
                if finished_loop == "y":
                    break
        else:
            final_spell_mapping = spell_check_mapping

        #fixing the spelling mistakes in the dataframe
        #inverting the dictionary so we can look up typos to find correct spellings
        typo_dict = {}
        for k,v in final_spell_mapping.items():
            for x in v:
                typo_dict.setdefault(x,[]).append(k)

        #using the typo dict to fix our dataframe
        if isinstance(cur_column_name, list):
            for col in cur_column_name:
                df.replace({col: typo_dict}, inplace=True)
        else:
            df.replace({cur_column_name: typo_dict}, inplace=True)

    return df
    

