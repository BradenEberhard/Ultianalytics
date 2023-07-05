import streamlit as st
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams

@st.cache_data
def get_games_df():
    games = Games()
    games_df = games.get_games()
    return games_df

@st.cache_data
def get_teams_df():
    teams = Teams()
    teams_df = teams.get_teams()
    return teams_df

def main():
    st.title('Game Dashboard')

    games_df = get_games_df()
    teams_df = get_teams_df()
    with st.expander('Filters'):
        team_filter = st.selectbox('Team', [x.capitalize() for x in teams_df.teamID.unique() if 'allstar' not in x])
        year_filter = st.selectbox('Year', teams_df[teams_df.teamID == team_filter].year)
        team_games = games_df[(games_df.homeTeamID == team_filter) | (games_df.awayTeamID == team_filter)]
        team_games = team_games[team_games.startTimestamp.apply(lambda x:x[:4]) == year_filter]
        game_filter = st.selectbox('Game', team_games.gameID)

if __name__ == '__main__':
    main()