"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";

interface DashboardLayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

export default function DashboardLayout({ sidebar, children }: DashboardLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans" dir="rtl">
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileMenuOpen(true)}
        className="fixed bottom-6 left-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-red text-white shadow-xl lg:hidden hover:bg-brand-redDark transition-colors"
        aria-label="فتح القائمة"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Mobile sidebar (drawer) */}
      <div
        className={`fixed inset-y-0 right-0 z-50 w-72 overflow-y-auto transition-transform duration-300 ease-in-out lg:hidden ${
          mobileMenuOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <button
          onClick={() => setMobileMenuOpen(false)}
          className="absolute left-4 top-4 text-white/80 hover:text-white z-10"
          aria-label="إغلاق القائمة"
        >
          <X className="h-6 w-6" />
        </button>
        {sidebar}
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:block flex-shrink-0">
        {sidebar}
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </div>
  );
}