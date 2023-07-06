import streamlit as st
import pandas as pd
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams
from audl.stats.endpoints.gamestats import GameStats
from audl.stats.endpoints.playergamestats import PlayerGameStats

def get_name_from_id(row):
    date = pd.to_datetime(row.startTimestamp).date().strftime('%m/%d/%y')
    out_str = f'{row.awayTeamID.capitalize()} at {row.homeTeamID.capitalize()} on {date}'
    return out_str

@st.cache_data
def get_box_scores(gameID):
    game_stats = GameStats(gameID)
    box_scores = game_stats.get_boxscores()
    box_scores.index.name = None
    box_scores.index = [x.capitalize() for x in box_scores.index]
    return box_scores

@st.cache_data
def get_roster_stats(gameID):
    playergamestats = PlayerGameStats()
    game_stats_df = playergamestats.get_request_as_df(f'playerGameStats?gameID={gameID}')
    game_stats_df = pd.merge(game_stats_df.player.apply(pd.Series), game_stats_df.drop('player', axis=1), left_index=True, right_index=True)
    game_stats_df['fullName'] = game_stats_df['firstName'] + ' ' + game_stats_df['lastName']
    stats_cols = ['playerID', 'teamID', 'fullName', 'oPointsPlayed', 'dPointsPlayed', 'assists', 'goals', 'hockeyAssists', 'completions', 'throwaways', 'stalls', 'yardsReceived', 'yardsThrown', 'hucksCompleted', 'drops',
    'blocks', 'callahans']
    return game_stats_df[stats_cols]


@st.cache_data
def get_games_df():
    games = Games()
    games_df = games.get_games()

    games_df['name'] = games_df.apply(get_name_from_id, axis=1)
    return games_df

@st.cache_data
def get_teams_df():
    teams = Teams()
    teams_df = teams.get_teams()
    teams_df = teams_df[teams_df.year.astype(int) >= 2021]
    return teams_df
    

def main():
    st.title('Game Dashboard')

    games_df = get_games_df()
    teams_df = get_teams_df()
    game_filter = '<select>'
    with st.expander('Filters'):
        team_filter = st.selectbox('Team', [x.capitalize() for x in teams_df.teamID.unique() if 'allstar' not in x])
        team_filter = team_filter.lower()
        year_filter = st.selectbox('Year', ['<select>'] + sorted(teams_df[teams_df.teamID == team_filter].year.astype(int)), 0)
        if year_filter != '<select>':
            team_games = games_df[(games_df.homeTeamID == team_filter) | (games_df.awayTeamID == team_filter)]
            team_games = team_games[team_games.startTimestamp.apply(lambda x:int(x[:4])) == year_filter]
            game_filter = st.selectbox('Game', ['<select>'] + sorted(team_games.name, key= lambda x:x[-8:]), 0)
    if game_filter != '<select>':
        game = games_df[games_df.name == game_filter]
        st.write(get_box_scores(game.iloc[0].gameID))
        roster_stats = get_roster_stats(game.iloc[0].gameID)
        roster_stats[roster_stats.teamID == game.homeTeamID]
        col1, col2 = st.columns(2)
        col1.write(roster_stats[roster_stats.teamID == game.iloc[0].homeTeamID])
        col2.write(roster_stats[roster_stats.teamID == game.iloc[0].awayTeamID])

if __name__ == '__main__':
    main()