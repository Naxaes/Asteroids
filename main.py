# python 3.5.2
# pygame 1.9.2b6

import pygame
import math
import random
from pygame.math import Vector2

successes, fails = pygame.init()
#assert successes == 6 and not fails  # All 6 modules where successfully initialized.


SIZE = WIDTH, HEIGHT = 720, 480
FPS = 60

COLORS = pygame.color.THECOLORS
COLOR_LIST = tuple(COLORS.values())
BACKGROUND_COLOR = COLORS['black']

PROJECTILE_SPAWN = [Vector2(x, 0) for x in range(0, WIDTH, WIDTH // 32)]
PROJECTILE_DIRECTION = [Vector2(x, HEIGHT) for x in range(0, WIDTH, WIDTH // 32)]

FIRE = pygame.USEREVENT + 1
ASTEROID_SPAWN = pygame.USEREVENT + 2
POWER_UP_SPAWN = pygame.USEREVENT + 3

ASTEROID_SPAWN_TIME = 1000
POWER_UP_SPAWN_TIME = 2500

POWER_UP_TIME = 5
FIRE_TIME_MS  = 250
FAST_FIRE_TIME_MS = 100

STATE_PLAYING   = 0
STATE_GAME_OVER = 1

MAX_LIVES = 3

FONT_BIG     = pygame.font.Font('resources/VeraMoBd.ttf', 32)
FONT_REGULAR = pygame.font.Font('resources/VeraMoBd.ttf', 24)
FONT_SMALL   = pygame.font.Font('resources/VeraMoBd.ttf', 12)

screen = pygame.display.set_mode(SIZE)
clock = pygame.time.Clock()


class Player(pygame.sprite.Sprite):

    def __init__(self, position):
        super(Player, self).__init__()

        size = width, height = (32, 32)
        triangle_vertices = (2, height - 2), (width // 2 - 2, 0), (width - 2, height - 2)

        self.original_image = pygame.Surface(size)
        pygame.draw.aalines(self.original_image, COLORS['white'], True, triangle_vertices, 2)
        self.original_image.set_colorkey(BACKGROUND_COLOR)
        self.image = self.original_image
        self.rect = pygame.Rect(position, size)

        self.position = Vector2(*position)
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)

        self.max_velocity = 3
        self.max_acceleration = 3

    def move(self, dt):
        key = pygame.key.get_pressed()

        if key[pygame.K_a]:
            self.acceleration[0] = -self.max_acceleration * dt
        elif key[pygame.K_d]:
            self.acceleration[0] = self.max_acceleration * dt
        else:
            self.acceleration[0] = 0

        if key[pygame.K_w]:
            self.acceleration[1] = -self.max_acceleration * dt
        elif key[pygame.K_s]:
            self.acceleration[1] = self.max_acceleration * dt
        else:
            self.acceleration[1] = 0

        self.velocity[0] = clamp(self.velocity[0], -self.max_acceleration, self.max_acceleration)
        self.velocity[1] = clamp(self.velocity[1], -self.max_acceleration, self.max_acceleration)

        self.velocity += self.acceleration
        self.position += self.velocity
        self.rect.center = self.position

    def collision(self):
        half_width = self.rect.width // 2
        if self.position[0] + half_width < 0:
            self.position[0] = WIDTH + half_width
        elif self.position[0] - half_width > WIDTH:
            self.position[0] = -half_width
        if self.position[1] + half_width < 0:
            self.position[1] = HEIGHT + half_width
        elif self.position[1] - half_width > HEIGHT:
            self.position[1] = -half_width

    def rotate(self):
        direction = Vector2(pygame.mouse.get_pos()) - self.position
        if direction.length_squared() != 0:
            angle = (360 / (2 * math.pi)) * -math.atan2(direction[1], direction[0]) - 90
            self.image = pygame.transform.rotate(self.original_image, int(angle))
            self.rect = self.image.get_rect(center=self.position)

    def update(self, dt):
        self.rotate()
        self.move(dt)
        self.collision()


class Projectile(pygame.sprite.Sprite):

    def __init__(self, radius, position, direction, speed=300):
        """
        A sprite that moves across the screen. Will be deleted when it's off screen.

        Args:
            radius:    x, y dimensions in pixels.
            position:  x, y position on screen in pixels.
            direction: x, y position to head against
            speed:     Pixels per second
        """
        super(Projectile, self).__init__()

        self.image = pygame.Surface((radius * 2, radius * 2))
        self.rect  = self.image.get_rect(center=position)
        self.image.set_colorkey(BACKGROUND_COLOR)

        self.position = Vector2(*position)
        self.velocity = (Vector2(*direction) - self.position).normalize() * speed

    def update(self, dt):
        screen_area = screen.get_rect()
        self.position += self.velocity * dt
        self.rect.center = self.position
        if not self.rect.colliderect(screen_area):
            self.kill()


class Bullet(Projectile):
    def __init__(self, position, direction, radius=2, speed=300):
        super(Bullet, self).__init__(radius=radius, position=position, direction=direction, speed=speed)
        pygame.draw.circle(self.image, COLORS['red'], (radius, radius), radius)


class Asteroid(Projectile):
    def __init__(self, position, direction, radius=16, speed=180):
        super(Asteroid, self).__init__(radius=radius, position=position, direction=direction, speed=speed)
        pygame.draw.circle(self.image, COLORS['white'], (radius, radius), radius, 1)


class Splitter(Projectile):
    def __init__(self, position, direction, radius=3, speed=300):
        super(Splitter, self).__init__(radius=radius, position=position, direction=direction, speed=speed)
        color = random.choice(COLOR_LIST)
        pygame.draw.circle(self.image, color, (radius, radius), radius)


class PowerUp(Projectile):

    SLOW_MO = 'Slow-mo'
    FAST_FIRE = 'Fast fire'
    EXTRA_LIFE = 'Extra life'
    PIERCING_BULLET = 'Piercing bullet'
    SPLITTER_DESTRUCTION = 'Splitter destruction'

    TYPES = [SLOW_MO, FAST_FIRE, EXTRA_LIFE, PIERCING_BULLET, SPLITTER_DESTRUCTION]

    COLOR = {
        SLOW_MO : COLORS['purple'],
        FAST_FIRE : COLORS['red'],
        EXTRA_LIFE : COLORS['green'],
        PIERCING_BULLET: COLORS['yellow'],
        SPLITTER_DESTRUCTION : COLORS['blue']
    }

    def __init__(self, position, direction, radius=8, speed=150):
        super(PowerUp, self).__init__(radius=radius, position=position, direction=direction, speed=speed)
        self.type  = random.choice(PowerUp.TYPES)
        self.color = PowerUp.COLOR[self.type]
        self.blink_color = COLORS['gray']
        self.blink_time  = 0.30
        self.blink_timer = self.blink_time
        pygame.draw.circle(self.image, self.color, (radius, radius), radius)

    def update(self, dt):
        super(PowerUp, self).update(dt)

        self.blink_timer -= dt
        if self.blink_timer <= -self.blink_time:
            self.blink_timer = self.blink_time

        radius = self.rect.width // 2

        factor = abs(self.blink_timer / self.blink_time)
        r = (1 - factor) * self.blink_color[0] + factor * self.color[0]
        g = (1 - factor) * self.blink_color[1] + factor * self.color[1]
        b = (1 - factor) * self.blink_color[2] + factor * self.color[2]

        pygame.draw.circle(self.image, (r, g, b), (radius, radius), radius)


class Explosion(pygame.sprite.Sprite):

    def __init__(self, position, radius=48):
        super(Explosion, self).__init__()

        self.image = pygame.Surface((radius, radius))
        self.rect  = self.image.get_rect(center=position)
        self.position = Vector2(position)

        self.death_time  = 6 / math.log2(radius * 2)
        self.death_timer = self.death_time

        self.color = COLORS['black']
        self.image.set_colorkey(BACKGROUND_COLOR)
        pygame.draw.circle(self.image, self.color, (radius, radius), int(radius * self.death_timer))

    def update(self, dt):
        self.death_timer -= dt

        if self.death_timer < 0:
            return self.kill()

        factor = 1 - self.death_timer / self.death_time
        radius = self.rect.width // 2

        r = max((1 - factor * 1) * 255, 0)
        g = max((1 - factor * 2) * 255, 0)
        b = max((1 - factor * 4) * 255, 0)

        self.color = (r, g, b)

        pygame.draw.circle(self.image, self.color, (radius, radius), int(radius * factor))
        

class FadingText(pygame.sprite.Sprite):

    def __init__(self, text, position, font=FONT_BIG, origin='topleft', color=COLORS['white'],
                 fade_in=0, hold_on=0.5, fade_out=0.5):
        super(FadingText, self).__init__()
        self.text = str(text)
        self.font = font
        self.color  = color
        self.origin = origin

        self.image = self.font.render(self.text, 0, self.color)
        self.rect  = self.image.get_rect(**{self.origin: position})

        self.state = 0
        self.transparency = 0

        self.fade_in_time   = fade_in
        self.fade_in_timer  = fade_in

        self.hold_on_timer  = hold_on

        self.fade_out_time  = fade_out
        self.fade_out_timer = fade_out

    def update(self, dt):
        if self.state == 0:
            self.fade_in_timer -= dt
            if self.fade_in_timer <= 0:
                self.state += 1
            else:
                factor = (self.fade_in_timer / self.fade_in_time) * 255
                self.image.set_alpha(factor)
        elif self.state == 1:
            self.hold_on_timer -= dt
            if self.hold_on_timer <= 0:
                self.state += 1
        elif self.state == 2:
            self.fade_out_timer -= dt
            if self.fade_out_timer <= 0:
                self.state += 1
            else:
                factor = (self.fade_out_timer / self.fade_out_time) * 255
                self.image.set_alpha(factor)
        else:
            self.kill()


class SpriteManager:
    
    def __init__(self, player):
        self.player    = player
        self.info      = pygame.sprite.Group()
        self.asteroids = pygame.sprite.Group()
        self.bullets   = pygame.sprite.Group()
        self.power_ups = pygame.sprite.Group()
        self.splitters = pygame.sprite.Group()
        self.explosions  = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.LayeredUpdates(player, layer=3)

        self.layer = {
            'player'     : 3,
            'info'       : 4,
            'asteroids'  : 2,
            'bullets'    : 2,
            'power_ups'  : 2,
            'splitters'  : 1,
            'explosions' : 0,
        }

    def add(self, **sprites):
        for group, sprite_list in sprites.items():
            getattr(self, group).add(sprite_list)
            self.all_sprites.add(sprite_list, layer=self.layer[group])
    
    def remove(self, *sprites):
        for sprite in sprites:
            sprite.kill()
    
    def draw(self, surface):
        self.all_sprites.draw(surface)
    
    def update(self, dt):
        self.all_sprites.update(dt)
    
    def empty(self):
        self.player = None
        self.asteroids.empty()
        self.bullets.empty()
        self.power_ups.empty()
        self.splitters.empty()
        self.explosions.empty()
        self.all_sprites.empty()


def clamp(value, minimum, maximum):
    if value < minimum:
        return minimum
    elif value > maximum:
        return maximum
    else:
        return value


def create_splitter(position, n):
    direction = lambda: (random.randint(0, WIDTH), random.randint(0, HEIGHT))
    speed = lambda: random.randint(180, 600)
    return [Splitter(position=position, direction=direction(), speed=speed()) for _ in range(n)]


def spawn_power_up(sprites):
    spawn_pos = random.choice(PROJECTILE_SPAWN)
    direction = random.choice(PROJECTILE_DIRECTION)
    sprites.add(power_ups=PowerUp(position=spawn_pos, direction=direction))


def spawn_asteroid(sprites):
    spawn_pos = random.choice(PROJECTILE_SPAWN)
    direction = random.choice(PROJECTILE_DIRECTION)
    sprites.add(asteroids=Asteroid(position=spawn_pos, direction=direction))


def fire(sprites, power_ups):
    if PowerUp.FAST_FIRE in power_ups:
        pygame.time.set_timer(FIRE, FAST_FIRE_TIME_MS)
    else:
        pygame.time.set_timer(FIRE, FIRE_TIME_MS)
    sprites.add(bullets=Bullet(position=sprites.player.position, direction=pygame.mouse.get_pos()))


def handle_collision(sprites, lives, score, power_ups):

    kill_bullets = False if PowerUp.PIERCING_BULLET in power_ups else True
    for sprite_a, sprite_b in pygame.sprite.groupcollide(sprites.bullets, sprites.asteroids, dokilla=kill_bullets, dokillb=True).items():
        # Will only use the first sprite since it's often just one and it won't make a big difference otherwise.
        sprite_b = sprite_b.pop()

        collision_area = sprite_a.rect.clamp(sprite_b.rect).center

        m = Explosion(collision_area, radius=sprite_b.rect.width)
        n = create_splitter(collision_area, 10)

        sprites.add(explosions=m, splitters=n)
        score += 10


    if PowerUp.SPLITTER_DESTRUCTION in power_ups:
        for sprite_a, sprite_b in pygame.sprite.groupcollide(sprites.splitters, sprites.asteroids, dokilla=True, dokillb=True).items():
            # Will only use the first sprite since it's often just one and it won't make a big difference otherwise.
            sprite_b = sprite_b.pop()

            collision_area = sprite_a.rect.clamp(sprite_b.rect).center

            m = Explosion(collision_area, radius=sprite_b.rect.width)
            n = create_splitter(collision_area, 10)

            sprites.add(explosions=m, splitters=n)
            score += 10

    for sprite in pygame.sprite.spritecollide(sprites.player, sprites.asteroids, dokill=True):
        collision_area = sprite.rect.clamp(sprites.player.rect)

        m = Explosion(collision_area.center, radius=256)
        n = create_splitter(collision_area.center, 10)

        sprites.add(explosions=m, splitters=n)
        lives -= 1

    for sprite in pygame.sprite.spritecollide(sprites.player, sprites.power_ups, dokill=True):
        if sprite.type == PowerUp.EXTRA_LIFE:
            lives += 1
        else:
            power_ups[sprite.type] = POWER_UP_TIME

    return lives, score, power_ups


def display_text(text, position, surface, font=FONT_BIG, origin='topleft'):
    image = font.render(str(text), 1, COLORS['white'])
    rect = image.get_rect(**{origin: position})
    surface.blit(image, rect)


def display_power_ups(power_ups):
    row = 0
    for power_up, timer in power_ups.items():
        display_text(
            text="{0} {1:0.1f} s".format(power_up, timer),
            position=(16, HEIGHT - 8 - 24 * row),
            surface=screen,
            font=FONT_REGULAR,
            origin='bottomleft'
        )
        row += 1


def run_game():
    state = STATE_PLAYING
    replay = False

    start_position = WIDTH // 2, HEIGHT - 128
    sprites = SpriteManager(player=Player(start_position))

    pygame.time.set_timer(POWER_UP_SPAWN, POWER_UP_SPAWN_TIME)
    pygame.time.set_timer(ASTEROID_SPAWN, ASTEROID_SPAWN_TIME)
    pygame.time.set_timer(FIRE, 0)

    power_ups = {}
    lives = MAX_LIVES
    time  = 0
    score = 0

    running = True

    while running:

        time_dt = update_dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    running = False
                    replay = True
                elif event.key == pygame.K_ESCAPE:
                    running = False
                    replay = False
            elif event.type == pygame.QUIT:
                running = False
                replay = False

            if state == STATE_PLAYING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    fire(sprites, power_ups)
                elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                    pygame.time.set_timer(FIRE, 0)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    fire(sprites, power_ups)
                elif event.type == pygame.MOUSEBUTTONUP:
                    pygame.time.set_timer(FIRE, 0)
                elif event.type == FIRE:
                    fire(sprites, power_ups)
                elif event.type == POWER_UP_SPAWN:
                    spawn_power_up(sprites)
                elif event.type == ASTEROID_SPAWN:
                    spawn_time = max(ASTEROID_SPAWN_TIME * 0.95 ** time, 10)
                    pygame.time.set_timer(ASTEROID_SPAWN, int(spawn_time))
                    spawn_asteroid(sprites)


        if state == STATE_PLAYING:

            new_lives, score, new_power_ups = handle_collision(sprites, lives, score, power_ups.copy())

            if new_lives < lives:
                sprites.add(info=FadingText('Ouch!', sprites.player.position, font=FONT_SMALL))
                if new_lives <= 0:
                    state = STATE_GAME_OVER
                    sprites.player.kill()
                    sprites.add(splitters=create_splitter(sprites.player.position, 500))
            elif new_lives != lives:
                sprites.add(info=FadingText('Extra life!', sprites.player.position, font=FONT_SMALL, color=COLORS['green']))
            lives = new_lives

            if new_power_ups.keys() != power_ups.keys():
                power_up = (set(new_power_ups) - set(power_ups)).pop()
                color = PowerUp.COLOR[power_up]
                sprites.add(info=FadingText('{}!'.format(power_up), sprites.player.position, font=FONT_SMALL, color=color))
            power_ups = new_power_ups

            time += time_dt

            if PowerUp.SLOW_MO in power_ups:
                update_dt = time_dt / 2

            for power_up in power_ups.copy():
                power_ups[power_up] -= time_dt
                if power_ups[power_up] <= 0:
                    del power_ups[power_up]

        sprites.update(update_dt)

        screen.fill(BACKGROUND_COLOR)
        sprites.draw(screen)
        display_power_ups(power_ups)
        display_text("Score: {0}".format(score),    (16, 16),       screen)
        display_text("Lives: {0}".format(lives),    (WIDTH/2, 16),  screen, origin='midtop')
        display_text("Time: {0:0.1f}".format(time), (WIDTH-16, 16), screen, origin='topright')

        if state == STATE_GAME_OVER:
            display_text('GAME OVER!', (WIDTH / 2, HEIGHT / 2), screen, origin='midbottom')
            display_text('Press r to try again', (WIDTH / 2, HEIGHT / 2), screen, origin='midtop')

        pygame.display.update()

    if replay:
        run_game()


if __name__ == '__main__':
    run_game()
