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
class GameInfo:
    time_left = 720
    home_score = 0
    away_score = 0
    current_game_id = None
    motion = 'motion'
    start_team = None
    rosters = None
    quarter = None
    home_players = None
    away_players = None

class Iterators:
    home_iterator = None
    away_iterator = None
    home_event = None
    away_event = None


def reset_globals(home_events, away_events):
    GameInfo.away_score = 0
    GameInfo.home_score = 0
    GameInfo.motion = None
    GameInfo.time_left = 720
    GameInfo.start_team = None
    GameInfo.quarter = 'Q1'
    GameInfo.home_players = None
    GameInfo.away_players = None

    Iterators.home_iterator = iter(home_events)
    Iterators.away_iterator = iter(away_events)


class Data:
    throws = []
    pulls = []


def set_iterators(home_events, away_events):
    Iterators.home_iterator = iter(home_events)
    Iterators.away_iterator = iter(away_events)
    Iterators.home_event = next(Iterators.home_iterator)
    Iterators.away_event = next(Iterators.away_iterator)

    if (event_types[Iterators.home_event['t']]) in ['OUR_MIDPOINT_TIMEOUT']:
        Iterators.home_event = next(Iterators.home_iterator)
    if (event_types[Iterators.away_event['t']]) == ['OUR_MIDPOINT_TIMEOUT']:
        Iterators.away_event = next(Iterators.away_iterator)

    if (event_types[Iterators.home_event['t']]) not in ['END_OF_Q1', 'END_OF_Q3', 'GAME_OVER', 'END_OF_OT1', 'END_OF_OT2', 'HALFTIME']:
        GameInfo.home_players = [GameInfo.rosters[x] for x in Iterators.home_event['l']]
    if (event_types[Iterators.away_event['t']]) not in ['END_OF_Q1', 'END_OF_Q3', 'GAME_OVER', 'END_OF_OT1', 'END_OF_OT2', 'HALFTIME']:
        GameInfo.away_players = [GameInfo.rosters[x] for x in Iterators.away_event['l']]
    if Iterators.home_event['t'] == 2:
        return Iterators.home_iterator
    elif Iterators.away_event['t'] == 2:
        return Iterators.away_iterator
    if (event_types[Iterators.away_event['t']]) in ['END_OF_Q1', 'END_OF_Q3', 'GAME_OVER', 'END_OF_OT1', 'END_OF_OT2', 'HALFTIME']:
        if (event_types[Iterators.away_event['t']]) == 'END_OF_Q1':
            GameInfo.quarter = 'Q2'
            GameInfo.time_left = 720
        elif (event_types[Iterators.away_event['t']]) == 'HALFTIME':
            GameInfo.quarter = 'Q3'
            GameInfo.time_left = 720
        elif (event_types[Iterators.away_event['t']]) == 'END_OF_Q3':
            GameInfo.quarter = 'Q4'
            GameInfo.time_left = 720
        elif (event_types[Iterators.away_event['t']]) == 'GAME_OVER':
            GameInfo.quarter = 'OT1'
            GameInfo.time_left = 300
        elif (event_types[Iterators.away_event['t']]) == 'END_OF_OT1':
            GameInfo.quarter = 'OT2'
            GameInfo.time_left = -1
    print('bad first event')
    return None
