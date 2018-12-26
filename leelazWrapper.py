# This is modified code from https://github.com/avysk/dumbstone - Thank you!
import os
import re
import sys
import time

from configparser import ConfigParser
from queue import Queue, Empty
from subprocess import PIPE, Popen
from threading import Thread
import datetime

from misc import format_to_00, format_00_to_leela

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

    def __init__(self, lz_binary, weights, visits, puct=0.8, log_f=_dumb_log, debug=False):
        """
        Start Leela Zero wrapper.

        :param lz_binary: path to Leela Zero binary
        :param weights: path to weights file
        :param visits: number of visits to use
        :param log_f: function to log messages
        """

        self._log = log_f
        self._debug_lz = debug
        cmd_line = [lz_binary]
        cmd_line += ['-w', weights]
        cmd_line += ['-v', str(visits)]
        cmd_line += ['-c', str(puct)]
        
        cmd_line += ['--gtp']
        cmd_line += ['-r10'] # do not resign before x%


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
            out = self._lz_out.get(timeout=30)  # blocking!
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
                if self._debug_lz:
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
            match = LzWrapper._VARIATION.match(line)
            if match:
                move, visits, win = match.groups()
                if (int(visits) >= min_visits) or (move == 'pass'):
                    # never drop pass variation
                    variations.append((move, visits, win))
                else:
                    dropped.append((move, visits))
        dropped_line = (("{} ({})".format(*drop) for drop in dropped))
        assert variations, "Didn't find any variations! " \
                           "Is min_visits too high or visits too low?"

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
            return move, []

        if move == "pass":
            return move, []
        # Now wait for variations
        while True:
            line = self._lz_err.get()  # blocking!
            if self._debug_lz:
                sys.stderr.write(line)
                sys.stderr.flush()
            if line[:8] == 'NN eval=':
                break
        variations = self._read_variations(min_visits)

        return format_to_00(move), variations
    def play(self, color, move):
        if not (move == 'resign' or move == 'pass'):
          move = format_00_to_leela(move)
        command = "play {} {}\r\n".format(color, move)
        self.pass_to_lz(command)
        return self._consume_stdout_until_ready()

    def undo(self):
        command = "undo\r\n"
        self.pass_to_lz(command)
        time.sleep(0.1)
        return self._consume_stdout_until_ready()
      
    def clear_board(self):
        command = "clear_board\r\n"
        self.pass_to_lz(command)
        time.sleep(0.1)
        try:
          self._consume_stdout_until_ready()
        except(Empty):
          print('clear board gave no feedback. Hope it still works.')
          pass
        return 
