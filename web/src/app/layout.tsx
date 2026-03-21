import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Kangaroo Prep",
  description: "A focused Math Kangaroo practice and mock exam workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
