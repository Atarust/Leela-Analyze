# create some plots from the result file

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv


def uct_plot():
    # plot different c values and their win probability

    # import csv file
    df = pd.read_csv("result_file.csv")
    df.v1 = df.v1.astype('int')
    df.v2 = df.v2.astype('int')
    df.win_b = df.win_b.astype('int')
    df.win_w = df.win_w.astype('int')
    
    df['trials'] = df['win_b'] + df['win_w']
    df['win_prob_b'] = df['win_b']/(df['trials'])

    # filter out entries with less than 10 games
    df = df[df.win_b+df.win_w >= 50]
    df = df[df.v1==10]
    df = df[df.v2==10]
    
    # make plot x=uct value, y=winprobability
    fig, ax = plt.subplots()
    df.sort_values('puct1').groupby('trials').plot.scatter(x='puct1',y='win_prob_b', ax=ax)
    plt.show()

def b_vs_w_win_plot():
    df = csv_to_winrate_arrays("winrate_file.csv")
    df = add_attributes(df)
    df = min_visits(df, min_visit=10)
    df = has_puct(df, puct1=0.8, puct2=0.8)

    print(df.describe())

    df_b = df[df.b_surrender]
    df_w = df[df.w_surrender]
    draw_winrates(df_b['winrates'])
    plt.show()
    draw_winrates(df_w['winrates'])
    plt.show()

def winrate_plot(min_visit=20):
    df = csv_to_winrate_arrays("winrate_file.csv")
    df = add_attributes(df)
    df = min_visits(df, min_visit=min_visit)
    df = has_puct(df, puct1=puct1, puct2=puct2)
    draw_winrates(df['winrates'])
    plt.show()

def ave_wr_depending_on_wr_after_n_moves(n=20, wr_range=10):
    df = csv_to_winrate_arrays("winrate_file.csv")
    df = add_attributes(df)
    #df = min_visits(df, min_visit=10)
    #df = has_puct(df, puct1=0.8, puct2=0.8)
    # look at wr after 10 moves. Then count how many games where
    wrs = []
    totals = []
    b_wons = []
    w_wons = []
    wr_ends = []
    for wr in range(0,100,wr_range):
        df_wr = df[df.apply(lambda x: x.winrates[n] > wr and x.winrates[n] < wr+wr_range, axis=1)]
        df_wr['wr_last'] = df_wr.apply(lambda x: x.winrates[-1], axis=1)
        #df_wr=df[df.winrates[10] > wr]
        # count how many games where won
        total = len(df_wr)
        b_won = len(df_wr[df_wr.w_surrender])
        w_won = len(df_wr[df_wr.b_surrender])
        wrs.append(wr)
        totals.append(total)
        b_wons.append(b_won)
        w_wons.append(w_won)
        wr_ends.append(df_wr.wr_last.mean())
        print("wr={}, total={}, b_won={}, w_won={}, rest={}".format(wr, total, b_won, w_won, total-b_won-w_won))
    plt.plot(wrs, wr_ends)
    plt.xlabel('wr after n moves')
    plt.ylabel('average wr last move')
    plt.show()

def count_wins_depending_on_wr_after_n_moves(n=-20):
    df = csv_to_winrate_arrays("winrate_file.csv")
    df = add_attributes(df)
    #df = min_visits(df, min_visit=10)
    #df = has_puct(df, puct1=0.8, puct2=0.8)
    # look at wr after 10 moves. Then count how many games where
    wrs = []
    totals = []
    b_wons = []
    w_wons = []
    for wr in range(0,100,10):
        df_wr = df[df.apply(lambda x: x.winrates[n] > wr and x.winrates[n] < wr+10, axis=1)]
        #df_wr=df[df.winrates[10] > wr]
        # count how many games where won
        total = len(df_wr)
        b_won = len(df_wr[df_wr.w_surrender])
        w_won = len(df_wr[df_wr.b_surrender])
        wrs.append(wr)
        totals.append(total)
        b_wons.append(b_won)
        w_wons.append(w_won)
        print("wr={}, total={}, b_won={}, w_won={}, rest={}".format(wr, total, b_won, w_won, total-b_won-w_won))
    plt.plot(wrs, b_wons)
    plt.plot(wrs, w_wons)
    plt.plot(wrs, totals)
    plt.show()
    

def depending_on_visit_plot():
    df = csv_to_winrate_arrays("winrate_file.csv")
    df = add_attributes(df)
    for v in df['v1'].unique():
        print(v)
        df_visits = df[df.v1 == v]
        df_visits = df_visits[df_visits.v2 == v]
        draw_winrates(df_visits['winrates'])
        plt.show()

def add_attributes(df):
    df['b_surrender'] = df.apply(lambda x: x.winrates[-1] < 20, axis=1)
    df['w_surrender'] = df.apply(lambda x: x.winrates[-1] > 80, axis=1)
    return df

def csv_to_winrate_arrays(csv_name):
    # winrate csv looks like this:
    # 2018-12-31 12:44:57.777072	/home/jonas/leela-study/leela-zero/src/leelaz	network.gz	10	10	0.3	0.8	63.27
    # date leela-binary network v1, v2, puct1 puct2 winrate_move1 winrate_move2 ...
    time_data = []
    leela_binary_data = []
    network_data = []
    v1_data = []
    v2_data = []
    puct1_data = []
    puct2_data = []
    winrate_data = []

    with open(csv_name) as csvfile:
        reader = csv.reader(csvfile)
        for line in reader:
            time_data.append(line[0])
            leela_binary_data.append(line[1])
            network_data.append(line[2])
            v1_data.append(int(line[3]))
            v2_data.append(int(line[4]))
            puct1_data.append(float(line[5]))
            puct2_data.append(float(line[6]))
            winrate_data.append([float(i) for i in line[7:-1:2]])
    data = {'time' : time_data, 'leela_binary' : leela_binary_data, 'v1' : v1_data, 
    'v2' : v2_data, 'puct1' : puct1_data, 'puct2' : puct2_data, 'winrates' : winrate_data}
    return pd.DataFrame(data)

def draw_winrates(winrate_data, samples=10):
    for winrates in winrate_data.sample(samples):
        plt.plot(winrates)
    plt.xlabel('Move Number')
    plt.ylabel('Winrate')


def not_alternates(entry):
    count_change_between_40_60 = 0
    length = len(entry.winrates)
    for idx in range(length -7, length-1):
        if entry.winrates[idx] > 60 and entry.winrates[idx+1] < 40:
            # alternates
            count_change_between_40_60 += 1
    alternates = count_change_between_40_60*2 / len(entry.winrates[-7:-1]) > 0.9
    print(count_change_between_40_60*2 / len(entry.winrates[-7:-1]))
    return not alternates
        
def min_visits(df, min_visit=10):
    df = df[df.v1 >= min_visit]
    df = df[df.v2 >= min_visit]
    return df 

def has_puct(df, puct1=0.8, puct2=0.8, delta=0.01):
    df = df[df.puct1 < puct1+delta]
    df = df[df.puct1 > puct1-delta]
    df = df[df.puct2 < puct2+delta]
    df = df[df.puct2 > puct2-delta]
    return df 

ave_wr_depending_on_wr_after_n_moves()
