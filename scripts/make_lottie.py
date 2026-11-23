"""Generate the two small Lottie animations in assets/lottie (ball bounce, goal burst).

They are hand-built from shapes so the app needs no external animation URLs at runtime.
    python scripts/make_lottie.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "lottie"
LIME = [0.83, 1.0, 0.23, 1]
WHITE = [1, 1, 1, 1]
INK = [0.04, 0.10, 0.07, 1]


def static(value):
    return {"a": 0, "k": value}


def keyframes(*frames, ease=(0.4, 0.6)):
    """frames: (time, value) pairs -> animated property with ease in/out."""
    out = []
    for t, v in frames:
        out.append({"t": t, "s": v if isinstance(v, list) else [v],
                    "i": {"x": [ease[1]], "y": [1]}, "o": {"x": [ease[0]], "y": [0]}})
    return {"a": 1, "k": out}


def transform(**props):
    base = {"p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0), "o": static(100)}
    base.update(props)
    return {"ty": "tr", **base}


def ellipse_group(size, fill=None, stroke=None, width=4):
    items = [{"ty": "el", "p": static([0, 0]), "s": static([size, size]), "d": 1}]
    if stroke:
        items.append({"ty": "st", "c": static(stroke), "o": static(100), "w": static(width), "lc": 2, "lj": 2})
    if fill:
        items.append({"ty": "fl", "c": static(fill), "o": static(100), "r": 1})
    items.append(transform())
    return {"ty": "gr", "it": items}


def layer(index, name, shapes, ks, op):
    return {"ddd": 0, "ind": index, "ty": 4, "nm": name, "sr": 1, "ks": ks, "ao": 0, "shapes": shapes,
            "ip": 0, "op": op, "st": 0, "bm": 0}


def layer_transform(p, s=None, o=None, r=None):
    return {"o": o or static(100), "r": r or static(0), "p": p, "a": static([0, 0, 0]), "s": s or static([100, 100, 100])}


def ball_bounce():
    op = 60
    ball = layer(1, "ball", [ellipse_group(18, fill=INK), ellipse_group(64, fill=WHITE, stroke=INK, width=5)],
                 layer_transform(p=keyframes((0, [120, 50, 0]), (30, [120, 165, 0]), (60, [120, 50, 0]), ease=(0.55, 0.45)),
                                 r=keyframes((0, 0), (60, 360))), op)
    shadow = layer(2, "shadow", [{"ty": "gr", "it": [{"ty": "el", "p": static([0, 0]), "s": static([70, 14]), "d": 1},
                                                    {"ty": "fl", "c": static(LIME), "o": static(45), "r": 1}, transform()]}],
                   layer_transform(p=static([120, 205, 0]),
                                   s=keyframes((0, [50, 50, 100]), (30, [110, 110, 100]), (60, [50, 50, 100]))), op)
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": op, "w": 240, "h": 240, "nm": "ball", "ddd": 0, "assets": [],
            "layers": [ball, shadow]}


def goal_burst():
    op = 75
    layers = []
    for i, delay in enumerate((0, 10, 20)):
        layers.append(layer(i + 1, f"ring{i}", [ellipse_group(200, stroke=LIME, width=10)],
                            layer_transform(p=static([150, 150, 0]),
                                            s=keyframes((delay, [5, 5, 100]), (delay + 40, [140, 140, 100])),
                                            o=keyframes((delay, 100), (delay + 40, 0))), op))
    for i in range(8):
        angle = i * 45
        import math
        dx, dy = math.cos(math.radians(angle)) * 120, math.sin(math.radians(angle)) * 120
        layers.append(layer(10 + i, f"spark{i}", [ellipse_group(18, fill=WHITE if i % 2 else LIME)],
                            layer_transform(p=keyframes((5, [150, 150, 0]), (45, [150 + dx, 150 + dy, 0])),
                                            o=keyframes((5, 100), (45, 100), (60, 0))), op))
    layers.append(layer(30, "ball", [ellipse_group(22, fill=INK), ellipse_group(70, fill=WHITE, stroke=INK, width=5)],
                        layer_transform(p=static([150, 150, 0]),
                                        s=keyframes((0, [0, 0, 100]), (15, [120, 120, 100]), (25, [100, 100, 100])),
                                        r=keyframes((0, 0), (75, 720))), op))
    return {"v": "5.7.4", "fr": 30, "ip": 0, "op": op, "w": 300, "h": 300, "nm": "goal", "ddd": 0, "assets": [],
            "layers": layers}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ball.json").write_text(json.dumps(ball_bounce()))
    (OUT / "goal.json").write_text(json.dumps(goal_burst()))
    print("Wrote", OUT)
