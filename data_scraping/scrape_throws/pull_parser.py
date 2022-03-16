from datacache import event_types, GameInfo, Data


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
        if event['r'] == -1:
            thrower_id = None
        else:
            thrower_id = GameInfo.rosters[event['r']]
    output = {
        'pull_type': event_name,
        'time': time,
        'pull_x': pull_x,
        'pull_y': pull_y,
        'thrower_id': thrower_id
    }
    Data.pulls.append(output)