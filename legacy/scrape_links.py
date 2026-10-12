from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
import time
import json
import time
import numpy
import glob
import os
import sqlite3
from sqlite_operations import setup_database, save_offer_to_db


def collect_list_of_links_to_offers(driver, category, n):
    wait = WebDriverWait(driver, 5)  # might be unnecessary wait
    driver.get(n)
    n = 1
    links_list = []
    offers_dictionary = {}
    check = True
    while check:
        time.sleep(1)

        # accept the olx
        try:
            driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            pass
        try:
            wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[1]/div[1]/div[2]/form/div[5]/div/div[2]/div/a",
                    )
                )
            )
        except:
            driver.refresh()

        # //*[@id="mainContent"]/div/div[2]/form/div[6]/div/section[1]/div/ul/a
        # /html/body/div[1]/div[2]/div/div[2]/form/div[6]/div/section[1]/div/ul/a/svg
        # //*[@id="943113386"]/div/div/div[2]/div[1]/a
        elements = driver.find_elements(By.XPATH, "//div/div/div[2]/div[1]/a")

        links = [
            elem.get_dom_attribute("href")
            for elem in elements
            if elem.get_dom_attribute("href").endswith("html")
        ]

        olx_links = [
            "https://www.olx.pl" + link for link in links if link.startswith("/")
        ]
        otodom_links = [
            link for link in links if link.startswith("https://www.otodom.pl")
        ]

        links_list.extend(olx_links)
        links_list.extend(otodom_links)
        try:
            time.sleep(1)
            # check if it's the first site of the search
            # //*[@id="mainContent"]/div/div[3]/form/div[6]/div/section[1]/div/ul/a
            # /html/body/div[1]/div[2]/div/div[3]/form/div[6]/div/section[1]/div/ul/a
            # this is needed as XPATH differs for first site
            if n == 1:
                try:
                    # driver.find_element(
                    #     By.XPATH,
                    #     f"/html/body/div[1]/div[2]/div/div[3]/form/div[6]/div/section[1]/div/ul/a/svg",
                    # ).click()
                    pagination_forward_button = driver.find_element(
                        By.CSS_SELECTOR, '[data-cy="pagination-forward"]'
                    )
                    pagination_forward_button.click()
                except:
                    try:
                        wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "/html/body/div[1]/div[1]/div[2]/form/div[5]/div/section[1]/div/ul/a",
                                )
                            )
                        ).click()
                    except TimeoutException:
                        driver.find_element(
                            By.XPATH,
                            f"/html/body/div[1]/div[1]/div[2]/form/div[5]/div/section[1]/div/ul/a",
                        ).click()
            else:
                try:
                    pagination_forward_button = driver.find_element(
                        By.CSS_SELECTOR, '[data-cy="pagination-forward"]'
                    )
                    pagination_forward_button.click()
                    # driver.find_element(
                    #     By.XPATH,
                    #     f"/html/body/div[1]/div[1]/div[2]/form/div[5]/div/section[1]/div/ul/a[2]",
                    # ).click()
                except:
                    try:
                        wait.until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "/html/body/div[1]/div[1]/div[2]/form/div[5]/div/section[1]/div/ul/a[2]",
                                )
                            )
                        ).click()
                    except TimeoutException:
                        driver.find_element(
                            By.XPATH,
                            f"/html/body/div[1]/div[1]/div[2]/form/div[5]/div/section[1]/div/ul/a[2]",
                        ).click()
            n = n + 1
        except NoSuchElementException:
            check = False

        links.clear()
        elements.clear()

    for i in links_list:
        if i not in offers_dictionary.keys():
            offers_dictionary[i] = {"size_category": category}

    return links_list, offers_dictionary


def get_links(driver, n):
    links_dictionary = {}
    unique_links_list = []
    links_list = []

    # filters names for every square footage category
    filters_names = [
        "-25",
        "25-40",
        "40-50",
        "50-60",
        "60-70",
        "70-80",
        "80-100",
        "100-120",
        "120-150",
        "150-",
    ]

    links_filter = [
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:to%5D=25",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=25&search%5Bfilter_float_m:to%5D=40",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=40&search%5Bfilter_float_m:to%5D=50",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=50&search%5Bfilter_float_m:to%5D=60",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=60&search%5Bfilter_float_m:to%5D=70",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=70&search%5Bfilter_float_m:to%5D=80",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=80&search%5Bfilter_float_m:to%5D=100",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=100&search%5Bfilter_float_m:to%5D=120",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=120&search%5Bfilter_float_m:to%5D=150",
        "?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_m:from%5D=150",
    ]

    # by using dictionary here we will only override the keys and category with the same key
    # this means more writes but
    for i in range(len(links_filter)):
        links_list_part_i, links_dict_part_i = collect_list_of_links_to_offers(
            driver, f"{filters_names[i]}", f"{n}{links_filter[i]}"
        )
        links_list.extend(links_list_part_i)
        links_dictionary.update(links_dict_part_i)

    unique_links_list = numpy.unique(links_list)

    return unique_links_list, links_dictionary


def main():
    # start measuring time
    start_time = time.time()
    t = time.localtime()
    str_t = time.strftime("%Y%m%d%H%M", t)

    # instantiate a driver
    driver = webdriver.Chrome()
    links_list, links_dict = get_links(
        driver, "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/warszawa/"
    )

    # check if the number of keys in dict is equal the length of a list
    if len(links_list) == len(links_dict.keys()):
        print("Success!")
    else:
        print(
            f"Something went wrong! Length of list is: {len(links_list)} and length of dict is: {len(links_dict.keys())}"
        )

    # Ensure the directories exists
    os.makedirs("links", exist_ok=True)
    os.makedirs("offers", exist_ok=True)

    # Construct the file path
    links_path = f".\links\links_{str_t}.txt"
    # Construct the file path
    offers_path = f".\offers\offers_{str_t}.json"

    with open(f"{links_path}", "w+", encoding="utf-8") as l:
        for a in links_list:
            l.write(f"{a}\n")

    with open(f"{offers_path}", "w+", encoding="utf-8") as d:
        json.dump(links_dict, d, indent=4)

    # get time elapsed
    print("--- %s seconds ---" % (time.time() - start_time))


def get_newest_json(folder_path):
    json_files = glob.glob(os.path.join(folder_path, "*.json"))

    if not json_files:
        raise FileNotFoundError("No JSON files found in the specified folder.")

    newest_file = max(json_files, key=os.path.getmtime)

    return newest_file


def save_to_db(file_path):
    with open(file_path, "r") as json_file:
        data = json.load(json_file)  # Load JSON data into a Python dictionary
        save_offer_to_db(data)


if __name__ == "__main__":
    main()
    folder_path = f".\offers"
    try:
        newest_json = get_newest_json(folder_path)
        print(f"Newest JSON file: {newest_json}")
        # setup_database()
        # save_to_db(newest_json)
    except FileNotFoundError as e:
        print(e)
