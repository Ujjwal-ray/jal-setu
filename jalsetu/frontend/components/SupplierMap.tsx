"use client";

import L from "leaflet";
import { useEffect, useMemo } from "react";
import { Circle, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { Loc, Supplier } from "@/lib/api";
import { rupee } from "@/lib/format";

const TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

const priceIcon = (price: number | null, active: boolean, off: boolean) =>
  L.divIcon({
    className: "",
    html: `<div class="mpin${active ? " mpin--on" : ""}${off ? " mpin--off" : ""}"><span>${rupee(price)}</span></div>`,
    iconSize: [64, 52],
    iconAnchor: [32, 52],
  });

const youIcon = L.divIcon({ className: "", html: '<div class="you-dot"><i></i></div>', iconSize: [28, 28], iconAnchor: [14, 14] });

function Follow({ loc, active }: { loc: Loc; active: Supplier | undefined }) {
  const map = useMap();
  useEffect(() => {
    map.setView([loc.lat, loc.lng], map.getZoom(), { animate: true });
  }, [loc.lat, loc.lng, map]);
  useEffect(() => {
    if (active && !map.getBounds().pad(-0.15).contains([active.lat, active.lng])) map.panTo([active.lat, active.lng]);
  }, [active, map]);
  return null;
}

function Picker({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}

export default function SupplierMap({
  loc,
  suppliers,
  activeId,
  radiusKm,
  onSelect,
  onPick,
}: {
  loc: Loc;
  suppliers: Supplier[];
  activeId: number | null;
  radiusKm: number;
  onSelect: (id: number) => void;
  onPick: (lat: number, lng: number) => void;
}) {
  const active = suppliers.find((s) => s.id === activeId);
  const icons = useMemo(
    () => Object.fromEntries(suppliers.map((s) => [s.id, priceIcon(s.price, s.id === activeId, !s.availability)])),
    [suppliers, activeId]
  );
  return (
    <MapContainer center={[loc.lat, loc.lng]} zoom={14} scrollWheelZoom={false} className="leaflet-host">
      <TileLayer url={TILE} attribution={ATTR} />
      <Follow loc={loc} active={active} />
      <Picker onPick={onPick} />
      {radiusKm > 0 && (
        <Circle center={[loc.lat, loc.lng]} radius={radiusKm * 1000} pathOptions={{ color: "#1d5fb4", weight: 1.5, dashArray: "6 6", fillOpacity: 0.06 }} />
      )}
      <Marker position={[loc.lat, loc.lng]} icon={youIcon} interactive={false} />
      {suppliers.map((s) => (
        <Marker
          key={s.id}
          position={[s.lat, s.lng]}
          icon={icons[s.id]}
          zIndexOffset={s.id === activeId ? 1000 : 0}
          eventHandlers={{ click: () => onSelect(s.id) }}
          keyboard
          title={s.business_name}
        >
          <Tooltip direction="top" offset={[0, -50]}>{s.business_name}</Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}

/** Small map used by suppliers to drop their shop pin. */
const shopIcon = L.divIcon({ className: "", html: '<div class="mpin mpin--on"><span>Shop</span></div>', iconSize: [64, 52], iconAnchor: [32, 52] });

function KeepInView({ at }: { at: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    if (!map.getBounds().contains(at)) map.panTo(at);
  }, [at, map]);
  return null;
}

export function PinPicker({ value, onChange }: { value: [number, number]; onChange: (v: [number, number]) => void }) {
  return (
    <MapContainer center={value} zoom={15} scrollWheelZoom={false} className="leaflet-host">
      <TileLayer url={TILE} attribution={ATTR} />
      <KeepInView at={value} />
      <Picker onPick={(a, b) => onChange([a, b])} />
      <Marker
        position={value}
        icon={shopIcon}
        draggable
        eventHandlers={{
          dragend: (e) => {
            const p = (e.target as L.Marker).getLatLng();
            onChange([p.lat, p.lng]);
          },
        }}
      />
    </MapContainer>
  );
}
