import type { Metadata, Viewport } from "next";
import { Jost } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import AppProvider from "@/components/AppProvider";

const jost = Jost({ subsets: ["latin"], variable: "--font-jost", display: "swap" });

export const metadata: Metadata = {
  title: "JalSetu — water jar delivery from verified suppliers near you",
  description: "Find verified 20-litre water-jar suppliers on a map, compare price and delivery charge, and request delivery in one tap.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0b3a86" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={jost.variable}>
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
