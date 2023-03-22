import json
import glob
import os


# reading newest file with links in a links folder
def read_newest_links():
    list_of_files = glob.glob("links/*.txt")
    newes_file_name = max(list_of_files, key=os.path.getctime)
    with open(newes_file_name, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    return links


# handling offers stored in preliminary file
def read_newest_offers():
    list_of_files = glob.glob("offers/*.json")
    latest_file = max(list_of_files, key=os.path.getctime)
    with open(latest_file) as json_file:
        offers = json.load(json_file)
    return offers
