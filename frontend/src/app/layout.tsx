import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Origami Pattern Studio",
  description: "Find origami models and turn an object or photo into a starting crease pattern.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link href="/" className="brand">
            <span aria-hidden>◆</span> Origami Pattern Studio
          </Link>
          <nav>
            <Link href="/">Studio</Link>
            <Link href="/catalog">Catalog</Link>
            <Link href="/bases">Bases</Link>
          </nav>
        </header>
        <main>{children}</main>
        <footer className="site-footer">
          Catalog entries link to their original sources. Generated patterns are starting points built from
          traditional bases.
        </footer>
      </body>
    </html>
  );
}
