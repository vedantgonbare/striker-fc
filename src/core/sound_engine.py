"""
sound_engine.py — Procedural sound generation using numpy + pygame.mixer.
No external audio files needed — every sound is synthesised at runtime.
Gracefully disabled if audio hardware isn't available.

Sounds:
  kick        — short thud/thwack
  pass        — softer kick
  goal        — triumphant rising chord
  whistle     — referee whistle
  crowd_roar  — crowd eruption burst
  crowd_ambient — continuous murmur (looping)
  ui_hover    — soft tick
  ui_select   — clean click
  bounce      — ball hitting wall
"""

import pygame
import numpy as np

SAMPLE_RATE = 44100
_AUDIO_OK   = False   # set True after successful mixer init


def _init_audio():
    global _AUDIO_OK
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.init()
        _AUDIO_OK = True
    except Exception:
        _AUDIO_OK = False


def _make_buffer(arr: np.ndarray):
    arr    = np.clip(arr, -1.0, 1.0)
    stereo = np.column_stack([arr, arr])
    pcm    = (stereo * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(pcm)


def _sine(freq, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _noise(duration):
    return np.random.uniform(-1, 1, int(SAMPLE_RATE * duration)).astype(np.float32)


def _envelope(arr, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    n      = len(arr)
    a_s    = int(attack  * SAMPLE_RATE)
    d_s    = int(decay   * SAMPLE_RATE)
    r_s    = int(release * SAMPLE_RATE)
    s_s    = max(0, n - a_s - d_s - r_s)
    env    = np.concatenate([
        np.linspace(0, 1,       a_s),
        np.linspace(1, sustain, d_s),
        np.full(s_s,   sustain),
        np.linspace(sustain, 0, r_s),
    ])
    env = env[:n]
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return arr * env


def _lowpass(arr, cutoff=500):
    rc  = 1.0 / (2 * np.pi * cutoff)
    dt  = 1.0 / SAMPLE_RATE
    a   = dt / (rc + dt)
    out = np.zeros_like(arr)
    v   = 0.0
    for i, x in enumerate(arr):
        v      = v + a * (x - v)
        out[i] = v
    return out


# ── Sound builders ─────────────────────────────────────────────────────────────

def _build_kick():
    dur = 0.18
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    raw = _noise(dur) * 0.6 + _sine(80, dur) * 0.7
    return _make_buffer((raw * np.exp(-t * 28)).astype(np.float32))


def _build_pass():
    dur = 0.12
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    raw = _noise(dur) * 0.45 + _sine(110, dur) * 0.5
    return _make_buffer((raw * np.exp(-t * 38)).astype(np.float32))


def _build_bounce():
    dur = 0.10
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    raw = _sine(220, dur) * 0.5 + _noise(dur) * 0.3
    return _make_buffer((raw * np.exp(-t * 45)).astype(np.float32))


def _build_whistle():
    dur = 0.55
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    freq= 2200 + 80 * np.sin(2 * np.pi * 6 * t)
    raw = np.sin(2 * np.pi * freq * t).astype(np.float32)
    env = _envelope(np.ones(len(raw)), attack=0.02, decay=0.05, sustain=0.9, release=0.15)
    return _make_buffer(raw * env)


def _build_goal():
    dur   = 1.8
    n     = int(SAMPLE_RATE * dur)
    t     = np.linspace(0, dur, n, endpoint=False)
    freqs = [523.25, 659.25, 783.99, 1046.5]
    raw   = np.zeros(n, dtype=np.float32)
    for i, f in enumerate(freqs):
        delay     = int(i * 0.12 * SAMPLE_RATE)
        wave      = np.sin(2 * np.pi * f * t).astype(np.float32) * 0.25
        wave[:delay] = 0
        raw      += wave
    return _make_buffer(raw * _envelope(np.ones(n), 0.05, 0.2, 0.8, 0.5))


def _build_crowd_roar():
    dur = 2.0
    raw = _lowpass(_noise(dur), cutoff=600)
    n   = len(raw)
    t   = np.linspace(0, dur, n)
    env = np.where(t < 0.3, t / 0.3, np.exp(-(t - 0.3) * 0.8))
    return _make_buffer((raw * env * 0.55).astype(np.float32))


def _build_crowd_ambient():
    dur = 4.0
    raw = _lowpass(_noise(dur), cutoff=350)
    n   = len(raw)
    t   = np.linspace(0, 2 * np.pi, n)
    env = 0.12 + 0.04 * np.sin(t)
    return _make_buffer((raw * env).astype(np.float32))


def _build_ui_hover():
    dur = 0.06
    raw = _sine(880, dur) * 0.3
    n   = len(raw)
    return _make_buffer((raw * np.exp(-np.linspace(0, 20, n))).astype(np.float32))


def _build_ui_select():
    dur = 0.10
    raw = _sine(1100, dur) * 0.35 + _sine(1400, dur) * 0.2
    n   = len(raw)
    return _make_buffer((raw * np.exp(-np.linspace(0, 18, n))).astype(np.float32))


# ── Null sound (silent fallback) ──────────────────────────────────────────────
class _NullSound:
    def play(self, *a, **kw): pass
    def set_volume(self, v): pass


class _NullChannel:
    def play(self, *a, **kw): pass
    def stop(self): pass


# ── Sound Engine ──────────────────────────────────────────────────────────────

class SoundEngine:
    _instance = None

    def __init__(self):
        _init_audio()
        self._ok = _AUDIO_OK
        self._sounds   = {}
        self._volumes  = {
            "kick": 0.90, "pass": 0.70, "bounce": 0.45,
            "whistle": 0.85, "goal": 0.95,
            "crowd_roar": 0.75, "crowd_ambient": 0.30,
            "ui_hover": 0.40, "ui_select": 0.60,
        }

        if self._ok:
            try:
                pygame.mixer.set_num_channels(16)
                builders = {
                    "kick":          _build_kick,
                    "pass":          _build_pass,
                    "bounce":        _build_bounce,
                    "whistle":       _build_whistle,
                    "goal":          _build_goal,
                    "crowd_roar":    _build_crowd_roar,
                    "crowd_ambient": _build_crowd_ambient,
                    "ui_hover":      _build_ui_hover,
                    "ui_select":     _build_ui_select,
                }
                for name, fn in builders.items():
                    try:
                        snd = fn()
                        snd.set_volume(self._volumes.get(name, 0.7))
                        self._sounds[name] = snd
                    except Exception:
                        self._sounds[name] = _NullSound()
                self._ambient_ch = pygame.mixer.Channel(0)
            except Exception:
                self._ok = False

        if not self._ok:
            for name in self._volumes:
                self._sounds[name] = _NullSound()
            self._ambient_ch = _NullChannel()

        self._ambient_playing = False

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Force re-init (call after new pygame.mixer.init)."""
        cls._instance = None

    def play(self, name: str, channel: int = -1):
        snd = self._sounds.get(name, _NullSound())
        try:
            if self._ok and channel >= 0:
                pygame.mixer.Channel(channel).play(snd)
            else:
                snd.play()
        except Exception:
            pass

    def start_ambient(self):
        if not self._ambient_playing:
            try:
                self._ambient_ch.play(self._sounds["crowd_ambient"], loops=-1)
                self._ambient_playing = True
            except Exception:
                pass

    def stop_ambient(self):
        try:
            self._ambient_ch.stop()
        except Exception:
            pass
        self._ambient_playing = False

    def goal_sequence(self):
        self.play("whistle",    channel=1)
        self.play("crowd_roar", channel=2)
        self.play("goal",       channel=3)

    def kickoff_whistle(self):
        self.play("whistle", channel=1)