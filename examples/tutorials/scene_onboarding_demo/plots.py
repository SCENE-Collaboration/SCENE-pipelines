"""Plots of a recording, drawn from the database; ``arena_image`` also opens the video."""

from __future__ import annotations

import cv2
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle

from scene_onboarding_demo.layout import DATA
from scene_onboarding_demo.schemas.behavior import MOVING_CM_S, Arena, Recording, Trajectory


def arena_image(key, *, frame: int = 0, pixels_per_cm: int = 10) -> np.ndarray:
    """A frame of the recording's video, warped to a top-down view of the arena."""
    video, width, depth = (Recording * Arena & key).fetch1("video_path", "width_cm", "depth_cm")
    capture = cv2.VideoCapture(str(DATA / video))
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = capture.read()
    if not ok:
        raise FileNotFoundError(video)
    scale = np.diag([pixels_per_cm, pixels_per_cm, 1]).astype(np.float64)
    size = (round(width * pixels_per_cm), round(depth * pixels_per_cm))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.warpPerspective(gray, scale @ Recording().pixels_to_cm(key), size)


def _arena_axes(ax, width, depth, title):
    """Arena outline, its central quarter dashed, in camera orientation (y down)."""
    ax.add_patch(Rectangle((0, 0), width, depth, fill=False, lw=1.5))
    center = Rectangle((width / 4, depth / 4), width / 2, depth / 2, fill=False, lw=0.8, ls="--")
    center.set_edgecolor("0.5")
    ax.add_patch(center)
    ax.set_xlim(-1, width + 1)
    ax.set_ylim(depth + 1, -1)
    ax.set_aspect("equal")
    ax.set_xlabel("cm")
    ax.set_title(title, fontsize=10)


def plot_path(ax, key, *, background: bool = True, vmax: float = 40, colorbar: bool = True):
    """The trajectory in the arena, coloured by speed; on the warped video frame if asked."""
    x, y, speed = (Trajectory & key).fetch1("x_cm", "y_cm", "speed_cm_s")
    width, depth = (Recording * Arena & key).fetch1("width_cm", "depth_cm")
    if background:
        ax.imshow(arena_image(key), extent=(0, width, depth, 0), cmap="gray", alpha=0.6)
    points = np.column_stack([x, y])
    segments = np.stack([points[:-1], points[1:]], axis=1)
    lines = LineCollection(segments, cmap="viridis", norm=plt.Normalize(0, vmax), lw=1.6)
    lines.set_array(speed[1:])
    ax.add_collection(lines)
    tracked = np.flatnonzero(~np.isnan(x))
    ax.plot(x[tracked[0]], y[tracked[0]], "o", mfc="white", mec="black", ms=7, label="start")
    ax.plot(x[tracked[-1]], y[tracked[-1]], "s", mfc="black", mec="white", ms=7, label="end")
    _arena_axes(ax, width, depth, "path, coloured by speed")
    ax.legend(loc="lower right", fontsize=7)
    if colorbar:
        ax.figure.colorbar(lines, ax=ax, shrink=0.75, label="speed (cm/s)")
    return lines


def plot_recording(key):
    """Three panels: path on the arena, speed over time, occupancy."""
    t = Recording().times(key)
    x, y, speed = (Trajectory & key).fetch1("x_cm", "y_cm", "speed_cm_s")
    width, depth = (Recording * Arena & key).fetch1("width_cm", "depth_cm")

    fig, (ax_path, ax_speed, ax_occ) = plt.subplots(
        1, 3, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1.15, 1.5, 1]}
    )
    plot_path(ax_path, key)

    ax_speed.plot(t, speed, lw=0.8, color="0.2")
    moving = speed > MOVING_CM_S
    label = f"moving (> {MOVING_CM_S:g} cm/s)"
    ax_speed.fill_between(
        t, 0, np.nanmax(speed), where=moving, color="tab:green", alpha=0.15, lw=0, label=label
    )
    ax_speed.set_xlabel("time (s)")
    ax_speed.set_ylabel("speed (cm/s)")
    ax_speed.set_title("speed", fontsize=10)
    ax_speed.legend(fontsize=7, loc="upper right")

    tracked = ~np.isnan(x)
    bins = [np.linspace(0, width, 14), np.linspace(0, depth, 14)]  # 4 cm squares
    occupancy, _, _ = np.histogram2d(x[tracked], y[tracked], bins=bins)
    image = ax_occ.imshow(
        occupancy.T * np.median(np.diff(t)), extent=(0, width, depth, 0), cmap="magma"
    )
    _arena_axes(ax_occ, width, depth, "time spent per 4 cm square")
    fig.colorbar(image, ax=ax_occ, shrink=0.75, label="s")
    fig.tight_layout()
    return fig
