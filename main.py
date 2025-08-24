"""
Tiny Planet: Siege — Online Co‑op (Single‑File, pygame)
-------------------------------------------------------
This build adds **online multiplayer (2‑player co‑op)** on top of the previous features:
- Host‑authoritative server (1 host + 1 client) — defend the core together
- Client sends inputs; host simulates world and streams compact snapshots
- Works over LAN or internet (port‑forward if needed)
- Still fully playable offline (no args)

Existing features kept: boss fights, powerups, coins, shop with upgrades, stronger early balance, lighting/particles, controller support, sound effects.

Run:
  pip install pygame

Host:
  python main.py --host 5000
Join:
  python main.py --join 127.0.0.1:5000
Single‑player (offline):
  python main.py

Controls:
  Keyboard/Mouse: WASD to move, mouse to aim, LMB shoot
  Gamepad: left stick move, right stick aim, RT/A to fire
  R restart (host only), 1–4 buy upgrades in shop (host only), B to skip shop

Notes:
- **Security**: this is a learning/demo netcode using JSON over TCP. Do not expose publicly without hardening.
- **NAT**: to play over the internet, forward the chosen port on the host's router.
- **Performance**: snapshots ~20 Hz; keep one client for simplicity.
"""

import math
import random
import sys
import time
import json
import socket
import threading
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import pygame

# ---------------------------- SETTINGS ---------------------------------
WIDTH, HEIGHT = 1200, 700
FPS = 60
NET_SNAPSHOT_HZ = 20  # server -> client
PLANET_RADIUS = 220
PLANET_CENTER = (WIDTH // 2 + 160, HEIGHT // 2)

# Gameplay tuning
STARTING_HP = 220
MAX_HP = 220
CORE_MAX_HP = 320
PLAYER_SPEED = 400.0  # CHANGED: Increased from 260.0 for faster movement
PLAYER_RADIUS = 14
PLAYER_REGEN_BETWEEN_WAVES = 28

BULLET_SPEED = 760.0
BULLET_LIFETIME = 1.2

ENEMY_BASE_HP = 22
ENEMY_SPEED = 72.0
ENEMY_DAMAGE_CORE = 8
ENEMY_RADIUS = 16

WAVE_BASE_ENEMIES = 25
BOSS_WAVE_INTERVAL = 5
WAVE_DURATION = 30.0 # NEW: Duration over which wave enemies spawn

COIN_PER_ENEMY = 3
COIN_PER_BOSS = 80

SHOP_TIME = 8.0

# Powerups
POWERUP_CHANCE = 0.18
POWERUP_TYPES = ["health", "shield", "overdrive", "orbital", "magnet"]

# Visuals
BG = (8, 10, 16)
WHITE = (240, 240, 240)
MUTED = (160, 170, 180)
ORANGE = (255, 170, 110)
GREEN = (96, 205, 120)
YELLOW = (240, 210, 100)
RED = (235, 95, 95)
CYAN = (110, 240, 240)

# Lighting
DARK_ALPHA = 190
LIGHT_RADIUS = 220

random.seed(42)

# ---------------------------- HELPERS ---------------------------------

def clamp(v, a, b):
    return a if v < a else b if v > b else v


def length(x, y):
    return math.hypot(x, y)


def norm(x, y):
    l = length(x, y)
    if l == 0:
        return 0.0, 0.0
    return x / l, y / l

# ---------------------------- AUDIO SYSTEM -----------------------------

class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.background_music = None
        self.music_playing = False
        self.sound_enabled = True
        self.load_sounds()
    
    def load_sounds(self):
        """Load all sound effects from the sound folder"""
        sound_files = {
            'background': 'background.mp3',
            'boss_die1': 'boss_die1.mp3',
            'boss_die2': 'boss_die2.mp3', 
            'boss_die3': 'boss_die3.mp3',
            'defeat': 'defeat.mp3',
            'enemy_die': 'enemy_die.mp3',
            'enemy_die2': 'enemy_die2.mp3',
            'laser_shot': 'laser_shot.mp3',
            'shop': 'shop.mp3',
            'super_shot': 'super_shot.mp3',
            'victory': 'victory.mp3'
        }
        
        sound_folder = os.path.join(os.path.dirname(__file__), 'sound')
        
        for name, filename in sound_files.items():
            filepath = os.path.join(sound_folder, filename)
            try:
                if os.path.exists(filepath):
                    if name == 'background':
                        # Background music handled separately
                        self.background_music = filepath
                    else:
                        self.sounds[name] = pygame.mixer.Sound(filepath)
                        # Adjust volumes for better balance
                        if name in ['laser_shot', 'super_shot']:
                            self.sounds[name].set_volume(0.4)
                        elif name in ['enemy_die', 'enemy_die2']:
                            self.sounds[name].set_volume(0.6)
                        elif name in ['boss_die1', 'boss_die2', 'boss_die3']:
                            self.sounds[name].set_volume(0.8)
                        elif name in ['defeat', 'victory']:
                            self.sounds[name].set_volume(0.9)
                        elif name == 'shop':
                            self.sounds[name].set_volume(0.7)
                else:
                    print(f"Warning: Sound file not found: {filepath}")
            except Exception as e:
                print(f"Error loading sound {name}: {e}")
    
    def play_sound(self, name, volume=1.0):
        """Play a sound effect"""
        if not self.sound_enabled or name not in self.sounds:
            return
        try:
            sound = self.sounds[name]
            if volume != 1.0:
                sound.set_volume(sound.get_volume() * volume)
            sound.play()
        except Exception as e:
            print(f"Error playing sound {name}: {e}")
    
    def play_background_music(self, loop=True):
        """Start background music"""
        if not self.sound_enabled or not self.background_music or self.music_playing:
            return
        try:
            pygame.mixer.music.load(self.background_music)
            pygame.mixer.music.set_volume(0.3)  # Keep background music quiet
            pygame.mixer.music.play(-1 if loop else 0)
            self.music_playing = True
        except Exception as e:
            print(f"Error playing background music: {e}")
    
    def stop_background_music(self):
        """Stop background music"""
        try:
            pygame.mixer.music.stop()
            self.music_playing = False
        except Exception:
            pass
    
    def play_random_enemy_death(self):
        """Play a random enemy death sound"""
        sounds = ['enemy_die', 'enemy_die2']
        available = [s for s in sounds if s in self.sounds]
        if available:
            self.play_sound(random.choice(available))
    
    def play_random_boss_death(self):
        """Play a random boss death sound"""
        sounds = ['boss_die1', 'boss_die2', 'boss_die3']
        available = [s for s in sounds if s in self.sounds]
        if available:
            self.play_sound(random.choice(available))

# Global sound manager instance
sound_manager = None

# ---------------------------- ART & TEXTURES ----------------------------

def radial_gradient(radius, inner, outer):
    surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        t = r / radius
        c = (
            int(inner[0]*t + outer[0]*(1-t)),
            int(inner[1]*t + outer[1]*(1-t)),
            int(inner[2]*t + outer[2]*(1-t)),
        )
        pygame.draw.circle(surf, c, (radius, radius), r)
    return surf


def clouds_texture(size, blobs=30):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rnd = random.Random(1337)
    for _ in range(blobs):
        x = rnd.randint(size//8, size-size//8)
        y = rnd.randint(size//8, size-size//8)
        r = rnd.randint(size//16, size//6)
        a = rnd.randint(26, 80)
        pygame.draw.circle(surf, (255,255,255,a), (x,y), r)
    return pygame.transform.smoothscale(pygame.transform.smoothscale(surf,(size//2,size//2)), (size,size))


def make_light_sprite(r):
    s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
    for rr in range(r,0,-1):
        a = int(255 * (1 - rr/r)**2)
        pygame.draw.circle(s, (a,a,a,a), (r,r), rr)
    return s

# ---------------------------- ENTITIES ---------------------------------
@dataclass
class Bullet:
    x: float; y: float; vx: float; vy: float; ttl: float; dmg: int; pierce: bool=False

@dataclass
class Enemy:
    x: float; y: float; hp: int; speed: float; coin: int; radius: int = ENEMY_RADIUS

@dataclass
class Boss:
    x: float; y: float; hp: int; phase: int; timer: float

@dataclass
class Powerup:
    x: float; y: float; kind: str; ttl: float = 9999.0

@dataclass
class Coin:
    x: float; y: float; vx: float; vy: float; ttl: float = 6.0

@dataclass
class Particle:
    x: float; y: float; vx: float; vy: float; ttl: float; color: Tuple[int,int,int]

@dataclass
class FloatingText:
    x: float; y: float; txt: str; ttl: float

@dataclass
class Player:
    x: float; y: float; vx: float=0.0; vy: float=0.0
    hp: int=STARTING_HP; max_hp: int=MAX_HP
    cooldown: float=0.0
    overdrive_t: float=0.0
    shield_t: float=0.0
    magnet_t: float=0.0
    spread_level: int=0
    damage_mult: float=1.0
    fire_rate: float=0.08
    pierce: bool=False
    is_remote: bool=False

# ---------------------------- GAME STATE ---------------------------------
@dataclass
class State:
    # players[0] = local/host; players[1] = remote (if any)
    players: List[Player] = field(default_factory=list)
    bullets: List[Bullet] = field(default_factory=list)
    enemies: List[Enemy] = field(default_factory=list)
    bosses: List[Boss] = field(default_factory=list)
    particles: List[Particle] = field(default_factory=list)
    powerups: List[Powerup] = field(default_factory=list)
    coins: List[Coin] = field(default_factory=list)
    floats: List[FloatingText] = field(default_factory=list)
    wave: int = 1
    in_shop: bool = False
    shop_time: float = SHOP_TIME
    # NEW: State for timed wave spawning
    wave_timer: float = 0.0
    enemies_to_spawn: int = 0
    spawn_cooldown: float = 0.0
    coins_total: int = 0
    core_hp: int = CORE_MAX_HP
    screenshake: float = 0.0
    game_over: bool = False
    victory: bool = False

# ---------------------------- GAME MECHANICS -----------------------------

def spawn_enemy(state: State, angle_offset=0.0, hp_bonus=0):
    ang = random.uniform(0, math.tau) + angle_offset
    x = PLANET_CENTER[0] + math.cos(ang)*(PLANET_RADIUS + 60)
    y = PLANET_CENTER[1] + math.sin(ang)*(PLANET_RADIUS + 60)
    hp = ENEMY_BASE_HP + hp_bonus
    e = Enemy(x,y,hp,ENEMY_SPEED + hp_bonus*0.7, COIN_PER_ENEMY)
    state.enemies.append(e)


def spawn_wave(state: State):
    state.in_shop = False
    state.shop_time = SHOP_TIME
    n = WAVE_BASE_ENEMIES + (state.wave-1)
    if state.wave <= 3:
        n = max(3, n-2)
    
    # CHANGED: Set up wave parameters for timed spawning instead of spawning all at once
    state.wave_timer = WAVE_DURATION
    state.enemies_to_spawn = n
    state.spawn_cooldown = 0.0 # Spawn first enemy immediately

    # Bosses still spawn at the beginning of their wave
    if state.wave % BOSS_WAVE_INTERVAL == 0:
        bx = PLANET_CENTER[0] + random.choice([-1,1])*(PLANET_RADIUS + 160)
        by = PLANET_CENTER[1]
        boss_hp = 260 + (state.wave//BOSS_WAVE_INTERVAL -1)*120
        state.bosses.append(Boss(bx,by,boss_hp,phase=0,timer=2.0))


def try_drop_powerup(state: State, x, y):
    if random.random() < POWERUP_CHANCE:
        kind = random.choice(POWERUP_TYPES)
        state.powerups.append(Powerup(x,y,kind))


def spawn_coin(state: State, x, y, amount):
    for _ in range(max(1, amount)):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(40,160)
        state.coins.append(Coin(x,y, math.cos(ang)*spd, math.sin(ang)*spd, ttl=5.0))


def spawn_explosion(state: State, x, y, intensity=18):
    for _ in range(intensity):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(30,360)
        vx = math.cos(ang)*spd
        vy = math.sin(ang)*spd
        c = (random.randint(200,255), random.randint(120,220), random.randint(40,90))
        state.particles.append(Particle(x,y,vx,vy,ttl=random.uniform(0.3,0.9),color=c))
    state.screenshake = min(36.0, state.screenshake + intensity*0.6)

# ---------------------------- UPDATES ----------------------------------

def update_player(p: Player, dt: float, ax: float, ay: float):
    p.vx += ax * dt; p.vy += ay * dt
    p.vx *= 1 - min(1, 8*dt); p.vy *= 1 - min(1, 8*dt)
    p.x += p.vx * dt; p.y += p.vy * dt
    # clamp to planet
    dx = p.x - PLANET_CENTER[0]; dy = p.y - PLANET_CENTER[1]
    d = math.hypot(dx,dy)
    maxr = PLANET_RADIUS - 18
    if d > maxr and d>0:
        nx, ny = dx/d, dy/d
        p.x = PLANET_CENTER[0] + nx*maxr
        p.y = PLANET_CENTER[1] + ny*maxr
        p.vx *= 0.2; p.vy *= 0.2


def player_fire_from_dir(state: State, p: Player, aim_dir: Tuple[float,float]):
    global sound_manager
    p.cooldown = max(0.0, p.cooldown)
    base_dmg = int(18 * p.damage_mult)
    bullets_to_fire = 1 + p.spread_level*2
    spread_angle = 0.28 if p.spread_level>0 else 0.0
    
    # Play appropriate shooting sound
    if sound_manager:
        if p.overdrive_t > 0 or p.damage_mult > 2.0:
            sound_manager.play_sound('super_shot')
        else:
            sound_manager.play_sound('laser_shot')
    
    for i in range(bullets_to_fire):
        ang_off = 0.0
        if bullets_to_fire>1:
            ang_off = ((i - (bullets_to_fire-1)/2) / (bullets_to_fire-1)) * spread_angle
        ca = math.cos(ang_off); sa = math.sin(ang_off)
        dirx,diry = aim_dir
        vx = (dirx*ca - diry*sa) * BULLET_SPEED
        vy = (dirx*sa + diry*ca) * BULLET_SPEED
        state.bullets.append(Bullet(p.x, p.y, vx, vy, BULLET_LIFETIME, base_dmg, pierce=p.pierce))


def update_bullets(state: State, dt: float):
    i=0
    while i < len(state.bullets):
        b = state.bullets[i]
        b.ttl -= dt
        if b.ttl <= 0:
            state.bullets.pop(i); continue
        b.x += b.vx*dt; b.y += b.vy*dt
        i+=1


def update_enemies(state: State, dt: float):
    i=0
    while i < len(state.enemies):
        e = state.enemies[i]
        dirx,diry = norm(PLANET_CENTER[0]-e.x, PLANET_CENTER[1]-e.y)
        e.x += dirx * e.speed * dt
        e.y += diry * e.speed * dt
        dx = e.x - PLANET_CENTER[0]; dy = e.y - PLANET_CENTER[1]
        if dx*dx + dy*dy <= (e.radius + 30)**2:
            state.core_hp -= ENEMY_DAMAGE_CORE
            spawn_explosion(state,e.x,e.y, intensity=10)
            spawn_coin(state,e.x,e.y,e.coin)
            state.enemies.pop(i); continue
        i+=1


def update_bosses(state: State, dt: float):
    i=0
    while i < len(state.bosses):
        b = state.bosses[i]
        ang = math.atan2(b.y-PLANET_CENTER[1], b.x-PLANET_CENTER[0])
        ang += 0.14*dt * (1 if b.phase%2==0 else -1)
        r = PLANET_RADIUS + 140
        b.x = PLANET_CENTER[0] + math.cos(ang)*r
        b.y = PLANET_CENTER[1] + math.sin(ang)*r
        b.timer -= dt
        if b.timer <= 0:
            if b.phase==0:
                for k in range(14):
                    a = k*(math.tau/14) + random.uniform(-0.06,0.06)
                    vx = math.cos(a)*260; vy=math.sin(a)*260
                    state.particles.append(Particle(b.x,b.y,vx,vy,ttl=1.2,color=(255,90,90)))
            elif b.phase==1:
                for _ in range(3 + state.wave//6):
                    dx = state.players[0].x - b.x; dy = state.players[0].y - b.y
                    if len(state.players)>1:
                        # aim at nearest player
                        d0 = dx*dx+dy*dy
                        dx2 = state.players[1].x - b.x; dy2 = state.players[1].y - b.y
                        if dx2*dx2+dy2*dy2 < d0:
                            dx,dy = dx2,dy2
                    dx+=random.uniform(-80,80); dy+=random.uniform(-80,80)
                    dirx,diry = norm(dx,dy)
                    state.bullets.append(Bullet(b.x,b.y,dirx*360,diry*360,ttl=2.0,dmg=32))
            else:
                for _ in range(2+state.wave//8):
                    spawn_enemy(state,hp_bonus=state.wave//2)
            b.timer = 1.8
            b.phase = (b.phase+1)%3
        if random.random() < 0.002*dt*100:
            spawn_enemy(state,hp_bonus=state.wave//3)
        if b.hp <= 0:
            spawn_explosion(state,b.x,b.y,intensity=48)
            spawn_coin(state,b.x,b.y,COIN_PER_BOSS)
            state.powerups.append(Powerup(b.x,b.y, random.choice(POWERUP_TYPES)))
            # Play boss death sound
            if sound_manager:
                sound_manager.play_random_boss_death()
            state.bosses.pop(i); continue
        i+=1


def handle_collisions(state: State):
    global sound_manager
    # bullets vs enemies/bosses
    i=0
    while i < len(state.bullets):
        b = state.bullets[i]
        hit = False
        for e in state.enemies:
            dx = e.x - b.x; dy = e.y - b.y
            if dx*dx + dy*dy <= (e.radius + 4)**2:
                e.hp -= b.dmg
                spawn_explosion(state, b.x, b.y, intensity=5)
                if not b.pierce:
                    hit = True
                break
        if not hit:
            for bo in state.bosses:
                dx = bo.x - b.x; dy = bo.y - b.y
                if dx*dx + dy*dy <= (44)**2:
                    bo.hp -= b.dmg
                    spawn_explosion(state, b.x, b.y, intensity=6)
                    if not b.pierce:
                        hit=True
                    break
        if hit:
            try: state.bullets.pop(i)
            except: pass
        else:
            i+=1

    # kill enemies
    i=0
    while i < len(state.enemies):
        e = state.enemies[i]
        if e.hp <= 0:
            spawn_explosion(state,e.x,e.y, intensity=12)
            spawn_coin(state,e.x,e.y,e.coin)
            try_drop_powerup(state,e.x,e.y)
            # Play enemy death sound
            if sound_manager:
                sound_manager.play_random_enemy_death()
            state.enemies.pop(i); continue
        i+=1

    # coins pickup (all players)
    i=0
    while i < len(state.coins):
        c = state.coins[i]
        c.ttl -= 1.0/FPS
        c.x += c.vx*(1.0/FPS); c.y += c.vy*(1.0/FPS)
        c.vx *= 0.995; c.vy *= 0.995
        if c.ttl<=0:
            state.coins.pop(i); continue
        picked=False
        for p in state.players:
            dx = p.x - c.x; dy = p.y - c.y
            if p.magnet_t>0:
                d = math.hypot(dx,dy)
                if d<200 and d>0.1:
                    c.vx += (dx/d)*240*(1.0/FPS)
                    c.vy += (dy/d)*240*(1.0/FPS)
            if dx*dx + dy*dy <= (28)**2:
                state.coins_total += 1
                picked=True
                break
        if picked:
            state.coins.pop(i); continue
        i+=1

    # powerup pickup (any)
    i=0
    while i < len(state.powerups):
        pwr = state.powerups[i]
        taken=False
        for pl in state.players:
            dx = pl.x - pwr.x; dy = pl.y - pwr.y
            if dx*dx + dy*dy <= (28)**2:
                apply_powerup(pl, pwr.kind)
                taken=True; break
        if taken:
            state.powerups.pop(i); continue
        i+=1

# ---------------------------- POWERUPS ---------------------------------

def apply_powerup(p: Player, kind: str):
    if kind=="health":
        heal = int(p.max_hp*0.45)
        p.hp = min(p.max_hp, p.hp + heal)
    elif kind=="shield":
        p.shield_t = 6.0
    elif kind=="overdrive":
        p.overdrive_t = 10.0
    elif kind=="orbital":
        # orbital strike wipes nearby enemies (host only, but harmless on client)
        pass
    elif kind=="magnet":
        p.magnet_t = 12.0

# ---------------------------- DRAWING ---------------------------------

def draw_starfield(surface, stars, t):
    for x,y,b,s in stars:
        tw = 0.75 + 0.25*math.sin(t*s + (x+y)*0.01)
        val = int(200*b*tw)
        surface.fill((val,val,val), (x,y,2,2))


def draw_planet(surface, base, clouds, t):
    surface.blit(base, base.get_rect(center=PLANET_CENTER))
    pygame.draw.circle(surface, (24,120,100), PLANET_CENTER, PLANET_RADIUS-8, width=3)
    cl = pygame.transform.rotozoom(clouds, t*8 % 360, 1.0)
    cl.set_alpha(100)
    surface.blit(cl, cl.get_rect(center=PLANET_CENTER))


def draw_entities(surface, state: State):
    # core
    pygame.draw.circle(surface, (60,80,90), PLANET_CENTER, 30)
    pygame.draw.circle(surface, WHITE, PLANET_CENTER, 30, width=2)
    # enemies
    for e in state.enemies:
        pygame.draw.circle(surface, ORANGE, (int(e.x),int(e.y)), e.radius)
        pygame.draw.circle(surface, WHITE, (int(e.x),int(e.y)), e.radius, width=2)
    for b in state.bosses:
        pygame.draw.circle(surface, (220,80,160), (int(b.x),int(b.y)), 40)
        pygame.draw.circle(surface, WHITE, (int(b.x),int(b.y)), 40, width=2)
    for c in state.coins:
        pygame.draw.circle(surface, (255,220,80), (int(c.x),int(c.y)), 6)
        pygame.draw.circle(surface, (220,180,60), (int(c.x),int(c.y)), 3)
    for p in state.powerups:
        col = (100,220,160) if p.kind=="health" else (200,200,80) if p.kind=="overdrive" else (140,200,255) if p.kind=="shield" else (240,160,80) if p.kind=="orbital" else (180,120,255)
        pygame.draw.rect(surface, col, pygame.Rect(int(p.x)-8,int(p.y)-8,16,16), border_radius=4)
    for part in state.particles:
        pygame.draw.circle(surface, part.color, (int(part.x),int(part.y)), 2)
    # bullets
    for b in state.bullets:
        pygame.draw.circle(surface, CYAN if b.dmg>26 else YELLOW, (int(b.x),int(b.y)), 3)


def draw_players(surface, players: List[Player]):
    for idx,pl in enumerate(players):
        col = CYAN if idx==0 else (140, 200, 255)
        pygame.draw.circle(surface, col, (int(pl.x),int(pl.y)), PLAYER_RADIUS)
        pygame.draw.circle(surface, WHITE, (int(pl.x),int(pl.y)), PLAYER_RADIUS, width=2)


def draw_hud(screen, font, state: State):
    x=20; y=18
    w=520; h=28
    pygame.draw.rect(screen, (30,36,44), (x,y,w,h), border_radius=8)
    pygame.draw.rect(screen, (60,70,80), (x,y,w,h), width=2, border_radius=8)
    hp_norm = clamp(state.core_hp/CORE_MAX_HP,0,1)
    pygame.draw.rect(screen, (120,220,140) if state.core_hp>90 else RED, (x+3,y+3,int((w-6)*hp_norm),h-6), border_radius=6)

    txt = font.render(f"Core: {state.core_hp}/{CORE_MAX_HP}", True, WHITE)
    screen.blit(txt, (x+10,y+4))
    txt2 = font.render(f"Wave: {state.wave}", True, WHITE)
    screen.blit(txt2, (x+w+16,y))

# ---------------------------- LIGHTING PASS -----------------------------

def apply_lighting(screen, light_sprite, players: List[Player], particles: List[Particle]):
    darkness = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    darkness.fill((0,0,0,DARK_ALPHA))
    l = pygame.transform.smoothscale(light_sprite, (LIGHT_RADIUS*2, LIGHT_RADIUS*2))
    for pl in players:
        darkness.blit(l, l.get_rect(center=(int(pl.x),int(pl.y))), special_flags=pygame.BLEND_RGBA_SUB)
    for p in particles:
        if p.color[0]>200:
            l2 = pygame.transform.smoothscale(light_sprite, (120,120))
            darkness.blit(l2, l2.get_rect(center=(int(p.x),int(p.y))), special_flags=pygame.BLEND_RGBA_SUB)
    screen.blit(darkness, (0,0))

# ---------------------------- SHOP / UPGRADES ---------------------------
SHOP_UPGRADES = [
    {"name":"Fire Rate -", "desc":"-15% fire delay", "cost":20, "apply": lambda s: setattr(s.players[0],'fire_rate', max(0.03, s.players[0].fire_rate*0.85))},
    {"name":"Damage +", "desc":"+25% damage", "cost":30, "apply": lambda s: setattr(s.players[0],'damage_mult', s.players[0].damage_mult*1.25)},
    {"name":"Spread", "desc":"Add spread shots", "cost":60, "apply": lambda s: setattr(s.players[0],'spread_level', min(2, s.players[0].spread_level+1))},
    {"name":"Piercing", "desc":"Bullets pierce enemies", "cost":120, "apply": lambda s: setattr(s.players[0],'pierce', True)},
]

# ---------------------------- NETWORKING --------------------------------
class NetServer:
    def __init__(self, port:int):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.listen(1)
        self.client: Optional[socket.socket] = None
        self.client_lock = threading.Lock()
        self.last_snapshot = 0.0
        self.inputs = {"ax":0.0, "ay":0.0, "aimx":0.0, "aimy":0.0, "fire":False}
        threading.Thread(target=self.accept_loop, daemon=True).start()

    def accept_loop(self):
        while True:
            c, addr = self.sock.accept()
            with self.client_lock:
                if self.client:
                    c.close()
                else:
                    self.client = c
                    c.setblocking(False)
                    print("Client connected:", addr)
                    threading.Thread(target=self.recv_loop, args=(c,), daemon=True).start()

    def recv_loop(self, c: socket.socket):
        buf = b""
        try:
            while True:
                try:
                    data = c.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b" " in buf:
                        line, buf = buf.split(b" ", 1)
                        try:
                            msg = json.loads(line.decode('utf-8'))
                            if msg.get("type") == "input":
                                self.inputs.update({
                                    "ax": float(msg.get("ax",0.0)),
                                    "ay": float(msg.get("ay",0.0)),
                                    "aimx": float(msg.get("aimx",0.0)),
                                    "aimy": float(msg.get("aimy",0.0)),
                                    "fire": bool(msg.get("fire",False)),
                                })
                        except Exception:
                            pass
                except BlockingIOError:
                    time.sleep(0.005)
        finally:
            with self.client_lock:
                if self.client is c:
                    self.client = None
            try: c.close()
            except: pass
            print("Client disconnected")

    def send_snapshot(self, snap: dict):
        with self.client_lock:
            if not self.client:
                return
            try:
                self.client.sendall((json.dumps(snap, separators=(',',':'))+" ").encode('utf-8'))
            except Exception:
                try: self.client.close()
                except: pass
                self.client=None

class NetClient:
    def __init__(self, host:str, port:int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.setblocking(False)
        self.recv_buf = b""
        self.out_lock = threading.Lock()

    def send_input(self, ax, ay, aimx, aimy, fire):
        msg = {"type":"input","ax":ax,"ay":ay,"aimx":aimx,"aimy":aimy,"fire":fire}
        data = (json.dumps(msg, separators=(',',':'))+" ").encode('utf-8')
        with self.out_lock:
            try:
                self.sock.sendall(data)
            except Exception:
                pass

    def poll_snapshots(self) -> List[dict]:
        out=[]
        try:
            data = self.sock.recv(4096)
            if data:
                self.recv_buf += data
        except BlockingIOError:
            pass
        except Exception:
            return out
        while b" " in self.recv_buf:
            line, self.recv_buf = self.recv_buf.split(b" ",1) 
            try:
                out.append(json.loads(line.decode('utf-8')))
            except Exception:
                pass
        return out

# ---------------------------- MAIN (HOST) -------------------------------

def host_main(port:int):
    global sound_manager
    
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    except Exception as e:
        print(f"Warning: Could not initialize mixer: {e}")
    
    # Initialize sound manager
    sound_manager = SoundManager()
    
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Tiny Planet: Siege — Host :{port}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('arial',18)
    big = pygame.font.SysFont('arial',22,bold=True)

    planet_base = radial_gradient(PLANET_RADIUS, (40,150,140), (26,90,110))
    clouds = clouds_texture(PLANET_RADIUS*2)
    stars = [(random.randint(0,WIDTH-1), random.randint(0,HEIGHT-1), random.random()*0.9+0.1, random.uniform(0.6,1.6)) for _ in range(260)]
    light = make_light_sprite(220)

    # controller
    joystick = None
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0); joystick.init()

    state = State(players=[
        Player(x=PLANET_CENTER[0], y=PLANET_CENTER[1]-PLANET_RADIUS//2, is_remote=False),
        Player(x=PLANET_CENTER[0], y=PLANET_CENTER[1]+PLANET_RADIUS//2-40, is_remote=True),
    ])
    spawn_wave(state)
    
    # Start background music
    sound_manager.play_background_music()

    server = NetServer(port) if port > 0 else None
    t=0.0
    last_snap=0.0
    running=True
    shop_sound_played = False
    defeat_sound_played = False
    victory_sound_played = False
    
    while running:
        dt = clock.tick(FPS)/1000.0
        t += dt
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: running=False
                if ev.key==pygame.K_r: 
                    state = State(players=state.players)
                    spawn_wave(state)
                    shop_sound_played = False
                    defeat_sound_played = False
                    victory_sound_played = False
                    sound_manager.play_background_music()
                if state.in_shop and ev.key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                    idx = {pygame.K_1:0,pygame.K_2:1,pygame.K_3:2,pygame.K_4:3}[ev.key]
                    up = SHOP_UPGRADES[idx]
                    if state.coins_total >= up['cost']:
                        state.coins_total -= up['cost']
                        up['apply'](state)
                if state.in_shop and ev.key==pygame.K_b:
                    state.shop_time = 0.0

        # Play shop sound when entering shop
        if state.in_shop and not shop_sound_played:
            sound_manager.play_sound('shop')
            shop_sound_played = True
        elif not state.in_shop:
            shop_sound_played = False

        # Check for game over/victory conditions
        if state.core_hp <= 0 and not defeat_sound_played:
            sound_manager.stop_background_music()
            sound_manager.play_sound('defeat')
            defeat_sound_played = True
        elif state.wave >= 20 and not state.enemies and not state.bosses and state.enemies_to_spawn == 0 and not victory_sound_played:
            sound_manager.stop_background_music()
            sound_manager.play_sound('victory')
            victory_sound_played = True

        # local input (player 0)
        if not state.in_shop and state.core_hp>0:
            if joystick and joystick.get_init():
                lx = joystick.get_axis(0); ly = joystick.get_axis(1)
                ax = lx * PLAYER_SPEED; ay = ly * PLAYER_SPEED
            else:
                keys = pygame.key.get_pressed()
                ax = (keys[pygame.K_d] - keys[pygame.K_a]) * PLAYER_SPEED
                ay = (keys[pygame.K_s] - keys[pygame.K_w]) * PLAYER_SPEED
            update_player(state.players[0], dt, ax, ay)

            # aim & fire local
            aim_dir = None; firing=False
            if joystick and joystick.get_init():
                rx = joystick.get_numaxes()>2 and joystick.get_axis(2) or 0.0
                ry = joystick.get_numaxes()>3 and joystick.get_axis(3) or 0.0
                if abs(rx)>0.15 or abs(ry)>0.15:
                    aim_dir = norm(rx, ry); firing = joystick.get_button(5) or joystick.get_button(7) or joystick.get_button(0)
            if aim_dir is None:
                mx,my = pygame.mouse.get_pos()
                dx = mx - state.players[0].x; dy = my - state.players[0].y
                aim_dir = norm(dx,dy)
                firing = firing or pygame.mouse.get_pressed(num_buttons=3)[0]

            p0 = state.players[0]
            p0.cooldown -= dt
            rate = p0.fire_rate * (0.5 if p0.overdrive_t>0 else 1.0)
            if p0.cooldown<=0 and firing:
                player_fire_from_dir(state, p0, aim_dir)
                p0.cooldown = rate
                state.screenshake = min(22.0, state.screenshake + 2.8)

            # remote player (player 1) from server.inputs
            if server:
                inp = server.inputs
                update_player(state.players[1], dt, inp["ax"], inp["ay"])
                p1 = state.players[1]
                p1.cooldown -= dt
                rate1 = p1.fire_rate * (0.5 if p1.overdrive_t>0 else 1.0)
                if p1.cooldown<=0 and inp["fire"]:
                    aim = norm(inp["aimx"], inp["aimy"])
                    if aim != (0.0,0.0):
                        player_fire_from_dir(state, p1, aim)
                        p1.cooldown = rate1

            # world updates
            update_bullets(state, dt)
            update_enemies(state, dt)
            update_bosses(state, dt)
            handle_collisions(state)
            
            # NEW: Timed wave spawning logic
            if not state.in_shop and state.enemies_to_spawn > 0:
                state.wave_timer = max(0, state.wave_timer - dt)
                state.spawn_cooldown -= dt

                if state.spawn_cooldown <= 0:
                    spawn_enemy(state, hp_bonus=(state.wave-1)//3)
                    state.enemies_to_spawn -= 1
                    
                    if state.enemies_to_spawn > 0:
                        if state.wave_timer > 0:
                            # Spread remaining spawns over the remaining time
                            time_per_enemy = state.wave_timer / state.enemies_to_spawn
                            state.spawn_cooldown = time_per_enemy
                        else:
                            # If time runs out, spawn the rest quickly
                            state.spawn_cooldown = 0.2

            # timers
            for pl in state.players:
                if pl.overdrive_t>0: pl.overdrive_t -= dt
                if pl.shield_t>0: pl.shield_t -= dt
                if pl.magnet_t>0: pl.magnet_t -= dt

            # CHANGED: Wave progression now checks if all enemies for the wave have been spawned
            if not state.in_shop and not state.enemies and not state.bosses and state.enemies_to_spawn == 0:
                state.in_shop = True
                state.shop_time = SHOP_TIME
                state.wave += 1
        else: # In shop or game over
            state.shop_time -= dt
            if state.shop_time <= 0 and state.in_shop:
                state.in_shop = False
                for pl in state.players:
                    pl.hp = min(pl.max_hp, pl.hp + PLAYER_REGEN_BETWEEN_WAVES)
                spawn_wave(state)

        # particles/coins lightweight updates
        for c in list(state.coins):
            c.ttl -= dt
            c.x += c.vx*dt; c.y += c.vy*dt
            c.vx *= 0.99; c.vy *= 0.99
            if c.ttl<=0: state.coins.remove(c)
        i=0
        while i < len(state.particles):
            part = state.particles[i]
            part.ttl -= dt
            if part.ttl<=0: state.particles.pop(i); continue
            part.x += part.vx*dt; part.y += part.vy*dt
            part.vx *= 0.96; part.vy *= 0.96
            i+=1

        # snapshots
        if server:
            last_snap += dt
            if last_snap >= 1.0/NET_SNAPSHOT_HZ:
                last_snap = 0.0
                snap = {
                    "type":"snapshot",
                    "wave": state.wave,
                    "core": state.core_hp,
                    "coins": state.coins_total,
                    "inshop": state.in_shop,
                    "shop_t": round(state.shop_time,2),
                    "players": [
                        {"x":state.players[0].x,"y":state.players[0].y,"hp":state.players[0].hp},
                        {"x":state.players[1].x,"y":state.players[1].y,"hp":state.players[1].hp},
                    ],
                    "enemies": [(round(e.x,1),round(e.y,1),e.hp) for e in state.enemies[:120]],
                    "bosses": [(round(b.x,1),round(b.y,1),b.hp) for b in state.bosses[:6]],
                    "bullets": [(round(b.x,1),round(b.y,1)) for b in state.bullets[:220]],
                    "powerups": [(int(p.x),int(p.y),p.kind) for p in state.powerups[:40]],
                    "coinsF": [(int(c.x),int(c.y)) for c in state.coins[:120]],
                }
                server.send_snapshot(snap)

        # screenshake
        sx=sy=0
        if state.screenshake>0:
            state.screenshake -= 30*dt
            sx = random.uniform(-1,1)*state.screenshake
            sy = random.uniform(-1,1)*state.screenshake

        # draw (host view)
        screen.fill(BG)
        stars_surf = screen
        draw_starfield(stars_surf, stars, t)
        temp = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        draw_planet(temp, planet_base, clouds, t)
        draw_entities(temp, state)
        draw_players(temp, state.players)
        screen.blit(temp, (sx,sy))
        apply_lighting(screen, light, state.players, state.particles)
        draw_hud(screen, font, state)

        # overlays
        if state.in_shop:
            ov = pygame.Surface((WIDTH-360, HEIGHT-220), pygame.SRCALPHA)
            ov.fill((12,14,18,220))
            rect = ov.get_rect(center=(WIDTH//2, HEIGHT//2))
            pygame.draw.rect(ov, (40,46,56), (12,12,rect.width-24,rect.height-24), border_radius=10)
            screen.blit(ov, rect.topleft)
            title = big.render("Shop — Host only", True, WHITE)
            screen.blit(title, (rect.x+28, rect.y+26))
            info = font.render(f"Coins: {state.coins_total} | Next in {int(state.shop_time)}s", True, MUTED)
            screen.blit(info, (rect.x+28, rect.y+60))
            for i,up in enumerate(SHOP_UPGRADES):
                y = rect.y+110 + i*48
                cost = up['cost']
                txt = font.render(f"{i+1}. {up['name']} ({cost}) - {up['desc']}", True, WHITE if state.coins_total>=cost else MUTED)
                screen.blit(txt, (rect.x+36,y))

        if state.core_hp <= 0:
            ov = pygame.Surface((WIDTH,140), pygame.SRCALPHA); ov.fill((0,0,0,200))
            screen.blit(ov, (100, HEIGHT//2-70))
            t1 = big.render("CORE DESTROYED!", True, RED)
            screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 40))
            t2 = font.render("Press R to restart.", True, WHITE)
            screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 4))

        pygame.display.flip()

    pygame.quit(); sys.exit()

# ---------------------------- MAIN (CLIENT) -----------------------------

def client_main(host:str, port:int):
    global sound_manager
    
    pygame.init()
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    except Exception as e:
        print(f"Warning: Could not initialize mixer: {e}")
    
    # Initialize sound manager for client too
    sound_manager = SoundManager()
    
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Tiny Planet: Siege — Client {host}:{port}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('arial',18)

    planet_base = radial_gradient(PLANET_RADIUS, (40,150,140), (26,90,110))
    clouds = clouds_texture(PLANET_RADIUS*2)
    stars = [(random.randint(0,WIDTH-1), random.randint(0,HEIGHT-1), random.random()*0.9+0.1, random.uniform(0.6,1.6)) for _ in range(260)]
    light = make_light_sprite(220)

    client = NetClient(host, port)
    
    # Start background music for client
    sound_manager.play_background_music()

    # simple render state mirrored from snapshots
    snap = {
        "wave":1, "core":CORE_MAX_HP, "coins":0, "players":[{"x":PLANET_CENTER[0],"y":PLANET_CENTER[1]-PLANET_RADIUS//2,"hp":STARTING_HP},{"x":PLANET_CENTER[0],"y":PLANET_CENTER[1]+PLANET_RADIUS//2-40,"hp":STARTING_HP}],
        "enemies":[], "bosses":[], "bullets":[], "powerups":[], "coinsF":[], "inshop":False, "shop_t":0.0
    }

    joystick = None
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0); joystick.init()

    t=0.0
    running=True
    shop_sound_played = False
    defeat_sound_played = False
    victory_sound_played = False
    
    while running:
        dt = clock.tick(FPS)/1000.0
        t+=dt
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: running=False

        # gather local input to send to host
        if joystick and joystick.get_init():
            lx = joystick.get_axis(0); ly = joystick.get_axis(1)
            ax = lx * PLAYER_SPEED; ay = ly * PLAYER_SPEED
            rx = joystick.get_numaxes()>2 and joystick.get_axis(2) or 0.0
            ry = joystick.get_numaxes()>3 and joystick.get_axis(3) or 0.0
            aimx,aimy = rx, ry
            fire = joystick.get_button(5) or joystick.get_button(7) or joystick.get_button(0)
        else:
            keys = pygame.key.get_pressed()
            ax = (keys[pygame.K_d] - keys[pygame.K_a]) * PLAYER_SPEED
            ay = (keys[pygame.K_s] - keys[pygame.K_w]) * PLAYER_SPEED
            mx,my = pygame.mouse.get_pos()
            # aim from my player (players[1]) position
            px,py = snap["players"][1]["x"], snap["players"][1]["y"]
            aimx,aimy = norm(mx-px, my-py)
            fire = pygame.mouse.get_pressed(num_buttons=3)[0]
        client.send_input(ax, ay, aimx, aimy, fire)

        # apply any new snapshots
        for s in client.poll_snapshots():
            if s.get("type")=="snapshot":
                snap = s

        # Play shop sound when entering shop
        if snap.get('inshop') and not shop_sound_played:
            sound_manager.play_sound('shop')
            shop_sound_played = True
        elif not snap.get('inshop'):
            shop_sound_played = False

        # Check for game over/victory conditions
        if snap.get('core', CORE_MAX_HP) <= 0 and not defeat_sound_played:
            sound_manager.stop_background_music()
            sound_manager.play_sound('defeat')
            defeat_sound_played = True
        elif snap.get('wave', 1) >= 20 and not snap.get('enemies') and not snap.get('bosses') and not victory_sound_played:
            sound_manager.stop_background_music()
            sound_manager.play_sound('victory')
            victory_sound_played = True

        # draw client view (purely visual)
        screen.fill(BG)
        draw_starfield(screen, stars, t)
        temp = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        draw_planet(temp, planet_base, clouds, t)
        # rebuild lightweight state for draw functions
        st = State(players=[Player(x=snap['players'][0]['x'],y=snap['players'][0]['y']), Player(x=snap['players'][1]['x'],y=snap['players'][1]['y'])])
        st.enemies = [Enemy(x,y,hp,ENEMY_SPEED,COIN_PER_ENEMY) for (x,y,hp) in snap['enemies']]
        st.bosses = [Boss(x,y,hp,0,0.0) for (x,y,hp) in snap['bosses']]
        st.bullets = [Bullet(x,y,0,0,1.0,20) for (x,y) in snap['bullets']]
        st.powerups = [Powerup(x,y,k) for (x,y,k) in snap['powerups']]
        st.coins = [Coin(x,y,0,0,3.0) for (x,y) in snap['coinsF']]
        draw_entities(temp, st)
        draw_players(temp, st.players)
        screen.blit(temp, (0,0))
        apply_lighting(screen, light, st.players, st.particles)
        # basic HUD
        hud_text = font.render(f"Wave {snap['wave']}  |  Core {snap['core']}/{CORE_MAX_HP}", True, WHITE)
        screen.blit(hud_text, (20, 16))
        if snap.get('inshop'):
            shop_text = font.render(f"Shop open… next wave in {int(snap.get('shop_t',0))}s", True, MUTED)
            screen.blit(shop_text, (20, 42))
            
        # Game over/victory overlays for client
        if snap.get('core', CORE_MAX_HP) <= 0:
            ov = pygame.Surface((WIDTH,140), pygame.SRCALPHA); ov.fill((0,0,0,200))
            screen.blit(ov, (100, HEIGHT//2-70))
            t1 = pygame.font.SysFont('arial',22,bold=True).render("CORE DESTROYED!", True, RED)
            screen.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 40))
            t2 = font.render("Host can restart with R.", True, WHITE)
            screen.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 4))
            
        pygame.display.flip()

    pygame.quit(); sys.exit()

# ---------------------------- ENTRYPOINT --------------------------------

def main():
    # parse args
    args = sys.argv[1:]
    if len(args)>=2 and args[0]=="--join":
        host,port = args[1].split(":")
        client_main(host, int(port))
        return
    if len(args)>=2 and args[0]=="--host":
        port = int(args[1])
        host_main(port)
        return
    # default: offline single player (host logic without networking and without remote player)
    host_main(0)  # port 0 -> binds but not used; single-player works fine

if __name__ == '__main__':
    main()
