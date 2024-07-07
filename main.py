# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This is a nice home for our Battlesnake called Hunter.

import random
import typing
from collections import deque
from server import run_server

# Important global variables
DIRECTIONS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}
POSSIBLE_MOVES = list(DIRECTIONS.keys())

# Thresholds for decision making
LOW_HEALTH_THRESHOLD = 30  # Health level at which snake prioritizes finding food
LENGTH_ADVANTAGE_THRESHOLD = (
    2  # Minimum length advantage to consider chasing other snakes
)


def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "Gruppe 7",
        "color": "#888888",
        "head": "default",
        "tail": "default",
    }


def start(game_state: typing.Dict):
    print("GAME START")


def end(game_state: typing.Dict):
    print("GAME OVER\n")
    print(f"Snake length: {len(game_state['you']['body'])}")


def is_safe(x: int, y: int, game_state: typing.Dict) -> bool:
    """
    Determines if a given position is safe for the snake to move to.

    Args:
        x (int): The x-coordinate to check.
        y (int): The y-coordinate to check.
        game_state (dict): The current game state.

    Returns:
        bool: True if the position is safe, False otherwise.
    """
    board_width = game_state["board"]["width"]
    board_height = game_state["board"]["height"]
    my_body = game_state["you"]["body"]

    # Check board boundaries
    if x < 0 or y < 0 or x >= board_width or y >= board_height:
        return False

    # Check self-collision
    if any(part["x"] == x and part["y"] == y for part in my_body[:-1]):
        return False

    # Check other snakes
    for snake in game_state["board"]["snakes"]:
        if snake["id"] != game_state["you"]["id"]:
            # Check body collision
            if any(part["x"] == x and part["y"] == y for part in snake["body"][:-1]):
                return False
            # Check head-to-head collision
            if (
                len(snake["body"]) >= len(my_body)
                and abs(snake["body"][0]["x"] - x) + abs(snake["body"][0]["y"] - y)
                == 1  # manhattan distance
            ):
                return False

    return True


def get_safe_moves(game_state: typing.Dict) -> list:
    """
    Determines all safe moves for the snake based on the current game state.

    Args:
        game_state (dict): The current game state.

    Returns:
        list: A list of safe moves.
    """
    my_head = game_state["you"]["body"][0]
    my_neck = game_state["you"]["body"][1]

    safe_moves = []

    for move, (dx, dy) in DIRECTIONS.items():
        # Prevent moving backwards
        if (
            (move == "up" and my_neck["y"] > my_head["y"])
            or (move == "down" and my_neck["y"] < my_head["y"])
            or (move == "left" and my_neck["x"] < my_head["x"])
            or (move == "right" and my_neck["x"] > my_head["x"])
        ):
            continue

        new_x, new_y = my_head["x"] + dx, my_head["y"] + dy

        if is_safe(new_x, new_y, game_state):
            safe_moves.append(move)

    return safe_moves


def find_path(start: tuple, goal: tuple, game_state: typing.Dict) -> list:
    """
    Finds a path from start to goal using a breadth-first search algorithm.

    Args:
        start (tuple): The starting position (x, y).
        goal (tuple): The goal position (x, y).
        game_state (dict): The current game state.

    Returns:
        list: A list of coordinates representing the path, or None if no path is found.
    """
    queue = deque([[start]])
    seen = set([start])

    while queue:
        path = queue.popleft()
        x, y = path[-1]
        if (x, y) == goal:
            return path
        for dx, dy in DIRECTIONS.values():
            x2, y2 = x + dx, y + dy
            if (x2, y2) not in seen and is_safe(x2, y2, game_state):
                queue.append(path + [(x2, y2)])
                seen.add((x2, y2))
    return None


def get_move_from_path(path: list, my_head: dict) -> str:
    """
    Determines the next move based on the given path and current head position.

    Args:
        path (list): A list of coordinates representing the path.
        my_head (dict): The current position of the snake's head.

    Returns:
        str: The next move direction, or None if the path is invalid.
    """
    if not path or len(path) < 2:
        return None
    next_move = path[1]
    if next_move[0] > my_head["x"]:
        return "right"
    elif next_move[0] < my_head["x"]:
        return "left"
    elif next_move[1] > my_head["y"]:
        return "up"
    elif next_move[1] < my_head["y"]:
        return "down"


def seek_food(game_state: typing.Dict, safe_moves: list) -> str:
    """
    Determines the next move to seek the closest food.

    Args:
        game_state (dict): The current game state.
        safe_moves (list): A list of safe moves.

    Returns:
        str: The next move direction to seek food, or None if no suitable move is found.
    """
    my_head = game_state["you"]["body"][0]
    food = game_state["board"]["food"]
    if food:
        closest_food = min(
            food,
            key=lambda f: abs(f["x"] - my_head["x"])
            + abs(f["y"] - my_head["y"]),  # manhattan distance
        )
        path_to_food = find_path(
            (my_head["x"], my_head["y"]),
            (closest_food["x"], closest_food["y"]),
            game_state,
        )
        if path_to_food:
            move = get_move_from_path(path_to_food, my_head)
            if move in safe_moves:
                print("Seeking food")
                return move
    return None


def chase_smaller_snake(game_state: typing.Dict, safe_moves: list) -> str:
    """
    Determines the next move to chase a smaller snake.

    Args:
        game_state (dict): The current game state.
        safe_moves (list): A list of safe moves.

    Returns:
        str: The next move direction to chase a smaller snake, or None if no suitable move is found.
    """
    my_head = game_state["you"]["body"][0]
    my_length = len(game_state["you"]["body"])
    for snake in game_state["board"]["snakes"]:
        if len(snake["body"]) < my_length:
            tail = snake["body"][-1]
            path_to_tail = find_path(
                (my_head["x"], my_head["y"]), (tail["x"], tail["y"]), game_state
            )
            if path_to_tail:
                move = get_move_from_path(path_to_tail, my_head)
                if move in safe_moves:
                    print("Chasing a smaller snake")
                    return move
    return None


def move(game_state: typing.Dict) -> typing.Dict:
    """
    Determines the next move for the snake based on the current game state.

    Args:
        game_state (dict): The current game state.

    Returns:
        dict: A dictionary containing the next move.
    """
    safe_moves = get_safe_moves(game_state)

    if not safe_moves:
        print("No safe moves. Making a random move")
        return {"move": random.choice(POSSIBLE_MOVES)}

    my_health = game_state["you"]["health"]
    my_length = len(game_state["you"]["body"])
    other_snakes_lengths = [
        len(snake["body"])
        for snake in game_state["board"]["snakes"]
        if snake["id"] != game_state["you"]["id"]
    ]
    max_snake_length = max(other_snakes_lengths) if other_snakes_lengths else 0

    # Prioritize food if health is low or we're not the longest snake
    if (
        my_health < LOW_HEALTH_THRESHOLD
        or my_length <= max_snake_length + LENGTH_ADVANTAGE_THRESHOLD
    ):
        food_move = seek_food(game_state, safe_moves)
        if food_move:
            return {"move": food_move}

    # Try to chase a smaller snake if we're not prioritizing food
    chase_move = chase_smaller_snake(game_state, safe_moves)
    if chase_move:
        return {"move": chase_move}

    # If no specific strategy applies, make a random safe move
    print("Making a random safe move")
    return {"move": random.choice(safe_moves)}


if __name__ == "__main__":
    run_server({"info": info, "start": start, "move": move, "end": end})
