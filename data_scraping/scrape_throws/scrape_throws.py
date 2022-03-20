"""This file pulls all the data from the AUDL stat server and creates 2 dfs
one is of every throw made and the other is every pull.
"""
from game_parser import parse_game
import pandas as pd
import requests as reqs
from concurrent.futures import ThreadPoolExecutor, wait
from datacache import GameInfo, Data

PULL_FILEPATH = '../../data_csv/pulls.csv'
THROW_FILEPATH = '../../data_csv/throws.csv'

def main():
    year = '2021'

    # if you want data for a different year you will likely need to adjust this page_count
    page_count = 15

    # a set containing every game_id for the specified year
    game_ids = set()

    # loop through each page of games and throw the game ids into a set
    # for some reason the audl stat server doesn't like large numbers for limit
    # so you can't just grab all the data at once
    for page in range(0, page_count):
        response = reqs.get(f'https://audl-stat-server.herokuapp.com/web-api/games?limit=10&years={year}&page={page}') 
        game_ids.update(list(map(lambda game: game['gameID'], response.json()['games'])))

    # #  for each game id grab all the home and away events for each team
    # futures = []
    # with ThreadPoolExecutor() as executor:
    #     for game_id in game_ids:
    #         futures.append(executor.submit(get_game, game_id))
            
    # futures, _ = wait(futures)
    # all_games = [future.result() for future in futures if future is not None]


    game_ids = '2021-08-08-DC-PIT'
    all_games = [get_game(game_ids)]
    # clear the files to write to
    # with open(THROW_FILEPATH, 'w+') as file:
    #     file.truncate(0)
    # with open(PULL_FILEPATH, 'w+') as file:
    #     file.truncate(0)

    # iterate over every game
    games = {list(game.items())[0][0]: list(game.items())[0][1] for game in all_games}
    for id, game in games.items():
        
        # get the rosters for both teams 
        home_roster = {x['id']: x['player']['ext_player_id'] for x in game['rostersHome']}
        away_roster = {x['id']: x['player']['ext_player_id'] for x in game['rostersAway']}
        home_roster.update(away_roster)
        GameInfo.rosters = home_roster
        GameInfo.current_game_id = id
        print(f'parsing game: {id}')

        # parse the game and add the data to a list
        parse_game(game)

  

    # output the data to files
    with open(THROW_FILEPATH, 'w+') as file:
        pd.DataFrame(Data.throws).to_csv(file, index=False)
    with open(PULL_FILEPATH, 'w+') as file:
        pd.DataFrame(Data.pulls).to_csv(file, index=False)


def get_game(game_id):
    response = reqs.get(f'https://audl-stat-server.herokuapp.com/stats-pages/game/{game_id}')
    game_dict = response.json()
    return {game_id: game_dict}

    
def reset_globals():
    GameInfo.away_score = 0
    GameInfo.home_score = 0
    GameInfo.motion = 'motion'
    GameInfo.time_left = 720
    GameInfo.start_team = None
    GameInfo.quarter = 'Q1'
    

if __name__ == '__main__':
    main()