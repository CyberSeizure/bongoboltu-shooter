import asyncio
import pygame
import os
import random

pygame.init()
pygame.font.init()  # Enables Font in pygame

# Audio may require a browser gesture before playback is allowed.
AUDIO_READY = False
try:
    pygame.mixer.music.load("assets/abong.mp3")
    pygame.mixer.music.set_volume(0.5)
except pygame.error:
    pass

def start_music():
    global AUDIO_READY
    if not AUDIO_READY:
        try:
            pygame.mixer.music.play(-1)
            AUDIO_READY = True
        except pygame.error:
            pass

pygame.joystick.init()
controller = None
if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    controller.init()
    print("Controller connected:", controller.get_name())

# Set Screen/Display Size
WIDTH, HEIGHT = 1060, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))

# Set Window Title
pygame.display.set_caption("Bongoboltu Shooter")

# Load images
# Enemy Spaceship Images
enemy1_ship = pygame.transform.scale(pygame.image.load(os.path.join("assets", "bong4.png")), (60, 40))
enemy2_ship = pygame.transform.scale(pygame.image.load(os.path.join("assets", "bong5.png")), (60, 40))


# Player (My Spaceship) Image
player_ship = pygame.transform.scale(pygame.image.load(os.path.join("assets", "dalim.png")), (70, 60))

# Laser Images
RED_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_red.png"))
BLUE_LASER = pygame.image.load(os.path.join("assets", "pixel_laser_blue.png"))

# Background Image
BG = pygame.transform.scale(pygame.image.load(os.path.join("assets", "bong.jpeg")), (WIDTH, HEIGHT))

# Loading screen image
LOADING_IMAGE = pygame.transform.scale(
    pygame.image.load(os.path.join("assets", "loading.png")),
    (WIDTH, HEIGHT))

ENDING_IMAGE = pygame.transform.scale(
    pygame.image.load(os.path.join("assets", "end.png")),
    (WIDTH, HEIGHT)
)

# Laser Class
class Laser:
    def __init__(self, x, y, img):  # Initialize the laser
        self.x = x
        self.y = y
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)

    def draw(self, window):  # Draw the laser in the window
        window.blit(self.img, (self.x, self.y))

    def move(self, vel):  # Move the laser forward
        self.y += vel

    def off_screen(self, height):  # Check if the laser is out of the screen or not
        return not(self.y <= height and self.y >= 0)

    def collision(self, obj):  # Check Collision with spacecraft
        return collide(self, obj)

# Ship Parent Class
class Ship:

    def __init__(self, x, y, health=100):
        self.x = x
        self.y = y
        self.health = health
        self.ship_img = None
        self.laser_img = None
        self.lasers = []
        self.cool_down_counter = 0

    def draw(self, window):
        window.blit(self.ship_img, (self.x, self.y))
        for laser in self.lasers:
            laser.draw(window)

    def move_lasers(self, vel, obj):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            elif laser.collision(obj):
                obj.health -= 10
                self.lasers.remove(laser)

    def cooldown(self):
        if self.cool_down_counter >= self.COOLDOWN:
            self.cool_down_counter = 0
        elif self.cool_down_counter > 0:
            self.cool_down_counter += 1

    def shoot(self):
        if self.cool_down_counter == 0:
            laser = Laser(self.x, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1

    def get_width(self):
        return self.ship_img.get_width()

    def get_height(self):
        return self.ship_img.get_height()


class Player(Ship):
    COOLDOWN = 8
    def __init__(self, x, y, health=100):
        super().__init__(x, y, health)
        self.ship_img = player_ship
        self.laser_img = BLUE_LASER
        self.mask = pygame.mask.from_surface(self.ship_img)
        self.max_health = health

    def move_lasers(self, vel, objs):
        self.cooldown()
        for laser in self.lasers:
            laser.move(vel)
            if laser.off_screen(HEIGHT):
                self.lasers.remove(laser)
            else:
                for obj in objs:
                    if laser.collision(obj):
                        objs.remove(obj)
                        if laser in self.lasers:
                            self.lasers.remove(laser)

    def draw(self, window):
        super().draw(window)
        self.health_bar(window)

    def health_bar(self, window):  # Shows the health bar below the player spaceship
        pygame.draw.rect(window, (255,0,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width(), 10))
        pygame.draw.rect(window, (0,255,0), (self.x, self.y + self.ship_img.get_height() + 10, self.ship_img.get_width() * (self.health/self.max_health), 10))


class Enemy(Ship):
    COOLDOWN = 90
    def __init__(self, x, y, ship_image, laser_image, health=100):
        super().__init__(x, y, health)
        self.ship_img = ship_image
        self.laser_img = laser_image
        self.mask = pygame.mask.from_surface(self.ship_img)

    def move(self, vel):
        self.y += vel

    def shoot(self):  # Automatically shoot by enemy
        if self.cool_down_counter == 0:
            laser = Laser(self.x-20, self.y, self.laser_img)
            self.lasers.append(laser)
            self.cool_down_counter = 1


def collide(obj1, obj2):  # Check if collision happens in that moment. Returns Boolean Value
    offset_x = obj2.x - obj1.x
    offset_y = obj2.y - obj1.y
    return obj1.mask.overlap(obj2.mask, (offset_x, offset_y)) != None

async def main():
    run = True
    level = 0
    FPS = 60  # Locked frame rate for consistent loop speeds and physics
    lives = 6
    main_font = pygame.font.SysFont("comicsans", 50)
    lost_font = pygame.font.SysFont("comicsans", 60)

    enemies = []
    wave_length = 5
    
    # Base speeds to be dynamically modified by level progression
    base_enemy_vel = 1.5
    base_laser_vel = 6
    player_vel = 8

    enemy_vel = base_enemy_vel
    laser_vel = base_laser_vel

    player = Player(300, 630)
    clock = pygame.time.Clock()

    lost = False
    lost_count = 0

    def redraw_window():  # Renders the main game and its visual window in the game loop
        WIN.blit(BG, (0,0))
        # draw text
        lives_label = main_font.render(f"Lives: {lives}", 1, ((255,0,0)))
        level_label = main_font.render(f"Level: {level}", 1, ((255,0,0)))

        WIN.blit(lives_label, (10, 10))
        WIN.blit(level_label, (WIDTH - level_label.get_width() - 10, 10))

        for enemy in enemies:
            enemy.draw(WIN)

        player.draw(WIN)

        if lost:
            lost_label = lost_font.render("Voira Dilo Reee", 1, (255,0,0))
            WIN.blit(lost_label, (WIDTH/2 - lost_label.get_width()/2, 350))

        pygame.display.update()

    while run:  # Most important part of the game. Game Loop/Infinity Loop
        clock.tick(FPS)
        redraw_window()

        if lives <= 0 or player.health <= 0:
            lost = True
            lost_count += 1

        if lost:
            if lost_count > FPS * 3:
                run = False
            else:
                continue

        if len(enemies) == 0:
            level += 1
            wave_length += 5
            # Dynamic scaling: Speed scales with level, but FPS stays stable
            enemy_vel = base_enemy_vel + (level * 0.3)
            laser_vel = base_laser_vel + (level * 0.3)
            
            for i in range(wave_length):
                enemy = Enemy(random.randrange(50, WIDTH-100), random.randrange(-1500, -100), random.choice([enemy1_ship, enemy2_ship]), RED_LASER)
                enemies.append(enemy)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

        # Keyboard Controls
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.x -= player_vel
        if keys[pygame.K_RIGHT]:
            player.x += player_vel
        if keys[pygame.K_UP]:
            player.y -= player_vel
        if keys[pygame.K_DOWN]:
            player.y += player_vel
        
        player.shoot()

        # Controller Controls
        if controller:
            pygame.event.pump()
            dx = controller.get_axis(0)
            dy = controller.get_axis(1)
            if abs(dx) > 0.2:
                player.x += dx * player_vel
            if abs(dy) > 0.2:
                player.y += dy * player_vel
            hat = controller.get_hat(0)
            player.x += hat[0] * player_vel
            player.y -= hat[1] * player_vel
            
        
        # Unified screen boundary constraints for both control methods
        player.x = max(0, min(player.x, WIDTH - player.get_width()))
        player.y = max(0, min(player.y, HEIGHT - player.get_height() - 15))

        for enemy in enemies[:]:
            enemy.move(enemy_vel)
            enemy.move_lasers(laser_vel, player)

            if random.randrange(0, 2*60) == 1:
                enemy.shoot()

            if collide(enemy, player):
                player.health -= 10
                enemies.remove(enemy)
            elif enemy.y + enemy.get_height() > HEIGHT:
                lives -= 1
                enemies.remove(enemy)

        player.move_lasers(-laser_vel, enemies)
        await asyncio.sleep(0)

    await ending_screen()

async def loading_screen():
    button_font = pygame.font.SysFont("comicsans", 40)

    button_width = 250
    button_height = 70

    button_x = WIDTH / 2 - button_width / 2
    button_y = 480

    button_rect = pygame.Rect(
        button_x,
        button_y,
        button_width,
        button_height
    )

    run = True

    while run:

        WIN.blit(LOADING_IMAGE, (0, 0))

        # Start button
        pygame.draw.rect(
            WIN,
            (255, 0, 0),
            button_rect,
            border_radius=15
        )

        button_label = button_font.render(
            "START GAME",
            True,
            (255, 255, 255)
        )

        WIN.blit(
            button_label,
            (
                button_x + button_width / 2 - button_label.get_width() / 2,
                button_y + button_height / 2 - button_label.get_height() / 2
            )
        )

        pygame.display.update()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    run = False


async def ending_screen():
    ending_font = pygame.font.SysFont("comicsans", 60)
    button_font = pygame.font.SysFont("comicsans", 35)

    button_width = 250
    button_height = 65

    button_x = WIDTH - button_width - 20
    button_y = HEIGHT - button_height - 20

    button_rect = pygame.Rect(
        button_x,
        button_y,
        button_width,
        button_height
    )

    run = True

    while run:
        WIN.blit(ENDING_IMAGE, (0, 0))

        # GAME OVER text
        ending_label = ending_font.render(
            "GAME OVER",
            True,
            (255, 0, 0)
        )

        WIN.blit(
            ending_label,
            (
                WIDTH // 2 - ending_label.get_width() // 2,
                250
            )
        )

        # PLAY AGAIN button
        pygame.draw.rect(
            WIN,
            (0, 0, 0, 0),
            button_rect,
            border_radius=15
        )

        button_label = button_font.render(
            "PLAY AGAIN",
            True,
            (255, 255, 255)
        )

        WIN.blit(
        button_label,
    (
        button_x + button_width / 2 - button_label.get_width() / 2,
        button_y + button_height / 2 - button_label.get_height() / 2
    )
)

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    await main()
                    return

        await asyncio.sleep(0)


async def main_menu():
    title_font = pygame.font.SysFont("comicsans", 50)
    run = True
    while run:
        WIN.blit(BG, (0,0))
        title_label = title_font.render("Maar Shala Ree", 1, (255,0,0))
        WIN.blit(title_label, (WIDTH/2 - title_label.get_width()/2, 350))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                start_music()
                await main()
                return

        await asyncio.sleep(0)

async def game():
    await loading_screen()
    await main_menu()

if __name__ == "__main__":
    asyncio.run(game())
