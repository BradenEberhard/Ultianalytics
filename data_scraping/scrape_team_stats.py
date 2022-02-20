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
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

"""these variables are self explanatory, just make sure the chrome path
points to the executable chrome driver and the file path outputs to the
right spot
"""
YEAR_LIST = ['2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2021']
AUDL_TEAM_STAT_URL = 'https://theaudl.com/stats/team'
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"
FILE_PATH = '../data_csv/team_stats.csv'



def main():
    """This is the main function to scrape the AUDL team
    stats data and save the output to a csv
    """
    all_dfs = []
    driver = get_driver()
    # start with all time stats for every team
    driver.get(AUDL_TEAM_STAT_URL)
    # wait until the table is loaded
    try:
        element = WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "svelte-xe7fx0")))
    except:
        # if it doesn't load in 5 seconds print out the url it failed on
        print(f'problem with url: {AUDL_TEAM_STAT_URL}')
        return None

    # get soup parser for html
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # scrape every teams all time data
    df1 = get_team_stats(driver, career=True)
    # scrape every teams' opponents all time data
    df2 = get_team_stats(driver, opponent=True, career=True)

    # merge the two data frames
    all_dfs.append(df1.merge(df2, how='left', on=['TEAM', 'G', 'L', 'SA', 'S', 'YEAR']))

    # loop over every year, get dfs and merge
    for year in tqdm(YEAR_LIST, total=len(YEAR_LIST)):
        df1 = get_team_stats(driver, year, False)
        df2 = get_team_stats(driver, year, True)
        all_dfs.append(df1.merge(df2, how='left', on=['TEAM', 'G', 'L', 'SA', 'S', 'YEAR']))

    # output to file
    with open(FILE_PATH) as f:
        pd.concat(all_dfs).to_csv(FILE_PATH)
    

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


def get_team_stats(driver, year='CAREER', opponent=False, career=False):
    """This function scrapes the actual data from the website

    Args:
        driver (driver): chrome driver
        year (str, optional): year being scraped. Defaults to 'CAREER'.
        opponent (bool, optional): if the opponents data is being scraped. Defaults to False.
        career (bool, optional): if its the entire career being scraped. Defaults to False.

    Returns:
        df: dataframe of scraped data
    """
    # gets the url based on parameters
    url = get_url(year, opponent, career)
    driver.get(url)

    # wait if necessary
    try:
       WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "svelte-xe7fx0")))
    except:
        print(f'problem with url: {url}')
        return None
    
    # get parser
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # navigate to table headers
    body = soup.find("table", {"class": "svelte-xe7fx0"})
    headers = body.find("thead").find("tr")
    
    # creates a list of all the headers in the table
    col_names = []
    for header in headers.find_all("th"):
        col_names.append(str(header.text).replace('▼', '').strip().upper())
    col_names.append('YEAR')
    
    # iterates over every table row, scrapes and adds it to a list
    row_list = []
    for row in body.find("tbody").find_all("tr"):
        team_row = []
        for td in row.find_all("td"):
            team_row.append(td.text)
        team_row.append(year)
        row_list.append(team_row)
    
    # convert the list to dataframe and return
    return pd.DataFrame(row_list, columns=col_names)


def get_url(year, opponent, career):
    """generates the correct url based on inputs"""
    if career and not opponent:
        return f'{AUDL_TEAM_STAT_URL}'
    elif career and opponent:
        return f'{AUDL_TEAM_STAT_URL}?opponent'
    if opponent:
        return f'{AUDL_TEAM_STAT_URL}?opponent&year={year}'
    return f'{AUDL_TEAM_STAT_URL}?year={year}'


if __name__ == '__main__':
    main()
