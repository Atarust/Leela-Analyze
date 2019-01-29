lz_binary = '/leela/leelaz'
weights = '/leela/best-network.gz'
visits = '10000'
nr_of_games = 10
  
import os
import re
import sys
import time

from configparser import ConfigParser
from queue import Queue, Empty
from subprocess import PIPE, Popen
from threading import Thread
import datetime


game = []
v = visits
w = weights

def stream_reader(stream, queue):
    """
    Read lines from stream and put them into queue.
    :param stream: where to read lines from
    :param queue: where to put the lines into
    """
    for line in stream:
        if isinstance(line, str):
            queue.put(line)
        else:
            queue.put(line.decode())
    stream.close()


def start_reader(stream):
    """
    Start reading lines from the given stream, putting them in a freshly
    created queue and return the queue.

    :param stream: stream to read from
    :returns: create queue
    """
    queue = Queue()
    reader = Thread(target=stream_reader, args=(stream, queue))
    reader.daemon = True
    reader.start()
    return queue


def dump_to_stream(queue, stream):
    """Dump queue content to stream, non-blocking.
    :param queue: where to get content from
    :param stream: where to dump content to
    """
    res = False
    while True:
        try:
            line = queue.get_nowait()
        except Empty:
            return res
        res = True
        stream.write(line)
        stream.flush()

def _dumb_log(message):
    sys.stderr.write("DUMBSTONE: {}\r\n".format(message))
    sys.stderr.flush()


class LzWrapper:
    """
    Wrapper for Leela Zero process.
    """
    _VARIATION = re.compile(r" *([^ ]*) -> *([^ ]*) \(V: ([^%]*)%\).*$")

    def __init__(self, lz_binary, weights, visits, log_f=_dumb_log):
        """
        Start Leela Zero wrapper.

        :param lz_binary: path to Leela Zero binary
        :param weights: path to weights file
        :param visits: number of visits to use
        :param log_f: function to log messages
        """

        self._log = log_f
        self._debug_lz = True

        cmd_line = [lz_binary]
        cmd_line += ['-w', weights]
        cmd_line += ['-v', visits]
        cmd_line += ['--gtp']

        # pylint: disable=fixme
        cmd_line += ['-m', '30']  # FIXME: hardcoded
        self._log("Starting LZ")
        self._lz = Popen(cmd_line,
                         stdin=PIPE, stdout=PIPE, stderr=PIPE,
                         bufsize=1)

        self._lz_out = start_reader(self._lz.stdout)
        self._lz_err = start_reader(self._lz.stderr)

    def dump_stderr(self):
        """
        Write to sys.stderr everything LZ has to say on stderr, return True if
        something was outputted, False otherwise.
        """
        if self._debug_lz:
            return dump_to_stream(self._lz_err, sys.stderr)
        else:
            with open(os.devnull, 'w') as nowhere:
                return dump_to_stream(self._lz_err, nowhere)

    def dump_stdout(self):
        """
        Write to sys.stdout everything LZ has to say on stdout, return True if
        something was outputted, False otherwise.
        """
        return dump_to_stream(self._lz_out, sys.stdout)

    def _consume_stdout_until_ready(self):
        legal_move = True
        while True:
            out = self._lz_out.get()  # blocking!
            the_output = out.strip()
            if self._debug_lz:
                self._log("Consumed: {}".format(the_output))
            if len(the_output) > 0 and the_output[0] == '?':
                legal_move = False
                print("found illegal move!")
                return legal_move
            if out[0:1] == '=':
                return legal_move

    def dump_stdout_until_ready(self):
        """
        Dump LZ's stdout to sys.stdout until GTP normal reply (starting with
        '=' or '?'); inclusive.
        """
        while True:
            out = self._lz_out.get()  # blocking!
            sys.stdout.write(out)
            sys.stdout.flush()
            if out[0:1] in ['=', '?']:
                return

    def pass_to_lz(self, command):
        """
        Pass the command to LZ without any modifications.

        :param command: ASCII string, the command to pass to LZ. Expected to
        end with \r\n
        :param dump_stdout: if True, dumps LZ's stdout to sys.stdout until '=
        ...' GTP line (inclusive)
        """
        command_bytes = bytes(command, encoding='ascii')
        self._lz.stdin.write(command_bytes)
        self._lz.stdin.flush()

    def _wait_for_move(self):
        while True:
            out = self._lz_out.get()  # blocking!
            if out[0:1] == '=':
                return out[2:].strip()
            else:
                sys.stdout.write(out)
                sys.stdout.flush()

    def _read_variations(self, min_visits):
        variations = []
        dropped = []
        while True:
            line = self._lz_err.get()  # blocking
            if self._debug_lz:
                sys.stderr.write(line)
                sys.stderr.flush()
            if line[:8] == 'NN eval=':
                # variations for expected reply start -- we're done
                break
        return variations


    # pylint:disable=too-many-arguments
    def genmove(self, color,
                probability=50.0,
                min_visits=0,
                max_drop_percent=100.0, pass_terminates=False):
        """
        Generate move.

        Will output things to stderr and stdout.

        :param color: player to generate move for ('b' or 'w')
        :param probability: preferred probability to win (float, percents)
        :param log_f: function to pass logging messages to
        """
        command = "genmove {}\r\n".format(color)
        self.pass_to_lz(command)
        # Ask LZ for the best move
        move = self._wait_for_move()
        if move == "resign":
            return move

        if move == "pass":
            return move

        # Now wait for variations
        while True:
            line = self._lz_err.get()  # blocking!
            if self._debug_lz:
                sys.stderr.write(line)
                sys.stderr.flush()
            if line[:8] == 'NN eval=':
                break

        return move
    def play(self, color, move):
        command = "play {} {}\r\n".format(color, move)
        self.pass_to_lz(command)
        return self._consume_stdout_until_ready()

def load_config():
    """
    Load dumbstone.ini
    """
    path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(path, 'dumbstone.ini')
    config = ConfigParser()
    with open(config_path, 'r') as config_file:
        config.read_file(config_file)
    return config

def new_game(game=game,visits=0,weights='weights'):
    game = []
    global v
    global w
    v = visits
    w = weights
def add_move(move, game=game):
    game.append(move)
    print("added {}".format(move))
def get_sgf():
    string = '(;GM[1]FF[4]RU[Chinese]DT[1999-12-31]SZ[19]KM[7.5]PB[LeelaZero_v={}]PW[Mirror]RE[B+Resign]C[visits = {}, weights file = {}]'.format(v, v, w)
    color = 'B'
    for move in game:

        if move == 'pass' or move == 'resign':
            continue
        string += ';{}[{}]'.format(color, format_00_to_sgf(move))

        if color == 'B':
            color = 'W'
        else:
            color = 'B'

    string += ')'
    return string

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
        return chr(move[0]+ord('a')) + chr(move[1]+ord('a'))
    else:
        return move

def format_00_to_a1(move):
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
  else:
    return 'B'
  
def get_move(leela, color):
    move = leela.genmove(color, probability=1, min_visits=0, pass_terminates=True)
    #print("get move: {}".format(move))
    assert(len(move) > 1)  # assert there is a move
    return format_to_00(move)

def mirror_move(move):

    # if pass
    if move == "pass":
        return move

    # if Resign
    if move == "resign":
        return "resign"

    # if tengen
    if move == (9,9):
        return "pass"

    mirrored_move = (18 - move[0], 18 - move[1])
    return mirrored_move

  
# read sgf file and create list of moves
opening = 'file.sgf'
with open(opening, "r") as text_file:
  content = text_file.read()
content = content.split(';')

moves = []
for command in content:
  if command[0] == 'B' or command[0] == 'W':
    #print('command = ' + command[:])
    #if(command[2:4] == 'resign' or  command[2:4] == 'pass'):
    #print('cmd=' + command[2:4])
    moves.append(format_sgf_to_00(command[2:4]))


# play all moves to bring leela in the correct state
leela = LzWrapper(lz_binary, weights, visits)
new_game(visits=visits, weights=weights)

color = 'B'
move_nr = 1
for move in moves:
  leela.play(color,format_00_to_a1(move))
  add_move(move)
  #print("play opening move:" + str(move_nr))
  #print(move)
  #print(format_00_to_a1(move))
  color = switched(color)
  move_nr += 1
opening_length = move_nr

#time.sleep(10)
# playout rest of the game using leela + mirror
while move != 'pass' and move != 'resign':
  if color == 'B':
    move = get_move(leela, color)    
  else:
    move = mirror_move(move)
    legal = leela.play(color,format_00_to_a1(move))
    if(not legal):
      print("mirroring is not possible at move", move_nr)
      break
  print(move)
  add_move(move)
  if(move == (9,9)):
    print("tengen played")
    break
  color = switched(color)
  move_nr += 1

# Mirror go has ended, either because there was a pass, a resign or an illegal move.

# just play normal leela untill end
while move != 'pass' and move != 'resign':
  if color == 'B':
    move = get_move(leela, color)    
  else:
    move = get_move(leela, color)    
    
  print(move)
  add_move(move)
  color = switched(color)
  move_nr += 1



sgf = get_sgf()
name = "opening_{}_spiegeln_w_vs_leela_b_game_v{}_openinglength{}_{}.sgf".format(opening, visits, opening_length, str(datetime.datetime.now()))
with open(name, "w") as text_file:
  text_file.write(sgf)
