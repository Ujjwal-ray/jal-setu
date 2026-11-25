"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, supplierQuery, type Filters, type Loc, type Supplier } from "@/lib/api";
import { useApp } from "./AppProvider";
import CallFab from "./CallFab";
import Footer from "./Footer";
import Hero from "./Hero";
import HowItWorks from "./HowItWorks";
import RequestForm from "./RequestForm";
import SupplierModal from "./SupplierModal";
import SupplierShowcase from "./SupplierShowcase";
import TopBar from "./TopBar";
import Verified from "./Verified";
import WeDeliver from "./WeDeliver";
import { Icon } from "./Icons";

const DEFAULT_LOC: Loc = { lat: 22.5645, lng: 88.3951, label: "Beliaghata, Kolkata" };
const DEFAULT_FILTERS: Filters = { q: "", maxKm: "3", maxPrice: "", sort: "distance", available: false };

const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

export default function Landing() {
  const { toast, user } = useApp();
  const router = useRouter();
  const isSupplier = user?.role === "supplier";
  const [loc, setLoc] = useState<Loc>(DEFAULT_LOC);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [all, setAll] = useState<Supplier[]>([]);
  const [allLoaded, setAllLoaded] = useState(false);
  const [list, setList] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeId, setActiveId] = useState<number | null>(null);
  const [orderId, setOrderId] = useState<number | null>(null);
  const [detailId, setDetailId] = useState<number | null>(null);

  // every verified supplier around the location (form, certificates, call button, hero stats)
  useEffect(() => {
    api<Supplier[]>(supplierQuery(loc))
      .then((r) => {
        setAll(r);
        setAllLoaded(true);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [loc]);

  // the filtered set shown in the slider + map (debounced for typing)
  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api<Supplier[]>(supplierQuery(loc, filters))
        .then((r) => {
          setList(r);
          setActiveId((cur) => (r.some((s) => s.id === cur) ? cur : r[0]?.id ?? null));
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [loc, filters]);

  useEffect(() => {
    if (error) toast(error);
  }, [error, toast]);

  // suppliers run their business from the dashboard; this page is for customers
  useEffect(() => {
    if (isSupplier) router.replace("/supplier");
  }, [isSupplier, router]);

  const open = useMemo(() => all.filter((s) => s.availability), [all]);
  const minPrice = useMemo(() => (open.length ? Math.min(...open.map((s) => s.price || Infinity)) : null), [open]);

  const locate = useCallback(() => {
    if (!navigator.geolocation) return toast("Location isn't available in this browser. Tap the map instead.");
    navigator.geolocation.getCurrentPosition(
      (p) => setLoc({ lat: p.coords.latitude, lng: p.coords.longitude, label: "your location" }),
      () => toast("Location permission was blocked. Tap the map to choose your area."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [toast]);

  if (isSupplier) return null; // on the way to /supplier

  const orderFrom = (id: number) => {
    setOrderId(id);
    setDetailId(null);
    scrollTo("order");
  };

  const ribbon = (
    <button className="ribbon-btn" onClick={() => scrollTo("suppliers")}>
      <Icon.pin width={18} height={18} /> {loc.label}
      <span className="ribbon-sep" />
      {all.length ? `${all.length} verified ${all.length === 1 ? "supplier" : "suppliers"}` : "Find suppliers"}
    </button>
  );

  return (
    <>
      <TopBar ribbon={ribbon} />
      <main>
        <Hero count={all.length || null} minPrice={minPrice} onOrder={() => scrollTo("order")} />
        <RequestForm suppliers={all} selectedId={orderId} onSelect={setOrderId} locLabel={loc.label} />
        <SupplierShowcase
          list={list}
          loading={loading}
          error={error}
          loc={loc}
          filters={filters}
          setFilters={setFilters}
          activeId={activeId}
          setActiveId={setActiveId}
          onOrder={orderFrom}
          onDetails={setDetailId}
          onPick={(lat, lng) => setLoc({ lat, lng, label: "the area you picked" })}
          onLocate={locate}
        />
        <HowItWorks />
        <WeDeliver />
        <Verified suppliers={all} loaded={allLoaded} onOpen={setDetailId} onOrder={() => scrollTo("order")} />
      </main>
      <Footer />
      <CallFab nearest={open[0]} onFind={() => scrollTo("suppliers")} />
      {detailId != null && (
        <SupplierModal
          id={detailId}
          distance={all.find((s) => s.id === detailId)?.distance_km}
          onClose={() => setDetailId(null)}
          onOrder={orderFrom}
        />
      )}
    </>
  );
}
