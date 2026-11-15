import type { Metadata } from "next";
import "../styles/tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "FlameIntel - Understand fire in microgravity",
  description: "Search and question NASA's microgravity combustion experiments. Every answer is cited, and missing data is never guessed.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preload" href="/landing/assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="icon" href="data:," />
      </head>
      <body>{children}</body>
    </html>
  );
}
