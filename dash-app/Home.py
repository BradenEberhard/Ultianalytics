import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE, 'https://use.fontawesome.com/releases/v5.15.3/css/all.css'])

# Custom CSS styles
custom_styles = {
    'header': {'background-color': '#333', 'color': 'white', 'padding': '20px'},
    'title': {'font-size': '36px'},
    'subheader': {'font-size': '24px', 'margin-top': '5px', 'cursor': 'pointer'},
    'summary': {'font-size': '18px', 'margin-top': '10px'},
    'markdown': {'font-size': '16px', 'margin-bottom': '10px'},
    'expander': {'background-color': '#f5f5f5', 'padding': '10px', 'margin-bottom': '20px'},
    'collapsed_box': {'max-height': '0', 'transition': 'max-height 0.2s ease-out'},
    'expanded_box': {'max-height': '500px', 'overflow': 'auto', 'transition': 'max-height 0.2s ease-in'},
    'content': {'margin-left': '200px', 'padding': '20px', 'transition': 'margin-left 0.2s ease-in-out'},
}

app.layout = html.Div([
        html.Nav([
        html.Div([
            html.H1('AUDL Dashboard', style={'font-size': '24px', 'color': 'white'}),
            dbc.DropdownMenu(
                label="Pages",
                children=[
                    dbc.DropdownMenuItem("Home", href="/"),
                    dbc.DropdownMenuItem("Page 1", href="/page1"),
                    dbc.DropdownMenuItem("Page 2", href="/page2"),
                ],
                color="dark",
                className="ml-auto",
                direction="down",
            ),
        ], className="container"),
    ], className="navbar navbar-dark bg-dark"),
    html.Div([
        dbc.Container([
            html.H1('Overview', style=custom_styles['title']),
            dcc.Markdown("This dashboard is my naive attempt at visualizing and analyzing the information available through the AUDL's API.", style=custom_styles['markdown']),
            html.Div([
                html.H2('Win Probability Archive', id='expand-wp-archive', className='section-toggle', style=custom_styles['subheader']),
                dbc.Collapse(
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Markdown("This page is designed to visualize win probabilities for completed AUDL games. It uses an LSTM that considers various gameplay dynamics and features, such as thrower coordinates, possession details, game quarter, scores, and score difference.", style=custom_styles['summary']),
                        ]),
                    ]),
                    id='collapse-wp-archive',
                    style=custom_styles['collapsed_box'],
                ),
            ], style=custom_styles['expander']),
            html.Div([
                html.H2('Throwing Direction', id='expand-throwing-dir', className='section-toggle', style=custom_styles['subheader']),
                dbc.Collapse(
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Markdown("This page condenses each player's throws into a polar histogram and shows usage, efficiency, and trends in throwing.", style=custom_styles['summary']),
                        ]),
                    ]),
                    id='collapse-throwing-dir',
                    style=custom_styles['collapsed_box'],
                ),
            ], style=custom_styles['expander']),
        ], style=custom_styles['content']),
    ]),
])

# Callbacks to toggle the collapse/expand behavior and adjust the height
app.callback(
    dash.dependencies.Output('collapse-wp-archive', 'is_open'),
    dash.dependencies.Input('expand-wp-archive', 'n_clicks'),
    dash.dependencies.State('collapse-wp-archive', 'is_open')
)(lambda n, is_open: not is_open if n else is_open)

app.callback(
    dash.dependencies.Output('collapse-throwing-dir', 'is_open'),
    dash.dependencies.Input('expand-throwing-dir', 'n_clicks'),
    dash.dependencies.State('collapse-throwing-dir', 'is_open')
)(lambda n, is_open: not is_open if n else is_open)

app.callback(
    dash.dependencies.Output('collapse-wp-archive', 'style'),
    dash.dependencies.Input('collapse-wp-archive', 'is_open')
)(lambda is_open: custom_styles['expanded_box'] if is_open else custom_styles['collapsed_box'])

app.callback(
    dash.dependencies.Output('collapse-throwing-dir', 'style'),
    dash.dependencies.Input('collapse-throwing-dir', 'is_open')
)(lambda is_open: custom_styles['expanded_box'] if is_open else custom_styles['collapsed_box'])


if __name__ == '__main__':
    app.run_server(debug=True)