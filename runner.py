import yaml
from utils.preprocessing import preprocess_tournament_results

#reading in our configurations
with open("./configs/config.yaml", 'r') as stream:
    try:
        cfg=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

#preprocessing our tournament data
df = preprocess_tournament_results(cfg["preprocessing"])

#placeholder for an actual rankings model

#printing message to specify that we finished
print("Completed the workflow")