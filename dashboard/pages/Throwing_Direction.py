import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit_analytics

years_to_date = ['2021', '2022', '2023']

@st.cache_data
def process_throws_df(path='./data/raw/all_games_0704.csv'):
    print('check', path)
    throws_df = pd.read_csv(path)
    throws_df.dropna(subset=['thrower_x', 'thrower_y'], inplace=True)
    throws_df['x_change'] = throws_df['receiver_x'] - throws_df['thrower_x']
    throws_df['y_change'] = throws_df['receiver_y'] - throws_df['thrower_y']
    throws_df['radians'] = np.arctan2(throws_df.receiver_y - throws_df.thrower_y, throws_df.receiver_x - throws_df.thrower_x)
    throws_df['degrees'] = np.rad2deg(throws_df['radians'])
    throws_df['year'] = throws_df.gameID.apply(lambda x:x[:4])
    return throws_df

def create_player_bar_polar_chart(throws_df, player, column='thrower', bins=12):
    if column not in ['thrower', 'receiver']:
        raise ValueError("Invalid column name. Choose either 'thrower' or 'receiver'.")

    count, plot = np.histogram(throws_df[throws_df[column] == player[0]].degrees, bins=bins, range=(-180, 180))
    turnover_count, turnover_plot = np.histogram(
        throws_df[(throws_df[column] == player[0]) & throws_df.turnover].degrees, bins=bins, range=(-180, 180)
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
        title=f'{player[1]} Throws'
    else:
        marker_color = count
        hover_text = [f"Total Count: {c}<extra></extra>" for c in count]
        colorscale='YlOrRd'
        title=f'{player[1]} Catches'
    hover_text = [text.replace('<br>trace=bar', '') for text in hover_text]

    title = title + f' Total: {np.sum(count)}'
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
            'text': title,
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

@st.cache_data
def get_players(path='./data/raw/players_0704.csv'):
    return pd.read_csv(path)

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
    st.title('Throwing Direction')
    throws_df = process_throws_df()
    players = get_players()
    players = players[players.playerID.isin(throws_df.thrower.unique())]

    with st.expander('Instructions'):
        st.write('''Since game event data is only available starting in 2021 you can filter by the year after that point and by team. The first two filters make it easier to find the player(s) you want to see limiting the list to the people who played on a given team in a year. The next year filter determines which season(s) throws to include in the visualization. I recommend selecting players one at a time when possible as each additional player takes a few seconds more.''')

    with st.expander('Analysis'):
        st.write('''while refraining from making any claims there are lots of trends you can see. Things ranging from who picks up the disc (having more throws than receptions), handlers vs cutters vs hybrids (based on distribution), throwing tendencies (flick vs backhand) and more.''')


    modification_container = st.container()
    with modification_container:
        with st.expander('Filters'):
            teams_filter = st.multiselect('Team(s)', sorted([x.capitalize() for x in players.teamID.unique()]))
            teams_filter = [x.lower() for x in teams_filter]
            new_players = players[players.teamID.isin(teams_filter)]
            year_filter = st.multiselect('Year(s) on Team', years_to_date)
            year_filter = [int(x) for x in year_filter]
            new_players = new_players[new_players.year.isin(year_filter)]
            all = st.checkbox("Select all")
            with st.container():
                # team_options = st.multiselect("Teams", [element for element in DATA.gameID.unique() if any(substring in element for substring in year_filter)])
                if all:
                    player_filter = st.multiselect('Player(s)', sorted((new_players['firstName'] + ' ' + new_players['lastName']).unique()),
                                                sorted((new_players['firstName'] + ' ' + new_players['lastName']).unique()))
                else:
                    player_filter = st.multiselect('Player(s)', sorted((new_players['firstName'] + ' ' + new_players['lastName']).unique()))


            throw_year_filter = st.multiselect('Year(s) for Throws', years_to_date)
            new_throws_df = throws_df[throws_df.year.isin(throw_year_filter)]

            col1, col2 = st.columns(2)
            for player in player_filter:
                first_name, last_name = player.split(' ')
                playerID = players[(players.firstName==first_name) & (players.lastName==last_name)].iloc[0].playerID
                player = (playerID, player)
                fig = create_player_bar_polar_chart(new_throws_df, player, 'thrower')
                col1.plotly_chart(fig, use_container_width=True)
                fig = create_player_bar_polar_chart(new_throws_df, player, 'receiver')
                col2.plotly_chart(fig, use_container_width=True)
    

if __name__ == '__main__':
    streamlit_analytics.start_tracking()
    main()
    streamlit_analytics.stop_tracking()