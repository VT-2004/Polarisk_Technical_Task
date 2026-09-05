import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Gmail Spend Intelligence — AI Financial Dashboard",
  description: "Securely analyze past inbox receipts, invoices, recurring subscriptions, and spending anomalies with full email traceability.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-50">
      <body className={`${inter.className} min-h-full flex flex-col bg-slate-950 text-slate-100 antialiased`}>
        {children}
      </body>
    </html>
  );
}
