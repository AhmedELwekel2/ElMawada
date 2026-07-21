"use client";

import Link from "next/link";
import AuthButtons from "./AuthButtons";

export default function Header() {
  return (
    <header className="fixed top-0 z-50 w-full border-b border-white/10 bg-brand-primary/95 backdrop-blur-md transition-all">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-2">
          {/* Logo */}
          <Link href="/">
            <img src="/mawadda-logo.png" alt="شعار مركز المودة" className="h-10 w-10 rounded-xl object-contain bg-white p-1" />
          </Link>
          <Link href="/" className="text-xl font-black text-white">
            مركز المودة
          </Link>
        </div>
        
        <div className="flex items-center gap-4">
          <AuthButtons />
        </div>
      </div>
    </header>
  );
}