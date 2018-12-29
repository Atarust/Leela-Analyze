from misc import switched, format_00_to_sgf

from leelazWrapper import _log_to_file

class sgf_creator:
    def __init__(self, opening=[], visits1=0, visits2=0, puct1=0.8, puct2=0.8, weights1='weights', weights2='weights', date='1999-12-31', 
                    player1='LeelaZero', player2='LeelaZero', result = 'B+Resign', comment=''):
        self.game = opening
        self.visits1 = visits1
        self.visits2 = visits2
        self.puct1 = puct1
        self.puct2 = puct2
        self.weights1 = weights1
        self.weights2 = weights1
        self.date = date
        self.player1 = player1
        self.player2 = player2
        self.result = result
        self.comment = comment
        self.comment += 'visits1 = {}, visits2 = {}, puct1={}, puct2={}, weights1 = {}, weights2 = {}'.format(self.visits1, self.visits2, self.puct1, self.puct2, self.weights1, self.weights2)
    def add_move(self, move):
        self.game.append(move)
    def add_comment(self,text):
        self.game.append("C[{}]".format(text))
    def get_sgf(self):
        string = '(;GM[1]FF[4]RU[Chinese]DT[{}]SZ[19]KM[7.5]PB[{}]PW[{}]RE[{}]C[{}]'.format(self.date, str(self.player1)+'_puct=' + str(self.puct1), str(self.player2)+'_puct=' + str(self.puct2), self.result, self.comment)
        color = 'B'
        for move in self.game:
            if move == 'pass' or move == 'resign':
                continue
            if len(move)>=2 and move[0] == 'C':
                # is a comment. like this: ;W[ss]C[dis is a test]
                string += move
                continue
            else:
                string += ';{}[{}]'.format(color, format_00_to_sgf(move))

            color = switched(color)

        string += ')'
        return string
    def save(self, filename):
        _log_to_file("saving sgf file")
        with open(filename, "w") as text_file:
            text_file.write(self.get_sgf())