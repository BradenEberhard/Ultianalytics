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
PAGE_START = 1
PAGE_END = 19
AUDL_GAME_STAT_URL = 'https://theaudl.com/league/game-search?page='
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"
FILE_PATH = '../data_csv/game_team_stats.csv'



def main():
    """This is the main function to scrape the AUDL game quarter
    stats data and save the output to a csv
    """
    start = timeit.default_timer()
    futures = []

    # loop over every page, get dfs and merge
    with ThreadPoolExecutor() as executor:
        for page in tqdm(range(PAGE_START, PAGE_END), total=PAGE_END - 1):
            futures.append(executor.submit(get_game_quarter_stats, page))

    # output to file
    with open(FILE_PATH) as f:
        # wait for all threads to complete
        futures, _ = wait(futures)

        # get the resulting dataframes
        all_dfs = [future.result() for future in futures]
        # combine data frames and output to FILE_PATH
        pd.concat(all_dfs).to_csv(FILE_PATH)
    stop = timeit.default_timer()
    print('Time: ', stop - start)  
    

def get_driver(page, counter):
    """gets the chrome driver and returns it. it will wait for the page to load.
    It also adds options to not load images and unneccessary info. If an attempt
    fails, it will retry 2 more times.
    """
    if counter >= 3:
        return None
    options = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    driver =  webdriver.Chrome(chrome_options=options, executable_path=CHROME_PATH)
    driver.get(f'{AUDL_GAME_STAT_URL}{page}')
    # wait if necessary
    try:
       WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "svelte-game")))
    except:
        print(f'problem with page: {page} number: {counter}')
        return get_driver(page, counter + 1)
    return driver


def get_game_quarter_stats(page):
    """This function scrapes the actual data from the website

    Returns:
        df: dataframe of scraped data
    """
    # gets a driver instance
    driver = get_driver(page, 1)
    
    # get parser
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # navigate to table headers
    all_dfs = []
    # iterate over every table on the page
    for link in soup.find_all("div", {"class": "svelte-game-header-links"}):

        # get the link for the advanced stat page
        advanced_stat_url = link.find("a")['href'].split('/')[-1]
        driver.get(f'https://theaudl.com/stats/game/{advanced_stat_url}')

        # wait for the information to load
        try:
            WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "team-stats")))
        except:
            # if it doesn't load, create a new soup object and check if the information exists
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            if soup.find("div", {"class": "error-container"}) is None:
                print(f'problem with url: https://theaudl.com/stats/game/{advanced_stat_url}')
            continue
            

        # create a soup parser for HTML
        advanced_soup = BeautifulSoup(driver.page_source, 'html.parser')

        # load the table colums as names, add 'GAME_INFO' to the end
        teams = [el for el in advanced_soup.find("div", {"class": "team-stats"}).find("thead").find("tr").find_all("th")]
        team1 = [teams[1].text]
        team2 = [teams[2].text]

        col_names = ['TEAM']


        # iterate over both rows in the quarter breakdown table
        for tr in advanced_soup.find("div", {"class": "team-stats"}).find("tbody").find_all("tr"):
            tds = tr.find_all("td")
            col_names.append(tr.find("th").text)
            team1.append(tds[0].text)
            team2.append(tds[1].text)

        # add the game info to the end
        team1.append(advanced_stat_url)
        team2.append(advanced_stat_url)
        col_names.append('GAME_INFO')

        # create a list of dfs
        all_dfs.append(pd.DataFrame([team1], columns=col_names))
        all_dfs.append(pd.DataFrame([team2], columns=col_names))
    # return 1 df
    return pd.concat(all_dfs)

if __name__ == '__main__':
    main()
