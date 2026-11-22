"""Generates JalSetu's vector illustrations (jar, cooler, van, how-it-works scenes).

    python tools/make_svg.py     # writes into frontend/public/img/
"""
import os, random

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "public", "img")
FONT = "Jost, 'Segoe UI', Helvetica, Arial, sans-serif"


def write(name, svg):
    with open(os.path.join(OUT, name), "w", encoding="utf8") as f:
        f.write(svg.strip() + "\n")
    print("wrote", name)


# ------------------------------------------------------------------ 20-litre jar
def _jar_outline():
    m = lambda p: (300 - p[0], p[1])
    segs = [  # left half, top -> bottom
        ("C", (128, 66), (126, 94), (46, 100), (34, 134)),
        ("C", (34, 134), (29, 145), (29, 152), (30, 160)),
        ("L", (30, 160), (30, 194)),
        ("C", (30, 194), (30, 200), (37, 202), (37, 208)),
        ("C", (37, 208), (37, 214), (30, 216), (30, 222)),
        ("L", (30, 222), (30, 336)),
        ("C", (30, 336), (30, 342), (37, 344), (37, 350)),
        ("C", (37, 350), (37, 356), (30, 358), (30, 364)),
        ("L", (30, 364), (30, 384)),
        ("C", (30, 384), (30, 402), (44, 410), (72, 410)),
        ("L", (72, 410), (150, 410)),
    ]
    f = lambda p: f"{p[0]:g} {p[1]:g}"
    d = "M130 46 L128 66 "
    for s in segs:
        d += (f"C{f(s[2])} {f(s[3])} {f(s[4])} " if s[0] == "C" else f"L{f(s[2])} ")
    for s in reversed(segs):
        if s[0] == "C":
            d += f"C{f(m(s[3]))} {f(m(s[2]))} {f(m(s[1]))} "
        else:
            d += f"L{f(m(s[1]))} "
    return d + "L170 46 Z"


def jar_group(uid="j", label="JalSetu", seed=3):
    rnd = random.Random(seed)
    body = _jar_outline()
    drops = []
    for _ in range(170):
        x, y = rnd.uniform(36, 264), rnd.uniform(110, 404)
        r = rnd.choice([1.6, 2, 2.4, 3, 3.5, 4.5, 6]) * rnd.uniform(.8, 1.2)
        drops.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{r:.1f}" ry="{r * rnd.uniform(.8, 1.05):.1f}" fill="url(#{uid}dg)"/>')
    bars = "".join(f'<rect x="{234 + i * 1.9:.1f}" y="266" width="{rnd.choice([0.8, 1.2, 1.8])}" height="30" fill="#1d3557"/>' for i in range(12))
    return f"""
  <defs>
    <linearGradient id="{uid}body" x1="0" x2="1">
      <stop offset="0" stop-color="#2f78c4"/><stop offset=".16" stop-color="#7fb8e8"/>
      <stop offset=".38" stop-color="#d9eefc"/><stop offset=".55" stop-color="#bfe0f7"/>
      <stop offset=".82" stop-color="#6aa8df"/><stop offset="1" stop-color="#2867b3"/>
    </linearGradient>
    <linearGradient id="{uid}v" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".3" stop-color="#fff" stop-opacity="0"/>
      <stop offset=".85" stop-color="#0d3f80" stop-opacity="0"/><stop offset="1" stop-color="#0d3f80" stop-opacity=".25"/>
    </linearGradient>
    <linearGradient id="{uid}cap" x1="0" x2="1">
      <stop offset="0" stop-color="#0e4fa8"/><stop offset=".35" stop-color="#3f8fe6"/>
      <stop offset=".6" stop-color="#2a74d0"/><stop offset="1" stop-color="#0b3f8c"/>
    </linearGradient>
    <linearGradient id="{uid}lab" x1="0" x2="1">
      <stop offset="0" stop-color="#c7dcef"/><stop offset=".25" stop-color="#ffffff"/>
      <stop offset=".7" stop-color="#f4f9fe"/><stop offset="1" stop-color="#b9d1ea"/>
    </linearGradient>
    <linearGradient id="{uid}sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2a6fc2"/><stop offset="1" stop-color="#bfe0fa"/>
    </linearGradient>
    <radialGradient id="{uid}dg" cx=".35" cy=".3" r=".75">
      <stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".3" stop-color="#fff" stop-opacity=".2"/>
      <stop offset=".75" stop-color="#3b82c9" stop-opacity=".12"/><stop offset="1" stop-color="#174f92" stop-opacity=".55"/>
    </radialGradient>
    <clipPath id="{uid}clip"><path d="{body}"/></clipPath>
    <filter id="{uid}soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>
  </defs>
  <ellipse cx="150" cy="414" rx="128" ry="9" fill="#0b2a55" opacity=".28" filter="url(#{uid}soft)"/>
  <path d="{body}" fill="url(#{uid}body)" opacity=".96"/>
  <path d="{body}" fill="url(#{uid}v)"/>
  <g clip-path="url(#{uid}clip)">
    <path d="M30 238 Q150 252 270 238 L270 320 Q150 334 30 320 Z" fill="url(#{uid}lab)"/>
    <path d="M30 238 Q150 252 270 238" stroke="#1d5fb4" stroke-width="3" fill="none"/>
    <path d="M30 320 Q150 334 270 320" stroke="#1d5fb4" stroke-width="3" fill="none"/>
    <g transform="translate(0 4)">
      <path d="M58 300 L80 266 L90 280 L104 258 L128 300 Z" fill="url(#{uid}sky)"/>
      <path d="M80 266 L86 275 L80 273 L75 274 Z M104 258 L111 270 L104 267 L98 269 Z" fill="#fff"/>
      <path d="M93 250 C93 250 86 259 86 264 A7 7 0 0 0 100 264 C100 259 93 250 93 250 Z" fill="#f26a1b"/>
      <text x="128" y="288" font-family="{FONT}" font-size="27" font-weight="700" font-style="italic" fill="#14509e">{label}</text>
      <text x="130" y="304" font-family="{FONT}" font-size="8.6" letter-spacing=".6" fill="#3f6fa8">PACKAGED DRINKING WATER</text>
      <text x="130" y="316" font-family="{FONT}" font-size="8.6" font-weight="700" fill="#f26a1b">20 L</text>
    </g>
    {bars}
    <path d="M37 208 Q150 223 263 208" stroke="#fff" stroke-width="3" fill="none" opacity=".75"/>
    <path d="M37 213 Q150 228 263 213" stroke="#205fa8" stroke-width="2" fill="none" opacity=".35"/>
    <path d="M37 350 Q150 365 263 350" stroke="#fff" stroke-width="3" fill="none" opacity=".75"/>
    <path d="M37 355 Q150 370 263 355" stroke="#205fa8" stroke-width="2" fill="none" opacity=".35"/>
    <path d="M34 160 Q150 176 266 160" stroke="#fff" stroke-width="2" fill="none" opacity=".5"/>
    <rect x="60" y="120" width="15" height="290" rx="7" fill="#fff" opacity=".55" filter="url(#{uid}soft)"/>
    <rect x="86" y="140" width="5" height="260" rx="2.5" fill="#fff" opacity=".35"/>
    <rect x="236" y="140" width="7" height="260" rx="3.5" fill="#fff" opacity=".25"/>
    {''.join(drops)}
  </g>
  <path d="{body}" fill="none" stroke="#1f5ea8" stroke-width="1.5" opacity=".55"/>
  <rect x="126" y="50" width="48" height="18" rx="3" fill="#a9d1f3" opacity=".9"/>
  <rect x="114" y="42" width="72" height="12" rx="5" fill="url(#{uid}cap)"/>
  <rect x="119" y="8" width="62" height="38" rx="8" fill="url(#{uid}cap)"/>
  <g stroke="#0a3a80" stroke-width="1.2" opacity=".45">{''.join(f'<line x1="{124 + i * 4.4:.1f}" y1="12" x2="{124 + i * 4.4:.1f}" y2="42"/>' for i in range(12))}</g>
  <rect x="128" y="11" width="10" height="30" rx="4" fill="#fff" opacity=".35"/>
"""


def make_jar():
    write("jar.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 430" width="300" height="430">{jar_group()}</svg>')


# ------------------------------------------------------------------ water cooler
def make_cooler():
    jar = jar_group("c", seed=9)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 820" width="300" height="820">
  <defs>
    <linearGradient id="cb" x1="0" x2="1">
      <stop offset="0" stop-color="#c3ccd5"/><stop offset=".3" stop-color="#f4f7f9"/><stop offset=".55" stop-color="#ffffff"/>
      <stop offset=".85" stop-color="#e1e6eb"/><stop offset="1" stop-color="#b3bec9"/>
    </linearGradient>
    <linearGradient id="cr" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#cfd7df"/><stop offset="1" stop-color="#e9edf1"/>
    </linearGradient>
    <linearGradient id="cl" x1="0" x2="1"><stop offset="0" stop-color="#b7c1cb"/><stop offset=".5" stop-color="#dfe5ea"/><stop offset="1" stop-color="#aab5c0"/></linearGradient>
    <filter id="cs" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5"/></filter>
  </defs>
  <ellipse cx="150" cy="806" rx="120" ry="10" fill="#0b2a55" opacity=".25" filter="url(#cs)"/>
  <g transform="translate(150 336) rotate(180) scale(.8) translate(-150 -46)">{jar}</g>
  <rect x="66" y="318" width="168" height="34" rx="12" fill="url(#cl)"/>
  <path d="M46 362 Q46 340 68 340 L232 340 Q254 340 254 362 L254 792 Q254 802 244 802 L56 802 Q46 802 46 792 Z" fill="url(#cb)"/>
  <text x="150" y="380" text-anchor="middle" font-family="{FONT}" font-size="15" font-style="italic" font-weight="600" fill="#6a7d92">JalSetu</text>
  <circle cx="141" cy="395" r="2.6" fill="#3d8be0"/><circle cx="159" cy="395" r="2.6" fill="#e5534b"/>
  <rect x="78" y="414" width="144" height="170" rx="14" fill="url(#cr)" stroke="#bcc6d0"/>
  <g>
    <rect x="98" y="430" width="40" height="28" rx="6" fill="#e6ebef" stroke="#aeb9c4"/>
    <rect x="106" y="436" width="24" height="12" rx="4" fill="#9fd0ff" stroke="#3b82c9"/>
    <rect x="113" y="458" width="10" height="20" rx="3" fill="#c9d1d9" stroke="#9aa6b2"/>
    <rect x="162" y="430" width="40" height="28" rx="6" fill="#e6ebef" stroke="#aeb9c4"/>
    <rect x="170" y="436" width="24" height="12" rx="4" fill="#ffb3ad" stroke="#d9473f"/>
    <rect x="177" y="458" width="10" height="20" rx="3" fill="#c9d1d9" stroke="#9aa6b2"/>
  </g>
  <rect x="92" y="560" width="116" height="16" rx="4" fill="#8f9baa"/>
  <g stroke="#6d7a89" stroke-width="2">{''.join(f'<line x1="{98 + i * 8}" y1="563" x2="{98 + i * 8}" y2="573"/>' for i in range(14))}</g>
  <rect x="62" y="608" width="176" height="180" rx="10" fill="none" stroke="#c4cdd6" stroke-width="2"/>
  <rect x="74" y="690" width="10" height="34" rx="4" fill="#c4cdd6"/>
  <rect x="58" y="350" width="10" height="440" rx="5" fill="#fff" opacity=".6"/>
</svg>"""
    write("cooler.svg", svg)


# ------------------------------------------------------------------ delivery van
def make_van():
    rnd = random.Random(4)
    jars = []
    for row in range(6):
        for col in range(6):
            cx = 250 + col * 33 + (row % 2) * 16 + rnd.uniform(-3, 3)
            cy = 236 - row * 31 + rnd.uniform(-3, 3)
            r = 17 + rnd.uniform(-1.5, 1.5)
            cap = rnd.random() < .45
            jars.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#vj)" stroke="#8cc3f0" stroke-width="1.5"/>'
                        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * .62:.1f}" fill="none" stroke="#e3f3ff" stroke-width="1.3" opacity=".8"/>'
                        + (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * .36:.1f}" fill="#1e63c4"/>' if cap else "")
                        + f'<ellipse cx="{cx - r * .35:.1f}" cy="{cy - r * .4:.1f}" rx="{r * .28:.1f}" ry="{r * .16:.1f}" fill="#fff" opacity=".8"/>')
    wheel = lambda x: f"""<g transform="translate({x} 252)">
      <circle r="41" fill="#1d2126"/><circle r="36" fill="#2b3036"/>
      <circle r="24" fill="url(#vr)"/><circle r="8" fill="#4b535c"/>
      {''.join(f'<circle cx="{14 * __import__("math").cos(a * 1.2566):.1f}" cy="{14 * __import__("math").sin(a * 1.2566):.1f}" r="3.4" fill="#6b747e"/>' for a in range(5))}
    </g>"""
    body = ("M30 72 Q30 44 58 44 L440 44 Q470 44 488 62 L540 128 Q548 138 562 141 L612 151 Q632 155 634 176 "
            "L636 236 Q636 250 622 250 L560 250 A54 54 0 0 0 452 250 L200 250 A54 54 0 0 0 92 250 L44 250 Q30 250 30 236 Z")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 320" width="660" height="320">
  <defs>
    <linearGradient id="vb" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffd84a"/><stop offset=".5" stop-color="#ffc107"/><stop offset="1" stop-color="#ea9a00"/>
    </linearGradient>
    <linearGradient id="vs" x1="0" x2="1">
      <stop offset="0" stop-color="#000" stop-opacity=".12"/><stop offset=".15" stop-color="#000" stop-opacity="0"/>
      <stop offset=".9" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".25"/>
    </linearGradient>
    <linearGradient id="vw" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5d7c99"/><stop offset=".5" stop-color="#22374d"/><stop offset="1" stop-color="#3e5d7b"/>
    </linearGradient>
    <radialGradient id="vj" cx=".4" cy=".35" r=".7">
      <stop offset="0" stop-color="#e4f3ff"/><stop offset=".6" stop-color="#8cc4f2"/><stop offset="1" stop-color="#3c84cf"/>
    </radialGradient>
    <radialGradient id="vr" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#f1f3f5"/><stop offset="1" stop-color="#8e98a3"/></radialGradient>
    <clipPath id="vd"><rect x="232" y="60" width="190" height="186"/></clipPath>
    <filter id="vsh" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  </defs>
  <ellipse cx="335" cy="292" rx="305" ry="14" fill="#0b1b2e" opacity=".3" filter="url(#vsh)"/>
  <path d="{body}" fill="url(#vb)"/>
  <path d="{body}" fill="url(#vs)"/>
  <path d="M34 60 Q36 50 58 50 L440 50" stroke="#fff" stroke-width="3" opacity=".55" fill="none"/>
  <line x1="32" y1="156" x2="632" y2="156" stroke="#d48a00" stroke-width="2" opacity=".7"/>
  <rect x="232" y="60" width="190" height="186" fill="#1a2733"/>
  <g clip-path="url(#vd)">{''.join(jars)}</g>
  <rect x="232" y="60" width="190" height="186" fill="none" stroke="#c98300" stroke-width="3"/>
  <path d="M150 58 L232 58 L232 246 L150 246 Z" fill="none" stroke="#d48a00" stroke-width="2"/>
  <rect x="160" y="70" width="64" height="62" rx="6" fill="url(#vw)" opacity=".92"/>
  <path d="M446 56 L476 56 L530 128 L446 128 Z" fill="url(#vw)"/>
  <path d="M452 62 L470 62 L500 104 L452 104 Z" fill="#fff" opacity=".12"/>
  <path d="M440 50 L440 246" stroke="#d48a00" stroke-width="2"/>
  <rect x="452" y="140" width="24" height="7" rx="3" fill="#7a5a00" opacity=".6"/>
  <rect x="198" y="140" width="22" height="7" rx="3" fill="#7a5a00" opacity=".6"/>
  <path d="M470 92 L452 92 L452 112 L472 112 Z" fill="#20262c"/>
  <path d="M614 160 Q630 162 632 172 L632 194 L614 190 Z" fill="#fffbe8" stroke="#c9a200"/>
  <rect x="556" y="226" width="84" height="24" rx="8" fill="#2a2f36"/>
  <rect x="22" y="222" width="40" height="28" rx="8" fill="#2a2f36"/>
  <rect x="36" y="96" width="10" height="44" rx="4" fill="#e04b2c" opacity=".85"/>
  {wheel(146)}{wheel(506)}
</svg>"""
    write("van.svg", svg)


# ------------------------------------------------------------------ how-it-works scenes
SC_DEFS = """<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e7f1fb"/><stop offset="1" stop-color="#bcd6f0"/></linearGradient>
  <linearGradient id="nv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f6cc0"/><stop offset="1" stop-color="#0a3478"/></linearGradient>
  <radialGradient id="btn" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#3b7dd6"/><stop offset=".6" stop-color="#14489a"/><stop offset="1" stop-color="#0a2f6e"/></radialGradient>
  <filter id="sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#0b2a55" flood-opacity=".22"/></filter>
</defs>"""


def pin(x, y, price=None, color="url(#nv)", s=1.0):
    tag = ""
    if price:
        tag = (f'<g transform="translate({x + 16 * s} {y - 52 * s})"><rect width="{58 * s}" height="{26 * s}" rx="{13 * s}" fill="#fff" filter="url(#sh)"/>'
               f'<text x="{29 * s}" y="{18 * s}" text-anchor="middle" font-family="{FONT}" font-size="{15 * s}" font-weight="700" fill="#f26a1b">{price}</text></g>')
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 0 C-6 -14 -20 -24 -20 -40 A20 20 0 0 1 20 -40 C20 -24 6 -14 0 0 Z" fill="{color}" filter="url(#sh)"/>'
            f'<path d="M0 -50 C0 -50 -7 -41 -7 -37 A7 7 0 0 0 7 -37 C7 -41 0 -50 0 -50 Z" fill="#fff"/></g>') + tag


def city(w, h, seed=1):
    rnd = random.Random(seed)
    blocks = []
    for gx in range(0, w, 96):
        for gy in range(0, h, 84):
            blocks.append(f'<rect x="{gx + 10}" y="{gy + 10}" width="{76 + rnd.randint(-8, 0)}" height="{64 + rnd.randint(-8, 0)}" rx="6" fill="{rnd.choice(["#eef5fc", "#e3eef9", "#f4f9fe", "#dcebd9"])}"/>')
    roads = (f'<path d="M-10 {h * .62} C{w * .3} {h * .5} {w * .6} {h * .78} {w + 10} {h * .6}" stroke="#fff" stroke-width="16" fill="none"/>'
             f'<path d="M{w * .42} -10 C{w * .38} {h * .4} {w * .52} {h * .6} {w * .46} {h + 10}" stroke="#fff" stroke-width="12" fill="none"/>'
             f'<path d="M-10 {h * .2} C{w * .4} {h * .28} {w * .7} {h * .1} {w + 10} {h * .22}" stroke="#9cc8ee" stroke-width="22" fill="none"/>')
    return f'<rect width="{w}" height="{h}" fill="#d7e7f6"/>' + "".join(blocks) + roads


def scene(name, inner):
    write(name, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 768 508" width="768" height="508" overflow="hidden">{SC_DEFS}'
                f'<rect width="768" height="508" fill="url(#bg)"/>{inner}</svg>')


def phone(x, y, w, h, screen):
    return (f'<g transform="translate({x} {y})" filter="url(#sh)"><rect width="{w}" height="{h}" rx="30" fill="#0f2f63"/>'
            f'<clipPath id="ps{x}"><rect x="10" y="12" width="{w - 20}" height="{h - 24}" rx="22"/></clipPath>'
            f'<rect x="10" y="12" width="{w - 20}" height="{h - 24}" rx="22" fill="#fff"/>'
            f'<g clip-path="url(#ps{x})"><g transform="translate(10 12)">{screen}</g></g>'
            f'<rect x="{w / 2 - 30}" y="18" width="60" height="8" rx="4" fill="#0f2f63"/></g>')


def make_scenes():
    # 1 choose your area
    s1 = (f'<circle cx="150" cy="120" r="70" fill="#fff" opacity=".35"/><circle cx="640" cy="400" r="110" fill="#fff" opacity=".3"/>'
          + phone(274, 30, 220, 450,
                  city(200, 426, 2)
                  + '<rect x="14" y="30" width="172" height="40" rx="20" fill="#fff" filter="url(#sh)"/>'
                  + f'<text x="44" y="56" font-family="{FONT}" font-size="15" fill="#1d4f9a">Beliaghata, Kolkata</text>'
                  + '<circle cx="30" cy="50" r="6" fill="#f26a1b"/>'
                  + '<circle cx="100" cy="230" r="54" fill="#f26a1b" opacity=".12"/><circle cx="100" cy="230" r="30" fill="#f26a1b" opacity=".2"/>'
                  + pin(100, 236, color="#f26a1b", s=1.2)
                  + '<rect x="24" y="360" width="152" height="42" rx="21" fill="url(#nv)"/>'
                  + f'<text x="100" y="387" text-anchor="middle" font-family="{FONT}" font-size="15" fill="#fff">Use my location</text>'))
    scene("how-1.svg", s1)
    # 2 suppliers on the map
    s2 = (city(768, 508, 5)
          + '<circle cx="380" cy="270" r="150" fill="#2f6cc0" opacity=".08" stroke="#2f6cc0" stroke-dasharray="8 8" stroke-width="2"/>'
          + '<circle cx="380" cy="270" r="22" fill="#f26a1b" opacity=".25"/><circle cx="380" cy="270" r="10" fill="#f26a1b" stroke="#fff" stroke-width="3"/>'
          + pin(250, 210, "₹40") + pin(480, 180, "₹35") + pin(300, 380, "₹45") + pin(520, 360, "₹38") + pin(640, 120, "₹42", s=.85))
    scene("how-2.svg", s2)
    # 3 compare
    def card(x, name, price, dist, deliv, star, best=False):
        return (f'<g transform="translate({x} 70)" filter="url(#sh)"><rect width="250" height="370" rx="22" fill="#fff"/>'
                + (f'<rect x="150" y="-14" width="96" height="28" rx="14" fill="#f26a1b"/><text x="198" y="5" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#fff">Best price</text>' if best else "")
                + '<rect x="95" y="34" width="60" height="84" rx="16" fill="#9fcdf2"/><rect x="113" y="22" width="24" height="16" rx="4" fill="#1e63c4"/>'
                + '<rect x="95" y="66" width="60" height="22" fill="#fff" opacity=".85"/>'
                + f'<text x="125" y="156" text-anchor="middle" font-family="{FONT}" font-size="19" font-weight="600" fill="#0f3d82">{name}</text>'
                + f'<text x="125" y="206" text-anchor="middle" font-family="{FONT}" font-size="40" font-weight="700" fill="#f26a1b">{price}</text>'
                + "".join(f'<circle cx="40" cy="{246 + i * 36}" r="9" fill="#2f6cc0"/><text x="58" y="{252 + i * 36}" font-family="{FONT}" font-size="16" fill="#1d4f9a">{t}</text>'
                          for i, t in enumerate([dist, deliv, star])) + "</g>")
    s3 = card(110, "Aqua Pure", "₹40", "0.9 km away", "₹10 delivery", "★ 5.0 rating") \
         + card(408, "Shree Jal", "₹35", "1.4 km away", "₹20 delivery", "★ 4.0 rating", best=True) \
         + f'<circle cx="384" cy="255" r="30" fill="url(#btn)" filter="url(#sh)"/><text x="384" y="262" text-anchor="middle" font-family="{FONT}" font-size="18" font-weight="700" fill="#fff">VS</text>'
    scene("how-3.svg", s3)
    # 4 request in one tap
    form = ('<rect width="200" height="426" fill="#eaf4fc"/>'
            + f'<text x="100" y="64" text-anchor="middle" font-family="{FONT}" font-size="16" fill="#1d4f9a">Request delivery</text>'
            + "".join(f'<rect x="22" y="{86 + i * 58}" width="156" height="38" rx="8" fill="#fff" stroke="#c9dcef"/><rect x="34" y="{101 + i * 58}" width="{[90, 120, 70][i]}" height="8" rx="4" fill="#c4d6ea"/>' for i in range(3))
            + '<circle cx="100" cy="330" r="46" fill="url(#btn)" filter="url(#sh)"/>'
            + f'<text x="100" y="336" text-anchor="middle" font-family="{FONT}" font-size="17" fill="#fff">Order</text>')
    s4 = (phone(200, 30, 220, 450, form)
          + f'<g transform="translate(470 150)" filter="url(#sh)"><rect width="170" height="56" rx="28" fill="url(#nv)"/><text x="85" y="35" text-anchor="middle" font-family="{FONT}" font-size="19" fill="#fff">Call supplier</text></g>'
          + f'<g transform="translate(470 230)" filter="url(#sh)"><rect width="170" height="56" rx="28" fill="#25b05a"/><text x="85" y="35" text-anchor="middle" font-family="{FONT}" font-size="19" fill="#fff">WhatsApp</text></g>'
          + f'<g transform="translate(470 310)" filter="url(#sh)"><rect width="170" height="56" rx="28" fill="#fff"/><text x="85" y="35" text-anchor="middle" font-family="{FONT}" font-size="19" fill="#f26a1b">₹40 + ₹10</text></g>')
    scene("how-4.svg", s4)
    # 5 track status
    steps = [("Requested", True), ("Accepted", True), ("On the way", True), ("Delivered", False)]
    nodes = ""
    for i, (t, done) in enumerate(steps):
        x = 120 + i * 176
        nodes += (f'<circle cx="{x}" cy="230" r="46" fill="{"url(#btn)" if done else "#fff"}" stroke="#9cc6ea" stroke-width="6" filter="url(#sh)"/>'
                  f'<path d="M{x} 206 C{x} 206 {x - 14} 224 {x - 14} 234 A14 14 0 0 0 {x + 14} 234 C{x + 14} 224 {x} 206 {x} 206 Z" fill="{"#fff" if done else "#9cc6ea"}"/>'
                  f'<text x="{x}" y="318" text-anchor="middle" font-family="{FONT}" font-size="22" fill="#0f3d82">{t}</text>')
    s5 = ('<path d="M120 230 L648 230" stroke="#9cc6ea" stroke-width="8"/><path d="M120 230 L472 230" stroke="#1d5fb4" stroke-width="8"/>'
          + nodes
          + '<g transform="translate(520 120) scale(.22)"><rect x="30" y="44" width="560" height="206" rx="20" fill="#ffc107"/><rect x="440" y="60" width="100" height="70" rx="8" fill="#2a3e55"/>'
            '<circle cx="146" cy="252" r="44" fill="#1d2126"/><circle cx="506" cy="252" r="44" fill="#1d2126"/></g>'
          + f'<text x="384" y="420" text-anchor="middle" font-family="{FONT}" font-size="20" fill="#1d4f9a">Status updates for every request</text>')
    scene("how-5.svg", s5)
    # 6 verification
    rows = [("Aqua Pure Suppliers", True), ("Shree Jal Distributors", True), ("Blue Drop Agency", True), ("New Local Supplier", False)]
    lst = ""
    for i, (n, ok) in enumerate(rows):
        y = 120 + i * 74
        lst += (f'<circle cx="150" cy="{y + 26}" r="20" fill="#cfe3f6"/><path d="M150 {y + 12} C150 {y + 12} 141 {y + 24} 141 {y + 30} A9 9 0 0 0 159 {y + 30} C159 {y + 24} 150 {y + 12} 150 {y + 12} Z" fill="#2f6cc0"/>'
                f'<text x="184" y="{y + 33}" font-family="{FONT}" font-size="19" fill="#0f3d82">{n}</text>'
                f'<rect x="430" y="{y + 10}" width="112" height="32" rx="16" fill="{"#d9f3e5" if ok else "#fdeccf"}"/>'
                f'<text x="486" y="{y + 32}" text-anchor="middle" font-family="{FONT}" font-size="15" fill="{"#17864b" if ok else "#b0700a"}">{"Verified ✓" if ok else "Pending"}</text>')
    s6 = ('<g filter="url(#sh)"><rect x="110" y="60" width="460" height="400" rx="20" fill="#fff"/></g>'
          '<rect x="110" y="60" width="460" height="44" rx="20" fill="#eaf2fb"/><rect x="110" y="84" width="460" height="20" fill="#eaf2fb"/>'
          '<circle cx="138" cy="82" r="6" fill="#f26a1b"/><circle cx="158" cy="82" r="6" fill="#ffc107"/><circle cx="178" cy="82" r="6" fill="#25b05a"/>'
          + lst
          + '<g transform="translate(600 110)" filter="url(#sh)"><path d="M0 0 L60 -24 L120 0 L120 70 C120 120 60 150 60 150 C60 150 0 120 0 70 Z" fill="url(#nv)"/>'
            '<path d="M32 62 L54 84 L92 42" stroke="#fff" stroke-width="12" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
    scene("how-6.svg", s6)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    make_jar(); make_cooler(); make_van(); make_scenes()
