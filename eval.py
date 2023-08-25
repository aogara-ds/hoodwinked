import os
import sys
import pandas as pd
import time
from environment import Game
from agent import Player
import warnings
import argparse
warnings.simplefilter(action='ignore', category=FutureWarning)

"""
This script allows you to run a batch of games. Specify the games you'd like to run
in a file such as jobs/1.csv, and then run `python eval.py --job_number 1`. The results
will be saved in /results in a .csv file with a integer name. Temporary copies will also 
be saved, in order to prevent the loss of data if your machine stops running. 
"""

def run_job(
    num_games: int, 
    num_players: int, 
    impostor_agent: str, 
    innocent_agent: str, 
    discussion: bool, 
    start_location: str,
    eval_cols: list[str],
):
    """
    Runs a number of games with the given specifications. 
    Returns a dictionary of eval results with a row for each player. 
    """
    # Initialize dictionary to be returned
    eval_dict = {colname: [] for colname in eval_cols}

    # Run each game and store results
    for i in range(1, num_games+1):
        try:
            # Time the game
            start_time = time.time()

            # Define the game
            discussion = discussion
            game = Game(discussion=discussion)

            # Load the players into the game
            game.load_random_players(num_players, impostor_agent, innocent_agent)

            # Play the game
            player_dicts = game.play()

            # Record the runtime
            end_time = time.time()
            runtime = end_time - start_time

            # Condense player dicts into a single dictionary
            for player_dict in player_dicts:
                for k in list(eval_dict.keys())[4:]:
                    if k in player_dict.keys():
                        eval_dict[k].append(player_dict[k])
                    else:
                        eval_dict[k].append("")
            
            # Store game-level information in eval_dict
            # Duplicated in each agent's row for ease of display
            # Memory inefficient -- change this if low on memory
            eval_dict["game_num"].extend([i for _ in range(num_players)])
            eval_dict["runtime"].extend([runtime for _ in range(num_players)])
            eval_dict["num_players"].extend([num_players for _ in range(num_players)])
            eval_dict["discussion"].extend([discussion for _ in range(num_players)])

            # Count API hits for monitoring
            api_hits = sum(eval_dict['num_turns'][-num_players:]) + \
                sum([i if (type(i)!=str) else 0 for i in eval_dict['num_killed'][-num_players:]]) * 2 * num_players
            print(f'api_hits: {api_hits}')

            if i % 10 == 0:
                temp_save(eval_dict)

        # Catch errors and continue with the next game
        except Exception as e:
            print("Error: ", e.args)
            temp_save(eval_dict)
            time.sleep(30)
            continue

    return eval_dict


def temp_save(eval_dict):
    temp_save = pd.DataFrame(eval_dict)
    temp_save_path = get_save_path().replace(".csv", "_temp.csv")
    temp_save.to_csv(temp_save_path)


def get_save_path():
    """
    Returns a pathname to be used throughout the evaluation. 
    """
    save_dir = 'results'
    if not os.path.exists(save_dir): os.makedirs(save_dir)
    file_name = str(len([name for name in os.listdir(save_dir)
                    if os.path.isfile(os.path.join(save_dir, name))]))
    full_path = save_dir + '/' + file_name + '.csv'
    return full_path

if __name__ == "__main__":
    # Read the command line argument for the job number
    parser = argparse.ArgumentParser(description='Process the job number.')
    parser.add_argument('--job_number', type=int, required=True, help='Which .csv file in the /jobs folder to run')
    parser.add_argument('job_number', type=int, 
    args = parser.parse_args()
    job_number = args.job_number

    # Read the schedule of jobs
    schedule = pd.read_csv(f"jobs/{job_number}.csv")
    save_path = get_save_path()
    
    # Set up the evaluation structure
    results_cols = [
        "game_num", "runtime", "num_players", "discussion",
        "name", "agent", "killer", "num_turns", "banished",
        "killed", "escaped", "num_killed", "num_escaped", 
        "duplicate_search_rate", "vote_rate_for_self", "vote_rate_for_killer", 
        "witness_vote_rate_for_killer", "non_witness_vote_rate_for_killer",
        "story", "actions", "votes", "witness_during_vote",
    ]
    results = {colname: [] for colname in results_cols}

    # Run each job individually
    for idx, row in schedule.iterrows():
        eval_dict = run_job(
            num_games = row['num_games'],
            num_players = row['num_players'],
            impostor_agent = row['impostor_agent'],
            innocent_agent = row['innocent_agent'],
            discussion = row['discussion'],
            start_location = row['start_location'],
            eval_cols = results_cols
        )

        # Join all eval dicts into a single results dict
        for k, v in eval_dict.items():
            if k not in results.keys():
                results[k] = v
            else:
                results[k].extend(v)
        
        # Save results as .csv in results folder after each job
        results_df = pd.DataFrame(results)
        results_df.to_csv(save_path)