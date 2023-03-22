### A threaded scraper
### This script will scrape a list of websites

import glob
import os
import time
import json
import file_handler
from multiprocessing import Process, Queue, JoinableQueue, Event
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException

unknown = {
    "price": "Unknown",
    "offer_title": "Unknown",
    "location": "Unknown",
    "active": "No",
}


def try_find_element(driver, xpath, not_found_message):
    # find single element using xpath
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        element = driver.find_element(By.XPATH, xpath).text
        return element
    except NoSuchElementException:
        return not_found_message
    except:
        return f"Unknown exception at {xpath}"


def find_404(driver):
    # find if the url is working
    f404 = driver.title
    if ("404" in f404) or ("Ups, mamy problem" in f404) or ("Archiwalne:" in f404):
        return "No"
    else:
        return "Yes"


def connect_to_offer_url(driver, url):
    # connection to single url
    driver.get(url)
    time.sleep(1)
    try:
        driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
    except:
        pass

    if find_404(driver) == "No":
        return False

    return True


def parse_with_selenium_olx(driver):
    #'//*[@id="root"]/div[1]/div[3]/div[3]/div[1]/div[1]/div[3]',
    #         '//div[@data-testid="ad-price-container"]/h3',
    price = try_find_element(
        driver,
        '//div[@data-testid="ad-price-container"]/h3',
        "price not found on the olx.pl",
    )
    #  '//*[@id="root"]/div[1]/div[3]/div[3]/div[1]/div[2]/div[2]/h1',
    offer_title = try_find_element(
        driver,
        '//h1[@data-cy="ad_title"]',
        "title not found on the olx.pl",
    )

    location = try_find_element(
        driver,
        '//*[@id="root"]/div[1]/div[3]/div[3]/div[2]/div[2]/div/section/div[1]/div',
        "location not found on the olx.pl",
    )

    info_offer = {
        "price": price,
        "offer_title": offer_title,
        "location": location,
        "active": "True",
    }
    return info_offer


def parse_with_selenium_otodom(driver):
    price = try_find_element(
        driver,
        '//strong[@aria-label="Cena"]',
        "price not found on the otodom.pl",
    )

    offer_title = try_find_element(
        driver,
        '//h1[@data-cy="adPageAdTitle"]',
        "title not found on the otodom.pl",
    )

    location = try_find_element(
        driver,
        '//a[@aria-label="Adres"]',
        "location not found on the otodom.pl",
    )

    info_offer = {
        "price": price,
        "offer_title": offer_title,
        "location": location,
        "active": "True",
    }
    return info_offer


def parse_with_selenium(driver, url):
    offer_data = unknown

    if find_404(driver) == "No":
        offer_data["active"] = find_404(driver)
        return {url: offer_data}

    if "https://www.otodom.pl" in url:
        offer_data = parse_with_selenium_otodom(driver=driver)
        return {url: offer_data}
    if "https://www.olx.pl" in url:
        offer_data = parse_with_selenium_olx(driver=driver)
        return {url: offer_data}


def scrape_single_page(driver, queue, url):
    connect_to_offer_url(driver, url)
    dump_data(driver, queue, url)


def dump_data(driver, queue, url):
    dump = parse_with_selenium(driver, url)
    print(dump)
    queue.put(dump)


def main():
    # start measuring time
    start_time = time.time()

    list_of_files = glob.glob("links/*.txt")
    newest_links_list_file_name = str(max(list_of_files, key=os.path.getctime))
    print(f"type:{newest_links_list_file_name}")
    date = newest_links_list_file_name[12:-4]
    print(f"date: {str(date)}")
    links_list = file_handler.read_newest_links()
    links_dict = file_handler.read_newest_offers()

    # Initialize the queues
    scrapeQueue = JoinableQueue()
    dumpQueue = Queue()

    # Create empty proxy list
    offers = []

    # Start the scrapers
    for i in range(4):
        worker = Process(target=Scraper, args=(scrapeQueue, dumpQueue))
        worker.start()

    # Load the scrapeQueue
    for link in links_list:
        scrapeQueue.put(link)

    # Wait for the scrapers to finish
    scrapeQueue.join()

    # Regex the ip port pairs out of the textDumps
    while not dumpQueue.empty():
        dump = dumpQueue.get()
        offers.append(dump)

    print(f"Number of offers: {len(offers)}")

    for i in offers:
        url = list(i.keys())[0]
        category = links_dict[url]["size_category"]
        i[url]["size_category"] = category
        links_dict.update(i)

    with open(f"offers\offers_{date}.json", "w+", encoding="utf-8") as d:
        json.dump(links_dict, d, indent=4)

    # get time elapsed
    print("--- %s seconds ---" % (time.time() - start_time))

    return


class Scraper(Process):
    def __init__(self, scrape_queue, dump_queue):
        Process.__init__(self)
        self.exit = Event()
        self.driver = webdriver.Chrome()
        self.scrape_queue = scrape_queue
        self.dump_queue = dump_queue
        self.run()

    def run(self):
        while not self.scrape_queue.empty():
            url = self.scrape_queue.get()
            try:
                print(f"Scraping {url}")
                scrape_single_page(self.driver, self.dump_queue, url)
                print(f"[+] {url} has been scraped.")
            except WebDriverException as e:
                print(f"[-] {url} WebDriver failed with exception: \n {str(e)}")
            except:
                print(f"[-] {url} : Unknown Exception.")
            self.scrape_queue.task_done()
        self.shutdown()

    def shutdown(self):
        self.driver.close()
        self.exit.set()


if __name__ == "__main__":
    main()
