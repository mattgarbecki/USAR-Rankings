# USAR-Rankings
This repository will be used to test various rankings systems for the USA Roundnet Rankings committee.


## Initial Setup

To use this code base, start by installing conda onto your computer. This can be located here:
https://www.anaconda.com/products/individual

Then, navigate to the terminal on Mac (for windows instructions we can expand later) and follow the following steps:

1. Navigate to the folder you would like these files to be in using the cd command.
2. Run "conda create --name rankings_env python==3.9
3. Run "conda activate rankings_env"
4. Run "pip install -r requirements.txt"

Now, you should be all set to run the python code!

To download the github code, stay in the folder whre you want everything to be and run the following commands:

1. git clone https://github.com/mattgarbecki/USAR-Rankings.git

Everything should now be setup!

## Running the files

To run the actual python files, there are two options:

1. Download an IDE that can be used to code. You can go here if you would like this option to download visual studio code: https://code.visualstudio.com/download
2. Run from terminal. To run the files from the terminal, first navigate to where the files are sitting in the terminal. Then, run this command "python ./runner.py"

## Changing the configurations

To change any configurations used in the runner, navigate to the config.yaml file and change anything you would like and then rerun the runner.py file.
