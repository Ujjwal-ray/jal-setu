import { Icon } from "./Icons";

const PLACES = [
  { icon: Icon.home, label: "Homes" },
  { icon: Icon.apartment, label: "Apartments" },
  { icon: Icon.office, label: "Offices" },
  { icon: Icon.hostel, label: "Hostels & PGs" },
  { icon: Icon.school, label: "Schools & colleges" },
  { icon: Icon.shop, label: "Shops & cafés" },
];

export default function WeDeliver() {
  return (
    <section className="deliver" aria-labelledby="deliver-title">
      <h2 id="deliver-title" className="headline headline--section">We deliver</h2>
      <img className="deliver-van" src="/img/van.svg" alt="Delivery van loaded with 20 litre water jars" />
      <ul className="places">
        {PLACES.map(({ icon: I, label }) => (
          <li key={label}>
            <span className="place-ring"><I width={64} height={64} /></span>
            <span>{label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
