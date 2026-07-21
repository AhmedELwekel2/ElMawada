import type { Metadata } from "next";
import { Cairo } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "./contexts/AuthContext";
import Header from "./components/Header";

const cairo = Cairo({ subsets: ["latin", "arabic"], weight: ["400", "700", "900"] });

export const metadata: Metadata = {
  title: "مركز المودة للإرشاد الأسري وفض النزاعات",
  description: "مركز المودة للإرشاد الأسري وفض النزاعات — أخبار ومحتوى متخصص في الصحة النفسية والإرشاد الأسري.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ar" dir="rtl">
      <body className={`${cairo.className} min-h-screen bg-slate-100 text-slate-900 antialiased`}>
        <AuthProvider>
          <Header />
          <main className="pt-16">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}