# -*- coding: utf-8 -*-
"""
mp_stubs.py - Faux peripheriques MicroPython pour tester le firmware sur PC.

Ce module remplace machine, framebuf, usb.device et time par des versions
simulees, ce qui permet d'EXECUTER REELLEMENT le code du macropad sur un
ordinateur, sans ESP32. Il ne fait pas partie du firmware embarque : ne
copiez pas tools/ sur la carte.
"""

import sys
import types


# =====================================================================
# Horloge virtuelle
# =====================================================================
class StopSimulation(Exception):
    """Levee pour interrompre proprement une boucle infinie simulee."""


class VirtualClock:
    def __init__(self):
        self.now = 0
        self.steps = 0
        self.max_steps = None

    def reset(self):
        self.now = 0
        self.steps = 0
        self.max_steps = None

    def advance(self, ms):
        self.now += ms


CLOCK = VirtualClock()

_TICKS_PERIOD = 1 << 30
_TICKS_HALF = _TICKS_PERIOD // 2


def _ticks_ms():
    return CLOCK.now % _TICKS_PERIOD


def _ticks_add(ticks, delta):
    return (ticks + delta) % _TICKS_PERIOD


def _ticks_diff(a, b):
    """Reproduit la semantique MicroPython : difference signee circulaire."""
    diff = (a - b) % _TICKS_PERIOD
    if diff >= _TICKS_HALF:
        diff -= _TICKS_PERIOD
    return diff


def _sleep_ms(ms):
    CLOCK.advance(ms)
    CLOCK.steps += 1
    if CLOCK.max_steps is not None and CLOCK.steps > CLOCK.max_steps:
        raise StopSimulation()


def _sleep(seconds):
    _sleep_ms(int(seconds * 1000))


def make_time_module():
    module = types.ModuleType("time")
    module.ticks_ms = _ticks_ms
    module.ticks_us = lambda: _ticks_ms() * 1000
    module.ticks_add = _ticks_add
    module.ticks_diff = _ticks_diff
    module.sleep_ms = _sleep_ms
    module.sleep_us = lambda us: _sleep_ms(us // 1000)
    module.sleep = _sleep
    module.time = lambda: CLOCK.now // 1000
    return module


# =====================================================================
# machine : Pin, I2C, PWM, USBDevice
# =====================================================================
class PinScript:
    """Scenario d'etats des broches en fonction du temps virtuel."""

    def __init__(self):
        self.events = []          # (instant_ms, gpio, niveau)
        self.defaults = {}

    def reset(self):
        self.events = []
        self.defaults = {}

    def set_default(self, gpio, level):
        self.defaults[gpio] = level

    def schedule(self, at_ms, gpio, level):
        self.events.append((at_ms, gpio, level))

    def press(self, at_ms, gpio, duration_ms, active_level=0, bounces=0):
        """Appui realiste : rebonds puis niveau stable, puis relachement."""
        idle = 1 - active_level
        moment = at_ms
        for _ in range(bounces):
            self.schedule(moment, gpio, active_level)
            self.schedule(moment + 1, gpio, idle)
            moment += 2
        self.schedule(moment, gpio, active_level)
        self.schedule(at_ms + duration_ms, gpio, idle)

    def level(self, gpio, now):
        level = self.defaults.get(gpio, 1)
        best = -1
        for moment, pin, value in self.events:
            if pin == gpio and moment <= now and moment >= best:
                best = moment
                level = value
        return level


SCRIPT = PinScript()


class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    PULL_DOWN = 3
    OPEN_DRAIN = 4

    instances = {}

    def __init__(self, gpio, mode=None, pull=None):
        self.gpio = gpio
        self.mode = mode
        self.pull = pull
        self._out = 0
        if gpio not in SCRIPT.defaults:
            SCRIPT.set_default(gpio, 1 if pull == Pin.PULL_UP else 0)
        Pin.instances[gpio] = self

    def value(self, *args):
        if args:
            self._out = args[0]
            return None
        return SCRIPT.level(self.gpio, CLOCK.now)

    def __repr__(self):
        return "Pin(%d)" % self.gpio


class I2C:
    """Bus I2C simule avec un SH1106 a l'adresse 0x3C."""

    def __init__(self, bus, scl=None, sda=None, freq=100000):
        self.bus = bus
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.devices = [0x3C]
        self.command_bytes = 0
        self.data_bytes = 0
        self.transactions = 0

    def scan(self):
        return list(self.devices)

    def writeto(self, address, buffer):
        if address not in self.devices:
            raise OSError(19, "ENODEV")
        self.transactions += 1
        if buffer and buffer[0] == 0x40:
            self.data_bytes += len(buffer) - 1
        else:
            self.command_bytes += len(buffer)
        return len(buffer)

    def writevto(self, address, vector):
        if address not in self.devices:
            raise OSError(19, "ENODEV")
        self.transactions += 1
        total = 0
        for index, part in enumerate(vector):
            total += len(part)
            if index > 0:
                self.data_bytes += len(part)
        return total


class PWM:
    instances = []

    def __init__(self, pin, freq=None, duty_u16=None):
        self.pin = pin
        self._freq = freq or 0
        self._duty = duty_u16 or 0
        self.history = []
        PWM.instances.append(self)

    def freq(self, *args):
        if args:
            self._freq = args[0]
            return None
        return self._freq

    def duty_u16(self, *args):
        if args:
            self._duty = args[0]
            self.history.append((CLOCK.now, args[0]))
            return None
        return self._duty

    def deinit(self):
        self._duty = 0


class USBDevice:
    BUILTIN_NONE = object()
    BUILTIN_DEFAULT = object()


def make_machine_module():
    module = types.ModuleType("machine")
    module.Pin = Pin
    module.I2C = I2C
    module.PWM = PWM
    module.USBDevice = USBDevice
    module.idle = lambda: None
    module.freq = lambda *a: 240000000
    module.reset = lambda: None
    return module


# =====================================================================
# framebuf
# =====================================================================
MONO_VLSB = 0
MONO_HLSB = 3


class FrameBuffer:
    """FrameBuffer monochrome fidele pour MONO_VLSB et MONO_HLSB.

    Compte en plus les ecritures hors ecran (out_of_bounds) : cela permet de
    detecter une mise en page OLED qui deborde des 128x64 pixels.
    """

    def __init__(self, buffer, width, height, format_):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format_
        self.out_of_bounds = 0

    # -- acces pixel ---------------------------------------------------
    def _index_mask(self, x, y):
        if self.format == MONO_VLSB:
            return (y // 8) * self.width + x, 1 << (y & 7)
        stride = (self.width + 7) // 8
        return y * stride + (x // 8), 0x80 >> (x & 7)

    def pixel(self, x, y, colour=None):
        if not (0 <= x < self.width and 0 <= y < self.height):
            self.out_of_bounds += 1
            return 0
        index, mask = self._index_mask(x, y)
        if colour is None:
            return 1 if self.buffer[index] & mask else 0
        if colour:
            self.buffer[index] |= mask
        else:
            self.buffer[index] &= ~mask & 0xFF
        return None

    # -- primitives ----------------------------------------------------
    def fill(self, colour):
        value = 0xFF if colour else 0x00
        for i in range(len(self.buffer)):
            self.buffer[i] = value

    def fill_rect(self, x, y, width, height, colour):
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            self.out_of_bounds += 1
        for dy in range(height):
            for dx in range(width):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    index, mask = self._index_mask(px, py)
                    if colour:
                        self.buffer[index] |= mask
                    else:
                        self.buffer[index] &= ~mask & 0xFF

    def rect(self, x, y, width, height, colour):
        self.hline(x, y, width, colour)
        self.hline(x, y + height - 1, width, colour)
        self.vline(x, y, height, colour)
        self.vline(x + width - 1, y, height, colour)

    def hline(self, x, y, width, colour):
        self.fill_rect(x, y, width, 1, colour)

    def vline(self, x, y, height, colour):
        self.fill_rect(x, y, 1, height, colour)

    def text(self, string, x, y, colour=1):
        """Police 8x8 simulee : motif deterministe, geometrie exacte."""
        if y < 0 or y + 8 > self.height or x < 0:
            self.out_of_bounds += 1
        if x + 8 * len(string) > self.width:
            self.out_of_bounds += 1
        for position, char in enumerate(string):
            base = x + position * 8
            for row in range(8):
                for col in range(7):      # 7 colonnes + 1 d'espacement
                    if (row + col + ord(char)) % 3 == 0:
                        px, py = base + col, y + row
                        if 0 <= px < self.width and 0 <= py < self.height:
                            index, mask = self._index_mask(px, py)
                            if colour:
                                self.buffer[index] |= mask
                            else:
                                self.buffer[index] &= ~mask & 0xFF


def make_framebuf_module():
    module = types.ModuleType("framebuf")
    module.FrameBuffer = FrameBuffer
    module.MONO_VLSB = MONO_VLSB
    module.MONO_HLSB = MONO_HLSB
    return module


# =====================================================================
# usb.device / usb.device.keyboard
# =====================================================================
class FakeKeyboardInterface:
    """Reproduit le contrat de usb.device.keyboard.KeyboardInterface."""

    KEY_REPORT_LEN = 8

    def __init__(self):
        self.reports = []          # historique des rapports HID emis
        self._open = False
        self.busy_until = 0

    def is_open(self):
        return self._open

    def open_interface(self):
        self._open = True

    def send_keys(self, down_keys, timeout_ms=100):
        if not self._open:
            return False
        if CLOCK.now < self.busy_until:
            return False
        report = bytearray(self.KEY_REPORT_LEN)
        index = 2
        for key in down_keys:
            if key < 0:
                report[0] |= -key
            elif index < self.KEY_REPORT_LEN:
                report[index] = key
                index += 1
        self.reports.append((CLOCK.now, bytes(report)))
        return True


class FakeUSBDeviceSingleton:
    def __init__(self):
        self.interfaces = ()
        self.kwargs = {}
        self.is_active = False
        self.init_count = 0

    def init(self, *itfs, **kwargs):
        self.interfaces = itfs
        self.kwargs = kwargs
        self.is_active = True
        self.init_count += 1
        for itf in itfs:
            if hasattr(itf, "open_interface"):
                itf.open_interface()

    def active(self, *args):
        if args:
            self.is_active = args[0]
        return self.is_active


USB_SINGLETON = FakeUSBDeviceSingleton()


def make_usb_modules():
    usb_pkg = types.ModuleType("usb")
    usb_device = types.ModuleType("usb.device")
    usb_device.get = lambda: USB_SINGLETON
    usb_device_keyboard = types.ModuleType("usb.device.keyboard")
    usb_device_keyboard.KeyboardInterface = FakeKeyboardInterface

    class KeyCode:
        pass

    usb_device_keyboard.KeyCode = KeyCode
    usb_pkg.device = usb_device
    usb_device.keyboard = usb_device_keyboard
    return {
        "usb": usb_pkg,
        "usb.device": usb_device,
        "usb.device.keyboard": usb_device_keyboard,
    }


# =====================================================================
def install(with_usb=True):
    """Installe tous les faux modules dans sys.modules."""
    CLOCK.reset()
    SCRIPT.reset()
    Pin.instances = {}
    PWM.instances = []
    sys.modules["time"] = make_time_module()
    sys.modules["machine"] = make_machine_module()
    sys.modules["framebuf"] = make_framebuf_module()
    if with_usb:
        sys.modules.update(make_usb_modules())
    else:
        for name in ("usb", "usb.device", "usb.device.keyboard"):
            sys.modules.pop(name, None)
    return CLOCK, SCRIPT
