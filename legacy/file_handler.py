import json
import glob
import os


# reading newest file with links in a links folder
def read_newest_links(path: str):
    list_of_files = glob.glob(path)
    newest_file_name = max(list_of_files, key=os.path.getctime)
    with open(newest_file_name, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    return newest_file_name, links


# handling offers stored in preliminary file
def read_newest_offers(path):
    list_of_files = glob.glob(path)
    latest_file = max(list_of_files, key=os.path.getctime)
    with open(latest_file) as json_file:
        offers = json.load(json_file)
    return latest_file, offers
