import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Second PC",
  description: "A persistent Linux desktop with an AI agent that lives inside it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Geist via Vercel CDN */}
        <link rel="preconnect" href="https://assets.vercel.com" />
        <link
          rel="stylesheet"
          href="https://assets.vercel.com/raw/upload/v1677117922/fonts/2/geist.css"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://assets.vercel.com/raw/upload/v1677117922/fonts/3/geist-mono.css"
          crossOrigin="anonymous"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
