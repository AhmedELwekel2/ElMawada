"use client";

import { useAuth } from "../contexts/AuthContext";
import { User, LogOut, Shield } from "lucide-react";
import Link from "next/link";

export default function AuthButtons() {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="flex items-center gap-3">
        <Link
          href="/login"
          className="rounded-full bg-white px-5 py-2 text-sm font-bold text-brand-red shadow-sm hover:bg-slate-50 transition-colors"
        >
          تسجيل الدخول
        </Link>
        <Link
          href="/register"
          className="rounded-full bg-brand-red px-5 py-2 text-sm font-bold text-white shadow-sm hover:bg-brand-redDark transition-colors"
        >
          إنشاء حساب
        </Link>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 bg-white/10 px-3 py-2 rounded-full">
        <div className="h-6 w-6 rounded-full bg-white/20 flex items-center justify-center">
          <User className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-medium text-white">
          {user?.full_name || user?.username}
        </span>
        {user?.role === "admin" && (
          <Shield className="h-3 w-3 text-yellow-300" />
        )}
      </div>
      
      <button
        onClick={logout}
        className="flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 text-sm font-medium text-white hover:bg-white/20 transition-colors"
        title="تسجيل الخروج"
      >
        <LogOut className="h-4 w-4" />
        <span className="hidden sm:inline">تسجيل الخروج</span>
      </button>
    </div>
  );
}