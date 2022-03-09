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


def reset_globals():
    DynamicGlobals.away_score = 0
    DynamicGlobals.home_score = 0
    DynamicGlobals.motion = 'motion'
    DynamicGlobals.time_left = 720
    DynamicGlobals.start_team = None
    DynamicGlobals.quarter = 'Q1'