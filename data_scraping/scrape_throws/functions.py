from datacache import event_types, DynamicGlobals


def penalty_origin(event, origin):
    if (event_types[event['t']]) == 'D_PENALTY_ON_THEM':
        origin['origin_y'] += 10
        if origin['origin_y'] > 100:
            origin['origin_y'] = 100
            origin['origin_x'] = 0
    if (event_types[event['t']]) == 'O_PENALTY_ON_US':
        origin['origin_y'] -= 10
    return origin


def add_score(entry, home_players, away_players):
    entry['home_players'] = home_players
    entry['away_players'] = away_players
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
        home_players = [DynamicGlobals.rosters[x] for x in event['l']]
    else:
        away_players = [DynamicGlobals.rosters[x] for x in event['l']]
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
    if DynamicGlobals.time_left == -380:
        time = 0
    else:
        time = DynamicGlobals.time_left
    if DynamicGlobals.time_left == -301:
        time = 529
    if DynamicGlobals.time_left == -691:
        time = 529
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
        'time_left': time,
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
        if event['r'] == -1:
            player = None
        else:
            player = DynamicGlobals.rosters[event['r']]
    output = {
        'origin_x': origin_x,
        'origin_y': origin_y,
        'player': player
    }
    return output
