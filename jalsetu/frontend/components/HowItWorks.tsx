"use client";

import { useState } from "react";
import { Icon } from "./Icons";

const STEPS = [
  { img: "/img/how-1.svg", text: "Open JalSetu and choose your area" },
  { img: "/img/how-2.svg", text: "See verified suppliers on one map" },
  { img: "/img/how-3.svg", text: "Compare jar price, delivery charge and distance" },
  { img: "/img/how-4.svg", text: "Request delivery, call or WhatsApp in one tap" },
  { img: "/img/how-5.svg", text: "Follow your request until the jars arrive" },
  { img: "/img/how-6.svg", text: "Every supplier is checked by a JalSetu admin" },
];

/** Centre card in full colour, neighbours tinted blue — like a photo reel. */
export default function HowItWorks() {
  const [i, setI] = useState(0);
  const n = STEPS.length;
  const go = (d: number) => setI((i + d + n) % n);
  const visible = [-2, -1, 0, 1, 2].map((k) => ({ k, idx: (i + k + n) % n }));

  return (
    <section className="how" aria-labelledby="how-title">
      <h2 id="how-title" className="headline headline--section">
        From map
        <br />
        to doorstep
      </h2>
      <div className="reel" aria-roledescription="carousel">
        {visible.map(({ k, idx }) => (
          <figure
            key={idx}
            className={"reel-card" + (k === 0 ? " is-on" : "")}
            style={{ "--k": k } as React.CSSProperties}
            aria-hidden={k !== 0}
            onClick={() => k !== 0 && go(k)}
          >
            <div className="reel-img">
              <img src={STEPS[idx].img} alt={k === 0 ? STEPS[idx].text : ""} />
            </div>
            <figcaption>
              <b>{idx + 1}.</b> {STEPS[idx].text}
            </figcaption>
          </figure>
        ))}
        <button className="arrow arrow--light arrow--l" onClick={() => go(-1)} aria-label="Previous step"><Icon.chevL /></button>
        <button className="arrow arrow--light arrow--r" onClick={() => go(1)} aria-label="Next step"><Icon.chevR /></button>
      </div>
    </section>
  );
}
