"""this was the first file i created to scrape the data
and therefore it has a lot of minor changes itneeds. Mainly that
chrome will crash after running it for a while so the drivers should be parallelized
and retried if it crashs similar to the other files. it also takes quite a while to run.
I had to run it in chunks restarting it when it crashed and total run time was a few hours.

Braden Eberhard, braden.ultimate@gmail.com, 2/21/22
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

START_PAGE = 90
NUM_PAGES = 136
AUDL_PLAYER_STAT_URL = 'https://theaudl.com/league/players?page='
FILE_PATH = 'player_stats.csv'
CHROME_PATH = "/Users/bradeneberhard/Documents/chromedriver"


def main():
    options = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    driver = webdriver.Chrome(chrome_options=options, executable_path=CHROME_PATH)
    df_list = []
    for page_num in tqdm(range(START_PAGE, NUM_PAGES), total=NUM_PAGES - START_PAGE):
        url = AUDL_PLAYER_STAT_URL + str(page_num)
        driver.get(url)
        player_links = get_player_links(driver)
        for player_link in player_links:
            player_df = get_player_df(driver, player_link)
            if player_df is not None:
                df_list.append(player_df)
        print('saving page: {}'.format(page_num))
        with open(FILE_PATH, 'a') as f:
            pd.concat(df_list).to_csv(f, header=False, index=False)
        df_list = []


def get_player_links(driver):
    all_links = driver.find_elements_by_tag_name('a')
    return [elem.get_attribute('href') for elem in all_links if 'league/players/' in elem.get_attribute('href') and '#' not in elem.get_attribute('href')]


def get_player_df(driver, player_link):
    driver.get(player_link)
    try:
        element = WebDriverWait(driver,5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, "svelte-mkdd1m")))
    except:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        player = soup.find("div", {"class": "audl-player-display-name"})
        print("problem with player: {}".format(player.text))
        return None
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    body = soup.select("table.svelte-mkdd1m tbody")
    player = soup.find("div", {"class": "audl-player-display-name"})
    df_list = []
    for count, table in enumerate(body):
        rows = []
        for row in table.find_all('tr'):
            season = 'none'
            if count == 0:
                season = 'regular season'
            elif count == 1:
                season = 'post-season'
            stats = [col.text for col in row.find_all('td')] + [player.text, season]
            rows.append(stats)
        headers = ['Year - Team', 'G', 'PP', 'M', 'AST', 'GLS', 'BLK', '+/-', 'Cmp', 'Cmp%', 'TY', 'RY', 'HA', 'T', 'S', 'D', 'C', 'Hck', 'Hck%', 'OPP', 'DPP', 'Pul', 'Pul%', 'PH', 'PLAYER', 'SEASON']
        df_list.append(pd.DataFrame(rows, columns=headers))
    return pd.concat(df_list)


if __name__ == '__main__':
    main()
