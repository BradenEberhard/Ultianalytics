import streamlit as st
import pandas as pd
import numpy as np
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams
from audl.stats.endpoints.gamestats import GameStats
from audl.stats.endpoints.playergamestats import PlayerGameStats
from probability_model import GameProbability
from plotly.graph_objects import go

def plot_game(game_prob, gameID, features, max_length = 629):
    test_game = game_prob.data[game_prob.data.gameID == gameID]
    home_team = test_game.home_teamID.iloc[0].capitalize()
    away_team = test_game.away_teamID.iloc[0].capitalize()
    test_game = test_game[features]
    test_game = game_prob.normalizer.transform(test_game)
    pad_width = ((max_length - len(test_game), 0), (0, 0))  # Pad at the beginning with zeros
    test_game = np.pad(test_game, pad_width, mode='constant', constant_values=-1).astype(np.float32)
    out = game_prob.model.predict(test_game.reshape(1, 629, -1))
    df = pd.DataFrame(game_prob.normalizer.inverse_transform(test_game), columns=features)
    preds = out[np.array([df.times > 0])].flatten()
    counter = 0
    txts, xs, ys = [], [], []
    for _, group_df in df[df.times>0].groupby('total_points'):
        if group_df.total_points.sum() == 0:
            continue
        counter = counter + 1
        row = group_df.iloc[0]
        x = 48 - row.times/60
        y = out.flatten()[min(group_df.index)]
        minutes = (48 - x) % 12 // 1
        seconds = round((48 - x) % 12 % 1 * 60)
        txt = f'{home_team}: {int(row.home_team_score)} - {away_team}: {int(row.away_team_score)}<br>{int(minutes)}:{seconds:02d}'
        txts.append(txt)
        xs.append(x)
        ys.append(y)
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=48 - df[df.times > 0].times/60,
        y=preds,
        hoverinfo="skip",
        marker=dict(
            color="blue"
        ),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        mode='markers',
        x=xs,
        y=ys,
        hovertext=txts,
        hoverinfo="text",
        marker=dict(
            color="black",
            size=5
        ),
        showlegend=False,
        customdata=txts
    ))
    fig.add_hline(y=0.5, line_width=1, line_color="grey")
    fig.add_vline(x=12, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=24, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=36, line_width=1, line_dash="dash", line_color="black")
    fig.update_layout(title=f'{away_team} at {home_team} on {gameID[:10]}', title_x=0.5, xaxis_title="Time Passed", yaxis_title="Win Probability",
                    yaxis_range=[0,1], xaxis_range=[0,48], 
                    xaxis = dict(tick0=0,dtick=12,tickvals=[0, 12, 24, 36], ticktext=['Q1', 'Q2', 'Q3', 'Q4']), yaxis = dict(tick0=0,dtick=0.1))
    return fig

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
    game_stats_df['pointsPlayed'] = game_stats_df['oPointsPlayed'] + game_stats_df['dPointsPlayed']
    stats_cols = ['playerID', 'teamID', 'fullName', 'pointsPlayed', 'assists', 'goals', 'hockeyAssists', 'completions', 'throwaways', 'stalls', 'yardsReceived', 'yardsThrown', 'hucksCompleted', 'drops',
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
    
def write_col(col, roster_stats, teamID):
    col.write(teamID.capitalize())
    write_stats = roster_stats[roster_stats.teamID == teamID].drop(['playerID','teamID'], axis=1).set_index('fullName')
    col.write(write_stats[write_stats.pointsPlayed > 0])


def setup():
    st.set_page_config(layout='wide')
    css = '''
    <style>
        [data-testid="stSidebar"]{
            min-width: 0px;
            max-width: 200px;
        }
    </style>
    '''
    st.markdown(css, unsafe_allow_html=True)
    st.title('Game Dashboard')


def main():
    setup()

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

        features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
        game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
        game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')
        fig = plot_game(game_prob, game.iloc[0].gameID, features)
        st.plotly_chart(fig)


        roster_stats = get_roster_stats(game.iloc[0].gameID)
        col1, col2 = st.columns(2)
        write_col(col1, roster_stats, game.iloc[0].homeTeamID)
        write_col(col2, roster_stats, game.iloc[0].awayTeamID)

if __name__ == '__main__':
    main()