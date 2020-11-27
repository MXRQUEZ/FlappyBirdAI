import pygame
import random
import os
import neat

pygame.mixer.init()  # звук pygame
pygame.mixer.pre_init(frequency=44100, size=16, channels=1, buffer=256)  # преинициализация звуков
pygame.font.init()  # шрифты pygame

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 800
TEXT_SIZE = 25
TEXT_FONT = "arial"
RGB_WHITE = (255, 255, 255)
SMOOTHING = 1  # сглаживание

STATS_FONT = pygame.font.SysFont(TEXT_FONT, TEXT_SIZE, italic=True, bold=True)
WINDOW = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Flappy Bird")

# загрузка картинок
# convert - конвертирует картинку в удобный для pygame формат для быстродействия
bg_SCALE_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT + 50)
pipe_img = pygame.transform.scale2x(pygame.image.load('imgs/pipe.png').convert())  # загружаем картинку трубы
bg_img = pygame.transform.scale(pygame.image.load("imgs/bg.png").convert(), bg_SCALE_SIZE)
bird_images = [[pygame.transform.scale2x(pygame.image.load("imgs/yellow_bird" + str(x) + ".png")).convert_alpha()
                for x in range(1, 4)],
               [pygame.transform.scale2x(pygame.image.load("imgs/red_bird" + str(x) + ".png")).convert_alpha()
                for x in range(1, 4)],
               [pygame.transform.scale2x(pygame.image.load("imgs/blue_bird" + str(x) + ".png")).convert_alpha()
                for x in range(1, 4)],
               [pygame.transform.scale2x(pygame.image.load("imgs/purple_bird" + str(x) + ".png")).convert_alpha()
                for x in range(1, 4)],
               [pygame.transform.scale2x(pygame.image.load("imgs/ukrainian_bird" + str(x) + ".png")).convert_alpha()
                for x in range(1, 4)]]
floor_img = pygame.transform.scale2x(pygame.image.load('imgs/floor.png')).convert()

# загрузка звуков
death_sound = pygame.mixer.Sound('sounds/sfx_die.wav')
score_sound = pygame.mixer.Sound('sounds/sfx_point.wav')
jump_sound = pygame.mixer.Sound('sounds/sfx_wing.wav')
background_song = pygame.mixer.Sound('sounds/sfx_background.wav')
new_generation_sound = pygame.mixer.Sound('sounds/sfx_generation.wav')

# параметры конфига
MAX_GENERATIONS_TO_SPAWN = 50

# игровые переменные
generation = 0
high_score = 0

BIRD_IS_TOO_HIGH = -20
FLOOR_HEIGHT = 730
PIPE_SPAWNPOINT = 700
FPS = 30
clock = pygame.time.Clock()  # переменная для кадров в секунду

networks = []
birds = []
genomes = []

background_song.play(FPS)  # проигрываем бэкграундтрэк FPS раз


class Bird:

    IMGS = bird_images  # инициализируем картинки всех птиц

    ANIMATION_TIME = 5
    GRAVITY = 1
    JUMP_HEIGHT = 10.5
    SPEED_LIMIT = 20
    FALLING_SPEED = 8

    RANDRANGE_FROM = 1
    RANDRANGE_TO = 5

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 0
        self.tick_counter = 0

        self.bird_index = 0
        self.animation_index = 0
        self.set_bird_index()

        self.img = self.IMGS[self.bird_index][self.animation_index]
        self.img_height = self.img.get_height()

    def set_bird_index(self):
        self.bird_index = random.randrange(self.RANDRANGE_FROM, self.RANDRANGE_TO)

    def jump(self):
        self.speed = 0
        self.speed = -self.JUMP_HEIGHT  # отрицательное значение, т.к. начало координат в находится в левом верхнем углу

    def fall(self):
        self.speed += self.GRAVITY

        # устанавливаем лимит на падение, чтобы птица не падала слишком быстро
        if self.speed >= self.SPEED_LIMIT:
            self.speed = self.SPEED_LIMIT

        self.y = self.y + self.speed

    def draw(self, window):
        self.tick_counter += 1  # с каждым тиком увеличиваем переменную-счётчик

        # анимация птицы
        if self.tick_counter <= self.ANIMATION_TIME:
            # пока пройдёт количество тиков, равное ANIMATION TIME, оставляем первую картинку птицы
            self.animation_index = 0
        elif self.tick_counter <= self.ANIMATION_TIME*2:
            # как только проходит время(количество тиков), равное ANIMATION TIME * 2 = 10, меняем картинку на следующую
            self.animation_index = 1
        elif self.tick_counter <= self.ANIMATION_TIME*3:
            self.animation_index = 2
        elif self.tick_counter <= self.ANIMATION_TIME*4:
            self.animation_index = 1
        elif self.tick_counter == self.ANIMATION_TIME*4 + 1:  # повторяем то же действие по кругу
            self.animation_index, self.tick_counter = 0, 0

        if self.falling():
            # перестаём хлопать крыльями и замораживаем переменную-счётчик
            self.animation_index, self.tick_counter = 1, self.ANIMATION_TIME*2

        self.img = self.IMGS[self.bird_index][self.animation_index]

        draw_rotated_bird(window, self.img, self.speed, self.get_rectangle(), 1)

    def get_rectangle(self):
        # накладываем прямоугольник на птицу
        return self.img.get_rect(center=(self.x, self.y))

    def falling(self):
        is_falling = True
        if self.speed > self.FALLING_SPEED:
            return is_falling
        return not is_falling


class Pipe:

    BOTTOM_PIPE_IMG = pipe_img
    # переворачиваем картинку для верхней трубы (2 параметр - переворачиваем по x, 3 параметр - по Y)
    TOP_PIPE_IMG = pygame.transform.flip(pipe_img, False, True)
    WIDTH = BOTTOM_PIPE_IMG.get_width()

    GAP_BETWEEN_TOP_AND_BOTTOM_PIPES = 200
    PIPE_SPEED = 7
    RANDRANGE_FROM = 50
    RANDRANGE_TO = 450

    def __init__(self, x):

        self.x = x
        self.height = 0

        # позиция труб по y
        self.top_bottomleft = 0
        self.bottom_topleft = 0

        self.passed = False

        self.set_height()

    def set_height(self):
        self.height = random.randrange(self.RANDRANGE_FROM, self.RANDRANGE_TO)
        self.top_bottomleft = self.height
        self.bottom_topleft = self.height + self.GAP_BETWEEN_TOP_AND_BOTTOM_PIPES

    def move(self):
        self.x += -self.PIPE_SPEED

    def draw(self, window):
        topPipe_topleft = self.top_bottomleft - self.TOP_PIPE_IMG.get_height()
        window.blit(self.TOP_PIPE_IMG, (self.x, topPipe_topleft))
        window.blit(self.BOTTOM_PIPE_IMG, (self.x, self.bottom_topleft))

    def collided(self, bird):
        is_collided = True
        bottomPipe_rect = self.BOTTOM_PIPE_IMG.get_rect(topleft=(self.x, self.bottom_topleft))
        topPipe_rect = self.TOP_PIPE_IMG.get_rect(bottomleft=(self.x, self.top_bottomleft))

        if bird.get_rectangle().colliderect(bottomPipe_rect) \
            or bird.get_rectangle().colliderect(topPipe_rect):
            return is_collided
        return not is_collided


class Floor:

    IMG = floor_img

    FLOOR_SPEED = 7
    FLOOR_WIDTH = floor_img.get_width()

    def __init__(self, y):
        self.y = y  # высота пола по y
        self.x1 = 0
        self.x2 = self.FLOOR_WIDTH  # начальная координата второй картинки пола, которая движется прямо за первой

    def move(self):
        self.x1 += -self.FLOOR_SPEED
        self.x2 += -self.FLOOR_SPEED

        # как только каждая картинка пола заходит за экран(в левую сторону)
        # передвигаем её координату за втору(в правую)
        if self.x1 + self.FLOOR_WIDTH < 0:
            self.x1 = self.x2 + self.FLOOR_WIDTH

        if self.x2 + self.FLOOR_WIDTH < 0:
            self.x2 = self.x1 + self.FLOOR_WIDTH

    def draw(self, win):
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def draw_rotated_bird(window, bird_image, bird_angle, bird_rect, scale):
    # для отображения птицы под наклоном pygame использует 2 картинки для улучшения её качества
    # а именно картинки с повернутым изображением(rotated_image)
    # и картику с прямоугольником от оригинального изображения(bird_rect)
    # чтобы корректно отобразить результат, оригинальная картинка(bird_image) была конвертирована функцией convert_alpha
    # в нашем случае в качестве угла подходит скорость c отрицательным значением и увеличенным в 3 раза
    rotated_bird = pygame.transform.rotozoom(bird_image, -bird_angle*3, scale)
    window.blit(rotated_bird, bird_rect)


def draw_window(window, birds, pipes, floor, score):

    window.blit(bg_img, (0, 0))

    for pipe in pipes:
        pipe.draw(window)

    floor.draw(window)

    for bird in birds:
        bird.draw(window)

    def draw_stat(stat, text):
        nonlocal text_position
        stat_text = STATS_FONT.render(text + str(stat), SMOOTHING, RGB_WHITE)
        stat_width = stat_text.get_width()
        if text_position[0] == WINDOW_WIDTH - 10:
            text_position[0] -= stat_width
        window.blit(stat_text, text_position)

    text_position = [WINDOW_WIDTH - 10, 10]
    draw_stat(score, "Score: ")

    text_position = [10, 10]
    draw_stat(generation, "Generation: ")

    text_position = [10, 50]
    draw_stat(len(birds), "Alive: ")

    if high_score > 0:
        text_position = [WINDOW_WIDTH - 10, 50]
        draw_stat(high_score, "High score: ")

    pygame.display.update()  # обновляем наше окно с каждым кадром


def killBird(bird_index):
    global genomes, networks, birds
    bird_fitness = 5
    death_sound.play()
    genomes[bird_index].fitness -= bird_fitness
    networks.pop(bird_index)
    genomes.pop(bird_index)
    birds.pop(bird_index)


def feedBird():
    global genomes
    bird_fitness = 5
    for genome in genomes:
        genome.fitness += bird_fitness


def spawnBird(genome_network, genome):
    global genomes, networks, birds
    x = 230; y = 350
    networks.append(genome_network)
    birds.append(Bird(x, y))
    genomes.append(genome)


def funcActivated(output):
    func_activation = 0.5
    func_activated = True
    if output > func_activation:
        return func_activated
    return not func_activated


def main(config_genomes, config):
    global WINDOW, generation, high_score, birds, networks, genomes
    new_generation_sound.play()

    '''BIRD_FITNESS_PER_FRAME = 0.1'''
    generation += 1
    score = 0

    for genome_id, genome in config_genomes: # config_genomes - кортеж, где genome_id - айди каждого генома
        genome.fitness = 0  # устанавливаем начальное значение для "раскармливания" генома
        # создаём нейросеть для каждого генома со свойством config
        genome_network = neat.nn.FeedForwardNetwork.create(genome, config)
        spawnBird(genome_network, genome)

    floor = Floor(FLOOR_HEIGHT)
    pipes = [Pipe(PIPE_SPAWNPOINT)]

    game_executed = True
    while game_executed and len(birds) > 0:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_executed = False
                pygame.quit()
                quit()
                break

        # возвращаем индекс трубы для входных данных в нейронную сеть
        pipe_index = 0
        if len(birds) > 0:
            pipe_pass = pipes[pipe_index].x + pipes[pipe_index].WIDTH
            if len(pipes) > 1 and birds[0].x > pipe_pass:
                pipe_index += 1

        for bird_index, bird in enumerate(birds):
            '''# кормим каждую птицу по 0.1 за каждый кадр в секунду
            genome_list[bird_index].fitness += BIRD_FITNESS_PER_FRAME'''
            bird.fall()

            # выходной параметр нейронной сети
            # для каждой птицы вычисляем её расстояние от неё до верхней трубы(левый нижний угол)
            # и нижней трубы(левый верхний угол) по Y, используя функцию активации для нейронной сети(tanh)
            output_activation_function = networks[bird_index].activate((bird.y,
                                                                        abs(bird.y - pipes[pipe_index].top_bottomleft),
                                                                        abs(bird.y - pipes[pipe_index].bottom_topleft)))

            # т.к мы используем функцию гиперболического тангенса как функцию активации
            # то его значения расположены на интервале от -1 до 1 включительно
            # переменная output_activation_function является списком. из этого списка нам нужно только первое значение
            if funcActivated(output_activation_function[0]):
                bird.jump()
                jump_sound.play()

            if bird.y + bird.img_height >= FLOOR_HEIGHT or bird.y < BIRD_IS_TOO_HIGH:
                killBird(bird_index)

        floor.move()

        pipe_remove_list = []
        add_pipe = False

        for pipe in pipes:
            pipe.move()
            for bird_index, bird in enumerate(birds):
                if pipe.collided(bird):
                    killBird(bird_index)

            if pipe.x + pipe.WIDTH < 0:  # если труба вышла за экран
                pipe_remove_list.append(pipe)

            if not pipe.passed and pipe.x < bird.x:  # проверяем если птица всё-таки прошла через трубу
                pipe.passed = True
                add_pipe = True

        if add_pipe:
            score += 1
            score_sound.play()
            if score > high_score:
                high_score += 1
            feedBird()
            pipes.append(Pipe(WINDOW_WIDTH))

        for pipe in pipe_remove_list:
            pipes.remove(pipe)

        draw_window(WINDOW, birds, pipes, floor, score)


def run(config_file):
    # определяем свойства, описанные в конфиге для neat
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation, config_file)

    population = neat.Population(config)

    # выводим статы в терминал
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    population.run(main, MAX_GENERATIONS_TO_SPAWN)  # запускаем 50 поколений


if __name__ == '__main__':  # для использования конфига
    local_dir = os.path.dirname(__file__)  # сохраняем путь к файлу, в котором мы сейчас находимся
    config_path = os.path.join(local_dir, 'config-feedforward.txt')  # находим полный путь к конфигу
    run(config_path)  # запускаем конфиг
