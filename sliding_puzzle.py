import json
import os
from PIL import Image
import pygame as pg
import random

pg.init()
pg.display.set_caption("Sliding Puzzle")

def load_previous_state():
    """Will load the game state from the previous solve, including the scrambled board state and moves made."""
    
    path = 'previous_state.json'

    if not os.path.isfile(path):
        return {'moves_made': None, 'scrambled_board': None}
    else:
        with open(path, 'r') as f:
            return json.load(f)

def save_current_state(state):
    """This function will save the current state to a JSON file, including the initial scrambled board state and the moves made."""
    
    path = 'previous_state.json'
    with open(path, 'w') as f:
        json.dump(state, f, indent=4)
    
def crop(img, tiles_per_side):
    """Returns a list of cropped square tile images."""
    
    img_num = 0
    width, height = img.size
    cutsize = width // tiles_per_side
    tiles = []
    
    # Perform square tile cuts
    for i in range(height//cutsize):
        for j in range(width//cutsize):
            box = (j*cutsize, i*cutsize, (j+1)*cutsize, (i+1)*cutsize)
            tile = img.crop(box)
            tiles.append(tile)
    return tiles

def copy_board(board):
    return [[val for val in row] for row in board]

def pilImageToSurface(pilImage):
    return pg.image.fromstring(
        pilImage.tobytes(), pilImage.size, pilImage.mode).convert()

class Application:
    def __init__(self, grid, sidebar):
        self.running = True
        self.clock = pg.time.Clock()
        self.fps = 60

        self.grid = grid # Height is measures in number of tiles
        self.sidebar = sidebar # Height is measured in actual pixels

    def reset(self):
        self.grid.reset()
        self.sidebar.reset()

    def playback_reset(self):
        self.grid.playback_reset()
        self.sidebar.reset()
        
    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()

            if event.type == pg.KEYDOWN:
                if not self.grid.has_won:
                    self.grid.make_move(event.key)

                if event.key == pg.K_r:
                    self.reset()
                    self.grid.play_sfx('restart')

                # Replay of the last game
                if event.key == pg.K_p:
                    self.grid.toggle_playback_mode()

                    if self.grid.playback_mode:
                        self.playback_reset()
                        solve = self.grid.previous_state['moves_made']
                        self.grid.load_playback_grid(solve)
                        self.moves_to_preview = list(solve)
                    else:
                        self.reset()
                        self.grid.play_sfx('restart')
                        
                    
    def update(self, dt):
        self.grid.display()
        self.sidebar.display(dt)

        if self.grid.playback_mode:
            self.grid.grid_color = [128, 0, 0]
            if len(self.moves_to_preview) > 0:
                move = self.moves_to_preview.pop(0)
                self.grid.make_move(move)
            else:
                self.grid.toggle_playback_mode()

        elif self.grid.has_won:
            color = [random.randint(0, 255) for _ in range(3)]
            self.grid.grid_color = color
        else:
            self.grid.grid_color = self.grid.theme['grid_color']
            

    def run(self):
        dt = self.clock.tick(self.fps)
        self.update(dt)
        
        while self.running:
            dt = self.clock.tick(self.fps)
            self.event_loop()
            self.update(dt)
            pg.display.update()
        pg.quit()

    def quit(self):
        self.running = False

class Grid:
    def __init__(self, width, height, tile_length, margin_x, margin_y, theme, config):
        self.width = width
        self.height = height
        self.tile_length = tile_length
        
        self.empty_index = [width-1, height-1] # The index which starts
        self.moves_made = ''
        self.has_started = False
        self.playback_mode = False
        self.previous_state = load_previous_state() # Loads the JSON file for the previous game state for action replays

        # Offset from the edges of the screen
        self.margin_x = margin_x
        self.margin_y = margin_y

        # Setting themes
        self.theme = theme
        self.config = config
        self.grid_color = pg.Color(theme['grid_color'])
        self.line_color = pg.Color(theme['line_color'])
        self.font = pg.font.SysFont(theme['font_name'], 30)
        self.sfx_mapping = self.load_sounds()

        self.grid = self.initialise_grid()
        self.scrambled_board = copy_board(self.grid)
        self.has_started = True

    def __repr__(self):
        return str(self.grid)

    def __iter__(self):
        return iter(self.grid)

    @property
    def has_won(self):
        """
        Checks if the game is over, since all the tiles are in order
        """
        
        return self.is_ordered_grid(self.get_tile_values(self.grid))

    def is_ordered_grid(self, grid):
        """Returns if a given grid is ordered. This only compares grids which comprise only of integers and strings. This will not accept Tile objects."""
        
        return grid == self.get_new_grid()

    def get_tile_values(self, grid):
        """This ensures that the the input grid is converted into a basic matrix of integers and strings, even if the input contains Tile objects or integers."""
        res_grid = []
        for row in grid:
            res_row = []
            for tile in row:
                if isinstance(tile, Tile):
                    res_row.append(tile.value)
                else:
                    res_row.append(tile)
            res_grid.append(res_row)
        return res_grid
    
    def convert_to_tiles(self, grid):
        return [[Tile(i) for i in j] for j in grid]
    
    def find_bg_image(self, folder):
        """Any image file which is named 'bg' becomes the background image for the puzzle."""
        
        for file in os.listdir(folder):
            name, ext = os.path.splitext(file)
            if name.lower() == 'bg':
                return os.path.join(folder, file)
        
    def load_sounds(self):
        if self.theme['has_sound']:
            path = os.path.join(self.theme['theme'], 'sfx')
            sfx_mapping = {}
            for file in os.listdir(path):
                filename, _ = os.path.splitext(file)
                sfx = pg.mixer.Sound(os.path.join(path, file))
                sfx_mapping[filename] = sfx
            return sfx_mapping

    def play_sfx(self, sfx):
        if self.theme['has_sound']:
            self.sfx_mapping[sfx].play()
            
    def reset(self):
        """For restarting a new round afresh"""
        self.shuffle()
        self.moves_made = ''
        self.playback_mode = False

    def playback_reset(self):
        """For resetting the playback scene."""

        self.empty_index = [self.width-1, self.height-1]
        self.moves_made = ''

    def load_playback_grid(self, solve):
        """Function which loads the scrambled grid from the previous solve."""

        self.grid = self.get_new_grid()
        self.grid = self.process_grid(self.grid)
        self.reverse_solve(solve)
        
    def toggle_playback_mode(self):
        self.playback_mode = not self.playback_mode

    def get_image_chunks(self, path):
        img = Image.open(path)
        img = img.resize((self.width*self.tile_length, self.height*self.tile_length))
        return crop(img, self.width)

    def assign_image_chunks(self, grid, chunks):
        for row in grid:
            for tile in row:
                if tile.value != '':
                    tile.img = pilImageToSurface(chunks.pop(0))

    def process_image_bg(self, grid):
        image_path = self.find_bg_image(self.theme['theme'])
        chunks = self.get_image_chunks(image_path)
        self.assign_image_chunks(grid, chunks)
                    
    def get_new_grid(self):
        """Returns a grid containing integer elements. The empty space is represented as an empty string."""
        
        grid = []
        w, h = self.width, self.height
        
        for i in range(1, w*h, w):
            grid.append([str(j) for j in range(i, i+w)])
            
        # Replace the last element with an empty element
        x, y = self.empty_index
        grid[y][x] = ''
        return grid

    def initialise_grid(self):
        """Perform shuffle to the grid and convert each element to tile objects. This is used for starting a new game afresh."""

        self.grid = self.get_new_grid()
        self.grid = self.process_grid(self.grid)
        self.shuffle()
        return self.grid

    def process_grid(self, grid):
        """Function which loads a grid of scrambled integers and string and returns them in converted Tile format."""

        grid = self.convert_to_tiles(grid)
        if self.theme['has_image']:
            self.process_image_bg(grid)
        return grid

    def is_index_in_bounds(self, x, y):
        return x >= 0 and x < len(self.grid[0]) and y >= 0 and y < len(self.grid)
    
    def make_move(self, move, shuffle=False):
        """
        These moves will move a block into the space in that direction, if possible.
        This is equivalent to moving the empty space in the opposite direction.
        Inputs will be specified using the w,a,s,d keys for now.
        """
        
        x, y = self.empty_index

        # Find the neighboring block from the empty space in the opposite direction
        neighbors = {
            pg.K_UP: (x, y+1),
            pg.K_DOWN: (x, y-1),
            pg.K_RIGHT: (x-1, y),
            pg.K_LEFT: (x+1, y)
        }

        move_map = {
            pg.K_UP: 'U',
            pg.K_DOWN: 'D',
            pg.K_RIGHT: 'R',
            pg.K_LEFT: 'L',
        }

        letter_convert = {
            'U': pg.K_UP,
            'D': pg.K_DOWN,
            'R': pg.K_RIGHT,
            'L': pg.K_LEFT
        }

        # Convert letter moves to pygame inputs
        if move in {'U', 'D', 'L', 'R'}:
            move = letter_convert[move]
    
        # Swap with the neighbor
        if move in neighbors:
            nx, ny = neighbors[move]
            
            if self.is_index_in_bounds(nx, ny):
                self.grid[y][x], self.grid[ny][nx] = self.grid[ny][nx], self.grid[y][x]
                self.empty_index = [nx, ny]

                # So that shuffling doesn't increase move count
                if not shuffle:
                    self.moves_made += move_map[move]

                # Determine which sound to play
                if self.has_won and self.has_started:
                    self.play_sfx('win')
                    self.save_state()
                elif not shuffle:
                    self.play_sfx('move')

    def save_state(self):
        self.previous_state['moves_made'] = self.moves_made
        self.previous_state['scrambled_board'] = self.get_tile_values(self.scrambled_board)
        save_current_state(self.previous_state)

    def reverse_solve(self, solve):
        """Function which performs the inverse of the solved moves in order to tget the original scrambled state."""

        inverse = {
            'U': pg.K_DOWN,
            'D': pg.K_UP,
            'L': pg.K_RIGHT,
            'R': pg.K_LEFT
        }

        res = ''
        for move in reversed(solve):
            self.make_move(inverse[move], shuffle=True)
            
    def shuffle(self):
        """Will make 1000 random moves."""

        for _ in range(10000):
            move = random.choice([pg.K_UP, pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT])
            self.make_move(move, shuffle=True)

    def display(self):
        x, y = 0, 0
        screen.fill(self.grid_color)

        for y in range(self.height):
            for x in range(self.width):
                x_pos = (x * self.tile_length) + self.margin_x
                y_pos = (y * self.tile_length) + self.margin_y
                tile = self.grid[y][x]
                border_rect = pg.Rect(x_pos, y_pos, self.tile_length, self.tile_length)

                # If displaying chunks of an image
                if tile.img is not None:
                    screen.blit(tile.img, (x_pos, y_pos))

                if self.config['enable_tile_borders'] and tile.value != '':

                    if self.config['rounded_corners']:
                        pg.draw.rect(screen, self.line_color, border_rect, 1, border_radius=20)
                    else:
                        pg.draw.rect(screen, self.line_color, border_rect, 1)

                if self.config['enable_tile_numbers']:
                    text = self.font.render(tile.value, False, self.line_color)
                    text_rect = text.get_rect()
                    text_rect.center = border_rect.center
                    screen.blit(text, text_rect)
                

class Tile:
    def __init__(self, value, img=None):
        self.value = value
        self.img = img

    def __repr__(self):
        return f"Tile({self.value})"

class SideBar:
    def __init__(self, real_width, real_height, grid, theme):
        self.width = real_width
        self.height = real_height
        self.grid = grid
        self.tile_length = self.grid.tile_length

        # Setting themes
        self.sidebar_color = theme['sidebar_color']
        self.secondary_color = theme['line_color']
        self.font_name = theme['font_name']

        # Positions the sidebar on the right of the main grid
        self.sidebar_surface = pg.Surface((self.width, self.height))
        self.top_left = (self.grid.width * self.tile_length) + (self.grid.margin_x*2)

        self.timer = 0

    def display(self, dt):
        screen.blit(self.sidebar_surface, (self.top_left, 0))
        self.sidebar_surface.fill(pg.Color(self.sidebar_color))

        # Border dividing the grid and the sidebar
        pg.draw.line(self.sidebar_surface, pg.Color(self.secondary_color), (0, 0), (0, self.height), width=5)

        # Display info
        self.display_time()
        self.display_tips()
        self.display_moves()
        self.timer_tick(dt)

    def display_time(self):
        center = self.height // 2
        axis = center - 50
        margin_y = 15
        self.display_text("Time:", axis - margin_y)
        self.display_text(self.format_milliseconds(self.timer), axis + margin_y)

    def display_moves(self):
        center = self.height // 2
        axis = center + 50
        margin_y = 15
        self.display_text("Moves Made:", axis - margin_y)
        self.display_text(str(len(self.grid.moves_made)), axis + margin_y)

    def display_tips(self):
        axis = self.height - (self.height // 5) 
        self.display_text("Press [R] to restart", axis, size=15)
        
    def display_text(self, txt, y_pos, size=30):
        """
        This will display text at a given y position in the sidebar and will center it to look nice.
        By default, it will take in a tile_y_pos so it looks nice and aligned with the grid.
        """

        font = pg.font.SysFont(self.font_name, size)
        width, height = font.size(txt)
        x_pos = (self.width//2) - (width//2)
        y_pos = y_pos - (height // 2)
        text = font.render(txt, False, self.secondary_color)
        self.sidebar_surface.blit(text, (x_pos, y_pos))

    def format_milliseconds(self, milliseconds):
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{milliseconds:03d}"
        
    def reset(self):
        self.timer = 0

    def timer_tick(self, dt):
        if not self.grid.has_won and not self.grid.playback_mode:
            self.timer += dt
           

def main():
        
    tile_length = 50
    width = 10
    height = 10
    sidebar_width = 200
    sidebar_height = height

    margin_x = 20
    margin_y = 20

    global screen
    screen_width = (width * tile_length) + (sidebar_width) + (2*margin_x)
    screen_height = (height * tile_length) + (2*margin_y)
    screen = pg.display.set_mode((screen_width, screen_height))

    THEMES = {
        'classic': {
            'theme': 'classic',
            'grid_color': '#FFFFFF',
            'line_color': '#000000',
            'font_name': 'Times New Roman',
            'sidebar_color': '#FFFFFF',
            'has_image': False,
            'has_sound': True
        },

        'dark': {
            'theme': 'dark',
            'grid_color': '#37393e',
            'line_color': '#FFFFFF',
            'font_name': 'Helvetica',
            'sidebar_color': '#2f3136',
            'has_image': False,
            'has_sound': False
        },

        'hutao': {
            'theme': 'hutao',
            'grid_color': '#37393e',
            'line_color': '#FFFFFF',
            'font_name': 'Helvetica',
            'sidebar_color': '#2f3136',
            'has_image': True,
            'has_sound': True
        },

        'rock': {
            'theme': 'rock',
            'grid_color': '#37393e',
            'line_color': '#FFFFFF',
            'font_name': 'Helvetica',
            'sidebar_color': '#2f3136',
            'has_image': True,
            'has_sound': True
        }
    }

    theme = 'hutao'

    config = {
        'enable_tile_numbers': True,
        'enable_tile_borders': False,
        'rounded_corners': False
    }

    grid = Grid(width, height, tile_length, margin_x, margin_y, THEMES[theme], config)
    
    sidebar = SideBar(
        sidebar_width,
        (sidebar_height * tile_length) + (grid.margin_y*2),
        grid,
        THEMES[theme]
    )
        
    app = Application(grid, sidebar)
    app.run()

if __name__ == '__main__':
    main()
