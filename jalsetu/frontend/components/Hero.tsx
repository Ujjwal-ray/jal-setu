import { rupee } from "@/lib/format";
import { Icon } from "./Icons";
import RoundButton from "./RoundButton";

export default function Hero({
  count,
  minPrice,
  onOrder,
}: {
  count: number | null;
  minPrice: number | null;
  onOrder: () => void;
}) {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-head">
        <h1 id="hero-title" className="headline">Water jar delivery</h1>
        <p className="hero-sub">From verified local suppliers near you</p>
      </div>

      <div className="hero-stage">
        <div className="hero-products" aria-hidden="true">
          <div className="hero-products-inner">
            <img className="hp-cooler" src="/img/cooler.svg" alt="" />
            <img className="hp-jar hp-jar--back" src="/img/jar.svg" alt="" />
            <img className="hp-jar hp-jar--front" src="/img/jar.svg" alt="" />
          </div>
        </div>

        <div className="hero-side">
          <ul className="glass feature-list">
            <li>
              <span className="drop-badge"><Icon.drop /></span>
              <span>{count ? `${count} verified suppliers` : "Verified suppliers"} on one map</span>
            </li>
            <li>
              <span className="drop-badge"><Icon.drop /></span>
              <span>
                Compare 20 L jar prices <span className="accent">{minPrice ? `from ${rupee(minPrice)}` : "side by side"}</span>
              </span>
            </li>
            <li>
              <span className="drop-badge"><Icon.drop /></span>
              <span>
                Request delivery today, <span className="accent">track every step</span>
              </span>
            </li>
            <li>
              <span className="drop-badge"><Icon.drop /></span>
              <span>
                Order with one tap
                <span className="badges">
                  <span className="badge badge--wa"><Icon.chat width={14} height={14} /> WhatsApp</span>
                  <span className="badge badge--call"><Icon.phone width={13} height={13} /> Call</span>
                </span>
              </span>
            </li>
          </ul>
          <RoundButton onClick={onOrder} className="hero-cta">
            Order
            <br />
            now
          </RoundButton>
        </div>
      </div>
      <div className="hero-wave" aria-hidden="true" />
    </section>
  );
}
