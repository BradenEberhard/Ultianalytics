import streamlit as st
import pandas as pd
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams
from audl.stats.endpoints.gamestats import GameStats

def get_name_from_id(row):
    date = pd.to_datetime(row.startTimestamp).date().strftime('%m/%d/%y')
    out_str = f'{row.awayTeamID.capitalize()} at {row.homeTeamID.capitalize()} on {date}'
    return out_str

@st.cache_data
def get_box_scores(gameID):
    game_stats = GameStats(gameID)
    return game_stats.get_box_scores()

@st.cache_data
def get_roster_stats(gameID):
    game_stats = GameStats(gameID)
    return game_stats.get_roster_stats()


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
    with st.expander('Filters'):
        team_filter = st.selectbox('Team', [x.capitalize() for x in teams_df.teamID.unique() if 'allstar' not in x])
        team_filter = team_filter.lower()
        year_filter = st.selectbox('Year', sorted(teams_df[teams_df.teamID == team_filter].year.astype(int)))
        team_games = games_df[(games_df.homeTeamID == team_filter) | (games_df.awayTeamID == team_filter)]
        team_games = team_games[team_games.startTimestamp.apply(lambda x:int(x[:4])) == year_filter]
        game_filter = st.selectbox('Game', sorted(team_games.name, key= lambda x:x[-8:]))

    st.write(game_filter)
    game = games_df[games_df.name == game_filter]
    st.write(game.gameID)


if __name__ == '__main__':
    main()