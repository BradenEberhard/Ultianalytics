from this import d
from datacache import reset_globals, GameInfo, event_types, Iterators, set_iterators, Data
from functions import get_players, add_throw, get_new_origin, get_throw_row, add_goal, penalty_origin, update_blocker, update_quarter
from iter_functions import switch_iter
from pull_parser import parse_pull
import json
import pandas as pd

POINT_END_EVENTS = [6, 21, 7, 22, 23, 24, 25, 26, 27, 28]

def parse_game(game):
    # start with quarter 1
    reset_globals(json.loads(game['tsgHome']['events']), json.loads(game['tsgAway']['events']))

    
    all_points = []
    try:
        while True:
            all_points.append(get_next_point())
    except StopIteration as e:
        pass

    for point in all_points:
        parse_point(point)
    if GameInfo.home_score != game['game']['score_home'] or GameInfo.away_score != game['game']['score_away']:
        home, away = game['game']['score_home'], game['game']['score_away']
        print(f'scores dont match - parsed: {GameInfo.home_score}-{GameInfo.away_score} actual: {home}-{away}')
    


def parse_point(point):
    GameInfo.current_possession, GameInfo.current_point = [], []
    current_iter = set_iterators(point[0], point[1])
    if current_iter is None:
        return None
    
    team_on_offense = 'home' if current_iter == Iterators.home_iterator else 'away'
    origin = None
    previous_event = None
    num_timeouts = 0
    scoring_team = None
    try:
        while True:
            event = next(current_iter)
             # if a pull is happening, parse it and add it to pulls
            if 'PULL_' in (event_types[event['t']]):
                GameInfo.motion = 'pull'
                current_iter = switch_iter(current_iter)
                parse_pull(event)

            # if its a possession event, get the new spot and add the throw
            elif 'POSSESSION' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                # if no player had the disc before, don't add a throw
                if origin is not None:
                    throw = get_throw_row(origin=origin, new_origin=new_origin)
                    add_throw(throw, current_iter)
                origin = new_origin

            # if a goal occured, get the new origin, update the schore, get the throw, reset origin, update time
            elif 'GOAL' in (event_types[event['t']]):
                scoring_team = 'home' if current_iter == Iterators.home_iterator else 'away'
                new_origin = get_new_origin(event)
                add_goal(current_iter)
                goal = get_throw_row(origin=origin, new_origin=new_origin, goal=True)
                add_throw(goal, current_iter)
                origin, GameInfo.time_left= None, event['s']
                add_possession_data('goal')
                add_point_data(scoring_team, num_timeouts, team_on_offense)
                
                break
            
            # if a callahan occured, get the new origin, update the score, get the throw, update time
            elif 'CALLAHAN_THROWN' in (event_types[event['t']]):
                scoring_team = 'home' if current_iter == Iterators.home_iterator else 'away'
                new_origin = get_new_origin(event)
                add_goal(current_iter, callahan=True)
                goal = get_throw_row(origin=origin, new_origin=new_origin)
                add_throw(goal, current_iter)
                add_possession_data('callahan')
                origin, GameInfo.time_left, current_iter = None, event['s'], switch_iter(current_iter)
            
            # if a throwaway occured, get the new origin, get the throw, reset origin, switch iterators, mark as turnover
            elif (event_types[event['t']]) == 'THROWAWAY':
                new_origin = get_new_origin(event)
                throw = get_throw_row(origin=origin, new_origin=new_origin, throwaway=True)
                add_throw(throw, current_iter)
                add_possession_data('turnover')
                origin, current_iter, GameInfo.motion = None, switch_iter(current_iter), 'turnover'

            # if a penalty was called update the origin, mark as penalty
            elif (event_types[event['t']]) in ['O_PENALTY_ON_US', 'D_PENALTY_ON_THEM']:
                origin = penalty_origin(event, origin)
                GameInfo.motion = 'penalty'
            
            # if a block or callahan occured update the blocker and time if available
            elif (event_types[event['t']]) in ['BLOCK', 'CALLAHAN']:
                update_blocker(event)

            # if a drop occured, get the new origin, get the throw, reset origin, mark as turnover, switch iterators
            elif 'DROP' in (event_types[event['t']]):
                new_origin = get_new_origin(event)
                drop = get_throw_row(origin=origin, new_origin=new_origin, drop=True)
                add_throw(drop, current_iter)
                add_possession_data('turnover')
                origin, current_iter, GameInfo.motion = None, switch_iter(current_iter), 'turnover'
            
            # if a stall occurs, reset the origin, switch iterators, mark as turnover
            elif (event_types[event['t']])  == 'STALL':
                current_iter = switch_iter(current_iter)
                origin, GameInfo.motion = None, 'turnover'

            # if a midpoint timeout occured, update the time left and mark as timeout
            elif 'OUR_MIDPOINT_TIMEOUT' in (event_types[event['t']]):
                # FIXME this is an interesting point. i'm not sure if we should count time elapsed during timeouts
                GameInfo.time_left, GameInfo.motion = event['s'], 'timeout'
                current_iter, origin = switch_iter(current_iter), None
                num_timeouts = num_timeouts + 1
            elif 'SET_D_LINE_NO_PULL' in (event_types[event['t']]):
                if 'INJURY_ON_D' not in (event_types[previous_event['t']]):
                    get_players(current_iter, event)
                    current_iter = switch_iter(current_iter)
            elif 'SET_O_LINE_NO_PULL' in (event_types[event['t']]):
                get_players(current_iter, event)
            # pass if the event is in this list
            elif  (event_types[event['t']]) in ['THROWAWAY_CAUSED', 'STALL_CAUSED', 'INJURY_ON_D', 'INJURY_ON_O', 'THEIR_MIDPOINT_TIMEOUT', 'O_PENALTY_ON_THEM', 'D_PENALTY_ON_US']:
                pass 
            elif  (event_types[event['t']]) in ['HALFTIME', 'END_OF_Q1', 'END_OF_Q3', 'GAME_OVER', 'END_OF_OT1', 'END_OF_OT2']:
                add_possession_data('end_of_quarter')
                update_quarter(event)
                pass         
            else:
                event_str = event_types[event['t']]
                print(f'event {event_str} not supported')     
            previous_event = event
    except StopIteration as e:
        current_iter = switch_iter(current_iter)
        add_possession_data('None')
        add_point_data(scoring_team, num_timeouts, team_on_offense)
        try:
            event = next(current_iter)
        except StopIteration as e:
            return
        if (event_types[event['t']]) == 'D_PENALTY_ON_US':
            event = next(current_iter)
        if (event_types[event['t']]) not in ['SCORED_ON', 'HALFTIME', 'END_OF_Q1', 'END_OF_Q3', 'GAME_OVER', 'END_OF_OT1', 'END_OF_OT2']: 
            print(f'error with point {GameInfo.home_score}-{GameInfo.away_score} of game {GameInfo.current_game_id}')
            print('home')
            for el in point[0]: 
                print(event_types[el['t']])
            print('away')
            for el in point[1]: 
                print(event_types[el['t']])


def get_next_point():
    home_point = []
    Iterators.home_event = next(Iterators.home_iterator)
    home_point.append(Iterators.home_event)
    while (Iterators.home_event['t'] not in POINT_END_EVENTS):
        Iterators.home_event = next(Iterators.home_iterator)
        home_point.append(Iterators.home_event)

    away_point = []
    Iterators.away_event = next(Iterators.away_iterator)
    away_point.append(Iterators.away_event)
    while (Iterators.away_event['t'] not in POINT_END_EVENTS):
        Iterators.away_event = next(Iterators.away_iterator)
        away_point.append(Iterators.away_event)
        
    return (home_point, away_point)


def add_point_data(scoring_team, num_timeouts, team_on_offense):
    for row in GameInfo.current_point:
        row['scoring_team'] = scoring_team
        row['num_timeouts'] = num_timeouts
        row['team_on_offense'] = team_on_offense
        Data.throws.append(row)

def add_possession_data(result):
    for row in GameInfo.current_possession:
        row['poss_result'] = result
        GameInfo.current_point.append(row)
    GameInfo.current_possession = []