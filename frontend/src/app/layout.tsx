import type { Metadata } from "next";
import { Outfit, JetBrains_Mono } from "next/font/google";
import { AppLayout } from "@/components/layout/app-layout";
import { ToastContainer } from "@/components/common/toast-container";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aerospike Cluster Manager",
  description: "GUI management tool for Aerospike Community Edition",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${outfit.variable} ${jetbrainsMono.variable} antialiased`}>
        <AppLayout>{children}</AppLayout>
        <ToastContainer />
      </body>
    </html>
  );
}
