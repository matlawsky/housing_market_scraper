import numpy as np
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import re

def driver_setup():
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)

    return driver