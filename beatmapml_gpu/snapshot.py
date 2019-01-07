from slider import Beatmap
from slider.beatmap import Circle, Slider
from slider.mod import ar_to_ms
import numpy as np
import math
import threading
import heapq
import itertools

from .gl_backend import GLBackend
from .parameter_convert import calc_dimension
from .slider_process import linearize


def make_snapshots(beatmap: Beatmap,
                   target_width: int,
                   capture_rate: int) -> np.ndarray:
    """Make snapshots of a beatmap
    Args:
        beatmap (Beatmap): The beatmap to process.
        target_width (int): The pixel width of desired output.
        capture_rate (int): The capture rate of the snapshots in Hz
    Returns:
        Snapshots of the beatmap. A numpy array of size
        target_width x floor(target_width * 16 / 9)
        x 2 x (length_of_beatmap x capture_rate)
    """
    result = SnapshotThread.create_buffer(beatmap,
                                          target_width,
                                          capture_rate)
    processor = SnapshotThread(beatmap, target_width, capture_rate, result)
    processor.start()
    processor.join()
    return result


class SnapshotThread(threading.Thread):
    def __init__(self, beatmap, target_width, capture_rate, result):
        super().__init__()
        self._beatmap = beatmap
        self._target_width = target_width
        self._interval = 1000 / capture_rate
        self._lookahead = ar_to_ms(self._beatmap.approach_rate)
        self._result = result

    def run(self):
        gl_backend = GLBackend(
            self._target_width, self._beatmap.circle_size, self._lookahead)

        self._hitcircles = [
            o for o in self._beatmap.hit_objects if isinstance(o, Circle)]
        for circle in self._hitcircles:
            circle.time_ms = circle.time.total_seconds() * 1000
        self._hitcircles = sorted(
            self._hitcircles, key=lambda circle: circle.time_ms)

        self._sliders = [
            o for o in self._beatmap.hit_objects if isinstance(o, Slider)]
        for slider in self._sliders:
            slider.time_ms = slider.time.total_seconds() * 1000
            slider.end_ms = slider.end_time.total_seconds() * 1000
            slider.total_time = slider.end_ms - slider.time_ms
            slider.linearization = linearize(slider.curve,
                                             slider.total_time / slider.repeat)
        self._sliders = sorted(
            self._sliders, key=lambda slider: slider.time_ms)

        gl_backend.equip_circles(self._hitcircles)
        self.make_snapshots(gl_backend)
        gl_backend.destroy()

    def make_snapshots(self, gl_backend):
        circle_start = 0
        circle_end = 0

        slider_start = 0
        slider_counter = itertools.count()
        slider_pool = []

        num_slice = self._result.shape[0]

        for snapshot_idx in range(num_slice):
            tick = snapshot_idx * self._interval

            circle_start, circle_end = self.update_circle_pool(
                tick, circle_start, circle_end)

            slider_start = self.update_slider_pool(
                tick, slider_start, slider_pool, gl_backend, slider_counter)

            if circle_end > circle_start or len(slider_pool) > 0:
                gl_backend.setup()
                if circle_end > circle_start:
                    gl_backend.render_circles(tick, circle_start, circle_end)

                if len(slider_pool) > 0:
                    gl_backend.prepare_sliders(tick)
                    for _, _, slider in slider_pool:
                        gl_backend.render_slider(slider)
                self._result[snapshot_idx] = gl_backend.calc_avg()

    def update_circle_pool(self, tick, start, end):
        while (end < len(self._hitcircles) and
               self._hitcircles[end].time_ms <
               tick + self._lookahead):
            end += 1

        while (end > start and
               self._hitcircles[start].time_ms <
               tick):
            start += 1

        return start, end

    def update_slider_pool(self,
                           tick,
                           start,
                           slider_pool,
                           gl_backend,
                           counter):
        joined_sliders = []
        retired_sliders = []
        while (start < len(self._sliders) and
               self._sliders[start].time_ms <
               tick + self._lookahead):
            slider = self._sliders[start]
            heapq.heappush(slider_pool, (slider.end_ms, next(counter), slider))
            joined_sliders.append(slider)
            start += 1

        while len(slider_pool) > 0 and slider_pool[0][0] < tick:
            _, _, slider = heapq.heappop(slider_pool)
            retired_sliders.append(slider)

        if len(joined_sliders) > 0:
            gl_backend.equip_sliders(joined_sliders)

        if len(retired_sliders) > 0:
            gl_backend.unequip_sliders(retired_sliders)

        return start

    @staticmethod
    def create_buffer(beatmap, target_width, capture_rate):
        (w, h), _ = calc_dimension(target_width)
        end_time = max(beatmap.hit_objects,
                       key=lambda o: (o.end_time
                                      if isinstance(o, Slider) else o.time))
        num_slice = math.floor(
            end_time.time.total_seconds() * capture_rate) + 2
        return np.zeros((num_slice, w, h))
