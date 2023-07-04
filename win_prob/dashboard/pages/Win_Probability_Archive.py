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

def plot_game(game_prob, gameID, features, max_length = 629):
    test_game = game_prob.data[game_prob.data.gameID == gameID]
    home_team = test_game.home_teamID.iloc[0]
    away_team = test_game.away_teamID.iloc[0]
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
    fig.add_vline(x=12, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=24, line_width=1, line_dash="dash", line_color="black")
    fig.add_vline(x=36, line_width=1, line_dash="dash", line_color="black")
    fig.update_layout(title=f'{home_team} at {away_team} on {gameID[:10]}', title_x=0.5, xaxis_title="Time Passed", yaxis_title="Win Probability",
                    yaxis_range=[0,1], xaxis_range=[0,48], 
                    xaxis = dict(tick0=0,dtick=12,tickvals=[0, 12, 24, 36], ticktext=['Q1', 'Q2', 'Q3', 'Q4']), yaxis = dict(tick0=0,dtick=0.1))
    return fig

def main():
    st.title("Win Probability Archive")
    st.text('Use this page to see how ')
    with st.expander("Model Workings"):
        st.write("""The model was generated using an LSTM neural network, a type of recurrent neural network that excels at 
        capturing sequential patterns. It takes into account various features related to the game, such as the coordinates of the thrower, 
        the possession number, the type of possession throw, the game quarter, the quarter point, whether the team is playing at home, 
        the home team's score, the away team's score, the total points scored so far, the number of times the prediction has been made, and 
        the score difference between the two teams.

        The data was split into testing and training sets to evaluate and validate the model's performance. This division allows the model 
        to learn from a subset of the data during training and assess its accuracy on unseen data during testing.

        In addition to the split, the dataset was augmented to enhance the model's training process. 
        Data augmentation involves creating new synthetic samples by applying various transformations or perturbations to the existing data. 
        I decided to flip the home and away teams and flip the side of the field the disc is on. 
        By augmenting the dataset, the model becomes more robust to variations and can better generalize to unseen scenarios.
        The augmented dataset provides a diverse range of examples for the model to learn from, enabling it to capture different patterns and variations in the game dynamics. 

        I also attempted other models including Logistic Regression and XGBoost. All models performed similary with around 74 percent accuracy and 0.89 AUC
        I chose to use the LSTM because its inherent ability to capture nonlinear relationships and rely on the sequential format of the data. 
        Visually it also provided additional intuitive advantages including graphs that are much smoother while the other models frequently have sharp changes when a
        point is scored and a slightly better understanding that small leads matter less in the beginning of the game and more near the end.
        """)

    features = ['thrower_x', 'thrower_y', 'possession_num', 'possession_throw',
       'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score',
       'away_team_score','total_points', 'times', 'score_diff']
    game_prob = GameProbability('./data/processed/throwing_0627.csv', normalizer_path='./win_prob/saved_models/normalizer.pkl')
    game_prob.load_model(model_path='./win_prob/saved_models/accuracy_loss_model.h5')


    modification_container = st.container()
    with modification_container:
        st.sidebar.write('Filter Options')
        
        
        year_filter = st.multiselect('Year(s)', ['2021', '2022', '2023'])
        team_filter = st.multiselect('Team(s)', ['union', 'shred', 'spiders', 'sol', 'cascades', 'mechanix', 'windchill', 'aviators', 'royal', 'breeze', 'rush', 'phoenix', 'hustle', 'alleycats', 'legion', 'havoc', 'flyers', 'nitro', 'thunderbirds', 'empire', 'glory', 'summit', 'outlaws', 'growlers', 'radicals', 'cannons'])
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

        for team in team_options:
            fig = plot_game(game_prob, team, features)
            st.plotly_chart(fig)



if __name__ == '__main__':
    main()