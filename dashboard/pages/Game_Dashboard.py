import streamlit as st
import pandas as pd
import numpy as np
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams
from audl.stats.endpoints.gamestats import GameStats
from audl.stats.endpoints.playergamestats import PlayerGameStats
from probability_model import GameProbability
import plotly.graph_objects as go
from audl.stats.endpoints.gameevents import GameEventsProxy
from plotly.subplots import make_subplots
from PIL import Image

##TODO penalties, Scoreboard, histograms, team stat comparison, pulling data


def get_bin_data(df, nbinsx, nbinsy):
    hist, xedges, yedges = np.histogram2d(df['throwerX'], df['throwerY'], bins=[nbinsx, nbinsy])
    x_coords = []
    y_coords = []
    counts = []
    for i in range(nbinsx):
        for j in range(nbinsy):
            x = (xedges[i] + xedges[i+1]) / 2
            y = (yedges[j] + yedges[j+1]) / 2
            count = hist[i][j]
            x_coords.append(x)
            y_coords.append(y)
            counts.append(count)
    return x_coords, y_coords, counts


def shot_plot(game_throws, is_home_team, nbinsx=10, nbinsy=15):
    shots = game_throws[game_throws.is_home_team == is_home_team].dropna(subset=['throwerX', 'throwerY'])
    x_coords, y_coords, counts = get_bin_data(shots, nbinsx, nbinsy)
    # Create the figure
    fig = make_subplots(rows=2, cols=2,
                    row_heights=[0.2, 0.8],
                    column_widths=[0.7, 0.3],
                    vertical_spacing = 0.02,
                    horizontal_spacing = 0.02,
                    shared_yaxes=True,
                    shared_xaxes=False)

    # Add the bar chart
    fig.add_trace(go.Violin(
        x=shots.throwerX,
        name='',
        hoverinfo='none',
        line_color='#26828E'
    ), row=1, col=1)

    fig.add_trace(go.Violin(
        y=shots.throwerY,
        name='',
        hoverinfo='none',
        line_color='#26828E'
    ), row=2, col=2)

    # Add the main scatter plot
    fig.add_trace(go.Scatter(
        x=x_coords, y=y_coords, mode='markers', name='markers',
        marker=dict(
            size=counts, sizemode='area', sizeref=(2. * max(counts) / ((300 / nbinsx) ** 2)), sizemin=2.5,
            color=counts,  # Set the color to the counts using the "viridis" color scheme
            colorscale='viridis',  # Set the color scale to "viridis"
            line=dict(width=1, color='#333333'), symbol='circle',
            colorbar=dict(title='Counts')  # Add a color bar with the title "Counts"
        ),
        hovertemplate='Count: %{text}<extra></extra>',
        text=[int(x) for x in counts]
    ), row = 2, col = 1)

    # Add black horizontal lines at y = 20 and y = 100
    fig.add_shape(type='line', x0=-27, y0=20, x1=27, y1=20, line=dict(color='black', width=1), row=2, col=1)
    fig.add_shape(type='line', x0=-27, y0=100, x1=27, y1=100, line=dict(color='black', width=1), row=2, col=1)
    fig.add_shape(type='line', x0=-27, y0=0, x1=27, y1=0, line=dict(color='black', width=1), row=2, col=1)
    fig.add_shape(type='line', x0=-27, y0=120, x1=27, y1=120, line=dict(color='black', width=1), row=2, col=1)
    fig.add_shape(type='line', x0=-27, y0=0, x1=-27, y1=120, line=dict(color='black', width=1), row=2, col=1)
    fig.add_shape(type='line', x0=27, y0=0, x1=27, y1=120, line=dict(color='black', width=1), row=2, col=1)

    fig.update_layout(
        xaxis=dict(range=[-27, 27], showticklabels=False),  # Apply x-axis range to the scatter plot
        yaxis=dict(range=[0, None]),  # Apply y-axis range to the scatter plot
        xaxis2=dict(range=[-27, 27]),
        yaxis2=dict(range=[0, 120]),  
        showlegend=False,
        width=600,
        height=600,
        margin=dict(t=50, b=50, l=50, r=50),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)

    return fig


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
    
    home_logo = Image.open(f"./logos/{home_team.lower()}.png")
    away_logo = Image.open(f"./logos/{away_team.lower()}.png")
    fig.layout.images = [dict(
        source=home_logo,
        xref="paper", yref="paper",
        x=0, y=1,
        sizex=0.2, sizey=0.2,
        xanchor="left", yanchor="top"
      ), dict(
        source=away_logo,
        xref="paper", yref="paper",
        x=0, y=0,
        sizex=0.2, sizey=0.2,
        xanchor="left", yanchor="bottom"
      )]
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
    
def write_col(col, roster_stats, teamID, is_home_team, game_throws):
    col.write(teamID.capitalize())
    logo = Image.open(f"./logos/{teamID.lower()}.png")
    col.write(logo)
    write_stats = roster_stats[roster_stats.teamID == teamID].drop(['playerID','teamID'], axis=1).set_index('fullName')
    col.write(write_stats[write_stats.pointsPlayed > 0])
    col.plotly_chart(shot_plot(game_throws, is_home_team, 10, 15), use_container_width=True)


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
    game_events = GameEventsProxy()
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
        gameID = game.iloc[0].gameID
        game_throws = game_events.get_throws_from_id(gameID)
        st.write(get_box_scores(gameID))
        

        features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
        game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
        game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')
        fig = plot_game(game_prob, gameID, features)
        st.plotly_chart(fig)


        roster_stats = get_roster_stats(gameID)
        col1, col2 = st.columns(2)
        write_col(col1, roster_stats, game.iloc[0].homeTeamID, True, game_throws)
        write_col(col2, roster_stats, game.iloc[0].awayTeamID, False, game_throws)

if __name__ == '__main__':
    main()