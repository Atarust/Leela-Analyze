import datetime
import random

import subprocess
import sys

from leelazWrapper  import LzWrapper
from sgf_creator import sgf_creator
from misc import adjust_variations_to_color, switched, generate_comment


# analysis
# Should a worker make a single move or a single game? Or should leela simply be a cloud leela? -> best
# What each google cloud worker should do:
    # Play two different leelas each with their weights against each other (once)
    # return winner
    # return sgf, where each move has as comment the analysis during playing
    # return list: for each move the winrate for black
    # games should have some randomness in beginning...

def create_self_play_game(leela1, leela2, sgf, log_move="."):
    color = 'B'
    move_nr = 1
    while True:
        if color == 'B':
            move, variations = leela1.genmove(color)
            leela2.play(color, move)
        else:
            move, variations = leela2.genmove(color)
            leela1.play(color, move)
        variations = adjust_variations_to_color(variations,color)
        comment = generate_comment(move, move, variations, color, 0)
        sgf.add_move(move)
        sgf.add_comment(comment)
        comment = ""
        if move == 'resign':
            winner = switched(color)
            return winner, sgf
        sys.stdout.write(log_move)
        sys.stdout.flush()
        
        # simplification: game ends after first pass
        if move == 'pass':
            # find out who win by trusting last winrate
            if len(variations) > 0:
                last_winrate = variations[0][2]
            else:
                last_winrate = 50
            if last_winrate > 50:
                winner = color
            else:
                winner = switched(color)
            return winner, sgf
    
        color = switched(color)
        move_nr += 1

def main(nr_of_games=1):
    visits1 = 25
    visits2 = 50
    weights = 'network.gz'
    leela = '../leela-zero/src/leelaz'

    leela1 = LzWrapper(leela, weights, visits1)
    leela2 = LzWrapper(leela, weights, visits2)

    b_wins = 0
    w_wins = 0
    for i in range(nr_of_games):
        print("Game", i)
        leela1.clear_board()
        leela2.clear_board()
        sgf=sgf_creator(opening=[], visits1=visits1, visits2=visits2)
        winner, sgf = create_self_play_game(leela1, leela2, sgf)
        if(winner=='B'):
            b_wins += 1
        else:
            w_wins += 1
        print('\nb(v={})_wins:'.format(visits1),b_wins)
        print('w(v={})_wins:'.format(visits2),w_wins)
        sgf.save('games/eval_{}_vb{}_vw{}_{}.sgf'.format(str(datetime.datetime.now()), visits1, visits2, random.randint(0,100000)))

main(nr_of_games=50)