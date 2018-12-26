import datetime

def format_to_00(move_in):
    # there exists formats: a1, 00, aa, A1
    if len(move_in) == 2:
        move = (move_in[0],move_in[1])
    elif len(move_in) == 3:
        move = (move_in[0],move_in[1:3])
    else: # pass or resign
        return move_in

    if is_lower_case_letter(move[0]) and is_lower_case_letter(move[1]):
        # aa to 00
        return (coord_lower_letter_to_0(move[0]), coord_lower_letter_to_0(move[1]))
    elif is_lower_case_letter(move[0]) and is_number(move[1]):
        # a1 to 00
        return (coord_lower_letter_to_0(move[0]), int(move[1])-1)
    elif is_upper_case_letter(move[0]) and is_number(move[1]):
        # A1 to 00
        return (coord_upper_letter_to_0(move[0]), int(move[1])-1)
    elif is_number(move[0]) and is_number(move[1]):
        # 00
        return move
    else:
        print('unknown format of coordinates')

def format_sgf_to_00(move_in):
  # Die y-achse muss invertiert werden.
  return ((ord(move_in[0]) - ord('a')), 18 - (ord(move_in[1]) - ord('a')))

def format_00_to_sgf(move): # sgf format is aa including i and j
    if len(move) == 2:
        return chr(move[0]+ord('a')) + chr((18 - move[1])+ord('a'))

    else:
        return move

def format_00_to_a1(move):
    if len(move) == 2:
        return coord_0_to_lower_letter(move[0]) + str(move[1]+1)
    elif len(move) > 2:
        return move
    else:
        print('fail. move is too small')

def format_00_to_leela(move):
    if len(move) == 2:
        return coord_0_to_lower_letter(move[0]) + str(move[1]+1)
    elif len(move) > 2:
        return move
    else:
        print('fail. move is too small')

def is_lower_case_letter(coord):
    return ord(coord) >= ord('a') and ord(coord) <= ord('t')

def is_upper_case_letter(coord):
    return ord(coord) >= ord('A') and ord(coord) <= ord('T')

def is_number(coord):
    return int(coord) >= 0 and int(coord) <= 19

def coord_lower_letter_to_0(letter):
    # there is no j
    if ord(letter) < ord('i'):
        return ord(letter)-ord('a')
    else:
        return ord(letter)-ord('a')-1

def coord_upper_letter_to_0(letter):
    # there is no j
    if ord(letter) < ord('I'):
        return ord(letter)-ord('A')
    else:
        return ord(letter)-ord('A')-1

def coord_0_to_lower_letter(coord):
    # there is no i
    if coord < 8:
        return chr(coord+ord('a'))
    else:
        return chr(coord+ord('a')+1)

def coord_0_to_upper_letter(coord):
    # there is no i
    if coord < 8:
        return chr(coord+ord('A'))
    else:
        return chr(coord+ord('A')+1)

def switched(color):
  if color == 'B':
    return 'W'
  elif color == 'W':
    return 'B'
  else:
    return color

def mirror_move(move):

    # if pass
    if move == "pass":
        return move

    # if Resign
    if move == "resign":
        return "resign"

    # if tengen
    if move == (9,9):
        return "no_mirror"

    mirrored_move = (18 - move[0], 18 - move[1])
    return mirrored_move

def analyse_move(leela, color, actual_move, last_move_winrate):
    """ returns a comment containing variations"""
    best_move, variations = leela.genmove(color)
    # after genmove go back to original position
    leela.undo()

    new_variations = []

    for move_proposals in variations:
        move_prop = move_proposals[0]
        visits_prop = int(move_proposals[1])
        winrate_prop = float(move_proposals[2])
        # always show winrate from blacks perspective
        if color == 'W':
            winrate_prop = 100 - winrate_prop
        new_variations.append((move_prop, visits_prop, winrate_prop))
    variations = new_variations

    comment = generate_comment(best_move, actual_move, variations, color, last_move_winrate)
    if len(variations)>0:
        winrate = float(variations[0][2]) # assuming moves are sorted
    else:
        winrate = 0
    return comment, best_move, winrate

def generate_comment(best_move, actual_move, variations, color, last_move_winrate):
    comment = color + ":\n"
    for move_proposals in variations:
        comment += "{}: {} visits, {}%\n".format(move_proposals[0],move_proposals[1],move_proposals[2])
    if best_move == actual_move:
        comment += "\nbest move!!"
    if len(variations)>0:
        winrate_after_playing_this_move = float(variations[0][2])
        winrate_if_best_move_would_have_been_played = last_move_winrate
        loss = winrate_after_playing_this_move- winrate_if_best_move_would_have_been_played # how much winrate the move lost
        comment += "\nlost {}% winrate (this display still needs to be tested)".format(loss)
    return comment

def adjust_variations_to_color(variations,color):
    new_variations = []
    for move_proposals in variations:
        move_prop = move_proposals[0]
        visits_prop = int(move_proposals[1])
        winrate_prop = float(move_proposals[2])
        # always show winrate from blacks perspective
        if color == 'W':
            winrate_prop = 100 - winrate_prop
        new_variations.append((move_prop, visits_prop, winrate_prop))
    return new_variations