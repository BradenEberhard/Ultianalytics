import streamlit as st
import streamlit_analytics
import pandas as pd
import numpy as np
from audl.stats.endpoints.games import Games
from audl.stats.endpoints.teams import Teams
from audl.stats.endpoints.gamestats import GameStats
from audl.stats.endpoints.playergamestats import PlayerGameStats
from audl.stats.endpoints.gameevents import GameEvents
from probability_model import GameProbability, process_games
import plotly.graph_objects as go
from audl.stats.endpoints.gameevents import GameEventsProxy
from plotly.subplots import make_subplots
from PIL import Image
from datetime import datetime, timedelta
import plotly.express as px
from audl.stats.endpoints.teamstats import TeamStats
from streamlit_autorefresh import st_autorefresh



##TODO If game is live update every 30 seconds

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

        game_events = GameEvents(gameID, self.game_events)
        game_events.process_game_events()
        game_df = game_events.get_events_df(True, True, True)
        self.game_df = process_games(game_df)

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

def plot_team_percents(cache):
    team_stats = cache.team_stats
    stat_cols = ['completionPercentage', 'holdPercentage', 'oLineConversionPercentage', 'breakPercentage', 'dLineConversionPercentage', 'huckPercentage', 'redZoneConversionPercentage']
    team_stats.columns = [x.replace('Perc', 'Percentage').replace('completions', 'completion').replace('hucks', 'huck') for x in team_stats.columns]
    games = Games()
    season_stats = pd.DataFrame(games.get_season_stats())[['teamID', 'teamName'] + stat_cols]

    home_team_stats = team_stats.iloc[0][stat_cols] * 100
    away_team_stats = team_stats.iloc[1][stat_cols] * 100
    homeTeamID = cache.homeTeamID.capitalize()
    awayTeamID = cache.awayTeamID.capitalize()

    fig = go.Figure()

    for col in stat_cols:
        fig.add_trace(go.Box(x=season_stats[col].astype(float), orientation='h', name=col, marker=dict(color='#36454F'), hoverinfo='none',))
    fig.add_trace(go.Scatter(x=home_team_stats, y=stat_cols, mode='markers', marker=dict(color='#16693C'), name='Home Team Averages',
                            text=season_stats[stat_cols].median(),
                            hovertemplate="<br>".join([
                                f"{homeTeamID}"+": %{x:.1f}%",
                                "League Average: %{text:.1f}%"
                                "<extra></extra>",
                            ])))
    fig.add_trace(go.Scatter(x=away_team_stats, y=stat_cols, mode='markers', marker=dict(color='#0D0887'), name='Home Team Averages',
                            text=season_stats[stat_cols].median(),
                            hovertemplate="<br>".join([
                                f"{awayTeamID}"+": %{x:.1f}%",
                                "League Average: %{text:.1f}%"
                                "<extra></extra>",
                            ])))

    custom_labels = ['Completion %', 'Hold %', 'O Line Conversion', 'Break %', 'D Line Conversion', 'Huck Completion %', 'Red Zone Conversion']

    fig.update_layout(title='Percentage Statistics', title_x=0.5,
        showlegend=False,
        yaxis_ticktext=custom_labels,
        yaxis_tickvals=list(range(len(custom_labels)))
    )

    return fig

def plot_game(game_prob, cache):
    features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
    test_game, teams = game_prob.process_new_game(cache.game_df, features)
    home_team, away_team, date = teams[0][0], teams[0][1], teams[0][2][0][:10]
    test_game = test_game.astype(np.float32)
    if len(test_game) == 0:
        st.write('no data')
        return
    out = game_prob.model.predict(test_game.reshape(1, 629, -1))
    df = pd.DataFrame(game_prob.normalizer.inverse_transform(test_game.reshape(629, -1)), columns=features)
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
        txt = f'{home_team.capitalize()}: {int(row.home_team_score)} - {away_team.capitalize()}: {int(row.away_team_score)}<br>{int(minutes)}:{seconds:02d}'
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
    fig.update_layout(title=f'{away_team.capitalize()} at {home_team.capitalize()}', title_x=0.5, xaxis_title="Time Passed", yaxis_title="Win Probability",
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
    left_col, _, right_col = st.columns([2, 7, 2])
    logo = Image.open(f"./logos/{cache.homeTeamID}.png")
    left_col.image(logo, width=150)

    logo = Image.open(f"./logos/{cache.awayTeamID}.png")
    right_col.image(logo, width=150)

def plot_pulls(cache, col1, col2):
    def pull_helper(indexer):
        team_pullers = {}
        team_pullers['In Bounds'] = pulls[indexer].in_bounds.sum()
        rollers = (pulls[indexer].pullX > 25) | (pulls[indexer].pullX < -25)
        team_pullers['Roller'] = rollers.sum()
        team_pullers['In Bounds'] = team_pullers['In Bounds'] - team_pullers['Roller']
        team_pullers['Out of Bounds'] = (~pulls[indexer].in_bounds).sum()

        pullers = pd.DataFrame(pulls[indexer].groupby('puller').puller.count())
        return pullers, pd.Series(team_pullers)

    def pull_plot(team_pullers, team_pulls, team_name):
        # Create the subplot grid with 1 row and 1 column
        fig = make_subplots(rows=1, cols=1)

        # Add the donut chart trace
        fig.add_trace(go.Pie(
            labels=list(team_pullers.index),
            values=team_pullers.values.flatten(),
            name='Pullers',
            marker=(dict(colors=px.colors.sequential.Blues_r)),
            domain={'x': [0.2, 0.8], 'y': [0.2, 0.8]},
            text=list(team_pullers.index + ' ' + team_pullers.values.flatten().astype(str)),
            textfont=dict(color='black')
        ))

        # Add the pie chart trace in the center
        fig.add_trace(go.Pie(
            labels=team_pulls.index,
            values=team_pulls.values,
            name='Pulls',
            marker=(dict(colors=px.colors.sequential.Greens_r)),
            hole=0.7,  # Set the hole size to create a donut chart
            domain={'x': [0, 1], 'y': [0, 1]},
            text=list(team_pulls.index + ' ' + team_pulls.values.astype(str)),
        ))

        # Update the layout to display the legend and set its position
        fig.update_layout(title={
                    'text' : f'{team_name} Pulls:{team_pulls.sum()}',
                    'x':0.5,
                    'xanchor': 'center'
                },
            showlegend=False,
            legend=dict(
                x=0.7,
                y=0.5
            ),
            uniformtext_minsize=10, uniformtext_mode='hide'
        )
        fig.update_traces(
            hovertemplate="%{label}: %{value}<br>(%{percent})<extra></extra>",
            textposition='inside',
            opacity=0.8,
        )

        # Show the plot
        return fig
    
    pulls = cache.pulls
    home_team_pullers, home_team_pulls = pull_helper(pulls.is_home_team)
    away_team_pullers, away_team_pulls = pull_helper(~pulls.is_home_team)
    fig = pull_plot(home_team_pullers, home_team_pulls, cache.homeTeamID.capitalize())
    col1.plotly_chart(fig, use_container_width=True)
    fig = pull_plot(away_team_pullers, away_team_pulls, cache.awayTeamID.capitalize())
    col2.plotly_chart(fig, use_container_width=True)

def get_team_stats(cache):
    df = cache.team_stats
    def get_frac_string(row, names):
        for name in names:
            numerator = f'{name}Numer'
            denominator = f'{name}Denom'
            if row[denominator] == 0:
                row[f'{name}'] = '0/0 (0%)'
            else:
                row[f'{name}'] = f'{row[numerator]}/{row[denominator]} ({(row[numerator]/row[denominator])*100:.1f}%)'
        return row

    df = df.apply(get_frac_string, args=(['completions', 'hucks'],) ,axis=1)

    def get_score_string(row, names):
        for name in names:
            numerator = f'{name}Scores'
            denominator = f'{name}Possessions'
            if row[denominator] == 0:
                row[f'{name}'] = '0/0 (0%)'
            else:
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
    _, m, r, r2 = st.columns([3, 2, 1, 1])
    status = cache.game.iloc[0].status
    if status != 'Final':
        status = f'{status}'
    m.header(f'Game Status: {status}')
    left_col, right_col = st.columns([4, 6])
    plot_team_stats(cache, left_col)
    right_col.plotly_chart(plot_team_percents(cache), use_container_width=True)
    return r, r2

def display_game(data_cache, games_df, game_filter):
    data_cache.game = games_df[games_df.name == game_filter]
    if data_cache.game.iloc[0].status == 'Upcoming' or data_cache.game.iloc[0].status == 'About to Start':
        st.header(f'Game is {data_cache.game.iloc[0].status}')
        if data_cache.game.iloc[0].status != 'Final':
            st.button('Refresh', on_click=refresh_stats, args=(data_cache,))
    else:
        data_cache.set_game(data_cache.game.iloc[0].gameID)
        col6, col7 = write_scoreboard(data_cache)
        col6.button('Refresh', on_click=refresh_stats, args=(data_cache,))
        continuous_refresh = col7.button('Continuous Refresh (every 30 seconds)', on_click=refresh_stats, args=(data_cache,))
        if continuous_refresh:
            count = st_autorefresh(interval=1000*30, limit=100, key="game_refresh")

        game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
        game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')
        fig = plot_game(game_prob, data_cache)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        l_col, r_col = st.columns(2)
        l_col.plotly_chart(shot_plot(data_cache.game_throws, True, data_cache.homeTeamID, 10, 15), use_container_width=True)
        r_col.plotly_chart(shot_plot(data_cache.game_throws, False, data_cache.awayTeamID, 10, 15), use_container_width=True)
        plot_pulls(data_cache, l_col, r_col)
        with st.expander('Roster Stats'):
            print_logos(data_cache)
            l2_col, r2_col = st.columns(2)
            write_stats = data_cache.roster_stats[data_cache.roster_stats.teamID == data_cache.homeTeamID].drop(['playerID','teamID'], axis=1).set_index('fullName')
            l2_col.write(write_stats[write_stats.pointsPlayed > 0])
            write_stats = data_cache.roster_stats[data_cache.roster_stats.teamID == data_cache.awayTeamID].drop(['playerID','teamID'], axis=1).set_index('fullName')
            r2_col.write(write_stats[write_stats.pointsPlayed > 0])

def plot_team_stats(cache, col):
    try:
        home_score = cache.box_scores.loc[cache.homeTeamID.capitalize()]['T'].astype(int)
    except:
        home_score = 0
    try:
        away_score = cache.box_scores.loc[cache.awayTeamID.capitalize()]['T'].astype(int)
    except:
        away_score = 0

    df = cache.team_stats[['completionsNumer', 'hucksNumer', 'blocks', 'turnovers', 'redZonePossessions']]
    df.index = [cache.homeTeamID.capitalize(), cache.awayTeamID.capitalize()]
    df['Penalties'] = cache.penalties
    
    df = df.T
    df[f'{cache.homeTeamID.capitalize()}_prob'] = df.apply(lambda x: round((x.iloc[0]/x.sum())*100, 1), axis=1)
    df[f'{cache.awayTeamID.capitalize()}_prob'] = 100 - df[f'{cache.homeTeamID.capitalize()}_prob']
    df['Category'] = ['Completions', 'Hucks', 'Blocks', 'Turnovers', 'Red Zone<br>Possessions', 'Penalties']
    df.index = df.Category
    df = df.reindex(['Completions', 'Hucks', 'Blocks', 'Turnovers', 'Red Zone<br>Possessions', 'Penalties'])
    mark_color=['#31688E', '#35B779']
    fig = go.Figure()
    for i, team in enumerate([cache.homeTeamID.capitalize(), cache.awayTeamID.capitalize()]):
        fig.add_trace(go.Bar( 
        x=df[f'{team}_prob'], y=df['Category'],
        showlegend=False,
        orientation='h',
        marker=dict(
            color=mark_color[i]
        ),
        width=0.8,
        text=df[team],
        textposition='inside', insidetextanchor='middle',
        hoverinfo='skip'
    ))
    fig.update_layout(
                  title=dict(text=f'{home_score} - {away_score}', x=0.52, y=1, yanchor="bottom",font=dict(size=32), automargin=True, yref='paper'),
                  yaxis_title='',
                  xaxis_title='',
                  barmode='stack',
                  yaxis=dict(autorange="reversed"),
                  xaxis=dict(
        showticklabels=False  # Remove the x-axis tick labels
    ))

    home_logo = Image.open(f"./logos/{cache.homeTeamID.lower()}.png")
    away_logo = Image.open(f"./logos/{cache.awayTeamID.lower()}.png")
    fig.add_layout_image(
        dict(
            source=home_logo,
            xref="paper", yref="paper",
            x=0, y=1,
            sizex=0.25, sizey=0.25,
            xanchor="center", yanchor="bottom"
        )
    )

    fig.add_layout_image(
        dict(
            source=away_logo,
            xref="paper", yref="paper",
            x=1, y=1,
            sizex=0.25, sizey=0.25,
            xanchor="right", yanchor="bottom"
        )
    )
    col.plotly_chart(fig, use_container_width=True)

def main():
    setup()
    data_cache, games_df, game_filter = DataCache(), get_games_df(), '<select>'
    with st.expander('This Week\'s Game(s)'):
        today = datetime.today().date()
        last_week = datetime.today().date() - timedelta(days=7)
        games_df['dates'] = [pd.to_datetime(x).date() for x in games_df.startTimestamp]
        this_weeks_games = games_df[(games_df.dates <= today) & (games_df.dates >= last_week)]
        game_filter = st.selectbox('Game', ['<select>'] + list(this_weeks_games['name']), 0)
    if game_filter != '<select>':
        display_game(data_cache, games_df, game_filter)
        


        
    
if __name__ == '__main__':
    streamlit_analytics.start_tracking()
    main()
    streamlit_analytics.stop_tracking()