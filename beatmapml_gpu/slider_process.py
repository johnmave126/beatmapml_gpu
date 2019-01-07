import numpy as np
from bezier._geometric_intersection import linearization_error
import bezier
import math
import itertools
from slider.curve import *

BEZIER_TOLERANCE = 0.2


def bezier_linearize_helper(curve, eps):
    if linearization_error(curve.nodes) < eps:
        return [curve.nodes.T[-1]]
    curve_left, curve_right = curve.subdivide()
    return (bezier_linearize_helper(curve_left, eps) +
            bezier_linearize_helper(curve_right, eps))


def bezier_linearize(curve):
    points = np.array(curve.points, dtype=np.double)
    bezier_curve = bezier.Curve.from_nodes(points.T)
    return ([points[0]] +
            bezier_linearize_helper(bezier_curve, BEZIER_TOLERANCE))


def perfect_at(curve, t):
    p_x, p_y = curve.points[0]
    c_x, c_y = curve._center
    radians = curve._angle * t

    x_dist = p_x - c_x
    y_dist = p_y - c_y

    cosr = np.cos(radians, dtype=np.float32)
    sinr = np.sin(radians, dtype=np.float32)

    return np.stack(
        [(x_dist * cosr - y_dist * sinr) + c_x,
         (x_dist * sinr + y_dist * cosr) + c_y],
    ).T


def perfect_linearize(curve):
    num_points = math.ceil(curve.req_length / 4)
    return perfect_at(curve, np.linspace(0, 1, num_points))


def linear_linearize(curve):
    return np.array(curve.points, dtype=np.float32)


def multibezier_linearize(curve):
    return list(itertools.chain(bezier_linearize(curve._curves[0]),
                                *(bezier_linearize(c)[1:]
                                  for c in curve._curves[1:])))


def linearize(curve, time_scale):
    if isinstance(curve, Bezier):
        points = np.array(bezier_linearize(curve), dtype=np.float32)
    elif isinstance(curve, Perfect):
        points = perfect_linearize(curve)
    elif isinstance(curve, Linear):
        points = linear_linearize(curve)
    elif isinstance(curve, MultiBezier):
        points = np.array(multibezier_linearize(curve), dtype=np.float32)

    vectors = np.diff(points, axis=0)
    output = np.empty((points.shape[0] + 2, 3), dtype=np.float32)
    output[1:-1, 0:2] = points
    distance = np.linalg.norm(vectors, ord=2, axis=1)
    np.cumsum(distance, out=output[2:-1, 2])
    output[1, 2] = 0
    output[0], output[-1] = output[1], output[-2]
    output[:, 2] *= time_scale / output[-1, 2]
    return output
