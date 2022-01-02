import os
from PIL import Image
import pygame as pg
import random

pg.init()
pg.display.set_caption("Sliding Puzzle")

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
        
    def event_loop(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit()

            if event.type == pg.KEYDOWN:
                if not self.grid.is_solved:
                    self.grid.make_move(event.key)

                if event.key == pg.K_r:
                    self.reset()
                    self.grid.play_sfx('restart')
                    
    def update(self, dt):
        self.grid.display()
        self.sidebar.display(dt)

        if self.grid.is_solved:
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

        self.grid = self.get_new_grid(width, height)
        self.has_started = False
        self.moves_made = 0

        # Load image if present
        if theme['has_image']:
            image_path = self.find_bg_image(self.theme['theme'])
            chunks = self.get_image_chunks(image_path)
            self.assign_image_chunks(chunks)

        self.shuffle()
        self.has_started = True

    def __repr__(self):
        return str(self.grid)

    @property
    def is_solved(self):
        """
        Flatten a grid into a list of numbers and check if it is the same as a solved list.
        i.e. converts something like [[1, 2], [3, None]] to [1, 2, 3, None]
        """
        
        return [tile.value for row in self.grid for tile in row][:-1] == list(map(str, range(1, self.width*self.height))) and self.has_started

    def find_bg_image(self, folder):
        """Any image file which is named 'bg' becomes the background image for the puzzle."""
        
        for file in os.listdir(folder):
            name, ext = os.path.splitext(file)
            if name.lower() == 'bg':
                print(os.path.join(folder, file))
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
        self.shuffle()
        self.moves_made = 0

    def get_image_chunks(self, path):
        img = Image.open(path)
        img = img.resize((self.width*self.tile_length, self.height*self.tile_length))
        return crop(img, self.width)

    def assign_image_chunks(self, chunks):
        for row in self.grid:
            for tile in row:
                if tile.value != '':
                    tile.img = pilImageToSurface(chunks.pop(0))
                    

    def get_new_grid(self, w, h):
        grid = []
        for i in range(1, w*h, w):
            grid.append([Tile(str(j)) for j in range(i, i+w)])

        # Replace the last element with an empty element
        x, y = self.empty_index
        grid[y][x] = Tile('')
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
    
        # Swap with the neighbor
        if move in neighbors:
            nx, ny = neighbors[move]
            
            if self.is_index_in_bounds(nx, ny):
                self.grid[y][x], self.grid[ny][nx] = self.grid[ny][nx], self.grid[y][x]
                self.empty_index = [nx, ny]

                # Determine which sound to play
                if self.is_solved:
                    self.play_sfx('win')
                elif not shuffle:
                    self.play_sfx('move')

                # So that shuffling doesn't increase move count
                if not shuffle:
                    self.moves_made += 1
    
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
        self.display_text(str(self.grid.moves_made), axis + margin_y)

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
        return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"
        
    def reset(self):
        self.timer = 0

    def timer_tick(self, dt):
        if not self.grid.is_solved:
            self.timer += dt
           

def main():
        
    tile_length = 100
    width = 6
    height = 6
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

    theme = 'rock'

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
