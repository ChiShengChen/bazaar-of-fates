import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Bazaar of Fates · 算命",
  description: "Eleven traditional divination systems · one birth input · deterministic charts + bilingual AI readings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
