"""Generates JalSetu's background art procedurally (no third-party images).

    python tools/make_art.py            # writes everything into frontend/public/img/

Outputs
  hero.jpg       sky, clouds and a 3-D rendered snowy mountain range (hero + page banners)
  snow.jpg       paler, misty variant for light sections
  underwater.jpg blue water with droplets (request form + footer)
  wave.png       water-surface strip with spray (hero -> water transition)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "public", "img")


# ---------------------------------------------------------------- noise helpers
def _resize(a, w, h):
    return np.asarray(Image.fromarray(a.astype(np.float32)).resize((w, h), Image.BICUBIC), dtype=np.float32)


def value_noise(h, w, cells_y, cells_x, rng):
    g = rng.random((cells_y + 3, cells_x + 3)).astype(np.float32)
    big = _resize(g, int(w * (cells_x + 3) / cells_x), int(h * (cells_y + 3) / cells_y))
    oy, ox = (big.shape[0] - h) // 2, (big.shape[1] - w) // 2
    return big[oy:oy + h, ox:ox + w]


def fbm(h, w, base, octaves, rng, persistence=0.5, ridged=False, aspect=1.0):
    total, amp, norm, weight = np.zeros((h, w), np.float32), 1.0, 0.0, np.ones((h, w), np.float32)
    for o in range(octaves):
        cy = max(1, int(base * 2 ** o))
        cx = max(1, int(base * 2 ** o * aspect))
        n = value_noise(h, w, cy, cx, rng)
        if ridged:
            n = 1.0 - np.abs(n * 2 - 1)
            n = n * n * weight
            weight = np.clip(n * 1.6, 0, 1)
        total += n * amp
        norm += amp
        amp *= persistence
    return total / norm


def blur(a, k):
    h, w = a.shape
    return _resize(_resize(a, max(2, w // k), max(2, h // k)), w, h)


def gauss(a, sigma):
    r = int(sigma * 3)
    k = np.exp(-(np.arange(-r, r + 1) ** 2) / (2 * sigma * sigma)); k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 1, a).astype(np.float32)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = t[..., None] if np.ndim(t) == np.ndim(a) - 1 else t
    return a * (1 - t) + b * t


def save_jpg(rgb, name, size=None, q=86):
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    if size:
        img = img.resize(size, Image.LANCZOS)
    img.save(os.path.join(OUT, name), quality=q, optimize=True, progressive=True)
    print("wrote", name, img.size)


# ---------------------------------------------------------------- mountains
def terrain(seed, D=1100, X=2400, peaks=()):
    rng = np.random.default_rng(seed)
    warp = fbm(D, X, 3, 4, rng) - 0.5
    r = fbm(D, X, 5, 8, rng, persistence=0.52, ridged=True, aspect=2.2)
    # domain-warp the ridged field so ridges are not grid aligned
    yy, xx = np.mgrid[0:D, 0:X].astype(np.float32)
    wy = np.clip(yy + warp * 90, 0, D - 1).astype(int)
    wx = np.clip(xx + (fbm(D, X, 3, 4, rng) - .5) * 160, 0, X - 1).astype(int)
    r = blur(r[wy, wx], 2) * 0.5 + r[wy, wx] * 0.5
    depth = yy / D
    cx = (xx - X / 2) / (X / 2)
    env = 0.08 + 0.92 * smooth(0.05, 0.75, depth)          # low near the camera, high far away
    env *= 0.45 + 0.55 * smooth(0.0, 0.55, np.abs(cx) + depth * 0.25)  # centre valley
    for (px, py, rad, amp) in peaks:                          # hand-placed massifs
        env += amp * np.exp(-(((xx - px * X) / (rad * X)) ** 2 + ((yy - py * D) / (rad * D * 1.3)) ** 2))
    h = (np.clip(r, 0, 1) ** 1.5) * env * 210
    h += (fbm(D, X, 2, 3, rng) - .5) * 30 * (1 - depth)     # gentle rolling foreground
    near = smooth(0.0, 0.45, depth)                          # soften fine detail close to the camera
    h = h * near + blur(h, 6) * (1 - near)
    return h.astype(np.float32), rng


def shade_terrain(H, rng, sun=(-0.62, -0.30, 0.72)):
    gy, gx = np.gradient(H)
    n = np.stack([-gx, -gy, np.ones_like(H) * 1.2], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array(sun, np.float32); L /= np.linalg.norm(L)
    diff = np.clip((n * L).sum(-1), 0, 1)
    nz = n[..., 2]
    cav = np.clip((H - blur(H, 10)) / 18, -1, 1)              # + ridge, - gully
    D, X = H.shape
    patch = fbm(D, X, 24, 5, rng)
    snow = smooth(0.50, 0.70, nz + (patch - .5) * 0.35 + np.clip(cav, -.3, .3) * .25)
    snow_lit = np.array([250, 252, 255], np.float32)
    snow_shd = np.array([128, 160, 202], np.float32)
    rock_lit = np.array([138, 150, 170], np.float32)
    rock_shd = np.array([58, 74, 104], np.float32)
    d = (diff ** 0.8)[..., None]
    snowc = snow_shd * (1 - d) + snow_lit * d
    rockc = rock_shd * (1 - d) + rock_lit * d
    rockc *= (0.75 + 0.5 * patch[..., None])
    col = mix(rockc, snowc, snow)
    col *= (0.88 + 0.12 * np.clip(cav * 2 + 1, 0, 1))[..., None]
    return col


def render_scene(H, C, W, Ht, cam_h, horizon, fov_deg=64, haze=(208, 224, 242), haze_k=700, haze_max=0.9):
    D, X = H.shape
    f = (W / 2) / math.tan(math.radians(fov_deg / 2))
    steps = []
    d = 1.5
    while d < D - 2:
        steps.append(d)
        d += max(0.2, d * 0.0016)
    ds = np.array(steps, np.float32)
    S = len(ds)
    sx = (np.arange(W, dtype=np.float32) - W / 2) / f      # world x per unit depth
    wx = X / 2 + sx[None, :] * ds[:, None]                 # S x W
    wy = np.broadcast_to(ds[:, None], wx.shape)
    valid = (wx >= 0) & (wx < X - 1)
    wxc = np.clip(wx, 0, X - 1.001)
    x0 = wxc.astype(int); fx = wxc - x0
    y0 = wy.astype(int); fy = wy - y0
    def bil(A):
        a = A[y0, x0]; b = A[y0, x0 + 1]; c = A[y0 + 1, x0]; e = A[y0 + 1, x0 + 1]
        return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + e * fx) * fy
    h = bil(H)
    h = np.where(valid, h, -1e4)
    sy = horizon + (cam_h - h) * f / ds[:, None]           # projected screen row
    ymin = np.minimum.accumulate(sy, axis=0)               # occlusion front -> back
    cols = np.stack([bil(C[..., i]) for i in range(3)], -1)
    Cb = np.stack([gauss(C[..., i], 1.0) for i in range(3)], -1)        # light mip-map for distant rows
    far = smooth(200, 900, ds)[:, None, None] * 0.6
    cols = cols * (1 - far) + np.stack([bil(Cb[..., i]) for i in range(3)], -1) * far
    t = (1 - np.exp(-ds / haze_k)) * haze_max
    cols = cols * (1 - t[:, None, None]) + np.array(haze, np.float32) * t[:, None, None]
    img = np.zeros((Ht, W, 3), np.float32)
    mask = np.zeros((Ht, W), bool)
    rows = np.arange(Ht, dtype=np.float32)
    for c in range(W):
        col = ymin[:, c]
        idx = np.searchsorted(-col, -rows, side="left")    # first step whose top <= row
        ok = idx < S
        img[ok, c] = cols[idx[ok], c]
        mask[ok, c] = True
    return img, mask


def sky(W, Ht, rng, top=(30, 92, 178), mid=(98, 156, 222), low=(214, 230, 247), mid_at=0.42):
    y = np.linspace(0, 1, Ht, dtype=np.float32)[:, None]
    top, mid, low = (np.array(c, np.float32) for c in (top, mid, low))
    a = smooth(0, mid_at, y)[..., None]
    b = smooth(mid_at, 1.0, y)[..., None]
    g = top * (1 - a) + mid * a
    g = g * (1 - b) + low * b
    return np.broadcast_to(g, (Ht, W, 3)).copy()


def clouds(W, Ht, rng, cover, base=3, soft=0.18):
    n = fbm(Ht, W, base, 7, rng, persistence=0.55, aspect=W / Ht * 0.55)
    dens = smooth(1 - cover, 1 - cover + soft, n)
    # light from the upper-left: compare density with a shifted copy for self-shadowing
    sh = np.roll(np.roll(n, 10, 0), 8, 1)
    light = np.clip(0.62 + (n - sh) * 6, 0.35, 1.0)
    white = np.array([255, 255, 255], np.float32)
    grey = np.array([170, 190, 216], np.float32)
    col = grey * (1 - light[..., None]) + white * light[..., None]
    return col, dens


def make_mountains():
    W, Ht = 2880, 1620                                    # rendered 1.5x, saved at 1920x1080
    H, rng = terrain(7, peaks=[(0.20, 0.62, 0.10, 0.85), (0.80, 0.55, 0.11, 0.95), (0.62, 0.80, 0.09, .7), (0.36, 0.86, 0.08, .55)])
    C = shade_terrain(H, rng)
    img, mask = render_scene(gauss(H, 1.3), C, W, Ht, cam_h=70, horizon=Ht * 0.60, haze=(214, 230, 248), haze_k=1400, haze_max=.6)
    s = sky(W, Ht, rng)
    cc, cd = clouds(W, Ht, rng, cover=0.58, soft=0.26)
    yy = np.linspace(0, 1, Ht, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
    centre = np.exp(-(xx / 0.55) ** 2) * np.exp(-((yy - 0.22) / 0.2) ** 2)   # cloud bank behind the headline
    cd = np.clip(cd * (0.6 + 0.4 * smooth(0.0, 0.3, yy)) + centre * 0.55 * smooth(.25, .6, cd + .3), 0, 1)
    cd = cd * (1 - smooth(0.5, 0.66, yy))
    s = mix(s, cc, cd)
    out = np.where(mask[..., None], img, s)
    # low mist drifting over the far peaks
    mc, md = clouds(W, Ht, rng, cover=0.36, base=4)
    band = np.exp(-((yy - 0.52) / 0.09) ** 2)
    out = mix(out, mc * 0.5 + 250 * 0.5, md * band * 0.85)
    # snowfield brightening towards the bottom (where products stand)
    fog = smooth(0.70, 1.0, yy) * 0.55
    out = mix(out, np.array([246, 250, 255], np.float32) * np.ones_like(out), np.broadcast_to(fog, (Ht, W)))
    save_jpg(out, "hero.jpg", (1920, 1080))


def make_snow():
    W, Ht = 2880, 1350
    H, rng = terrain(21, peaks=[(0.25, 0.75, 0.12, 0.8), (0.72, 0.68, 0.12, 0.9), (0.5, 0.9, 0.1, .5)])
    C = shade_terrain(H, rng, sun=(-0.5, -0.45, 0.8))
    img, mask = render_scene(gauss(H, 1.3), C, W, Ht, cam_h=75, horizon=Ht * 0.62, haze=(232, 240, 250), haze_k=900, haze_max=.8)
    s = sky(W, Ht, rng, top=(206, 222, 240), mid=(226, 236, 248), low=(240, 245, 252))
    cc, cd = clouds(W, Ht, rng, cover=0.4)
    s = mix(s, cc * .3 + 250 * .7, cd * .8)
    out = np.where(mask[..., None], img, s)
    yy = np.linspace(0, 1, Ht, dtype=np.float32)[:, None]
    # wash everything towards white so text stays readable; strongest at top and bottom
    wash = 0.30 + 0.70 * smooth(0.60, 0.97, yy) + 0.25 * (1 - smooth(0.0, 0.3, yy))
    paper = np.broadcast_to(np.array([251, 253, 255], np.float32), out.shape)
    out = mix(out, paper, np.broadcast_to(np.clip(wash, 0, 1), (Ht, W)))
    save_jpg(out, "snow.jpg", (1920, 900))


# ---------------------------------------------------------------- water
def _droplet(img, cx, cy, rx, ry, strength=1.0):
    """Shade one water droplet sitting on glass into float RGB `img` (in place)."""
    H, W, _ = img.shape
    x0, x1 = max(0, int(cx - rx - 2)), min(W, int(cx + rx + 3))
    y0, y1 = max(0, int(cy - ry - 2)), min(H, int(cy + ry + 3))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u, v = (xx - cx) / rx, (yy - cy) / ry
    d = np.sqrt(u * u + v * v)
    inside = smooth(1.0, 0.92, d)
    rim = smooth(0.55, 1.0, d)
    delta = (-62 * rim * (0.55 + 0.45 * np.clip(-v + .3, 0, 1))          # dark rim, heavier on top
             + 75 * np.exp(-(u * u / 0.30 + (v - 0.50) ** 2 / 0.05))      # caustic at the bottom
             + 230 * np.exp(-((u + 0.33) ** 2 + (v + 0.42) ** 2) / 0.016)  # specular glint
             + 14)
    tint = np.array([0.80, 0.95, 1.0], np.float32)
    img[y0:y1, x0:x1] += (delta * inside * strength)[..., None] * tint


def water_base(W, Ht, rng, top=(74, 152, 216), bottom=(26, 92, 174)):
    y = np.linspace(0, 1, Ht, dtype=np.float32)[:, None, None]
    base = np.array(top, np.float32) * (1 - y) + np.array(bottom, np.float32) * y
    base = np.broadcast_to(base, (Ht, W, 3)).copy()
    n = fbm(Ht, W, 3, 6, rng, aspect=W / Ht)
    base += ((n - .5) * 46)[..., None]
    # sun rays fanning down from the top centre
    yy, xx = np.mgrid[0:Ht, 0:W].astype(np.float32)
    ang = np.arctan2(xx - W / 2, yy + Ht * 0.35)
    ray = value_noise(1, 900, 1, 90, rng)[0]
    a = np.clip(((ang + 1.6) / 3.2 * 899).astype(int), 0, 899)
    rays = smooth(0.55, 0.9, ray[a]) * np.exp(-yy / (Ht * 0.7))
    base += (rays * 55)[..., None] * np.array([0.8, 0.95, 1], np.float32)
    return base


def make_underwater():
    W, Ht = 1920, 1100
    rng = np.random.default_rng(5)
    img = water_base(W, Ht, rng)
    for _ in range(1100):
        r = 3 + rng.pareto(2.2) * 6
        r = min(r, 30)
        _droplet(img, rng.uniform(0, W), rng.uniform(0, Ht), r * rng.uniform(1.0, 1.25), r * rng.uniform(0.8, 1.0),
                 strength=rng.uniform(0.6, 1.0))
    img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32)
    save_jpg(img, "underwater.jpg", q=84)


def make_wave():
    W, Ht = 1920, 360
    rng = np.random.default_rng(11)
    x = np.arange(W, dtype=np.float32)
    n1 = value_noise(1, W, 1, 40, rng)[0] - .5
    n2 = value_noise(1, W, 1, 160, rng)[0] - .5
    surf = 170 + 16 * np.sin(x / 700 * 6.283 + 1.2) + 9 * np.sin(x / 210 * 6.283) + n1 * 40 + n2 * 14
    crowns = []
    for cx in (140, 520, 960, 1330, 1760):
        cx += rng.uniform(-60, 60); hgt = rng.uniform(40, 95); wid = rng.uniform(50, 120)
        crowns.append((cx, hgt, wid))
        bump = np.exp(-((x - cx) / wid) ** 2) * hgt
        spikes = np.clip(value_noise(1, W, 1, 90, rng)[0] - .3, 0, 1) * 1.6
        surf -= bump * (0.55 + 0.45 * spikes)
    yy = np.arange(Ht, dtype=np.float32)[:, None]
    depth = yy - surf[None, :]                       # >0 below the surface
    top = np.array([176, 220, 246], np.float32); low = np.array([86, 165, 228], np.float32)
    t = smooth(90, Ht * 0.66, yy)[..., None]        # reaches the underwater colour where the sections meet
    col = np.broadcast_to(top * (1 - t) + low * t, (Ht, W, 3)).copy()
    col += (np.exp(-np.clip(depth, 0, None) / 22) * 45)[..., None]   # aerated, bright just under the surface
    streak = fbm(Ht, W, 10, 5, rng, aspect=0.18)    # long horizontal streaks
    col += ((streak - .5) * 90 * np.exp(-np.clip(depth, 0, None) / 90))[..., None]
    crest = np.exp(-((depth - 3) / 4) ** 2)
    col = col * (1 - crest[..., None] * .7) + 255 * crest[..., None] * .7
    alpha = smooth(-1.5, 1.5, depth)
    # mist and spray above the surface
    mist = np.exp(-np.clip(-depth, 0, None) / 18) * 0.35 * (1 - alpha)
    col = np.where((alpha > 0)[..., None], col, 250)
    a = np.clip(alpha + mist, 0, 1)
    img = np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)
    im = Image.fromarray(img, "RGBA")
    dr = ImageDraw.Draw(im, "RGBA")
    for (cx, hgt, wid) in crowns:
        base_y = 170
        for _ in range(int(hgt * 1.2)):
            ox = rng.normal(0, wid * 0.7); oy = -abs(rng.normal(0, hgt * 0.9)) - 10
            r = abs(rng.normal(2.2, 1.6)) + 0.6
            px, py = cx + ox, base_y + oy
            dr.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, int(rng.uniform(140, 235))),
                       outline=(120, 185, 230, 160))
    im.save(os.path.join(OUT, "wave.png"), optimize=True)
    print("wrote wave.png", im.size)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ["mountains", "snow", "underwater", "wave"]
    for name in which:
        fn = globals().get("make_" + name)
        if fn:
            fn()
