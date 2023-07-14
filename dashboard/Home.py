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
import streamlit_analytics


##TODO track website analytics
##TODO player dashboard
##TODO team dashboard
##TODO transfer to Dash
##TODO detailed README

def main():
    st.title("AUDL Dashboard")
    st.caption("braden.ultimate@gmail.com, 2023")
    st.header("""General Information""")
    st.write("""Welcome to my fun project using the AUDL's data API to visualize different aspects of ultimate frisbee. To get started, choose any of the features from the sidebar and start exploring! Look through past games, examine individual throwers tendencies or follow along with live games. 
                 If you're looking for deeper insights, you can read more about each page below.""")
    with st.expander("Game Dashboards"):
        st.write("""'This Weeks Games' and 'Game Dashboard Archive' both use a similar dashboard to display a games breakdown. This includes: team stats, pulls, win probability, and shot charts. You can follow live games in 'This Weeks Games' with a note that the AUDL updates their data every few minutes so certain portions of it may lag behind real time. Even so, there are some really cool things you can follow not available anywhere else such as a custom AI model that tracks win probability, shot charts and more. Any game from the past week is available here, otherwise you can find it in the archives. If you want to use it for scouting purposes you can follow pulling trends or see where teams like to have the disc (e.g. the pheonix don't mind spending a lot of time in their own endzone while the breeze get a lot of redzone touches)""")
    with st.expander("Win Probability Archive"):
        st.write("""This page is designed to visualize win probabilities for completed AUDL games. It uses an LSTM that considers various gameplay dynamics and features, such as thrower coordinates, possession details, game quarter, scores, and score difference. You can read more about the model on the page. While it isn't perfect you can see things the model seems to pick up on that humans might not normally think of. The sequential nature of an LSTM makes interesting predictions in the middle of the game (Q2/3) that other models don't pick up on such as if a team starts mounting a comeback after being down multiple scores, the model often isn't convinced they will win until they are up by multiple scores.""")
    with st.expander("Throwing Direction"):
        st.write("""This page condenses each players throws into a polar histogram and shows usage, efficiency and trends in throwing. I have a lot more to do looking into individual player stats but for now this is a unique way to see what players do with the disc in their hands and off the disc. In essence, its a graph of player tendencies. Compare graphs like Elijah Jaime to one like Matt Gouchoe-Hanas and see the obvious difference between handlers and cutters. Additionally you can see that players like Nethercutt has a preference for his flick and David Cranston likes to get open on the flick side laterally from the disc""")
    with st.expander("Problems and Errors?"):
        st.write("""This is of course, just a side project and i don't have the time to really make this a usable product. Plus there are plenty of issues with the data on the end of the AUDL (I can't complain though since they have by far the best store of data for the sport by a long shot). If you see an error it may be a problem with the specific game/player and you may have to look for something else. Usually refreshing the page should give you a fresh start.""")
    with st.expander("""Where can I see more?"""):
        st.write("""Interested in more stats in ultimate? One of my good friends has been doing a blog using the same data: https://analysisbycomet.substack.com""")
    with st.expander("""Contact Me"""):
        st.write("""I'm happy to hear from you for whatever reason. Have feedback, questions on methods, or want to contribute you can contact me at braden.ultimate@gmail.com or look at the code yourself https://github.com/BradenEberhard/Ultianalytics""")
 
if __name__ == '__main__':
    streamlit_analytics.start_tracking()
    main()
    streamlit_analytics.stop_tracking()