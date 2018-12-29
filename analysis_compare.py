import datetime
import random

import subprocess
import sys
from tqdm import tqdm
import time

from leelazWrapper  import LzWrapper, _log_to_file, save_result, _error_to_file, _winrate_to_file
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
    winrates = [] # collect winrates of moves from view of B.
    for _ in range(10000):
        if color == 'B':
            move, variations = leela1.genmove(color)
            leela2.play(color, move)
        else:
            move, variations = leela2.genmove(color)
            leela1.play(color, move)
        variations = adjust_variations_to_color(variations,color)
        if len(variations) > 0:
            winrates.append(variations[0][2])
        comment = generate_comment(move, move, variations, color, 0)
        sgf.add_move(move)
        sgf.add_comment(comment)
        comment = ""
        if move == 'resign':
            winner = switched(color)
            return winner, sgf, winrates
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
            return winner, sgf, winrates
    
        color = switched(color)
        move_nr += 1


def run_experiment(leela, weights, v1=1, v2=1, puct1=0.8, puct2=0.8, nr_of_games=1):
    leela1 = LzWrapper(leela, weights, v1, nr_rand_moves=10, remote=remote, puct=puct1)
    leela2 = LzWrapper(leela, weights, v2, nr_rand_moves=10, remote=remote, puct=puct2)

    b_wins = 0
    w_wins = 0
    #_log_to_file("Experiment: B visits={}, W visits={}, nr_of_games={}".format(v1, v2, nr_of_games))
    for i in range(nr_of_games):
        print("\nGame: nr_of_games={}/{}, leela={}, weights={}, v1={}, v2={}, puct1={}, puct2={}".format(str(i),str(nr_of_games), str(leela), str(weights), str(v1), str(v2), str(puct1), str(puct2)))
        _log_to_file("Clearing board.")
        leela1.clear_board()
        leela2.clear_board()
        
        sgf=sgf_creator(opening=[], visits1=v1, visits2=v2, puct1=puct1,puct2=puct2)
        _log_to_file("create self play.")
        try:
            winner, sgf, winrates = create_self_play_game(leela1, leela2, sgf)
            # dirty hack so that winrates are always from one side
            if winrates[-1] - winrates[-2] > 50:
                old_wr = winrates
                winrates = []
                c = 'B'
                for wr in old_wr:
                    if c == 'W':
                        winrates.append(100-wr)
                    else:
                        winrates.append(wr)
                    c = switched(c)

        except Exception as e_during_self_play:
            _error_to_file(e_during_self_play)
            print("Error at: nr_of_games={}, leela={}, weights={}, v1={}, v2={}, puct1={}, puct2={}".format(str(i), str(leela), str(weights), str(v1), str(v2, str(puct1), str(puct2))))
            print(e_during_self_play)
            continue
        if(winner=='B'):
            b_wins += 1
        else:
            w_wins += 1
        _log_to_file('\nB:W wins: {}-{}'.format(b_wins,w_wins))
        _winrate_to_file(leela, weights, v1, v2, winrates,puct1=puct1)
        sgf.save('games/eval_{}_vb{}_vw{}_puctb{}_{}.sgf'.format(str(datetime.datetime.now()), v1, v2, puct1, random.randint(0,100000)))
    return b_wins, w_wins

def main(remote=False):

    normal_leela = '/home/jonas/leela-study/leela-zero/src/leelaz'
    remote_leela = 'scripts/remote-leelaz'

    weights = 'network.gz'
    if remote:
        leela = remote_leela
    else:
        leela = normal_leela

    if remote:
        # start remote cloud
        print("Starting cloud")
        subprocess.call("scripts/start-instance.sh")

    nr_of_games = 100
    v1_range = [100]
    v2_range = ['same']
    puct1_range = [0.5, 0.6,0.9, 1]
    puct2=0.8
    print("Starting experiment. Nr_of_games={}, v1_range={}, v2_range={}, puct1_range={}".format(nr_of_games, list(v1_range), list(v2_range), list(puct1_range)))

    with open("results", "a") as myfile:
        myfile.write('visits_black,visits_white,win_black,win_white;\n')
    for v1 in v1_range:
        for v2 in [v1]:
            for puct1 in puct1_range:
                print(v1, v2, puct1)
                b_wins, w_wins = run_experiment(leela, weights, v1=v1, v2=v2, puct1=puct1, nr_of_games=nr_of_games)
                save_result(leela,weights,v1,v2,b_wins,w_wins,puct1=puct1)
                _log_to_file('Result: v1={}, v2={}, puct1={}: {}-{}'.format(v1,v2,puct1,b_wins,w_wins))
                with open("results", "a") as myfile:
                    myfile.write('{},{},{},{},{},{};\n'.format(v1,v2,puct1,puct2,b_wins,w_wins))

    if remote:
        # stop remote cloud
        print("stopping cloud.")
        subprocess.call("scripts/stop-instance.sh")
    print("End of experiment.\n\n\n")

remote = False

try:
    main(remote=remote)
except Exception as e:
    print(e)
    if remote:
        print("Error. stopping cloud.")
        subprocess.call("scripts/stop-instance.sh")