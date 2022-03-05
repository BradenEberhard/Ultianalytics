from hashlib import new
import requests as reqs 
import copy
import json
import csv

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

class DynamicGlobals:
    time_elapsed = 0
    home_score = 0
    away_score = 0

# pretty print events with the human readable type info
def print_events(events):
  for event in events:
    event_cpy = copy.copy(event)
    event_cpy['t'] = event_types[event['t']]
    print(event_cpy)

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
        game_id = '2021-07-09-PHI-NY'
        response = reqs.get(f'https://audl-stat-server.herokuapp.com/stats-pages/game/{game_id}')
        game_dict = response.json()
        away_events = json.loads(response.json()['tsgAway']['events'])
        game_events_dict[game_id] = game_dict
        break

    for _, game in game_events_dict.items():
        parse_game(game)

def parse_game(game):
    
    home_players, away_players = [], []
    list_of_pulls, list_of_throws = [], []
    origin = None
    home_iterator = iter(json.loads(game['tsgHome']['events']))
    away_iterator = iter(json.loads(game['tsgAway']['events']))
    if not game['tsgHome']['startOnOffense']:
        current_iter = home_iterator
    else:
        current_iter = away_iterator
    while(True):
        event = next(current_iter)
        if 'l' in event:
            home_players, away_players = get_players(current_iter, home_iterator, event, home_players, away_players)
        elif 'PULL_' in (event_types[event['t']]):
            pull = parse_pull(event)
            list_of_pulls.append(add_score(pull, home_players, away_players))
            current_iter = switch_iter(home_iterator, away_iterator, current_iter)
        elif 'POSSESSION' in (event_types[event['t']]):
            new_origin = get_new_origin(event)
            if origin is not None:
                throw = get_throw_row(origin=origin, new_origin=new_origin)
                list_of_throws.append(add_score(throw, home_players, away_players))
            origin = new_origin
        elif 'SCORED_ON' in (event_types[event['t']]):
            continue
        elif 'GOAL' in (event_types[event['t']]):
            new_origin = get_new_origin(event)
            add_goal(current_iter, home_iterator)
            goal = get_throw_row(origin=origin, new_origin=new_origin)
            list_of_throws.append(add_score(goal, home_players, away_players))
            origin = None
            DynamicGlobals.time_elapsed += event['s']
        else:
            event_str = event_types[event['t']]
            print(f'event {event_str} not supported')



        # elif 'THROWAWAY' in (event_types[event['t']]):
        #     new_origin = get_new_origin(event)
        #     throw = get_throwaway(origin, new_origin)
        #     list_of_throws.append(add_score(throw, players_on_field, home_score, away_score))
        #     origin = None

        # elif 'DROP' in (event_types[event['t']]):
        #     new_origin = get_new_origin(event)
        #     drop = get_drop(origin, new_origin)
        #     list_of_throws.append(add_score(drop, players_on_field, home_score, away_score))
        #     origin = None
        # elif 'BLOCK' in (event_types[event['t']]):
        #     block = get_block(event['r'])
        #     list_of_throws.append(add_score(block, players_on_field, home_score, away_score))

        # else:
        #     event_type = event_types[event['t']]
        #     print(f'NOT YET IMPLEMENTED: {event_type}')


def switch_iter(home, away, current):
    if home == current:
        return away
    return home

def add_score(entry, home_players, away_players):
    entry['home_players'] = home_players
    entry['away_players'] = away_players
    entry['home_score'] = DynamicGlobals.home_score
    entry['away_score'] = DynamicGlobals.away_score
    return entry


def add_goal(current_iter, home_iterator):
    if current_iter == home_iterator:
        DynamicGlobals.home_score += 1
    else:
        DynamicGlobals.away_score += 1


def get_players(current_iter, home_iterator, event, home_players, away_players):
    if current_iter == home_iterator:
        home_players = event['l']
    else:
        away_players = event['l']
    return home_players, away_players


def get_throw_row(origin=None, new_origin=None, blocker=None, throwaway=False, callahan=False, drop=False, score=False, time_elapsed=None):
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
        'score': score,
        'time_elapsed': time_elapsed
    }
    return output

def get_new_origin(event):
    origin_x = event['x']
    origin_y = event['y']
    player = event['r']
    output = {
        'origin_x': origin_x,
        'origin_y': origin_y,
        'player': player
    }
    return output
    
    

def parse_pull(event):
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
    
    
    
    

    






if __name__ == '__main__':
    main()