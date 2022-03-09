"""This file pulls all the data from the AUDL stat server and creates 2 dfs
one is of every throw made and the other is every pull.
"""
from hashlib import new
from itertools import tee
import pandas as pd
import requests as reqs 
import copy
import json
import csv


PULL_FILEPATH = '../data_csv/pulls.csv'
THROW_FILEPATH = '../data_csv/throws.csv'

# event_types as defined by the audl stat server
event_types = {
    # Defense
    2: 'SET_D_LINE',
    40: 'SET_D_LINE_NO_PULL',
    3: 'PULL_INBOUNDS',
    4: 'PULL_OUT_OF_BOUNDS',
    44: 'PULL_OUR_OFFSIDES',
    45: 'PULL_THEIR_OFFSIDES',
    5: 'BLOCK',
    9: 'THROWAWAY_CAUSED',
    6: 'CALLAHAN',
    21: 'SCORED_ON',
    18: 'STALL_CAUSED',
    11: 'D_PENALTY_ON_US',
    13: 'O_PENALTY_ON_THEM',
    15: 'THEIR_MIDPOINT_TIMEOUT',
    31: 'THEIR_TIMEOUT_ON_O',
    32: 'OUR_TIMEOUT_ON_D',

    # Offense
    1: 'SET_O_LINE',
    41: 'SET_O_LINE_NO_PULL',
    19: 'DROP',
    20: 'POSSESSION',
    7: 'CALLAHAN_THROWN',
    8: 'THROWAWAY',
    22: 'GOAL',
    17: 'STALL',
    10: 'O_PENALTY_ON_US',
    12: 'D_PENALTY_ON_THEM',
    14: 'OUR_MIDPOINT_TIMEOUT',
    29: 'THEIR_TIMEOUT_ON_D',
    30: 'OUR_TIMEOUT_ON_O',

    # Any
    0: 'UNKNOWN',
    42: 'INJURY_ON_O',
    43: 'INJURY_ON_D',
    23: 'END_OF_Q1',
    24: 'HALFTIME',
    25: 'END_OF_Q3',
    26: 'GAME_OVER',
    27: 'END_OF_OT1',
    28: 'END_OF_OT2'
}

# this class stores some global variable that are appended to every throw entry
class DynamicGlobals:
    time_left = 720
    home_score = 0
    away_score = 0
    current_game_id = None
    motion = 'motion'
    start_team = None
    rosters = None
    quarter = None

def main():
    year = '2021'

    # if you want data for a different year you will likely need to adjust this page_count
    page_count = 15

    # dictionary keyed with game ids that contains an array of home and away events
    game_events_dict = {}

    # a set containing every game_id for the specified year
    game_ids = set()

    # loop through each page of games and throw the game ids into a set
    # for some reason the audl stat server doesn't like large numbers for limit
    # so you can't just grab all the data at once
    for page in range(0, page_count):
        response = reqs.get(f'https://audl-stat-server.herokuapp.com/web-api/games?limit=10&years={year}&page={page}') 
        game_ids.update(list(map(lambda game: game['gameID'], response.json()['games'])))

    #  for each game id grab all the home and away events for each team
    for game_id in game_ids:
        print('fetching game:', game_id)
        response = reqs.get(f'https://audl-stat-server.herokuapp.com/stats-pages/game/{game_id}')
        game_dict = response.json()
        game_events_dict[game_id] = game_dict

    # clear the files to write to
    with open(THROW_FILEPATH, 'w+') as file:
        file.truncate(0)
    with open(PULL_FILEPATH, 'w+') as file:
        file.truncate(0)

    all_pulls = []
    all_throws = []
    # iterate over every game
    for id, game in game_events_dict.items():
        # get the rosters for both teams
        home_roster = {x['id']: [x['player_id'], x['player']['ext_player_id']] for x in game['rostersHome']}
        away_roster = {x['id']: [x['player_id'], x['player']['ext_player_id']] for x in game['rostersAway']}
        home_roster.update(away_roster)
        DynamicGlobals.rosters = home_roster
        DynamicGlobals.current_game_id = id
        print(f'parsing game: {id}')

        # parse the game and add the data to a list
        pull_df, throw_df = parse_game(game)
        all_pulls.append(pull_df)
        all_throws.append(throw_df)

    # output the data to files
    with open(THROW_FILEPATH, 'w+') as file:
        pd.concat(all_throws).to_csv(file, index=False)
    with open(PULL_FILEPATH, 'w+') as file:
        pd.concat(all_pulls).to_csv(file, index=False)


def parse_game(game):
    # start with quarter 1
    reset_globals()

    #initialize variables
    home_players, away_players = [], []
    list_of_pulls, list_of_throws = [], []
    origin = None
    home_iterator = iter(json.loads(game['tsgHome']['events']))
    away_iterator = iter(json.loads(game['tsgAway']['events']))

    # start with the team on defense
    if not game['tsgHome']['startOnOffense']:
        current_iter = home_iterator
        DynamicGlobals.start_team = 'away'
    else:
        current_iter = away_iterator
        DynamicGlobals.start_team = 'home'
    try:
        # loop until the iterator runs out of entries
        while(True):
            event = next(current_iter)

            # if the players are listed, update the players on field       
            if 'l' in event:
                home_players, away_players = get_players(current_iter, home_iterator, event, home_players, away_players)

            # if a pull is happening, parse it and add it to pulls
            elif 'PULL_' in (event_types[event['t']]):
                pull = parse_pull(event)
                list_of_pulls.append(add_score(pull, home_players, away_players))
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
                DynamicGlobals.motion = 'pull'

            # if its a possession event, get the new spot and add the throw
            elif 'POSSESSION' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                # if no player had the disc before, don't add a throw
                if origin is not None:
                    throw = get_throw_row(origin=origin, new_origin=new_origin)
                    list_of_throws.append(add_score(throw, home_players, away_players))
                origin = new_origin

            # pass if the event is in this list
            elif  (event_types[event['t']]) in ['THROWAWAY_CAUSED', 'SCORED_ON', 'STALL_CAUSED', 'INJURY_ON_D', 'INJURY_ON_O']:
                continue

            # if a goal occured, get the new origin, update the schore, get the throw, reset origin, update time
            elif 'GOAL' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                add_goal(current_iter, home_iterator)
                goal = get_throw_row(origin=origin, new_origin=new_origin)
                list_of_throws.append(add_score(goal, home_players, away_players))
                origin = None
                DynamicGlobals.time_left = event['s']
            
            # if a callahan occured, get the new origin, update the score, get the throw, update time
            elif 'CALLAHAN_THROWN' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                add_goal(current_iter, home_iterator, callahan=True)
                goal = get_throw_row(origin=origin, new_origin=new_origin)
                list_of_throws.append(add_score(goal, home_players, away_players))
                origin = None
                DynamicGlobals.time_left = event['s']
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
            
            # if a throwaway occured, get the new origin, get the throw, reset origin, switch iterators, mark as turnover
            elif (event_types[event['t']]) == 'THROWAWAY':
                new_origin = get_new_origin(event)
                throw = get_throw_row(origin=origin, new_origin=new_origin, throwaway=True)
                list_of_throws.append(add_score(throw, home_players, away_players))
                origin = None
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
                DynamicGlobals.motion = 'turnover'
            
            # if a midpoint timeout occured, update the time left and mark as timeout
            elif 'MIDPOINT_TIMEOUT' in (event_types[event['t']]):
                # FIXME this is an interesting point. i'm not sure if we should count time elapsed during timeouts
                DynamicGlobals.time_left = event['s'] 
                DynamicGlobals.motion = 'timeout'
            
            # if a block or callahan occured update the blocker and time if available
            elif (event_types[event['t']]) in ['BLOCK', 'CALLAHAN']:
                if 'r' in event:
                    list_of_throws[-1]['blocker'] = event['r']
                else:
                    list_of_throws[-1]['blocker'] = 'none_listed'
                if 's' in event:
                    DynamicGlobals.time_left = event['s']
            
            # if a drop occured, get the new origin, get the throw, reset origin, mark as turnover, switch iterators
            elif 'DROP' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                drop = get_throw_row(origin=origin, new_origin=new_origin, drop=True)
                list_of_throws.append(add_score(drop, home_players, away_players))
                origin = None
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
                DynamicGlobals.motion = 'turnover'
            
            # if a penalty was called update the origin, mark as penalty
            elif 'PENALTY_ON' in (event_types[event['t']]):
                origin = penalty_origin(event, origin)
                DynamicGlobals.motion = 'penalty'
            
            # if a quarter ends, update the quarter, update the iterators and reset origin
            elif 'END_OF_Q' in (event_types[event['t']]) or 'HALFTIME' in (event_types[event['t']]):
                if (event_types[event['t']]) == 'END_OF_Q1':
                    DynamicGlobals.quarter = 'Q2'
                elif (event_types[event['t']]) == 'HALFTIME':
                    DynamicGlobals.quarter = 'Q3'
                elif (event_types[event['t']]) == 'END_OF_Q3':
                    DynamicGlobals.quarter = 'Q4'
                current_quarter = event_types[event['t']]
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
                event = next(current_iter)
                origin = None
                while (event_types[event['t']]) != current_quarter:
                    event = next(current_iter)
                current_iter = get_iter_starter(event, home_iterator, away_iterator)
            
            # if a stall occurs, reset the origin, switch iterators, mark as turnover
            elif 'STALL' in (event_types[event['t']]):
                origin = None
                current_iter = switch_iter(home_iterator, away_iterator, current_iter)
                DynamicGlobals.motion = 'turnover'
            
            # if regulation or OT2 ends, update quarter, reset time, end loop if game is done
            elif (event_types[event['t']]) in ['GAME_OVER', 'END_OF_OT2']:
                DynamicGlobals.quarter = 'OT1'
                if (event_types[event['t']]) == 'GAME_OVER':
                    DynamicGlobals.time_left = 300
                if 'lr' not in event:
                    break
                origin = None
                next(switch_iter(home_iterator, away_iterator, current_iter))
                if event['o']:
                    current_iter = switch_iter(home_iterator, away_iterator, current_iter)
            
            # if OT1 ends, update quarter and time, see if OT2 exists and set iterator to defensive team
            elif 'END_OF_OT1' in (event_types[event['t']]):
                DynamicGlobals.quarter = 'OT2'
                curr_is_home = (home_iterator == current_iter)
                DynamicGlobals.time_left = 0
                current_iter, check_iter = tee(current_iter)
                next_event = next(check_iter)
                if next_event is None:
                    break
                if 'SET_O_LINE' in (event_types[next_event['t']]):
                    if curr_is_home:
                        next(away_iterator)
                        current_iter = away_iterator
                    else:
                        next(home_iterator)
                        current_iter = home_iterator
                else:
                    if curr_is_home:
                        next(away_iterator)
                    else:
                        next(home_iterator)
            # catch all events not listed above
            else:
                event_str = event_types[event['t']]
                print(f'event {event_str} not supported')
    except StopIteration:
        pass
    return pd.DataFrame(list_of_pulls), pd.DataFrame(list_of_throws)


def get_iter_starter(event, home, away):
    if (event_types[event['t']]) in ['END_OF_Q1', 'END_OF_Q3'] and DynamicGlobals.start_team == 'home':
        return home
    elif (event_types[event['t']]) in ['HALFTIME'] and DynamicGlobals.start_team == 'away':
        return home
    return away



def penalty_origin(event, origin):
    if (event_types[event['t']]) == 'D_PENALTY_ON_THEM':
        origin['origin_y'] += 10
        if origin['origin_y'] > 100:
            origin['origin_y'] = 100
            origin['origin_x'] = 0
    if (event_types[event['t']]) == 'O_PENALTY_ON_US':
        origin['origin_y'] -= 10
    return origin



def switch_iter(home, away, current):
    if home == current:
        return away
    return home


def add_score(entry, home_players, away_players):
    entry['home_players'] = home_players
    entry['away_players'] = away_players
    entry['home_player_names'] = [DynamicGlobals.rosters[x] for x in home_players]
    entry['away_player_names'] = [DynamicGlobals.rosters[x] for x in away_players]
    entry['home_score'] = DynamicGlobals.home_score
    entry['away_score'] = DynamicGlobals.away_score
    entry['game_id'] = DynamicGlobals.current_game_id
    entry['quarter_id'] = DynamicGlobals.quarter
    return entry


def add_goal(current_iter, home_iterator, callahan=False):
    if current_iter == home_iterator and not callahan:
        DynamicGlobals.home_score += 1
    else:
        DynamicGlobals.away_score += 1


def get_players(current_iter, home_iterator, event, home_players, away_players):
    if current_iter == home_iterator:
        home_players = event['l']
    else:
        away_players = event['l']
    return home_players, away_players


def get_throw_row(origin=None, new_origin=None, blocker=None, throwaway=False, callahan=False, block=False, drop=False, time_elapsed=None):
    if origin is None:
        thrower = None
        origin_x = None
        origin_y = None
    else:
        thrower = origin['player']
        origin_x = origin['origin_x']
        origin_y = origin['origin_y']
    if new_origin is None:
        receiver = None
        destination_x = None
        destination_y = None
    else:
        receiver = new_origin['player']
        destination_x = new_origin['origin_x']
        destination_y = new_origin['origin_y']
    score = str(DynamicGlobals.home_score) + '-' + str(DynamicGlobals.away_score)
    output = {
        'thrower': thrower,
        'origin_x': origin_x,
        'origin_y': origin_y,
        'receiver': receiver,
        'destination_x': destination_x,
        'destination_y': destination_y,
        'blocker': blocker,
        'throwaway': throwaway,
        'callahan': callahan,
        'drop': drop,
        'block': block,
        'score': score,
        'time_left': DynamicGlobals.time_left,
        'motion': DynamicGlobals.motion
    }
    if DynamicGlobals.motion != 'motion':
        DynamicGlobals.motion = 'motion'
    return output

def get_new_origin(event):
    origin_x = event['x']
    origin_y = event['y']
    player = None
    if 'r' in event:
        player = event['r']
    output = {
        'origin_x': origin_x,
        'origin_y': origin_y,
        'player': player
    }
    return output
    
    

def parse_pull(event):
    # FIXME players and time not working correctly
    event_name = event_types[event['t']]
    time = None
    pull_x = None
    pull_y = None
    thrower_id = None
    if 'x' in event and 'y' in event:
        pull_x = event['x']
        pull_y = event['y']
    if 'ms' in event:
        time = event['ms']
    if 'r' in event:
        thrower_id = event['r']
    output = {
        'pull_type': event_name,
        'time': time,
        'pull_x': pull_x,
        'pull_y': pull_y,
        'thrower_id': thrower_id
    }
    return output
    
    
def reset_globals():
    DynamicGlobals.away_score = 0
    DynamicGlobals.home_score = 0
    DynamicGlobals.motion = 'motion'
    DynamicGlobals.time_left = 720
    DynamicGlobals.start_team = None
    DynamicGlobals.quarter = 'Q1'
    

    






if __name__ == '__main__':
    main()