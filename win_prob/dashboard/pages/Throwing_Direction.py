import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

def process_throws_df(path='../data/raw/all_games_0626.csv'):
    throws_df = pd.read_csv(path)
    throws_df.dropna(subset=['thrower_x', 'thrower_y'], inplace=True)
    throws_df['x_change'] = throws_df['receiver_x'] - throws_df['thrower_x']
    throws_df['y_change'] = throws_df['receiver_y'] - throws_df['thrower_y']
    throws_df['radians'] = np.arctan2(throws_df.receiver_y - throws_df.thrower_y, throws_df.receiver_x - throws_df.thrower_x)
    throws_df['degrees'] = np.rad2deg(throws_df['radians'])
    return throws_df

def create_player_bar_polar_chart(throws_df, player, column='thrower', bins=12):
    if column not in ['thrower', 'receiver']:
        raise ValueError("Invalid column name. Choose either 'thrower' or 'receiver'.")

    count, plot = np.histogram(throws_df[throws_df[column] == player].degrees, bins=bins, range=(-180, 180))
    turnover_count, turnover_plot = np.histogram(
        throws_df[(throws_df[column] == player) & throws_df.turnover].degrees, bins=bins, range=(-180, 180)
    )
    fig = create_bar_polar_chart(count, plot, player, turnover_count, column)
    return fig

def calculate_midpoints(sorted_array):
    midpoints = []
    
    for i in range(1, len(sorted_array)):
        midpoint = (sorted_array[i] + sorted_array[i-1]) / 2
        midpoints.append(midpoint)
    
    return midpoints

def create_bar_polar_chart(count, plot, player, turnover_count, column):
    if column == 'thrower':
        marker_color = count
        hover_text = [f"Total Count: {c}<br>Turnovers: {t} ({t/c*100:.1f}%)<extra></extra>" for c, t in zip(count, turnover_count)]
        colorscale='Blugrn'
    else:
        marker_color = count
        hover_text = [f"Total Count: {c}<extra></extra>" for c in count]
        colorscale='YlOrRd'
    hover_text = [text.replace('<br>trace=bar', '') for text in hover_text]


    fig = go.Figure(data=go.Barpolar(
        r=count,
        theta=calculate_midpoints(plot),
        marker_color=marker_color,
        hovertemplate=hover_text,
        marker=dict(
            color=marker_color,
            colorscale=colorscale,
            showscale=True
        )
    ))

    fig.update_layout(
        title={
            'text': player,
            'x': 0.5,  # Center the title horizontally
            'xanchor': 'center',  # Anchor the title to the center
            'yanchor': 'top'  # Position the title at the top of the plot
        },
        polar=dict(
            bargap=0,
            angularaxis=dict(
                ticktext=['90°', 'attacking endzone', '270°', 'defending endzone'],
                tickvals=[0, 90, 180, 270],
            ),
            radialaxis=dict(
                tickfont=dict(
                    color='black',
                    size=12
                )
            )
        )
    )

    return fig

def main():

    throws_df = process_throws_df()

    modification_container = st.container()
    with modification_container:
        player_filter = st.multiselect('Year(s)', throws_df.thrower.unique())
        for player in player_filter:
            fig = create_player_bar_polar_chart(throws_df, player)
            st.write(fig)


    

if __name__ == '__main__':
    main()