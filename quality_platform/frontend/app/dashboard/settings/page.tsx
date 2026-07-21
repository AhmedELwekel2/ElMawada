"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Save, Loader2, Key } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

type Setting = {
    id?: number;
    key: string;
    value: string;
    description?: string;
};

export default function SettingsPage() {
    const [settings, setSettings] = useState<Record<string, Setting>>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/api/settings`);
            if (!res.ok) throw new Error("فشل في جلب الإعدادات");
            const data: Setting[] = await res.json();

            const settingsMap: Record<string, Setting> = {};
            data.forEach(s => {
                settingsMap[s.key] = s;
            });

            // Default empty strings if not exist
            if (!settingsMap["blog_keywords"]) {
                settingsMap["blog_keywords"] = { key: "blog_keywords", value: "", description: "مثال: Quality Management | ISO, compliance" };
            }
            if (!settingsMap["news_api_key"]) {
                settingsMap["news_api_key"] = { key: "news_api_key", value: "", description: "مفتاح NewsAPI" };
            }

            setSettings(settingsMap);
        } catch (e: any) {
            setError(e.message || "حدث خطأ غير متوقع");
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (key: string, value: string) => {
        setSettings(prev => ({
            ...prev,
            [key]: { ...prev[key], value }
        }));
        setSuccess(false);
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            setError(null);
            setSuccess(false);

            // Save all updated settings
            for (const [key, setting] of Object.entries(settings)) {
                await fetch(`${API_BASE}/api/settings`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        key: setting.key,
                        value: setting.value,
                        description: setting.description
                    })
                });
            }

            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (e: any) {
            setError("فشل في حفظ الإعدادات. تأكد من اتصال الخادم.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="flex min-h-screen bg-slate-100 font-sans" dir="rtl">
            {/* Sidebar - Similar to dashboard, simplified */}
            <aside className="hidden w-64 flex-shrink-0 border-l border-brand-red/20 bg-gradient-to-b from-[#1C5E58] to-[#2E9E95] px-6 py-8 text-white shadow-xl lg:block">
                <div className="mb-10">
                    <div className="flex items-center gap-2">
                        <img src="/mawadda-logo.png" alt="شعار مركز المودة" className="h-9 w-9 rounded-lg bg-white/95 p-1 object-contain" />
                        <div className="text-xs font-semibold tracking-wide text-white/80">
                            مركز المودة
                        </div>
                    </div>
                    <h1 className="mt-3 text-xl font-bold">
                        للإرشاد الأسري وفض النزاعات
                    </h1>
                </div>

                <nav className="space-y-2 text-sm font-medium text-white/80">
                    <Link
                        href="/dashboard"
                        className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
                    >
                        لوحة القيادة
                    </Link>
                    <button
                        type="button"
                        className="block w-full rounded-lg px-3 py-2 text-right bg-white/90 text-brand-redDark shadow-sm"
                    >
                        الإعدادات
                    </button>
                </nav>
            </aside>

            {/* Main content */}
            <main className="flex-1 bg-slate-50 px-4 py-8 sm:px-8 lg:px-10">
                <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-6">
                    <div>
                        <div className="flex items-center gap-2 text-brand-redDark mb-2">
                            <Link href="/dashboard" className="hover:text-brand-red transition-colors">لوحة القيادة</Link>
                            <span className="text-slate-400">/</span>
                            <span>الإعدادات</span>
                        </div>
                        <h2 className="text-3xl font-bold text-slate-900">
                            إعدادات النظام
                        </h2>
                        <p className="mt-1 text-sm text-slate-600">
                            تخصيص كلمات البحث ومفاتيح الذكاء الاصطناعي لتوليد التقارير.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleSave}
                            disabled={saving || loading}
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-primary px-6 py-2.5 text-sm font-bold text-white shadow-sm transition-colors hover:bg-brand-secondary disabled:opacity-50"
                        >
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                            حفظ التعديلات
                        </button>
                    </div>
                </header>

                {error && (
                    <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-700">
                        تم حفظ الإعدادات بنجاح.
                    </div>
                )}

                {loading ? (
                    <div className="flex h-40 items-center justify-center">
                        <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
                    </div>
                ) : (
                    <div className="mx-auto max-w-4xl space-y-6">

                        {/* SEO Settings */}
                        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                            <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
                                <h3 className="font-bold text-slate-900 flex items-center gap-2">
                                    <Key className="h-5 w-5 text-slate-400" />
                                    الكلمات المفتاحية (SEO)
                                </h3>
                            </div>
                            <div className="p-6">
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    كلمات توليد مدونات الجودة
                                </label>
                                <input
                                    type="text"
                                    dir="ltr"
                                    value={settings["blog_keywords"]?.value || ""}
                                    onChange={(e) => handleChange("blog_keywords", e.target.value)}
                                    placeholder="Quality Management Excellence | ISO, continuous improvement"
                                    className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary text-left bg-slate-50"
                                />
                                <p className="mt-2 text-xs text-slate-500">
                                    يرجى استخدام الصيغة: <code className="bg-slate-100 px-1 py-0.5 rounded text-brand-primary">الكلمة الرئيسية | كلمة فرعية 1, كلمة فرعية 2</code> باللغة الإنجليزية.
                                </p>
                            </div>
                        </div>

                        {/* API Keys (Optional Display) */}
                        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
                            <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
                                <h3 className="font-bold text-slate-900 flex items-center gap-2">
                                    <Key className="h-5 w-5 text-slate-400" />
                                    مفاتيح الربط (API Keys)
                                </h3>
                            </div>
                            <div className="p-6 space-y-5">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">
                                        مفتاح NewsAPI
                                    </label>
                                    <input
                                        type="password"
                                        dir="ltr"
                                        value={settings["news_api_key"]?.value || ""}
                                        onChange={(e) => handleChange("news_api_key", e.target.value)}
                                        placeholder="••••••••••••••••••••••••••••"
                                        className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm focus:border-brand-primary focus:outline-none focus:ring-1 focus:ring-brand-primary text-left bg-slate-50"
                                    />
                                    <p className="mt-1 text-xs text-slate-500">
                                        سيتم استخدام هذا المفتاح لجلب الأخبار إذا تم تفعيله بدلاً من المتغيرات البيئية (.env).
                                    </p>
                                </div>
                            </div>
                        </div>

                    </div>
                )}
            </main>
        </div>
    );
}
