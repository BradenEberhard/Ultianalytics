import streamlit as st
from probability_model import GameProbability
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import mpld3
from mpld3 import plugins
import streamlit.components.v1 as components
import plotly.graph_objects as go
from PIL import Image
import os.path 
import streamlit_analytics


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
    
    if os.path.isfile(f"./logos/{home_team.lower()}.png") and os.path.isfile(f"./logos/{away_team.lower()}.png"):
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

def main():
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
    st.title("Win Probability Archive")
    with st.expander("Instructions"):
        st.write("""Since game event data is only available starting in 2021 you can filter by the year after that point and by team. Once both these fields are chosen you can pick which game(s) you would like to see. Click the checkbox to immediately select every possible game with the provided filters. Hover over the plots to see the score and time left in the quarter. Between my rudimentary front-end skills and the basic framework I am using each graph takes a few seconds to load.""")
    with st.expander("Model Workings"):
        st.write("""
The model was generated using an LSTM neural network, a powerful type of recurrent neural network known for its ability to capture sequential patterns. It leverages the inherent sequential nature of the game by considering a range of features related to the gameplay dynamics. These features include the thrower's coordinates, the possession number, the type of possession throw, the game quarter, the quarter point, whether the team is playing at home, the home team's score, the away team's score, the total points scored so far, the number of times the prediction has been made, and the score difference between the two teams.

To ensure the model's reliability and effectiveness, the dataset was carefully divided into testing and training sets. This division allows for the evaluation and validation of the model's performance by training it on a subset of the data and assessing its accuracy on unseen data during testing.

To further enhance the training process, data augmentation techniques were applied to the dataset. In particular, the dataset was augmented by flipping the home and away teams and changing the side of the field the disc is on. These transformations introduce additional variations and scenarios for the model to learn from, making it more robust and better able to generalize to unseen situations.

During the model development process, other approaches such as Logistic Regression and XGBoost were explored. However, the LSTM model consistently demonstrated similar performance with around 74 percent accuracy and 0.89 AUC (Area Under the Curve). The LSTM's inherent ability to capture nonlinear relationships and effectively handle sequential data, combined with its visually smoother output, particularly in response to scoring events, made it the preferred choice. Additionally, the LSTM model exhibited a better understanding of the game dynamics, recognizing that small leads matter less in the beginning of the game and gain more significance as the game progresses.

**NOTE: many games have issues with the data especially with timing such as a later point having more time left than a previous point. In these cases, the data was excluded. Because of this, some points and/or games are not available""")

    features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
    game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
    game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')


    modification_container = st.container()
    with modification_container:
        with st.expander('Filters'):
            year_filter = st.multiselect('Year(s)', ['2021', '2022', '2023'])
            team_filter = st.multiselect('Team(s)', ['Union', 'Shred', 'Spiders', 'Sol', 'Cascades', 'Mechanix', 'Windchill', 'Aviators', 'Royal', 'Breeze', 'Rush', 'Phoenix', 'Hustle', 'Alleycats', 'Legion', 'Havoc', 'Flyers', 'Nitro', 'Thunderbirds', 'Empire', 'Glory', 'Summit', 'Outlaws', 'Growlers', 'Radicals', 'Cannons'])
            team_filter = [x.lower() for x in team_filter]
            DATA = game_prob.data
            DATA = DATA[(DATA.home_teamID.isin(team_filter)) | (DATA.away_teamID.isin(team_filter))]
            all = st.checkbox("Select all")
            with st.container():
                # team_options = st.multiselect("Teams", [element for element in DATA.gameID.unique() if any(substring in element for substring in year_filter)])
                if all:
                    team_options = st.multiselect("Select one or more options:",
                        [element for element in DATA.gameID.unique() if any(substring in element for substring in year_filter)],[element for element in DATA.gameID.unique() if any(substring in element for substring in year_filter)])
                else:
                    team_options = st.multiselect("Teams", [element for element in DATA.gameID.unique() if any(substring in element for substring in year_filter)])

            for team in sorted(team_options):
                fig = plot_game(game_prob, team, features)
                st.plotly_chart(fig)


if __name__ == '__main__':
    main()