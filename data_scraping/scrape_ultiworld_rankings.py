"""
This file iterates over all ultiworld club and college rankings. It also reads
the prior ranking and the change. for some reason it works better doing one division
at a time and a for loop with all of them was crashing for me so i did each individually
and added a function to concat at the end.

Braden Eberhard, braden.ultimate@gmail.com, 2/25/22
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor, wait
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from datetime import datetime
import timeit
import re

"""these variables are self explanatory, just make sure the chrome path
points to the executable chrome driver and the file path outputs to the
right spot. 
"""

D1_WOMENS_START = 'https://ultiworld.com/ranking/18945/college-d-i-womens-division-power-rankings-season-2014-week-9/'
D1_MENS_START = 'https://ultiworld.com/ranking/26605/college-d-i-mens-division-power-rankings-season-2015-11-10-14/'
D3_MENS_START = 'https://ultiworld.com/ranking/66336/college-d-iii-mens-rankings-2018-season-week-of-5-9-18/'
D3_WOMENS_START = 'https://ultiworld.com/ranking/18629/college-d-iii-womens-power-rankings-season-2014-week-9/'
CLUB_WOMENS_START = 'https://ultiworld.com/ranking/25244/club-womens-division-power-rankings-season-2014-10-9/'
CLUB_MIXED_START = 'https://ultiworld.com/ranking/72317/club-mixed-power-rankings-2018-season-final/'
CLUB_MENS_START = 'https://ultiworld.com/ranking/25196/club-mens-division-power-rankings-season-2014-10-8/'
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"
# these are the variables to change
DIVISION = 'CLUB_MEN'
FILE_PATH = f'../data_csv/ultiworld_rankings_{DIVISION}.csv'



def main():
    """This is the main function to scrape the Ultiworld ranking data and save the output to a csv
    """
    
    start = timeit.default_timer()
    futures = []

    # loop over every page, get dfs and merge
    with ThreadPoolExecutor() as executor:
        futures.append(executor.submit(get_ultiworld_rankings, CLUB_MENS_START))

    # output to file
    
    with open(FILE_PATH, 'w+') as f:
        # wait for all threads to complete
        futures, _ = wait(futures)

        # get the resulting dataframes
        all_dfs = [future.result() for future in futures]
        # combine data frames and output to FILE_PATH
        pd.concat(all_dfs).to_csv(FILE_PATH)
    stop = timeit.default_timer()
    print('Time: ', stop - start)  
    

def get_driver(url, counter):
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
       WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "description-table")))
    except:
        print(f'problem with url: {url} number: {counter}')
        return get_driver(url, counter + 1)
    return driver


def get_ultiworld_rankings(start):
    """This function scrapes the actual data from the website

    Returns:
        df: dataframe of scraped data
    """
    # gets a driver instance
    driver = get_driver(start, 1)
    
    # get parser
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    year_dfs = []
    # iterrate over every year provided by ultiworld
    for link in soup.find("th",text="Years").parent.find_all("a"):
        url = link['href']
        driver = get_driver(url, 1)
        print(f'accesed url: {url}')
        soup3 = BeautifulSoup(driver.page_source, 'html.parser')
        year_dfs.append(get_year_stats(soup3))
    return pd.concat(year_dfs)



def get_year_stats(soup):
    # navigate to table headers
    all_dfs = []
    # iterate over every date on the page
    for link in soup.find("th",text=re.compile(r'\d*\sRankings')).parent.find_all("a"):
        driver = get_driver(link['href'], 1)

        # create a soup parser for HTML
        soup2 = BeautifulSoup(driver.page_source, 'html.parser')

        # load the table colums as names
        ranking_df = pd.read_html(str(soup2.find("table", {"class":"table table-hover ranking"})))[0]
        date = datetime.strptime(soup.find("div", {"class":"reference-heading__datetime"}).text, 'Published on %B %d, %Y')
        # Some early pages don't have column headers
        if 'Rank' not in ranking_df:
            ranking_df.columns = ['Rank', 'Team']
        # include the date and division
        ranking_df['Date'] = date
        ranking_df['Division'] = DIVISION
        # drop the last row where teams that left the top 25 are listed
        if 25 in ranking_df.index:
            ranking_df.drop(25, inplace=True)
        all_dfs.append(ranking_df)

    # return 1 df
    return pd.concat(all_dfs)

def combine_files():
    df = pd.concat(
    map(pd.read_csv, ['./data_csv/ultiworld_rankings_CLUB_MEN.csv',
                    './data_csv/ultiworld_rankings_CLUB_WOMEN.csv',
                    './data_csv/ultiworld_rankings_CLUB_MIXED.csv',
                    './data_csv/ultiworld_rankings_D1_MEN.csv',
                    './data_csv/ultiworld_rankings_D3_MEN.csv',
                    './data_csv/ultiworld_rankings_D1_WOMEN.csv',
                    './data_csv/ultiworld_rankings_D3_WOMEN.csv'
                    ]), ignore_index=True)
    with open('../ultiworld_rankings_all.csv', 'w+') as f:
        df.to_csv('../ultiworld_rankings_all.csv')

if __name__ == '__main__':
    main()