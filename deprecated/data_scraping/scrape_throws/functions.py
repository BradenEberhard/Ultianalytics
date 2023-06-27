from datacache import event_types, GameInfo, Iterators, Data


def penalty_origin(event, origin):
    if (event_types[event['t']]) == 'D_PENALTY_ON_THEM':
        origin['origin_y'] += 10
        if origin['origin_y'] > 100:
            origin['origin_y'] = 100
            origin['origin_x'] = 0
    if (event_types[event['t']]) == 'O_PENALTY_ON_US':
        origin['origin_y'] -= 10
    return origin


def add_throw(entry, current_iter):
    entry['home_players'] = GameInfo.home_players
    entry['away_players'] = GameInfo.away_players
    entry['home_score'] = GameInfo.home_score
    entry['away_score'] = GameInfo.away_score
    entry['game_id'] = GameInfo.current_game_id
    entry['quarter_id'] = GameInfo.quarter
    entry['team_with_possession'] = 'home' if current_iter == Iterators.home_iterator else 'away'
    GameInfo.current_possession.append(entry)


def add_goal(current_iter, callahan=False):
    if current_iter == Iterators.home_iterator and not callahan:
        GameInfo.home_score += 1
    else:
        GameInfo.away_score += 1


def get_players(current_iter, event):
    if current_iter == Iterators.home_iterator:
        GameInfo.home_players = [GameInfo.rosters[x] for x in event['l']]
    else:
        GameInfo.away_players = [GameInfo.rosters[x] for x in event['l']]


def get_throw_row(origin=None, new_origin=None, blocker=None, throwaway=False, callahan=False, block=False, drop=False, goal=False):
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
    score = str(GameInfo.home_score) + '-' + str(GameInfo.away_score)
    if GameInfo.time_left == -380:
        time = 0
    else:
        time = GameInfo.time_left
    if GameInfo.time_left == -301:
        time = 529
    if GameInfo.time_left == -691:
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
        'goal': goal,
        'score': score,
        'time_left': time,
        'motion': GameInfo.motion
    }
    if GameInfo.motion != 'motion':
        GameInfo.motion = 'motion'
    return output


def get_new_origin(event):
    origin_x = event['x']
    origin_y = event['y']
    player = None
    if 'r' in event:
        if event['r'] == -1:
            player = None
        else:
            player = GameInfo.rosters[event['r']]
    output = {
        'origin_x': origin_x,
        'origin_y': origin_y,
        'player': player
    }
    return output


def update_blocker(event):
    if 'r' in event:
        if event['r'] == -1:
            GameInfo.current_point[-1]['blocker'] = 'none_listed'
        elif len(GameInfo.current_point) > 0:
            GameInfo.current_point[-1]['blocker'] = GameInfo.rosters[event['r']]
    else:
        GameInfo.current_point[-1]['blocker'] = 'none_listed'
    if 's' in event:
        GameInfo.time_left = event['s']


def update_quarter(event):
    if (event_types[event['t']]) == 'END_OF_Q1':
        GameInfo.quarter = 'Q2'
        GameInfo.time_left = 720
    elif (event_types[event['t']]) == 'HALFTIME':
        GameInfo.quarter = 'Q3'
        GameInfo.time_left = 720
    elif (event_types[event['t']]) == 'END_OF_Q3':
        GameInfo.quarter = 'Q4'
        GameInfo.time_left = 720
    elif (event_types[event['t']]) == 'GAME_OVER':
        GameInfo.quarter = 'OT1'
        GameInfo.time_left = 300
    elif (event_types[event['t']]) == 'END_OF_OT1':
        GameInfo.quarter = 'OT2'
        GameInfo.time_left = -1