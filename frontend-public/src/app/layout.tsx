import type { Metadata } from "next";
import { Bricolage_Grotesque, DM_Sans, JetBrains_Mono } from "next/font/google";
import { UtmCaptureBoundary } from "@/components/UtmCaptureBoundary";
import { WebVitalsReporter } from "@/lib/web-vitals";
import "./globals.css";

const bricolageGrotesque = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-data",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Summa Vision — Canadian Macroeconomic Data Visualized",
  description:
    "High-quality infographics from Statistics Canada and CMHC data. Housing, inflation, and economic trends.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${bricolageGrotesque.variable} ${dmSans.variable} ${jetBrainsMono.variable}`}>
      <body>
        <WebVitalsReporter />
        <UtmCaptureBoundary>{children}</UtmCaptureBoundary>
      </body>
    </html>
  );
}
