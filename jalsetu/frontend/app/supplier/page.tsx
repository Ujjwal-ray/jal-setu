import type { Metadata } from "next";
import SupplierDashboard from "@/components/pages/SupplierDashboard";

export const metadata: Metadata = { title: "Supplier dashboard · JalSetu" };

export default function Page() {
  return <SupplierDashboard />;
}
