from datacache import event_types, DynamicGlobals

def switch_iter(home, away, current):
    if home == current:
        return away
    return home


def get_iter_starter(event, home, away):
    if (event_types[event['t']]) in ['END_OF_Q1', 'END_OF_Q3'] and DynamicGlobals.start_team == 'home':
        return home
    elif (event_types[event['t']]) in ['HALFTIME'] and DynamicGlobals.start_team == 'away':
        return home
    return away