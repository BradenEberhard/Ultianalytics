"""This file scrapes all the tabular data from the audl team stats
website as listed below. For some reason the waiting isn't perfect
and sometimes it takes a couple of tries to run all the way through.
Run time is around 2-3 minutes

Braden Eberhard, braden.ultimate@gmail.com, 2/19/22
"""
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
PAGE_END = 130
AUDL_GAME_STAT_URL = 'https://theaudl.com/league/game-search?page='
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"
FILE_PATH = '../data_csv/game_stats.csv'



def main():
    """This is the main function to scrape the AUDL game
    stats data and save the output to a csv
    """
    start = timeit.default_timer()
    futures = []

    # loop over every page, get dfs and merge
    with ThreadPoolExecutor() as executor:
        for page in tqdm(range(PAGE_START, PAGE_END), total=PAGE_END - 1):
            futures.append(executor.submit(get_game_stats, page))

    # output to file
    with open(FILE_PATH) as f:
        futures, _ = wait(futures)
        all_dfs = [future.result() for future in futures]
        pd.concat(all_dfs).to_csv(FILE_PATH)
    stop = timeit.default_timer()

    print('Time: ', stop - start)  
    

def get_driver():
    """gets the chrome driver and returns it. It also
    adds options to not load images and unneccessary info
    """
    options = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    return webdriver.Chrome(chrome_options=options, executable_path=CHROME_PATH)


def get_game_stats(page):
    """This function scrapes the actual data from the website

    Returns:
        df: dataframe of scraped data
    """
    # gets a driver instance
    driver = get_driver()
    # gets the url based on parameters
    driver.get(f'{AUDL_GAME_STAT_URL}{page}')

    # wait if necessary
    try:
       WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "svelte-game")))
    except:
        print(f'problem with page: {page}')
        return None

    col_names = ['GAME_INFO', 'LOCATION', 'TEAM1_NAME', 'TEAM1_SCORE', 'TEAM2_NAME', 'TEAM2_SCORE']
    
    
    # get parser
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # navigate to table headers
    
    all_rows = []
    for table in soup.find_all("div", {"class": "svelte-game"}):
        data_row = []
        data_row.append(get_game_info(table))
        
        game_location = table.find("div", {"class": "svelte-game-info-location"}).text
        data_row.append(game_location)
        for team in table.find_all("a", {"class": "svelte-game-team"}):
            data_row.append(team.find("div", {"class": "svelte-game-team-info"}).text)
            data_row.append(team.find("span", {"class": "svelte-game-team-score"}).text)
        all_rows.append(data_row)

    
    # convert the list to dataframe and return
    return pd.DataFrame(all_rows, columns=col_names)


def get_game_info(table):
    game_header = table.find("div", {"class": "svelte-game-header-info"}).text
    try:
        return datetime.strptime(game_header, '%a, %m/%d %Y %I:%M %p')
    except ValueError as e:
        print('Value error')
        print(game_header)
        return datetime.strptime(game_header, '%a, %m/%d %Y TBD')


if __name__ == '__main__':
    main()
