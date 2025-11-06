import json
import pandas as pd
import tabulate as tb
import numpy

def get_input(prompt: str, check_function: callable = lambda x: True, evaluate_function: callable = lambda x: x):
    print(prompt)
    input_value = input()
    if check_function(input_value):
        return evaluate_function(input_value)
    else:
        print("Input not valid, please try again.")
        return get_input(prompt, check_function)

def add_game(player_list : list[str], number_of_rounds: int, scores: list[int], place: str):
    print("Adding a new game...")
    with open('games.json', 'r') as file:
        games = json.load(file)
    ids = [game["id"] for game in games]
    new_id = max(ids) + 1 if ids else 1
    games.append({
        "id": new_id,
        "scores": {player_list[i]: scores[i] for i in range(len(player_list))},
        "rounds": number_of_rounds,
        "place": place        
    })
    with open('games.json', 'w') as file:
        file.write(json.dumps(games, indent=4))
    print("Game added successfully.")

def enter_game():
    print("Entering a new game...")
    player_list = get_input(
        "Please enter the players' names (comma-separated): ",
        check_function=lambda x: len([name.strip() for name in x.split(',')]) >= 4,
        evaluate_function=lambda x: [name.strip() for name in x.split(',')]
    )
    number_of_rounds = get_input(
        "Please enter the number of rounds: ",
        check_function=lambda x: x.isdigit() and int(x) > 0,
        evaluate_function=lambda x: int(x)
    )
    player_scores = get_input(
        "Please enter the scores (comma-separated): ",
        check_function=lambda x: len([score.strip() for score in x.split(',')]) == len(player_list) and all(score.lstrip('-').isdigit() for score in x.split(',')) and sum([int(score.strip()) for score in x.split(',')]) == 0,
        evaluate_function=lambda x: [int(score.strip()) for score in x.split(',')]
    )
    place = get_input(
        "Please enter the place of the game: ",
        evaluate_function=lambda x: x.strip()
    )
    print("Is the following entry correct?")
    print(f"Players: {player_list}, Rounds: {number_of_rounds}, Scores: {player_scores}, Place: {place}")
    if input("Is this correct? (y/n): ").lower() == 'y':
        add_game(player_list, number_of_rounds, player_scores, place)
    else:
        print("Entry not correct, please try again.")
        enter_game()

def transform_json_to_dfs():
    with open('games.json', 'r') as file:
        games = json.load(file)
    player_rows, game_rows = [], []
    for game in games:
        game_rows.append({
            "id": game["id"],
            "rounds": game["rounds"],
            "place": game["place"]
        })
        for player, score in game["scores"].items():
            round_multiplier = 0.8 if len(game["scores"]) == 5 else 1
            player_rows.append({
                "id": game["id"],
                "player": player,
                "score": score,
                "rounds": int(game["rounds"] * round_multiplier),
                "place": game["place"],
            })
    return pd.DataFrame(player_rows), pd.DataFrame(game_rows)

def clean_stats(stats):
    cleaned_stats = {}
    for key, value in stats.items():
        if isinstance(value, list):
            cleaned_stats[key] = ', '.join([str(value) for value in value])
        elif isinstance(value, pd.DataFrame):
            cleaned_stats[key] = ', '.join([f"{name} ({val})" for name, val in zip(value["player"], value[value.columns[1]])])
        else:
            cleaned_stats[key] = value
    return cleaned_stats

def evaluate_stats():
    print("Evaluating stats...")

    player_data, game_data = transform_json_to_dfs()
    players = player_data["player"].unique().tolist()

    place_counts = game_data["place"].value_counts().reset_index()
    place_counts.columns = ['place', 'count']

    stats = {
        "Included players": players,
        "Included places": list(place_counts.itertuples(index=False, name=None)),
        "Total games": len(game_data),
        "Total rounds": game_data["rounds"].sum(),
        "Highest total score": player_data.groupby("player")["score"].max().reset_index().sort_values(by="score", ascending=False),
        "Lowest total score": player_data.groupby("player")["score"].min().reset_index().sort_values(by="score", ascending=True),
        "Average score per round": player_data.groupby('player').agg(score_sum=('score', 'sum'), rounds_sum=('rounds', 'sum')).assign(score=lambda df: round(df['score_sum'] / df['rounds_sum'], 3)).reset_index()[['player', 'score']].sort_values(by='score', ascending=False),
        "Games won": player_data.loc[player_data.groupby('id')['score'].idxmax()]['player'].value_counts().reset_index(name='games_won').rename(columns={'index': 'player'}),
        "Games played": player_data.groupby('player')['id'].count().reset_index(name='games_played').sort_values(by='games_played', ascending=False),
        "Rounds played": player_data.groupby('player')['rounds'].sum().reset_index(name='total_rounds').sort_values(by='total_rounds', ascending=False),
        "Average placement (4P normalized)": player_data.assign(raw_placement=lambda df: df.groupby('id')['score'].rank(ascending=False, method='min')).merge(player_data.groupby('id').size().reset_index(name='total_players_in_round'), on='id').assign(normalized_placement=lambda df: 1 + (df['raw_placement'] - 1) * (4 - 1) / (df['total_players_in_round'] - 1).replace(0, 1)).groupby('player')['normalized_placement'].mean().reset_index(name='avg_normalized_placement').sort_values(by='avg_normalized_placement', ascending=True)
    }
    stats["Games won"] = stats["Games won"].merge(stats["Games played"], on='player', how='outer').fillna(0).drop(columns=['games_played']).astype({'games_won': int}).sort_values(by='games_won', ascending=False)
    stats["Games won per game"] = stats["Games won"].merge(stats["Games played"], on='player').assign(games_won_per_game=lambda df: round(df['games_won'] / df['games_played'], 3)).drop(columns=['games_won', 'games_played']).sort_values(by='games_won_per_game', ascending=False)
    
    stats_cleaned = clean_stats(stats)

    table = tb.tabulate(stats_cleaned.items(), tablefmt="grid")
    print("Statistics:")
    print(table)
    with open('stats.txt', 'w') as file:
        file.write(table)
        
if __name__ == "__main__":

    print("Welcome to DokoStats!")
    print("(1) Enter new game. (2) Evaluate stats. (3) Exit")
    choice = input("Please enter your choice: ")
    if choice == "1":
        enter_game()
    elif choice == "2":
        evaluate_stats()
    else:
        print("Exiting the program.")
        exit()