import pygame

#TODO: 
# needs aditional work on GUI/UX; 
# add timer; 
# chosen piece following the mouse;

# Initialize Pygame
pygame.init()

# Screen dimensions
CELL_SIZE = 120
ROWS, COLS = 6, 6
BUFFER = 40
WIDTH, HEIGHT = CELL_SIZE * ROWS + BUFFER * 2, CELL_SIZE * COLS + BUFFER * 2
GRID_THICKNESS = 2

# Colors
BEIGE = (225, 225, 200)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
LIGHT_RED = (255, 127, 127)
BLUE = (0, 0, 255)
LIGHT_BLUE = (173, 216, 230)
GRAY = (200, 200, 200)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 100)

# Game states
START, PLAYER1_MOVE, PLAYER2_MOVE, MOVE_CHECK, CHECK_WIN, END, RESTART = \
"START", "PLAYER1_MOVE", "PLAYER2_MOVE", "MOVE_CHECK", "CHECK_WIN", "END", "RESTART"

# Set up of screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Diamond Game")
clock = pygame.time.Clock()
FPS = 30

# Fonts
font = pygame.font.SysFont(None, 100)

class Player:
    def __init__(self, pieces: list) -> None:
        self.pieces = pieces

    def draw(self, highlight = False) -> None:
        for piece in self.pieces:
            pos = (piece.position[0] * CELL_SIZE + BUFFER, piece.position[1] * CELL_SIZE + BUFFER)
            if highlight:
                # highlight buffer set to 2px, increase if needed
                pygame.draw.circle(screen, WHITE, pos, piece.rad + 2, 2)
            pygame.draw.circle(screen, piece.color, pos, piece.rad)

class Pieces:
    def __init__(self, type: str, color, position: tuple, rad) -> None:
        self.type = type
        self.color = color
        self.position = position
        self.rad = rad

    # for debugging purposes
    def __repr__(self) -> str:
        return f"{self.type}, {self.position}"

class Game:
    def __init__(self) -> None:
        self.state = START
        self.hole_rad = 10; self.predict_rad = 8; self.player_rad = 15; self.king_buffer = 5
        player1_pieces = []; player2_pieces = []
        piece_positions = set()
        for i in range(3): 
            for j in range(3):
                if (i, j) == (1,1):
                    player1_pieces.append(Pieces("King", BLUE, (i, j + 2), self.player_rad + self.king_buffer))
                    player2_pieces.append(Pieces("King", RED, (i + 4, j + 2), self.player_rad + self.king_buffer))
                else:
                    player1_pieces.append(Pieces("Pawn", LIGHT_BLUE, (i, j + 2), self.player_rad))
                    player2_pieces.append(Pieces("Pawn", LIGHT_RED, (i + 4, j + 2), self.player_rad))
                piece_positions.add((i, j + 2))
                piece_positions.add((i + 4, j + 2))
        player1 = Player(player1_pieces); player2 = Player(player2_pieces)
        self.players = [player1, player2]
        self.piece_positions = piece_positions
        self.current_player_index = 0
        self.selected_piece = []
        self.jumped = False; self.show_valid_moves = False; self.moved = False
        self._excluded_spots = {(0,0), (0,1), (1,0), (1,1), (6,0), (5,0), (6,1), (5,1), (0,6), (0,5), (1,6), (1,5), (6,6), (6,5), (5,6), (5,5)}
        self._directions = ((1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1))
        self.winner = -1
                
    def draw_board(self) -> None:
        # fill background
        screen.fill(BEIGE)
        # draw board
        board = pygame.Rect(BUFFER, BUFFER, CELL_SIZE * ROWS, CELL_SIZE * COLS)
        pygame.draw.rect(screen, BLACK, board, GRID_THICKNESS)
        # draw grid lines
        for big_row in range(3):
            for big_col in range(3):
                if (big_row, big_col) in {(0,0), (2,0), (0,2), (2,2)}:
                    big_grid = pygame.Rect(BUFFER + (big_col * 2) * CELL_SIZE, BUFFER + (big_row * 2) * CELL_SIZE, CELL_SIZE * 2, CELL_SIZE * 2)
                    pygame.draw.rect(screen, BLACK, big_grid, GRID_THICKNESS // 2)
                else:
                    for row in range(2):
                        for col in range(2):
                            grid = pygame.Rect(BUFFER + (col + big_col * 2) * CELL_SIZE, BUFFER + (row + big_row * 2) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                            pygame.draw.rect(screen, BLACK, grid, GRID_THICKNESS // 2)
                            diagonal = pygame.Surface((CELL_SIZE * 1.38, 4), pygame.SRCALPHA)
                            pygame.draw.rect(diagonal, BLACK, (0, 0, CELL_SIZE * 1.38, GRID_THICKNESS))
                            rotated_1 = pygame.transform.rotate(diagonal, 315)
                            screen.blit(rotated_1, (BUFFER + (col + big_col * 2) * CELL_SIZE, BUFFER + (row + big_row * 2) * CELL_SIZE))
                            rotated_2 = pygame.transform.rotate(diagonal, 45)
                            screen.blit(rotated_2, (BUFFER + (col + big_col * 2) * CELL_SIZE, BUFFER + (row + big_row * 2) * CELL_SIZE))                
        # draw holes
        for row in range(7):
            for col in range(7):
                if (row, col) not in self._excluded_spots:
                    pygame.draw.circle(screen, BLACK, (BUFFER + row * CELL_SIZE, BUFFER + col * CELL_SIZE), self.hole_rad)

    def draw_players(self) -> None:
        player1, player2 = self.players
        player1.draw(highlight = (self.state == PLAYER1_MOVE))
        player2.draw(highlight = (self.state == PLAYER2_MOVE))

    def handle_event(self, event) -> None:
        if event.button == 1:
            x_pos, y_pos = event.pos

            # snap position into corrisponding grid
            x = (x_pos - BUFFER) // CELL_SIZE; y = (y_pos - BUFFER) // CELL_SIZE
            if ((x_pos - BUFFER) % CELL_SIZE) * 4 >= CELL_SIZE * 3:
                x += 1
            elif ((x_pos - BUFFER) % CELL_SIZE) * 4 > CELL_SIZE:
                return None
            if ((y_pos - BUFFER) % CELL_SIZE) * 4 >= CELL_SIZE * 3:
                y += 1
            elif ((y_pos - BUFFER) % CELL_SIZE) * 4 > CELL_SIZE:
                return None

            # handling selection/movement of pieces
            if self.selected_piece and ((x, y) not in self.piece_positions):
                self.moved = True
                if not self.handle_move((x, y)):
                    self.current_player_index = 1 - self.current_player_index
                    self.state = CHECK_WIN
                    self.selected_piece.clear()
                    self.show_valid_moves = False; self.jumped = False; self.moved = False
                check_winner = self.check_king()
                if check_winner >= 0:
                    self.state = END
                    self.winner = check_winner
            elif not self.moved:
                self.handle_select((x, y))
        
        # right-click to end turn
        elif event.button == 3:
            self.current_player_index = 1 - self.current_player_index
            self.state = CHECK_WIN
            self.selected_piece.clear()
            self.show_valid_moves = False; self.jumped = False; self.moved = False
                
    def handle_select(self, pos: tuple) -> None:
        for piece in self.players[self.current_player_index].pieces:
            if pos == piece.position:
                self.selected_piece.clear()
                self.show_valid_moves = True
                self.selected_piece.append(piece)
                return None

    def handle_move(self, pos: tuple) -> bool:
        valid = self.valid_moves(self.selected_piece[0].position)
        if len(valid) == 0:
            return False
        if pos in valid:
            if abs(pos[0] - self.selected_piece[0].position[0]) == 2 or abs(pos[1] - self.selected_piece[0].position[1]) == 2:
                self.jumped = True
                jumped_pos = ((pos[0] + self.selected_piece[0].position[0]) // 2, (pos[1] + self.selected_piece[0].position[1]) // 2)
                for piece in self.players[1 - self.current_player_index].pieces:
                    if piece.position == jumped_pos:
                        self.players[1 - self.current_player_index].pieces.remove(piece)
                        self.piece_positions.remove(piece.position)
                        break
                self.piece_positions.remove(self.selected_piece[0].position)
                self.selected_piece[0].position = pos
                self.piece_positions.add(pos)
                self.state = MOVE_CHECK
                return True
            else:
                self.piece_positions.remove(self.selected_piece[0].position)
                self.selected_piece[0].position = pos
                self.piece_positions.add(pos)
                self.state = MOVE_CHECK
                return False

    def is_in_grid(self, pos) -> bool:
        return (0 <= pos[0] <= 6 and 0 <= pos[1] <= 6) and pos not in self._excluded_spots

    def valid_moves(self, pos: tuple) -> set[tuple]:
        val_move = []
        for d in self._directions:
            next_pos = (d[0] + pos[0], d[1] + pos[1])
            if self.is_in_grid(next_pos):
                if next_pos in self.piece_positions:
                    if self.is_in_grid((next_pos[0] + d[0], next_pos[1] + d[1])) and (next_pos[0] + d[0], next_pos[1] + d[1]) not in self.piece_positions:
                        if (next_pos, (next_pos[0] + d[0], next_pos[1] + d[1])) not in {((1,4), (2,5)), ((2,5), (1,4)), ((1,2), (2,1)), ((2,1), (1,2)), ((4,1), (5,2)), ((5,2), (4,1)), ((4,5), (5,4)), ((5,4), (4,5))} and \
                           (pos, next_pos) not in {((1,4), (2,5)), ((2,5), (1,4)), ((1,2), (2,1)), ((2,1), (1,2)), ((4,1), (5,2)), ((5,2), (4,1)), ((4,5), (5,4)), ((5,4), (4,5))}:
                            val_move.append((next_pos[0] + d[0], next_pos[1] + d[1]))
                elif not self.jumped:
                    if (pos, next_pos) not in {((1,4), (2,5)), ((2,5), (1,4)), ((1,2), (2,1)), ((2,1), (1,2)), ((4,1), (5,2)), ((5,2), (4,1)), ((4,5), (5,4)), ((5,4), (4,5))}:
                        val_move.append(next_pos)
        return val_move

    def highlight_valid_moves(self, pos) -> None:
        for moves in self.valid_moves(pos):
            pygame.draw.circle(screen, GRAY, (moves[0] * CELL_SIZE + BUFFER, moves[1] * CELL_SIZE + BUFFER), self.predict_rad)

    def highlight_selected_piece(self) -> None:
        if self.selected_piece:
            piece = self.selected_piece[0]
            pygame.draw.circle(screen, YELLOW, (piece.position[0] * CELL_SIZE + BUFFER, piece.position[1] * CELL_SIZE + BUFFER), self.predict_rad // 2)

    def check_king(self) -> int:
        for i in range(2):
            player = self.players[i]
            for piece in player.pieces:
                if piece.type == "King":
                    break
            else:
                return 1 - i
        else:
            return -1

    def check_win(self) -> int:
        for i in range(2):
            player = self.players[i]
            if len(player.pieces) == 0:
                return 1 - i
        return self.check_king()
    
    def write_instructions(self) -> None:
        text_buffer = 40; box_thickness = 10; box_cleaning_1 = 5; box_cleaning_2 = 10
        instruct_1 = font.render("Left Click to", True, BEIGE)
        instruct_2 = font.render("Select & Move pieces", True, BEIGE)
        box_1 = pygame.Rect(0, HEIGHT // 2 - text_buffer * 6 - box_cleaning_1, WIDTH, text_buffer * 4 + box_cleaning_2)
        instruct_3 = font.render("Right Click to", True, BEIGE)
        instruct_4 = font.render("End your turn", True, BEIGE)
        box_2 = pygame.Rect(0, HEIGHT // 2 - text_buffer * 2 - box_cleaning_1, WIDTH, text_buffer * 4 + box_cleaning_2)
        instruct_5 = font.render("Press any key to", True, BEIGE)
        instruct_6 = font.render("Start the game!", True, BEIGE)
        box_3 = pygame.Rect(0, HEIGHT // 2 + text_buffer * 2 - box_cleaning_1, WIDTH, text_buffer * 4 + box_cleaning_2)
        screen.fill(BLACK)
        screen.blit(instruct_1, (WIDTH // 2 - instruct_1.get_width() // 2, HEIGHT // 2 - instruct_1.get_height() // 2 - text_buffer * 5))
        screen.blit(instruct_2, (WIDTH // 2 - instruct_2.get_width() // 2, HEIGHT // 2 - instruct_2.get_height() // 2 - text_buffer * 3))
        pygame.draw.rect(screen, BEIGE, box_1, box_thickness)
        screen.blit(instruct_3, (WIDTH // 2 - instruct_3.get_width() // 2, HEIGHT // 2 - instruct_3.get_height() // 2 - text_buffer))
        screen.blit(instruct_4, (WIDTH // 2 - instruct_4.get_width() // 2, HEIGHT // 2 - instruct_4.get_height() // 2 + text_buffer))
        pygame.draw.rect(screen, BEIGE, box_2, box_thickness)
        screen.blit(instruct_5, (WIDTH // 2 - instruct_5.get_width() // 2, HEIGHT // 2 - instruct_5.get_height() // 2 + text_buffer * 3))
        screen.blit(instruct_6, (WIDTH // 2 - instruct_6.get_width() // 2, HEIGHT // 2 - instruct_6.get_height() // 2 + text_buffer * 5))
        pygame.draw.rect(screen, BEIGE, box_3, box_thickness)

        
    def write_end_screen(self) -> None:
        if self.winner != -1:
            if self.winner == 0:
                winner_text = font.render(f"Blue Player wins!", True, BLUE)
            elif self.winner == 1:
                winner_text = font.render(f"Red Player wins!", True, RED)
            restart_text = font.render(f"Press any key to restart", True, BEIGE)
            box_1 = pygame.Rect(0, HEIGHT // 2 - 85, WIDTH, 170)
            screen.fill(BLACK)
            pygame.draw.rect(screen, BEIGE, box_1, 10)
            screen.blit(winner_text, (WIDTH // 2 - winner_text.get_width() // 2, HEIGHT // 2 - winner_text.get_height() // 2 - 40))
            screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 - restart_text.get_height() // 2 + 40))

    def run(self) -> int:
        self.draw_board()
        for player in self.players:
            player.draw()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button != 2:
                    self.handle_event(event)
                elif event.type == pygame.KEYDOWN:
                    if self.state == END:
                        self.state = RESTART
                    elif self.state == START:
                        self.state = PLAYER1_MOVE
            

            if self.state == START:
                self.write_instructions()
            elif self.state == END:
                self.write_end_screen()
            elif self.state == RESTART:
                return 0
            elif self.state == CHECK_WIN:
                self.winner = self.check_win()
                if self.winner in {0, 1}:
                    self.state = END
                else:
                    self.state = PLAYER2_MOVE if self.current_player_index else PLAYER1_MOVE
            else:
                self.draw_board()
                self.draw_players()
                if self.state == MOVE_CHECK:
                    if not len(self.valid_moves(self.selected_piece[0].position)):
                        self.current_player_index = 1 - self.current_player_index
                        self.state = CHECK_WIN
                        self.selected_piece.clear()
                        self.show_valid_moves = False; self.jumped = False; self.moved = False
                    else:
                        self.state = PLAYER2_MOVE if self.current_player_index else PLAYER1_MOVE
                if self.show_valid_moves:
                    self.highlight_valid_moves(self.selected_piece[0].position)
                if self.selected_piece:
                    self.highlight_selected_piece()
            
            pygame.display.flip()
            clock.tick(FPS)

while True:
    game = Game()
    exit_status = game.run()
raise