import requests
import pandas as pd
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import re

with open('openings_dict.json', 'r') as file:
    openings_dict = json.load(file)

def get_chess_archives(username):
    headers = {'User-Agent': 'head2head'}
    url = f'https://api.chess.com/pub/player/{username}/games/archives'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print(response.status_code)
        return response.json()
        

def get_chess_games(username):
    dataframes = []
    headers = {'User-Agent': 'head2head'}
    urls = pd.DataFrame(get_chess_archives(username))
    print(urls['archives'])
    
    for url in urls['archives']:
        print(url)
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            df = response.json()
            df = pd.DataFrame(df)
            df = pd.json_normalize(df['games'])
            dataframes.append(df)

    df = pd.concat(dataframes, ignore_index=True)
        

    return df


def pgn_to_eco(pgn):
    match = re.search(r'\[ECO "([^"]+)"\]', pgn)
    if match:
        return match.group(1)  # Capture the ECO code
    return None  # Return None if not found

def eco_to_opening(eco):
    return openings_dict[eco]

def rounder(x):
    return round(x,1)

# analyse games using pandas
def analyse_games(df, username, selected_colour):   
    # Cleaning
    #df = df[df['time_class'] == 'blitz']
    df = df[df['rated'] == True]
    df = df[df['rules'] == 'chess']
    df['White_Win'] = df['white.result'].apply(lambda x: 1 if x == 'win' else 0)
    draws = ['timevsinsufficient', 'repetition', 'stalemate', 'agreed','insufficient', '50move']
    df['Draw'] = df['white.result'].apply(lambda x: 1 if x in draws else 0)
    losses = ['timeout', 'checkmated', 'resigned', 'abandoned']
    df['Black_Win'] = df['white.result'].apply(lambda x: 1 if x in losses else 0)
    df['start_time'] = df['eco']
    
    df = df.drop(columns = ['tcn', 'uuid','initial_setup', 'fen','accuracies.white', 'accuracies.black','white.@id', 'white.uuid', 'black.@id', 'black.uuid','url', 'time_control', 'end_time', 'rated', 'time_class','rules', 'eco', 'white.result', 'black.result', 'start_time'], axis=1)
    df['eco'] = df['pgn'].apply(pgn_to_eco)
    df['opening'] = df['eco'].apply(eco_to_opening)
    wdf = df[df['white.username'].str.lower() == username.lower()]
    bdf = df[df['black.username'].str.lower() == username.lower()]
    wdf = wdf.rename(columns={'White_Win': 'Win', 'Black_Win': 'Loss', 'white.rating': 'user_rating', 'black.rating': 'opponent_rating'})
    bdf = bdf.rename(columns={'Black_Win': 'Win', 'White_Win': 'Loss', 'black.rating': 'user_rating', 'white.rating': 'opponent_rating'})
    if selected_colour == 'white':
        df = wdf
    elif selected_colour == 'black':
        df = bdf
    else:
        print('womp') 
    
    stats = df.groupby('opening').agg(
        Games_Played=('opening', 'count'),
        Win_Rate=('Win', 'mean'),
        Draw_Rate=('Draw', 'mean'),
        Loss_Rate=('Loss', 'mean'),
        Avg_Self_Rating=('user_rating', 'mean'),
        Avg_Opponent_Rating=('opponent_rating', 'mean')
    ).reset_index()

    stats = stats.sort_values(by='Games_Played', ascending=False)

    stats['Win_Rate'] = 100*stats['Win_Rate']
    stats['Draw_Rate'] = 100*stats['Draw_Rate']
    stats['Loss_Rate'] = 100*stats['Loss_Rate']

    stats['Win_Rate'] = stats['Win_Rate'].apply(rounder)
    stats['Draw_Rate'] = stats['Draw_Rate'].apply(rounder)
    stats['Loss_Rate'] = stats['Loss_Rate'].apply(rounder)
    stats['Avg_Opponent_Rating'] = stats['Avg_Opponent_Rating'].apply(rounder)
    stats['Avg_Self_Rating'] = stats['Avg_Self_Rating'].apply(rounder)

    print(stats)

def save_as_csv(games_data, username):
    games_data.to_csv(f'{username}.csv', index=False)

# Tkinter GUI setup
def create_gui():
    root = tk.Tk()
    root.title("Chess Profile Analysis")

    tk.Label(root, text="Enter Chess.com Username:").pack(pady=10)
    username_entry = tk.Entry(root)
    username_entry.pack(pady=10)

    def on_analyse_button_click(colour):
        username = username_entry.get().strip()
        if username:
            if colour == 'white':
                white_analyse_button.config(state=tk.DISABLED, text="Loading...")
            else:
                black_analyse_button.config(state=tk.DISABLED, text="Loading...")
            root.update()  # Refresh the UI
            try:
                data = get_chess_games(username)
                if not data.empty:
                    result_stats = analyse_games(data, username, colour)
                else:
                    messagebox.showerror("Error", "Could not fetch data for this user.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
            finally:
                if colour == 'white':
                    white_analyse_button.config(state=tk.NORMAL, text="Analyse White")
                else:
                    black_analyse_button.config(state=tk.NORMAL, text="Analyse Black")
                
        else:
            messagebox.showerror("Input Error", "Please enter a Chess.com username.")

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    white_analyse_button = tk.Button(button_frame, text="Analyse White", command=lambda: on_analyse_button_click("white"))
    white_analyse_button.grid(row=0, column=0, padx=5)

    black_analyse_button = tk.Button(button_frame, text="Analyse Black", command=lambda: on_analyse_button_click("black"))
    black_analyse_button.grid(row=0, column=1, padx=5)

    def on_save_button_click():
        username = username_entry.get()
        if username:
            data = get_chess_games(username)
            if data:
                save_as_csv(data, username)
                messagebox.showerror(f'saved as {username}.csv')
            else:
                messagebox.showerror("Error", "Could not fetch data for this user.")
        else:
            messagebox.showerror("Input Error", "Please enter a Chess.com username.")
            
    save_button = tk.Button(root, text="Save .csv", command=on_save_button_click)
    save_button.pack(pady=20)

    root.mainloop()

# Run the app
create_gui()



# problem with case sensitivity on bdf and wdf