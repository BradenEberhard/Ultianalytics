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
    modification_container = st.container()
    with modification_container:
        with st.expander('Filters'):
            team_filter = st.selectbox('Team(s)', [x.capitalize() for x in teams_df.teamID.unique() if 'allstar' not in x])
            st.write(team_filter.lower())

if __name__ == '__main__':
    main()