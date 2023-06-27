"""This file scrapes all the game quarter data from the audl game quarter stats
from the advanced stat page for each game. there are just over 250 games with 
this information at the moment. 
Run time is around 900 seconds for all pages but you can change the PAGE_END to 15 
since there aren't any older stats and it takes around 450 seconds.

Braden Eberhard, braden.ultimate@gmail.com, 2/21/22
"""
from numpy import column_stack
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, wait
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from datetime import datetime
import timeit

"""these variables are self explanatory, just make sure the chrome path
points to the executable chrome driver and the file path outputs to the
right spot
"""
PAGE_START = 16
PAGE_END = 30
AUDL_GAME_STAT_URL = 'https://theaudl.com/league/game-search?page='
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"
FILE_PATH = '../data_csv/play_by_play_stats.csv'



def main():
    """This is the main function to scrape the AUDL game quarter
    stats data and save the output to a csv
    """
    start = timeit.default_timer()
    futures = []

    # loop over every page, get dfs and merge
    with ThreadPoolExecutor() as executor:
        for page in range(PAGE_START, PAGE_END):
            futures.append(executor.submit(get_play_by_play_stats, page))
    # for page in tqdm(range(PAGE_START, PAGE_END), total=PAGE_END - PAGE_START):
    #         futures.append(get_play_by_play_stats(page))
    # output to file
    with open(FILE_PATH, 'w+') as f:
        # wait for all threads to complete
        futures, _ = wait(futures)

        # get the resulting dataframes
        all_dfs = [future.result() for future in futures if future is not None]
        # combine data frames and output to FILE_PATH
        pd.concat(all_dfs).to_csv(FILE_PATH)
    stop = timeit.default_timer()
    print('Time: ', stop - start)  
    

def get_driver(url, counter, class_str):
    """gets the chrome driver and returns it. it will wait for the page to load.
    It also adds options to not load images and unneccessary info. If an attempt
    fails, it will retry 2 more times.
    """
    if counter >= 3:
        return None
    options = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--no-sandbox')
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    driver =  webdriver.Chrome(options=options, service=Service(CHROME_PATH))
    driver.get(url)
    # wait if necessary
    try:
       WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, class_str)))
    except:
        print(f'problem with url: {url} number: {counter}')
        return get_driver(url, counter + 1, class_str)
    return driver


def get_play_by_play_stats(page):
    """This function scrapes the actual data from the website

    Returns:
        df: dataframe of scraped data
    """
    # gets a driver instance
    url = f'{AUDL_GAME_STAT_URL}{page}'
    driver = get_driver(url, 1, "svelte-game")
    print(f'accessed page: {page}')

    all_dfs = []
    
    # get parser
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # iterate over every table on the page
    for link in soup.find_all("div", {"class": "svelte-game-header-links"}):
        advanced_stat_url = link.find("a")['href'].split('/')[-1]
        if '2021' not in advanced_stat_url:
            continue

        # get the link for the advanced stat page
       
        url = f'https://theaudl.com/stats/game/{advanced_stat_url}'
        driver2 = get_driver(url, 1, 'play-by-play-quarter')
        if driver2 is None:
            return None
        print(f'accessed game: {advanced_stat_url}')

        # create a soup parser for HTML
        advanced_soup = BeautifulSoup(driver2.page_source, 'html.parser')
        quarters = []
        for count, quarter in enumerate(advanced_soup.find_all("div", {"class": "play-by-play-quarter"})):
            quarter_df = get_play_row(quarter)
            quarter_df['quarter'] = f'q{count + 1}'
            quarters.append(quarter_df)
        driver2.find_element(By.XPATH, "//div[@class='play-by-play']").find_element(By.XPATH, "//label[@class='btn btn-primary']").click()
        for count, quarter in enumerate(advanced_soup.find_all("div", {"class": "play-by-play-quarter"})):
            quarter_df = get_play_row(quarter)
            quarter_df['quarter'] = f'q{count + 1}'
            quarters.append(quarter_df)
        all_dfs.append(pd.concat(quarters))
    # return 1 df
    return pd.concat(all_dfs)


def get_play_row(quarter):
    plays = []
    for play in quarter.find_all("div", {"class": "title"}):
        play_row = []
        for element in play.find_all("span"):
            play_row.append(element.text)
        plays.append(play_row)
    cols = ['score', 'line', 'time_left', 'point_time', 'players']
    return pd.DataFrame(plays, columns=cols)


if __name__ == '__main__':
    main()
