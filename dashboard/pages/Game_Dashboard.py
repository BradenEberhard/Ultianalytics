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

##TODO Scoreboard

@st.cache_resource
class DataCache:
    def __init__(self):
        pass

    def get_box_scores(self):
        box_scores = self.game_stats.get_boxscores()
        box_scores.index.name = None
        box_scores.index = [x.capitalize() for x in box_scores.index]
        return box_scores
    
    def get_roster_stats(self):
        game_stats_df = self.player_game_stats.get_request_as_df(f'playerGameStats?gameID={self.gameID}')
        game_stats_df = pd.merge(game_stats_df.player.apply(pd.Series), game_stats_df.drop('player', axis=1), left_index=True, right_index=True)
        game_stats_df['fullName'] = game_stats_df['firstName'] + ' ' + game_stats_df['lastName']
        game_stats_df['pointsPlayed'] = game_stats_df['oPointsPlayed'] + game_stats_df['dPointsPlayed']
        stats_cols = ['playerID', 'teamID', 'fullName', 'pointsPlayed', 'assists', 'goals', 'hockeyAssists', 'completions', 'throwaways', 'stalls', 'yardsReceived', 'yardsThrown', 'hucksCompleted', 'drops',
        'blocks', 'callahans']
        return game_stats_df[stats_cols]
    
    def set_player_name_dict(self):
        name_dict = {}
        for _, row in self.roster_stats.iterrows():
            name_dict[f'{row.playerID}'] = row['fullName']
        self.name_dict = name_dict
    
    def update_pullers(self):
        idxs = self.pulls.puller
        new_idxs = []
        for idx in idxs:
            if idx in self.name_dict:
                new_idxs.append(self.name_dict[idx])
            else:
                new_idxs.append(idx)
        self.pulls.puller = new_idxs

    def update_game(self):
        self.game_events.get_request(f'games?gameIDs={self.gameID}')
        self.game = pd.DataFrame(self.game_events.current_request)

    def set_game(self, gameID):
        self.gameID = gameID
        self.game_stats = GameStats(gameID)
        self.game_events = GameEventsProxy()
        self.player_game_stats = PlayerGameStats()
        self.game_throws = self.game_events.get_throws_from_id(gameID)
        self.box_scores = self.get_box_scores()
        self.roster_stats = self.get_roster_stats()
        self.homeTeamID = self.game.iloc[0].homeTeamID.lower()
        self.awayTeamID = self.game.iloc[0].awayTeamID.lower()
        self.penalties = self.game_events.get_penalties_from_id(gameID)
        self.team_stats = self.game_stats.get_team_stats()
        self.set_player_name_dict()
        self.pulls = self.game_events.get_pulls_from_id(gameID)
        self.update_pullers()
        self.update_game()

    
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


def shot_plot(game_throws, is_home_team, teamID, nbinsx=10, nbinsy=15):
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
        title=f'{teamID.capitalize()} Throws: {int(np.sum(counts))}',
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


def plot_game(game_prob, gameID, max_length = 629):
    features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
    test_game = game_prob.data[game_prob.data.gameID == gameID]
    if len(test_game) == 0:
        st.write('no data')
        return
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
    
def write_col(col, cache, is_home_team, teamID):
    write_stats = cache.roster_stats[cache.roster_stats.teamID == teamID].drop(['playerID','teamID'], axis=1).set_index('fullName')
    col.write(write_stats[write_stats.pointsPlayed > 0])
    col.plotly_chart(shot_plot(cache.game_throws, is_home_team, teamID, 10, 15), use_container_width=True)

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


def print_logos(cache):
    left_col, right_col = st.columns(2)
    logo = Image.open(f"./logos/{cache.homeTeamID}.png")
    left_col.image(logo, width=150)

    logo = Image.open(f"./logos/{cache.awayTeamID}.png")
    right_col.image(logo, width=150)

def plot_pulls(cache, col1, col2):
    def pull_helper(indexer):
        team_pullers = pd.DataFrame(pulls[indexer].groupby('puller').puller.count())
        team_pullers.index.name = None
        team_pullers = team_pullers.sort_values('puller', ascending = False)
        team_pullers.columns = ['Pull Count']
        team_pullers.sort_values('Pull Count', ascending = False)
        team_pullers.loc['In Bounds'] = f'{pulls[indexer].in_bounds.sum()} ({pulls[indexer].in_bounds.mean()*100:.1f}%)'
        rollers = (pulls[indexer].pullX > 25) | (pulls[indexer].pullX < -25)
        team_pullers.loc['Roller'] = f'{rollers.sum()} ({rollers.mean()*100:.1f}%)'
        return team_pullers

    pulls = cache.pulls
    home_team_pulls = pull_helper(pulls.is_home_team)
    away_team_pulls = pull_helper(~pulls.is_home_team)
    col1.write(home_team_pulls)
    col2.write(away_team_pulls)

def get_team_stats(cache):
    df = cache.team_stats
    def get_frac_string(row, names):
        for name in names:
            numerator = f'{name}Numer'
            denominator = f'{name}Denom'
            row[f'{name}'] = f'{row[numerator]}/{row[denominator]} ({row[numerator]/row[denominator]:.1f}%)'
        return row

    df = df.apply(get_frac_string, args=(['completions', 'hucks'],) ,axis=1)

    def get_score_string(row, names):
        for name in names:
            numerator = f'{name}Scores'
            denominator = f'{name}Possessions'
            row[f'{name}'] = f'{row[numerator]}/{row[denominator]} ({row[numerator]/row[denominator]*100:.1f}%)'
        return row

    df = df.apply(get_score_string, args=(['oLine', 'dLine', 'redZone'],) ,axis=1)
    df.index = [cache.homeTeamID.capitalize(), cache.awayTeamID.capitalize()]
    cols = ['blocks', 'turnovers', 'completions', 'hucks', 'oLine', 'dLine', 'redZone']
    df = df[cols].T
    df.index = [x.capitalize() for x in df.index]
    df.loc['Penalties'] = list(cache.penalties)
    return df

def refresh_stats(cache):
    cache.set_game(cache.gameID)

def write_scoreboard(cache):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    logo = Image.open(f"./logos/{cache.homeTeamID}.png")
    col1.image(logo, width=50)
    
    col2.header(cache.game.iloc[0].homeScore)
    col3.header(cache.game.iloc[0].awayScore)

    logo = Image.open(f"./logos/{cache.awayTeamID}.png")
    col4.image(logo, width=50)
    col5.header(cache.game.iloc[0].status)

    col6.button('Refresh', on_click=refresh_stats, args=(cache,))



def main():
    setup()
    data_cache, games_df, teams_df, game_filter = DataCache(), get_games_df(), get_teams_df(), '<select>'
    with st.expander('Filters'):
        team_filter = st.selectbox('Team', [x.capitalize() for x in teams_df.teamID.unique() if 'allstar' not in x])
        team_filter = team_filter.lower()
        year_filter = st.selectbox('Year', ['<select>'] + sorted(teams_df[teams_df.teamID == team_filter].year.astype(int)), 0)
        if year_filter != '<select>':
            team_games = games_df[(games_df.homeTeamID == team_filter) | (games_df.awayTeamID == team_filter)]
            team_games = team_games[team_games.startTimestamp.apply(lambda x:int(x[:4])) == year_filter]
            game_filter = st.selectbox('Game', ['<select>'] + sorted(team_games.name, key= lambda x:x[-8:]), 0)
    
    if game_filter != '<select>':
        data_cache.game = games_df[games_df.name == game_filter]
        data_cache.set_game(data_cache.game.iloc[0].gameID)
        write_scoreboard(data_cache)
        col1, col2 = st.columns(2)
        col2.write(data_cache.box_scores)
        col1.write(get_team_stats(data_cache))
        
        game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
        game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')
        fig = plot_game(game_prob, data_cache.gameID)
        if fig is not None:
            st.plotly_chart(fig)

        
        print_logos(data_cache)
        col1, col2 = st.columns(2)
        plot_pulls(data_cache, col1, col2)
        col1, col2 = st.columns(2)
        write_col(col1, data_cache, True, data_cache.homeTeamID)
        write_col(col2, data_cache, False, data_cache.awayTeamID)

if __name__ == '__main__':
    main()