from datacache import reset_globals, DynamicGlobals, event_types
from functions import get_players, add_score, get_new_origin, get_throw_row, add_goal, penalty_origin
from iter_functions import get_iter_starter, switch_iter
from pull_parser import parse_pull
import json
from itertools import tee
import pandas as pd

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
                    if event['r'] == -1:
                        list_of_throws[-1]['blocker'] = 'none_listed'
                    else:
                        list_of_throws[-1]['blocker'] = DynamicGlobals.rosters[event['r']]
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