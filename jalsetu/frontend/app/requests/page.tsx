import type { Metadata } from "next";
import Requests from "@/components/pages/Requests";

export const metadata: Metadata = { title: "My requests · JalSetu" };

export default function Page() {
  return <Requests />;
}
