### A threaded scraper
### This script will scrape a list of websites

import glob
import os
import time
import json
import file_handler
import sqlite3
from multiprocessing import Process, Queue, JoinableQueue, Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from sqlite_operations import setup_database, save_offer_to_db
import traceback
import sys

# TODO: completeness of data measure

unknown = {
    "offer_id": "Unknown",
    "category": "Unknown",
    "website": "Unknown",
    "price": "Unknown",
    "offer_title": "Unknown",
    "location": "Unknown",
    "active": "No",
}


def try_find_element(driver, xpath, not_found_message):
    # find single element using xpath
    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        element = driver.find_element(By.XPATH, xpath).text
        return element
    except NoSuchElementException:
        return not_found_message
    except Exception as e:
        print(f"Logging to exception at 47: {e}")
        return f"Unknown exception at {xpath}"


def find_404(driver):
    # find if the url is working
    f404 = driver.title
    if ("404" in f404) or ("Ups, mamy problem" in f404) or ("Archiwalne:" in f404):
        return "No"
    else:
        return "Yes"


def connect_to_offer_url(driver, item):
    # connection to single url
    url = list(item.keys())[0]
    driver.get(url)
    time.sleep(1)
    try:
        driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
    except:
        pass

    if find_404(driver) == "No":
        return False

    return True


def find_by_selector(driver, selector, not_found_message):
    # find single element using xpath
    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        element = driver.find_element(By.XPATH, selector).text
        return element
    except NoSuchElementException:
        return not_found_message
    except:
        return f"Unknown exception at {selector}"


def parse_with_selenium_olx(offer_data, driver):

    id_olx = try_find_element(
        driver,
        '//div[@data-testid="ad-footer-bar-section"]/span[1]',
        "Not found",
    ).split("ID: ")[1]
    # driver.find_element(
    #     By.XPATH,
    #     '//*[@id="mainContent"]/div/div[2]/div[3]/div[1]/div[2]/div[5]/div',
    # ).split("ID: ")[0]

    #'//*[@id="root"]/div[1]/div[3]/div[3]/div[1]/div[1]/div[3]',
    #         '//div[@data-testid="ad-price-container"]/h3',
    price = try_find_element(
        driver,
        '//div[@data-testid="ad-price-container"]/h3',
        "Not found",
    )
    #  '//*[@id="root"]/div[1]/div[3]/div[3]/div[1]/div[2]/div[2]/h1',
    # //*[@id="mainContent"]/div/div[2]/div[3]/div[1]/div[2]/div/div[2]
    # //*[@id="mainContent"]/div/div[2]/div[3]/div[1]/div[2]/div/div[2]
    # /html/body/div[1]/div[2]/div/div[2]/div[3]/div[1]/div[2]/div/div[2]
    offer_title = try_find_element(
        driver,
        "//div[@data-cy='ad_title']/h4",
        "Not found",
    )

    location = try_find_element(
        driver,
        # '//*[@id="root"]/div[1]/div[3]/div[3]/div[2]/div[2]/div/section/div[1]/div',
        # //*[@id="mainContent"]/div/div[2]/div[3]/div[2]/div[2]/div/section/div[1]/div
        '//*[@id="mainContent"]/div/div[2]/div[3]/div[2]/div[2]/div/section/div[1]/div/p[1]',
        "Not found",
    )

    offer_data.update(
        {
            "offer_id": id_olx,
            "price": price,
            "offer_title": offer_title,
            "location": location,
            "active": "True",
        }
    )
    return offer_data


def parse_with_selenium_otodom(offer_data, driver):
    otodom_id = try_find_element(
        driver,
        '//p[text()="ID"]',
        "Not found",
    ).split(
        "ID: "
    )[1]

    price = try_find_element(
        driver,
        '//strong[@aria-label="Cena"]',
        "Not found",
    )

    offer_title = try_find_element(
        driver,
        '//h1[@data-cy="adPageAdTitle"]',
        "Not found",
    )

    # /html/body/div[1]/div[1]/main/div[3]/div[1]/div[1]/div[5]/div[2]/a
    # //*[@id="__next"]/div[1]/main/div[3]/div[1]/div[1]/div[5]/div[2]/a
    # __next > div.css-n9t2oe.e1b97qw40 > main > div.css-11zs7dp.edhb3g30 > div.css-1w41ge1.edhb3g31 > div:nth-child(1) > div.css-bg2zrz.ef3kcx00 > div.css-70qvj9.e42rcgs0 > a
    # <a href="#map" class="css-1jjm9oe e42rcgs1"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="none" viewBox="0 0 24 24" class="e42rcgs2 css-1d3z7c5"><path fill="currentColor" d="M12.88 7.92c0 .51-.41.92-.92.92s-.92-.41-.92-.92.41-.92.92-.92.92.41.92.92Z"></path><path fill="currentColor" fill-rule="evenodd" d="M16.48 10.99h3.28l2.2 11h-20l2.2-11h3.28l-.36-.62c-.49-.88-.74-1.8-.74-2.75C6.34 4.52 8.86 2 11.96 2s5.62 2.52 5.62 5.62c0 .95-.24 1.87-.73 2.74l-.37.63Zm-.9-3.37c0-2-1.62-3.62-3.62-3.62h-.01C9.96 4 8.33 5.62 8.33 7.62c0 .6.16 1.19.48 1.76l3.13 5.39 3.17-5.41c.31-.55.47-1.14.47-1.74Zm-9.82 5.37-1.31 7h15.01l-1.31-7H15.3l-2.26 3.86h-2.2L8.6 12.99H5.76Z" clip-rule="evenodd"></path></svg>ul. Mokotowska, Śródmieście Południowe, Śródmieście, Warszawa, mazowieckie</a>
    # location = try_find_element(
    #     driver,
    #     '//a[@aria-label="Adres"]',
    #     "location not found on the otodom.pl",
    # )
    # TODO not found
    # //*[@id="map"]/div[1]/text() on oto

    location = try_find_element(
        driver,
        '//*[@id="map"]/div[1]',
        "Not found",
    )

    offer_data.update(
        {
            "offer_id": otodom_id,
            "price": price,
            "offer_title": offer_title,
            "location": location,
            "active": "True",
        }
    )
    return offer_data


def check_if_expired(driver):
    try:
        # Wait for the element to be present
        message_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div[data-testid="ad-inactive-msg"] h4')
            )
        )
        # Check the text content of the element
        if message_element.text == "To ogłoszenie nie jest już dostępne":
            # print("The message indicates that the ad is no longer available.")
            return True
        else:
            print("The message is present but the text is different.")
            return True
    except TimeoutException:
        # print("The message element was not found within the timeout period.")
        return False


def parse_with_selenium(driver, item):
    offer_data = unknown
    url = list(item.keys())[0]
    offer_data.update(
        {
            "category": item[url]["size_category"],
            "website": str(url.split(".pl")[0].split("www.")[1]),
        }
    )

    print(offer_data)

    if find_404(driver) == "No":
        offer_data["active"] = find_404(driver)
        return {url: offer_data}

    if check_if_expired(driver) == True:
        return {url: offer_data}

    if "https://www.otodom.pl" in url:
        offer_data = parse_with_selenium_otodom(offer_data, driver=driver)
        return {url: offer_data}
    if "https://www.olx.pl" in url:
        offer_data = parse_with_selenium_olx(offer_data, driver=driver)
        return {url: offer_data}


def scrape_single_page(driver, queue, item):
    connect_to_offer_url(driver, item)
    dump_data(driver, queue, item)


def dump_data(driver, queue, item):
    dump = parse_with_selenium(driver, item)
    print(dump)
    queue.put(dump)


def main():
    # start measuring time
    start_time = time.time()
    # newest_links_file, links_list = file_handler.read_newest_links(
    #     "C:\\Users\\Matt\\housing_market_scraper\\housing_market_scraper\\links\\*.txt"
    # )
    # print(f"type:{newest_links_file}")
    # date = newest_links_file[12:-4]
    # print(f"date: {str(date)}")

    newest_dict_file, links_dict = file_handler.read_newest_offers(
        "C:\\Users\\Matt\\housing_market_scraper\\housing_market_scraper\\offers\\*.json"
    )

    # Initialize the queues
    scrapeQueue = JoinableQueue()
    dumpQueue = Queue()
    writeQueue = Queue()

    # Create empty proxy list
    offers = []

    # Start the scrapers
    workers = []
    for i in range(3):
        worker = Process(target=Scraper, args=(scrapeQueue, dumpQueue))
        worker.start()
        workers.append(worker)

    writer = Process(target=DB_Worker, args=("offers.db", writeQueue))
    writer.start()

    # Load the scrapeQueue
    for link, content in links_dict.items():
        scrapeQueue.put({link: content})

    # Wait for the scrapers to finish
    scrapeQueue.join()

    # Regex the ip port pairs out of the textDumps
    while not dumpQueue.empty():
        dump = dumpQueue.get()
        writeQueue.put(dump)
        offers.append(dump)

    # for i in range(1):
    #     worker = Process(target=Scraper, args=(scrapeQueue, dumpQueue))
    #     worker.start()

    print(f"Number of offers: {len(offers)}")

    with open(
        newest_dict_file,
        "w+",
        encoding="utf-8",
    ) as d:
        json.dump(links_dict, d, indent=4)

    time.sleep(3)
    # dumpQueue.join() wrong, not this kind of queue
    # get time elapsed
    print("--- %s seconds ---" % (time.time() - start_time))

    for w in workers:
        w.terminate()  # Stop the worker process
        w.join()
    writer.terminate()  # Stop the worker process
    writer.join()

    sys.exit(0)


class DB_Worker(Process):
    def __init__(self, db_path, writeQueue):
        super().__init__()
        self.exit = Event()
        self.db_path = db_path
        self.db_conn = sqlite3.connect(db_path)
        self.accepted_columns = [
            "url",
            "category",
            "website",
            "offer_id",
            "price",
            "offer_title",
            "location",
            "active",
        ]
        self.cursor = self.db_conn.cursor()
        self.write_queue = writeQueue
        self.run()

    def run(self):
        """
        The database worker function that runs in a separate process.
        """
        while True:
            task = self.write_queue.get()
            if task is None:  # Sentinel to stop the worker
                break
            # in case that there is no atomicity in a
            # in case task.keys() contains something else then the element of self.accepted_columns
            task_edited = {}

            for k, v in task.items():
                fk = f"SELECT url, active FROM offers WHERE url = {k}"
                for i in self.accepted_columns:
                    if i == self.accepted_columns[0]:
                        task_edited.update({i: k})
                    elif i not in list(v):
                        task_edited.update({i: "No data"})
                    else:
                        task_edited.update({i: v[i]})

                try:
                    # Perform the database write operation
                    entered_keys = ", ".join(task_edited.keys())
                    entered_values = ", ".join(
                        ["'" + i + "'" for i in task_edited.values()]
                    )

                    # check if there is a record
                    self.cursor.execute(
                        "SELECT url, active FROM offers WHERE url = ?",
                        (task_edited["url"],),
                    )

                    result = self.cursor.fetchone()
                    if result is None:
                        print("result: None")
                    else:
                        print("result: " + ", ".join(result))

                    if result is not None:
                        update_command_part = ", ".join(
                            [f"{t}='{e}'" for t, e in task_edited.items()][1:]
                        )

                        command = (
                            f"UPDATE offers SET {update_command_part} WHERE url = ? "
                        )
                        print(f"command: {command}")
                        self.cursor.execute(
                            command,
                            (task_edited["url"],),
                        )

                    else:
                        command = f"INSERT INTO offers ( {entered_keys} ) VALUES ( {entered_values} )"
                        print(f"command: {command}")
                        self.cursor.execute(
                            command,
                            (
                                # entered_keys,
                                # entered_values,
                            ),
                        )
                    self.db_conn.commit()
                except Exception as e:
                    print(f"Error writing to database: {e}")
                    traceback.print_exception(e, limit=2, file=sys.stdout)

        self.shutdown()

    def add_task(self, task):
        """
        Adds a task to the queue for the worker to process.
        """
        self.write_queue.put(task)

    def stop(self):
        """
        Stops the database worker process gracefully.
        """
        # Send sentinel value to stop the worker
        self.write_queue.put(None)
        self.write_queue.close()
        print("Worker process terminated.")

    def shutdown(self):
        self.stop()
        self.exit.set()


class Scraper(Process):
    def __init__(self, scrape_queue, dump_queue):
        super().__init__()
        self.exit = Event()
        self.driver = webdriver.Chrome()
        self.scrape_queue = scrape_queue
        self.dump_queue = dump_queue
        self.run()

    def restart_driver(self):
        self.driver.close()
        self.driver = webdriver.Chrome()

    def run(self):
        while not self.scrape_queue.empty():
            item = self.scrape_queue.get()
            url = list(item.keys())[0]
            try:
                print(f"Scraping {url}")
                scrape_single_page(self.driver, self.dump_queue, item)
                print(f"[+] {url} has been scraped.")
            except WebDriverException as e:
                print(f"[-] {url} WebDriver failed with exception: \n {str(e)}")
            except Exception as e:
                print(f"[-] {url} : Scraper Unknown Exception: {e}")
            self.scrape_queue.task_done()
            self.driver.refresh()
        self.shutdown()

    def shutdown(self):
        self.driver.close()
        self.exit.set()


if __name__ == "__main__":
    main()
