from datacache import event_types, Iterators

def switch_iter(current):
    if Iterators.home_iterator == current:
        return Iterators.away_iterator
    return Iterators.home_iterator


def get_iter_starter():
    if Iterators.home_event['t'] == 1:
        return Iterators.home_iterator, Iterators.home_event
    elif Iterators.away_event['t'] == 1:
        return Iterators.away_iterator, Iterators.away_event
    else:
        print('No event to start')
        return None