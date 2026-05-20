import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniClose",
  description: "The WhatsApp sales assistant for modern vendors.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}
