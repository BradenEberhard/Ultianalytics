import warnings
import pandas as pd
import tensorflow as tf
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import BatchNormalization, LSTM, LayerNormalization, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import LearningRateScheduler, EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras import backend as K
from tensorflow import keras
from sklearn.model_selection import train_test_split
from matplotlib import pyplot as plt
import textalloc as ta
import pickle
import math


class GameProbability():
    def __init__(self, path, normalizer_path='../saved_models/normalizer.pkl'):
        self.data = pd.read_csv(path).dropna(how='any', axis=0)
        self.normalizer_path = normalizer_path
        self.set_normalizer()


    def pad_arrays(self, array, max_length):
        """
        Pads each array in the given list of arrays to the specified maximum length.

        If the length of an array is greater than the maximum length, it truncates the array to the maximum length.
        If the length of an array is less than the maximum length, it pads the array with zeros at the beginning.

        Args:
            array (list): A list of arrays.
            max_length (int): The maximum desired length.

        Returns:
            list: The padded arrays.
        """
        padded_arrays = []
        for arr in array:
            if len(arr) > max_length: ##TODO allow for longer games
                arr = arr[-max_length:,:]
            pad_width = ((max_length - len(arr), 0), (0, 0))  # Pad at the beginning with zeros
            padded_array = np.pad(arr, pad_width, mode='constant', constant_values=-1)
            padded_arrays.append(padded_array)
        return padded_arrays
    
    
    def process_data(self, features):
        def add_team_swap(data):
            """
            Applies a team swap operation to the game data DataFrame. This is a form of data augmentation that
            relies on the incorrect assumption that being the home team and away team doesn't matter. However,
            in training we believe the additional data is more impactful than the advantage of being the home team.

            Swaps the home team's score with the away team's score, flips the home team win indicator,
            toggles the `is_home_team` flag, and modifies the game ID to indicate the team swap.

            Args:
                data (pandas.DataFrame): A DataFrame containing game data.

            Returns:
                pandas.DataFrame: The modified DataFrame with the team swap applied.
            """
            all_games = []
            for game in data.gameID.unique():
                GAME = data[data.gameID == game]
                GAME['temp'] = GAME['home_team_score']
                GAME['home_team_score'] = GAME['away_team_score']
                GAME['away_team_score'] = GAME['temp']
                GAME['home_team_win'] = (~GAME.home_team_win.astype(bool)).astype(int)
                GAME['is_home_team'] = ~GAME['is_home_team']
                GAME['gameID'] = GAME['gameID'] + '-teamswap'
                all_games.append(GAME.drop('temp', axis=1))
            return pd.concat([pd.concat(all_games), data])

        def add_x_swap(data):
            """
            Applies a thrower swap operation to the game data DataFrame. This is a form of data augmentation
            that assumes the game probability should be the same no matter which side of the field the disc is on.

            Multiplies the `thrower_x` column by -1 and modifies the game ID to indicate the thrower swap.

            Args:
                data (pandas.DataFrame): A DataFrame containing game data.

            Returns:
                pandas.DataFrame: The modified DataFrame with the thrower swap applied.
            """
            FLIPPED_X = data.copy()
            FLIPPED_X.thrower_x = FLIPPED_X.thrower_x * -1
            FLIPPED_X['gameID'] = FLIPPED_X['gameID'] + '-throwswap'
            return pd.concat([data, FLIPPED_X])

        def preprocess_data(data, features, label, testIDs):
            """
            Preprocess the data by grouping, sorting, and converting it to numpy arrays.

            Parameters:
                data (DataFrame): Input data.
                features (list): List of feature column names.
                label (str): Label column name.
                testIDs (list): List of gameIDs for test data.

            Returns:
                group_train_arrays (list): List of numpy arrays for training data groups.
                group_test_arrays (list): List of numpy arrays for test data groups.
                max_length (int): Maximum length among all groups.
            """
            # Step 1: Group the data by 'gameID'
            grouped = data.groupby(['gameID'])

            # Step 2: Sort the groups by length
            sorted_groups = sorted(grouped[features + label], key=lambda x: len(x[1]), reverse=True)

            # Step 3: Convert each group to a numpy array
            group_train_arrays = []
            group_test_arrays = []
            max_length = 0

            for gameID, group in sorted_groups:
                group_array = group.values  # Convert group DataFrame to a numpy array
                if len(group_array) > max_length:
                    max_length = len(group_array)
                if gameID in testIDs:
                    group_test_arrays.append(group_array)
                else:
                    group_train_arrays.append(group_array)

            return group_train_arrays, group_test_arrays, max_length

        def format_data(padded_train_arrays, padded_test_arrays):
            """
            Process the data by converting it into numpy arrays, normalizing the features,
            and converting them to tensors.

            Parameters:
                padded_train_arrays (list): List of padded train arrays.
                padded_test_arrays (list): List of padded test arrays.

            Returns:
                X_train (ndarray): Numpy array for training features.
                X_test (ndarray): Numpy array for test features.
                y_train (ndarray): Numpy array for training labels.
                y_test (ndarray): Numpy array for test labels.
                X_train_normalized (ndarray): Numpy array for normalized training features.
                X_test_normalized (ndarray): Numpy array for normalized test features.
            """
            def normalize_data(X_train, X_test):
                """
                Normalize the training and test data using Min-Max scaling.

                Parameters:
                    X_train (ndarray): Training data array.
                    X_test (ndarray): Test data array.

                Returns:
                    X_train_normalized (ndarray): Normalized training data.
                    X_test_normalized (ndarray): Normalized test data.
                """

                # Create a normalizer object
                self.normalizer = MinMaxScaler()

                # Normalize the training data
                X_train_flattened = X_train.reshape(-1, X_train.shape[-1])
                mask = (X_train_flattened[:, 0] != -1)
                X_train_normalized = X_train_flattened.copy()
                X_train_normalized[mask] = self.normalizer.fit_transform(X_train_flattened[mask])
                X_train_normalized = X_train_normalized.reshape(X_train.shape)

                # Normalize the test data using the same normalization parameters
                X_test_flattened = X_test.reshape(-1, X_test.shape[-1])
                mask = (X_test_flattened[:, 0] != -1)
                X_test_normalized = X_test_flattened.copy()
                X_test_normalized[mask] = self.normalizer.transform(X_test_flattened[mask])
                X_test_normalized = X_test_normalized.reshape(X_test.shape)
                
                with open(self.normalizer_path, 'wb') as file:
                    pickle.dump(self.normalizer, file)

                return X_train_normalized, X_test_normalized
            
            # Convert the list of arrays into a 3D numpy array
            data_train_array = np.stack(padded_train_arrays)
            data_test_array = np.stack(padded_test_arrays)

            # Split the arrays into features and labels
            X_train, X_test, y_train, y_test = data_train_array[:,:,:-1], data_test_array[:,:,:-1], data_train_array[:,:,-1], data_test_array[:,:,-1]

            # Normalize the features
            X_train_normalized, X_test_normalized = normalize_data(X_train, X_test)

            # Convert to tensors
            X_train, X_test, y_train, y_test, X_train_normalized, X_test_normalized = (
                X_train.astype(np.float32),
                X_test.astype(np.float32),
                y_train.astype(np.float32),
                y_test.astype(np.float32),
                X_train_normalized.astype(np.float32),
                X_test_normalized.astype(np.float32)
            )

            return y_train, y_test, X_train_normalized, X_test_normalized
        
        label = ['home_team_win']
        # Augment data and split into training and testing
        _, testIDs = train_test_split(self.data.gameID.unique(), test_size=0.2, random_state=42)
        data = add_x_swap(add_team_swap(self.data))

        group_train_arrays, group_test_arrays, max_length = preprocess_data(data, features, label, testIDs)

        # Pad the variable-length groups
        padded_train_arrays, padded_test_arrays = self.pad_arrays(group_train_arrays, max_length), self.pad_arrays(group_test_arrays, max_length)

        # Normalize and convert the padded arrays
        y_train, y_test, X_train_normalized, X_test_normalized = format_data(padded_train_arrays, padded_test_arrays)

        return X_train_normalized, X_test_normalized, y_train, y_test
    

    def set_normalizer(self):
        with open(self.normalizer_path, 'rb') as file:
            self.normalizer = pickle.load(file)
            

    def create_model(self, lstm_units, input_shape):
        model = tf.keras.Sequential()
        model.add(BatchNormalization(input_shape=input_shape))
        model.add(LSTM(units=lstm_units, return_sequences=True))
        model.add(LayerNormalization())
        model.add(Dense(units=1, activation='sigmoid'))
        return model
    
    
    def masked_loss(self, mask_value):
        def loss_function(y_true, y_pred):
            mask = K.cast(K.not_equal(y_true, mask_value), K.floatx())
            loss = K.binary_crossentropy(y_true * mask, y_pred * mask)
            return loss
        return loss_function

    
    def process_new_game(self, DATA, features, max_length=629):
        def normalize_new_game(X, normalizer):
                # Flatten the 3D training data
                X_flattened = X.reshape(-1, X.shape[-1])

                # Create a mask for padded values
                mask = (X_flattened[:, 0] != -1)

                # Apply normalization only to non-padded values
                X_normalized = X_flattened.copy()
                X_normalized[mask] = normalizer.transform(X_flattened[mask])

                # Reshape the normalized data back to the original shape
                X_normalized = X_normalized.reshape(X.shape)
                return X_normalized

        groups = DATA.groupby(['gameID'])

        group_arrays = []
        teams = []
        for gameID, group in groups:
            group_array = group[features+['home_team_win']].values  # Convert group DataFrame to a numpy array
            if len(group_array) > max_length:
                print(f'skipping game: {gameID} len: {len(group_array)}')
                continue
            teams.append((group.home_teamID.iloc[0], group.away_teamID.iloc[0], gameID[:10]))
            group_arrays.append(group_array)
        padded_arrays = self.pad_arrays(group_arrays, 629) #TODO allow for more throws
        data_array = np.stack(padded_arrays)
        X = data_array[:,:,:-1]
        X = normalize_new_game(X, self.normalizer)
        return X, teams


    def load_model(self, model_path='../saved_models/accuracy_loss_model.h5'):
        self.model = keras.models.load_model(model_path, custom_objects={'loss_function':self.masked_loss})

    def plot_games(self, DATA, features, show=False):
        X, teams = self.process_new_game(DATA, features)
        def get_arrays(df, predictions):
            txts, xs, ys = [], [], []
            for _, group_df in df[(df.times>0) & (df.total_points < 100)].groupby('total_points'):
                row = group_df.iloc[0]
                txt = f'{int(row.home_team_score)}-{int(row.away_team_score)}'
                x = 48 - row.times/60
                y = predictions.flatten()[min(group_df.index)]
                txts.append(txt)
                xs.append(x)
                ys.append(y)
            return txts, xs, ys
        width = 2
        height = math.ceil(X.shape[0] / 2)
        fig, ax = plt.subplots(height, width, figsize=(width*5,height*5))
        ax = ax.flatten()
        num_plots = X.shape[0]
        for idx in range(num_plots):
            current_game = X[idx,:,:].astype(np.float32)
            df = pd.DataFrame(self.normalizer.inverse_transform(current_game), columns=features)
            predictions = self.model.predict(current_game.reshape(1, 629, -1))
            txts, xs, ys = get_arrays(df, predictions)
            ax[idx].scatter(xs, ys, c='r', s=0.1)
            ta.allocate_text(fig, ax[idx], xs, ys, txts, x_scatter=xs, y_scatter=ys, textsize=7, linecolor='black')
            
            ax[idx].plot(48 - df[(df.times>0) & (df.total_points < 100)].times/60, predictions[np.array([(df.times>0) & (df.total_points < 100)])].flatten(), c='r')
            ax[idx].grid(alpha=0.3)
            ax[idx].set_yticks(np.arange(0,1.1,0.1))
            ax[idx].set_ylim([0,1])
            ax[idx].title.set_text(f'{teams[idx][1]} at {teams[idx][0]} on {teams[idx][2]}')
        if show:
            plt.show()
        return fig, ax
    
    def plot_game(self, gameID, features, max_length = 629):
        test_game = self.data[self.data.gameID == gameID][features]
        test_game = self.normalizer.transform(test_game)
        pad_width = ((max_length - len(test_game), 0), (0, 0))  # Pad at the beginning with zeros
        test_game = np.pad(test_game, pad_width, mode='constant', constant_values=-1).astype(np.float32)
        out = self.model.predict(test_game.reshape(1, 629, -1))
        df = pd.DataFrame(self.normalizer.inverse_transform(test_game), columns=features)
        preds = out[np.array([df.times > 0])].flatten()
        annotations = []
        counter = 0
        txts, xs, ys = [], [], []
        for _, group_df in df[df.times>0].groupby('total_points'):
            counter = counter + 1
            row = group_df.iloc[0]
            txt = f'{int(row.home_team_score)}-{int(row.away_team_score)}'
            x = 48 - row.times/60
            y = out.flatten()[min(group_df.index)]
            txts.append(txt)
            xs.append(x)
            ys.append(y)
        fig, ax = plt.subplots()
        ax.scatter(xs, ys, c='r', s=0.1)
        ta.allocate_text(fig,ax,xs,ys,
                        txts,
                        x_scatter=xs, y_scatter=ys,
                        textsize=10, linecolor='black')


        ax.plot(48 - df[df.times > 0].times/60, preds, c='r')
        ax.grid(alpha=0.3)
        ax.set_title(gameID)
        ax.set_ylim([0,1])
        return fig, ax
    
def process_games(GAMES):
    features = ['thrower_x', 'thrower_y', 'start_on_offense', 'point_start_time', 'possession_num', 'possession_throw', 'game_quarter', 'quarter_point', 'is_home_team', 'home_team_score', 'away_team_score', 'gameID', 'total_points', 'home_teamID', 'away_teamID']

    GAMES['total_points'] = GAMES['home_team_score'] + GAMES['away_team_score']
    GAMES = GAMES[GAMES.game_quarter < 5] ##TODO include overtimes
    GAMES['point_start_time'] = 720 - GAMES['point_start_time']
    GAMES = GAMES[features]

    games = []
    for gameID in GAMES.gameID.unique():
        GAME = GAMES[GAMES.gameID == gameID]
        points = []
        prev_point_time = 720
        current_quarter = 1
        prev_df = None
        error_points = 0
        for group_keys, group_df in GAME.groupby(['total_points', 'game_quarter']):
            if prev_df is None:
                prev_df = group_df
                continue

            prev_point_time = prev_df.point_start_time.max()
            if (current_quarter != group_df.game_quarter.max()):
                current_quarter = group_df.game_quarter.max()
                current_point_time = 0
            else:
                current_point_time = group_df.point_start_time.max()
            if current_point_time >= prev_point_time:
                error_points = error_points + 1
                continue
            times = np.linspace(prev_point_time, current_point_time + 1, len(prev_df))
            prev_df['times'] = times
            points.append(prev_df)
            prev_df = group_df
            if group_keys == (GAME.home_team_score.max()+GAME.away_team_score.max(), 4):
                times = np.linspace(current_point_time, 0, len(prev_df))
                prev_df['times'] = times
                points.append(prev_df)
        GAME_POINTS = pd.concat(points)
        GAME_POINTS.times = GAME_POINTS.times + ((4 - GAME_POINTS.game_quarter)*720)
        try:
            # if error_points > 0:
            #     print(f'{error_points} errors with {GAME_POINTS.gameID.iloc[0]}')
            assert GAME_POINTS.times.is_monotonic_decreasing, f'timing is off somewhere for game: {GAME_POINTS.gameID.iloc[0]}'
            home_team_win = GAME_POINTS[['away_team_score', 'home_team_score']].max().values.argmax() if GAME_POINTS['home_team_score'].max() != GAME_POINTS['away_team_score'].max() else -2
            GAME_POINTS['home_team_win'] = home_team_win
            games.append(GAME_POINTS)
        except AssertionError as e:
            print(e)

        PROCESSED_GAMES = pd.concat(games).drop(['point_start_time', 'start_on_offense'], axis=1)
        PROCESSED_GAMES['score_diff'] = PROCESSED_GAMES['home_team_score'] - PROCESSED_GAMES['away_team_score']
    return PROCESSED_GAMES[PROCESSED_GAMES.home_team_win >= 0]