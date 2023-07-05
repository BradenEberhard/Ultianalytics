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

def main():
    st.title("AUDL Dashboard")
    st.caption("Braden Eberhard, braden.ultimate@gmail.com, 2023")
    st.subheader("Overview")
    st.write("""This dashboard is my naive attempt at visualizing and analyzing the information available through the AUDL's API. """)
    with st.expander("Win Probability Archive"):
        st.write("""This page is designed to visualize win probabilities for completed AUDL games. It uses an LSTM that considers various gameplay dynamics and features, such as thrower coordinates, possession details, game quarter, scores, and score difference.""")
    with st.expander("Throwing Direction"):
        st.write("""This page condenses each players throws into a polar histogram and shows usage, efficiency and trends in throwing.""")
        

    



if __name__ == '__main__':
    main()