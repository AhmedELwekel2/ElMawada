"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

type Article = {
    title: string;
    description?: string;
    url: string;
    publishedAt?: string;
    source?: { name?: string };
};

type NewsResponse = {
    date: string;
    count: number;
    articles: Article[];
};

// Lightweight Markdown → HTML renderer (headings, bold, tables, lists, blockquote,
// hr, paragraphs). Avoids adding a dependency; tuned for RTL Arabic content.
function renderMarkdown(md: string): string {
    const esc = (s: string) =>
        s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const inline = (s: string) =>
        esc(s)
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/`(.+?)`/g, "<code>$1</code>");

    const lines = md.replace(/\r\n/g, "\n").split("\n");
    const html: string[] = [];
    let i = 0;
    let listOpen = false;
    const closeList = () => {
        if (listOpen) { html.push("</ul>"); listOpen = false; }
    };

    while (i < lines.length) {
        const line = lines[i];
        const trimmed = line.trim();

        // Table block
        if (/^\|.*\|$/.test(trimmed) && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
            closeList();
            const header = trimmed.slice(1, -1).split("|").map((c) => c.trim());
            i += 2;
            const rows: string[][] = [];
            while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) {
                rows.push(lines[i].trim().slice(1, -1).split("|").map((c) => c.trim()));
                i++;
            }
            html.push('<div class="overflow-x-auto my-4"><table class="w-full border-collapse text-sm">');
            html.push('<thead><tr>' + header.map((h) => `<th class="border border-slate-300 bg-brand-redSoft px-3 py-2 text-right font-semibold text-brand-redDark">${inline(h)}</th>`).join("") + "</tr></thead>");
            html.push("<tbody>" + rows.map((r) => "<tr>" + r.map((c) => `<td class="border border-slate-200 px-3 py-2 text-right align-top text-slate-700">${inline(c)}</td>`).join("") + "</tr>").join("") + "</tbody>");
            html.push("</table></div>");
            continue;
        }

        if (/^#{1,6}\s+/.test(trimmed)) {
            closeList();
            const level = (trimmed.match(/^#+/) as RegExpMatchArray)[0].length;
            const text = inline(trimmed.replace(/^#+\s+/, ""));
            if (level === 1) html.push(`<h1 class="mt-2 mb-4 text-2xl font-extrabold text-brand-redDark border-b-2 border-brand-red/30 pb-2">${text}</h1>`);
            else if (level === 2) html.push(`<h2 class="mt-7 mb-3 text-xl font-bold text-brand-redDark">${text}</h2>`);
            else html.push(`<h3 class="mt-5 mb-2 text-lg font-semibold text-slate-800">${text}</h3>`);
        } else if (/^>\s?/.test(trimmed)) {
            closeList();
            html.push(`<blockquote class="my-3 border-r-4 border-brand-red bg-brand-redSoft/60 px-4 py-2 text-brand-redDark font-medium rounded">${inline(trimmed.replace(/^>\s?/, ""))}</blockquote>`);
        } else if (/^(-{3,}|\*{3,})$/.test(trimmed)) {
            closeList();
            html.push('<hr class="my-6 border-slate-200" />');
        } else if (/^[-*+]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
            if (!listOpen) { html.push('<ul class="my-3 space-y-1.5 pr-5 list-disc marker:text-brand-red">'); listOpen = true; }
            html.push(`<li class="text-slate-700 leading-relaxed">${inline(trimmed.replace(/^([-*+]|\d+\.)\s+/, ""))}</li>`);
        } else if (trimmed === "") {
            closeList();
        } else {
            closeList();
            html.push(`<p class="my-3 leading-relaxed text-slate-700">${inline(trimmed)}</p>`);
        }
        i++;
    }
    closeList();
    return html.join("\n");
}

    export default function Dashboard() {
    const { token, user } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<"daily" | "weekly" | "monthly" | "pdf-viewer" | "reports" | "campaign">(
        "daily",
    );
    const [data, setData] = useState<NewsResponse | null>(null);
    
    // Handle initial tab from URL query parameter
    useEffect(() => {
        const searchParams = new URLSearchParams(window.location.search);
        const tab = searchParams.get('tab') as "daily" | "weekly" | "monthly" | "pdf-viewer" | "reports" | "campaign";
        if (tab) {
            setActiveTab(tab);
        }
    }, []);
    const [loading, setLoading] = useState(false);
    const [reportLoading, setReportLoading] = useState(false);
    const [magazineLoading, setMagazineLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    const [reports, setReports] = useState<any[]>([]);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [notifications, setNotifications] = useState<any[]>([]);
    const [showNotifications, setShowNotifications] = useState(false);
    const [campaignLoading, setCampaignLoading] = useState(false);
    const [campaign, setCampaign] = useState<{ title: string; date: string; articles_analyzed?: number; content: string } | null>(null);

    // Whenever the active tab changes, clear current data; user must click "تحديث البيانات"
    useEffect(() => {
        setData(null);
        setError(null);
    }, [activeTab]);

    const handleFetch = async (scope: "daily" | "weekly" | "monthly") => {
        try {
            setError(null);
            setLoading(true);
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/news/${scope}`, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const json = (await res.json()) as NewsResponse;
            setData(json);
        } catch (e: any) {
            setError(e?.message ?? "خطأ غير متوقع");
        } finally {
            setLoading(false);
        }
    };

    // Update URL when tab changes
    useEffect(() => {
        const url = new URL(window.location.href);
        url.searchParams.set('tab', activeTab);
        window.history.replaceState({}, '', url);
    }, [activeTab]);

    const handleGenerateReport = async (scope: "daily" | "weekly" | "monthly") => {
        // Check if user is a viewer (not approved for PDF generation)
        if (user?.role === "viewer") {
            setError("أنت غير معتمد لإنشاء تقارير PDF بعد. يرجى التواصل مع المشرف لترقية حسابك.");
            return;
        }
        try {
            setError(null);
            setReportLoading(true);
            console.log("Generating report...");
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(
                `${API_BASE}/api/reports/${scope}-blog`,
                {
                    method: "POST",
                    headers,
                },
            );
            console.log("Response status:", res.status);
            if (!res.ok) {
                // Try to read JSON error if available
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) {
                        message = json.detail;
                    }
                } catch {
                    // ignore parse error, keep default message
                }
                console.error("Fetch failed:", message);
                throw new Error(message);
            }

            const blob = await res.blob();
            console.log("Blob created, size:", blob.size);
            const url = window.URL.createObjectURL(blob);
            console.log("PDF URL generated:", url);
            setPdfUrl(url);
            setActiveTab("pdf-viewer" as any); // Force switch to PDF viewer tab
            // Refresh reports and notifications after report generation
            fetchReports();
            fetchNotifications();
        } catch (e: any) {
            console.error("Error in handleGenerateReport:", e);
            setError(
                e?.message
                    ? `خطأ أثناء توليد تقرير PDF: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد تقرير PDF",
            );
        } finally {
            setReportLoading(false);
        }
    };

    const handleGenerateMagazine = async () => {
        // Check if user is a viewer (not approved for PDF generation)
        if (user?.role === "viewer") {
            setError("أنت غير معتمد لإنشاء تقارير PDF بعد. يرجى التواصل مع المشرف لترقية حسابك.");
            return;
        }
        try {
            setError(null);
            setMagazineLoading(true);
            console.log("Generating magazine...");
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(
                `${API_BASE}/api/reports/magazine`,
                { 
                    method: "POST",
                    headers,
                },
            );
            console.log("Magazine response status:", res.status);
            if (!res.ok) {
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) message = json.detail;
                } catch { /* ignore */ }
                throw new Error(message);
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            setPdfUrl(url);
            setActiveTab("pdf-viewer");
            // Refresh notifications after magazine generation
            fetchNotifications();
            fetchReports();
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء توليد المجلة: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد المجلة",
            );
            // Refresh notifications even on error (to show failed status)
            fetchNotifications();
            fetchReports();
        } finally {
            setMagazineLoading(false);
        }
    };

    const handleGenerateCampaign = async () => {
        if (user?.role !== "admin") {
            setError("توليد الحملة التوعوية متاح للمشرف فقط.");
            return;
        }
        try {
            setError(null);
            setCampaignLoading(true);
            setActiveTab("campaign");
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/reports/awareness-campaign`, {
                method: "POST",
                headers,
            });
            if (!res.ok) {
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) message = json.detail;
                } catch { /* ignore */ }
                throw new Error(message);
            }
            const json = await res.json();
            setCampaign(json);
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء توليد الحملة التوعوية: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد الحملة التوعوية",
            );
        } finally {
            setCampaignLoading(false);
        }
    };

    const fetchReports = async (silent: boolean = false) => {
        try {
            if (!silent) setReportsLoading(true);
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/reports`, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            setReports(data.reports);
        } catch (e: any) {
            console.error("Error fetching reports:", e);
        } finally {
            if (!silent) setReportsLoading(false);
        }
    };

    const fetchNotifications = async () => {
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/notifications`, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            setNotifications(data.notifications);
        } catch (e: any) {
            console.error("Error fetching notifications:", e);
        }
    };

    const handleGeneratePersistentReport = async (reportType: string) => {
        // Check if user is a viewer (not approved for PDF generation)
        if (user?.role === "viewer") {
            setError("أنت غير معتمد لإنشاء تقارير PDF بعد. يرجى التواصل مع المشرف لترقية حسابك.");
            return;
        }
        try {
            setError(null);
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/reports/generate/${reportType}`, {
                method: "POST",
                headers,
            });
            if (!res.ok) {
                let message = `HTTP ${res.status}`;
                try {
                    const json = (await res.json()) as { detail?: string };
                    if (json?.detail) message = json.detail;
                } catch { /* ignore */ }
                throw new Error(message);
            }
            const data = await res.json();
            // Show success message
            alert(data.message);
            // Refresh reports and notifications
            fetchReports();
            fetchNotifications();
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء توليد التقرير: ${e.message}`
                    : "خطأ غير متوقع أثناء توليد التقرير",
            );
        }
    };

    const handleDownloadReport = async (reportId: number) => {
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/reports/${reportId}`, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${reportId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء تحميل التقرير: ${e.message}`
                    : "خطأ غير متوقع أثناء تحميل التقرير",
            );
        }
    };

    const handleDeleteReport = async (reportId: number) => {
        if (!confirm('هل أنت متأكد من حذف هذا التقرير؟')) return;
        
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            };
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const res = await fetch(`${API_BASE}/api/reports/${reportId}`, {
                method: "DELETE",
                headers,
            });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            // Refresh reports
            fetchReports();
        } catch (e: any) {
            setError(
                e?.message
                    ? `خطأ أثناء حذف التقرير: ${e.message}`
                    : "خطأ غير متوقع أثناء حذف التقرير",
            );
        }
    };

    // Load reports and notifications when component mounts
    useEffect(() => {
        if (token) {
            fetchReports();
            fetchNotifications();
        }
    }, [token]);

    // Auto-refresh notifications every 30 seconds
    useEffect(() => {
        if (!token) return;
        
        const interval = setInterval(() => {
            fetchNotifications();
        }, 30000);
        
        return () => clearInterval(interval);
    }, [token]);

    // Poll for pending reports status updates (silent - no loading flicker)
    useEffect(() => {
        if (!token || activeTab !== "reports") return;

        const hasPending = reports.some((r) => r.status === "pending");
        if (!hasPending) return;

        const pollInterval = setInterval(() => {
            fetchReports(true);
        }, 5000);

        return () => clearInterval(pollInterval);
    }, [token, activeTab, reports]);

    return (
        <ProtectedRoute>
            <div className="flex min-h-screen bg-slate-100 font-sans" dir="rtl">
            {/* Sidebar */}
            <aside className="w-64 flex-shrink-0 border-l border-brand-red/20 bg-gradient-to-b from-[#1C5E58] to-[#2E9E95] px-6 py-8 text-white shadow-xl">
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
                    <a
                        href="/dashboard/usage"
                        className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
                    >
                        إحصائيات الاستخدام
                    </a>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "daily"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("daily")}
                    >
                        الأخبار اليومية
                    </button>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "weekly"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("weekly")}
                    >
                        الأخبار الأسبوعية
                    </button>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "monthly"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("monthly")}
                    >
                        الأخبار الشهرية
                    </button>
                    <button
                        type="button"
                        className={`block w-full rounded-lg px-3 py-2 text-right ${activeTab === "reports"
                            ? "bg-white/90 text-brand-redDark shadow-sm"
                            : "hover:bg-white/10"
                            }`}
                        onClick={() => setActiveTab("reports")}
                    >
                        توليد تقارير بالذكاء الاصطناعي
                    </button>
                    {user?.role === "admin" && (
                        <a
                            href="/admin/users"
                            className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10 bg-white/20 text-brand-redDark shadow-sm"
                        >
                            إدارة المستخدمين
                        </a>
                    )}
                </nav>

                <div className="mt-10 rounded-xl bg-white/10 p-4 text-xs text-white/90">
                    <div className="mb-1 font-semibold text-white">
                        ملاحظة الاستخدام
                    </div>
                    <p>
                        يتم جمع المحتوى من مصادر متخصصة في الأسرة والمجتمع والصحة النفسية، مع
                        فلترة ذكية للمحتوى وتحليله لدعم عملية اتخاذ القرار.
                    </p>
                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 bg-slate-50 px-4 py-8 sm:px-8 lg:px-10">
                {/* Not Approved Banner for Viewer Users */}
                {user?.role === "viewer" && (
                    <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-4 shadow-sm">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-amber-100">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-amber-800">حسابك غير معتمد بعد</h3>
                                <p className="text-xs text-amber-700 mt-1">
                                    يمكنك تصفح الأخبار والبحث فيها، لكن لا يمكنك إنشاء تقارير PDF. يرجى التواصل مع المشرف لترقية حسابك إلى مستخدم معتمد.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                        <h2 className="text-2xl font-bold text-brand-redDark">
                            {activeTab === "daily" && "الأخبار النفسية والأسرية اليومية"}
                            {activeTab === "weekly" && "الأخبار النفسية والأسرية الأسبوعية"}
                            {activeTab === "monthly" && "الأخبار النفسية والأسرية الشهرية"}
                            {activeTab === "reports" && "توليد تقارير بالذكاء الاصطناعي"}
                            {activeTab === "campaign" && "الحملة التسويقية التوعوية"}
                        </h2>
                        {/* Notifications Bell */}
                        <div className="relative">
                            <button
                                onClick={() => setShowNotifications(!showNotifications)}
                                className="relative rounded-full p-2 text-slate-600 hover:bg-slate-200"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                </svg>
                                {notifications.length > 0 && (
                                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs text-white">
                                        {notifications.length}
                                    </span>
                                )}
                            </button>
                            
                            {/* Notifications Dropdown */}
                            {showNotifications && (
                                <div className="absolute right-0 top-8 z-10 w-80 rounded-lg border border-slate-200 bg-white shadow-lg">
                                    <div className="border-b border-slate-200 px-4 py-3">
                                        <h3 className="font-semibold text-slate-900">الإشعارات</h3>
                                    </div>
                                    <div className="max-h-64 overflow-y-auto">
                                        {notifications.length === 0 ? (
                                            <div className="px-4 py-3 text-sm text-slate-500">
                                                لا توجد إشعارات جديدة
                                            </div>
                                        ) : (
                                            notifications.map((notification) => (
                                                <div key={notification.id} className="border-b border-slate-100 px-4 py-3 last:border-b-0">
                                                    <div className="flex items-start gap-3">
                                                        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                                                            notification.type === 'report_generated' ? 'bg-green-100 text-green-600' :
                                                            notification.type === 'report_failed' ? 'bg-red-100 text-red-600' :
                                                            'bg-blue-100 text-blue-600'
                                                        }`}>
                                                            {notification.type === 'report_generated' && (
                                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                </svg>
                                                            )}
                                                            {notification.type === 'report_failed' && (
                                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                </svg>
                                                            )}
                                                            {notification.type === 'report_pending' && (
                                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                </svg>
                                                            )}
                                                        </div>
                                                        <div className="flex-1">
                                                            <div className="text-sm font-medium text-slate-900">{notification.title}</div>
                                                            <div className="text-xs text-slate-600">{notification.message}</div>
                                                            <div className="text-xs text-slate-400 mt-1">
                                                                {new Date(notification.created_at).toLocaleString('ar-SA')}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                    <div className="border-t border-slate-200 px-4 py-2">
                                        <button
                                            onClick={() => setShowNotifications(false)}
                                            className="text-xs text-slate-600 hover:text-slate-900"
                                        >
                                            إغلاق
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                        {activeTab === "daily" && "أحدث الممارسات والرؤى في الأسرة والمجتمع والجانب النفسي."}
                        {activeTab === "weekly" && "أحدث الممارسات والرؤى في الأسرة والمجتمع والجانب النفسي."}
                        {activeTab === "monthly" && "أحدث الممارسات والرؤى في الأسرة والمجتمع والجانب النفسي."}
                        {activeTab === "reports" && "جميع تقاريرك المحفوظة مع إمكانية إدارة وتنزيل التقارير."}
                        {activeTab === "campaign" && "استراتيجية حملة تسويقية توعوية متكاملة مستخلصة من أخبار الشهر."}
                    </p>
                    <div className="flex gap-2 text-sm text-slate-600">
                        {data && (
                            <span className="rounded-full bg-brand-redSoft px-3 py-1 text-brand-redDark">
                                {data.count}{" "}
                                {activeTab === "daily"
                                    ? "مقال اليوم"
                                    : activeTab === "weekly"
                                        ? "مقال خلال الأسبوع"
                                        : "مقال خلال الشهر"}
                            </span>
                        )}
                        <button
                            type="button"
                            onClick={() => handleFetch(activeTab === "pdf-viewer" || activeTab === "reports" || activeTab === "campaign" ? "daily" : activeTab)}
                            className="rounded-full bg-brand-red px-4 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-brand-redDark disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={loading || activeTab === "pdf-viewer" || activeTab === "reports" || activeTab === "campaign"}
                        >
                            {loading ? "جارٍ التحديث..." : "جلب من قاعدة البيانات"}
                        </button>
                    </div>
                </header>


                {loading && (
                    <div className="flex h-40 items-center justify-center">
                        <div className="h-9 w-9 animate-spin rounded-full border-2 border-brand-red border-t-transparent" />
                    </div>
                )}

                {error && !loading && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                        حدث خطأ أثناء جلب المحتوى: {error}
                    </div>
                )}

                {/* PDF Viewer Tab */}
                {activeTab === "pdf-viewer" && pdfUrl && (
                    <div className="flex h-[80vh] w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ring-1 ring-slate-900/5">
                        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-6 py-4">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-red/10 text-brand-red">
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                    </svg>
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-slate-800">التقرير الذكي بصيغة PDF</h3>
                                    <p className="text-xs text-slate-500">تم توليد التقرير بنجاح، يمكنك القراءة أدناه أو التحميل.</p>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <a
                                    href={pdfUrl}
                                    download={`Family_Society_Report_${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.pdf`}
                                    className="flex items-center gap-2 rounded-lg bg-brand-red px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-redDark hover:shadow-md"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    تحميل
                                </a>
                                <button
                                    onClick={() => {
                                        window.URL.revokeObjectURL(pdfUrl);
                                        setPdfUrl(null);
                                        setActiveTab("daily");
                                    }}
                                    className="rounded-lg bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-200 hover:text-slate-900"
                                >
                                    إغلاق وعودة
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 bg-slate-100/50 p-0 sm:p-2">
                            <iframe
                                src={pdfUrl}
                                className="h-full w-full rounded-xl border border-slate-200 bg-white"
                                title="PDF Report"
                            />
                        </div>
                    </div>
                )}

                {!loading && !error && data && activeTab !== "pdf-viewer" && (
                    <section className="space-y-4">
                        {data.articles.length === 0 && (
                            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
                                لا توجد محتوى متاح حالياً. سيقوم النظام بجلب المحتوى تلقائياً كل 6 ساعات.
                            </div>
                        )}

                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                            {data.articles.map((article, idx) => (
                                <article
                                    key={idx}
                                    className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-[0_10px_30px_rgba(185,0,25,0.25)]"
                                >
                                    <div>
                                        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-brand-red">
                                            {article.source?.name || "مصدر"}
                                        </div>
                                        <h3 className="mb-2 line-clamp-3 text-sm font-bold text-slate-900" dir="auto">
                                            {article.title}
                                        </h3>
                                        {article.description && (
                                            <p className="mb-3 line-clamp-3 text-xs leading-relaxed text-slate-600" dir="auto">
                                                {article.description}
                                            </p>
                                        )}
                                    </div>
                                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                                        <span>
                                            {article.publishedAt
                                                ? new Date(article.publishedAt).toLocaleString("ar-SA", {
                                                    dateStyle: "medium",
                                                })
                                                : ""}
                                        </span>
                                        <a
                                            href={article.url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="rounded-full bg-brand-redSoft px-3 py-1 text-[11px] font-medium text-brand-red hover:bg-brand-red/10"
                                        >
                                            قراءة المقال
                                        </a>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                )}

                {/* Reports Tab */}
                {activeTab === "reports" && (
                    <section className="space-y-6">
                        {/* Pending Reports Info Banner */}
                        {reports.some((r) => r.status === "pending") && (
                            <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 shadow-sm">
                                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-100">
                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                                </div>
                                <div>
                                    <h4 className="text-sm font-bold text-blue-800">جاري إنشاء تقرير...</h4>
                                    <p className="text-xs text-blue-600">يتم الآن توليد التقرير بالذكاء الاصطناعي. سيتم تحديث الحالة تلقائياً عند الاكتمال.</p>
                                </div>
                            </div>
                        )}
                        <div className={`grid gap-4 ${user?.role === "admin" ? "md:grid-cols-5" : "md:grid-cols-4"}`}>
                            <button
                                onClick={() => handleGeneratePersistentReport("daily")}
                                className="rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm transition hover:shadow-md"
                            >
                                <div className="mb-2 text-2xl">📊</div>
                                <h3 className="font-semibold text-slate-900">تقرير يومي</h3>
                                <p className="text-xs text-slate-600">إنشاء تقرير يومي محفوظ</p>
                            </button>
                            <button
                                onClick={() => handleGeneratePersistentReport("weekly")}
                                className="rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm transition hover:shadow-md"
                            >
                                <div className="mb-2 text-2xl">📈</div>
                                <h3 className="font-semibold text-slate-900">تقرير أسبوعي</h3>
                                <p className="text-xs text-slate-600">إنشاء تقرير أسبوعي محفوظ</p>
                            </button>
                            <button
                                onClick={() => handleGeneratePersistentReport("monthly")}
                                className="rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm transition hover:shadow-md"
                            >
                                <div className="mb-2 text-2xl">📉</div>
                                <h3 className="font-semibold text-slate-900">تقرير شهري</h3>
                                <p className="text-xs text-slate-600">إنشاء تقرير شهري محفوظ</p>
                            </button>
                            <button
                                onClick={() => handleGeneratePersistentReport("magazine")}
                                className="rounded-lg border border-slate-200 bg-white p-4 text-center shadow-sm transition hover:shadow-md"
                            >
                                <div className="mb-2 text-2xl">📰</div>
                                <h3 className="font-semibold text-slate-900">مجلة شهرية</h3>
                                <p className="text-xs text-slate-600">إنشاء مجلة شهرية محفوظة</p>
                            </button>
                            {user?.role === "admin" && (
                                <button
                                    onClick={handleGenerateCampaign}
                                    disabled={campaignLoading}
                                    className="rounded-lg border border-brand-red/30 bg-brand-redSoft p-4 text-center shadow-sm transition hover:shadow-md disabled:opacity-60"
                                >
                                    <div className="mb-2 text-2xl">📣</div>
                                    <h3 className="font-semibold text-brand-redDark">حملة توعية</h3>
                                    <p className="text-xs text-slate-600">{campaignLoading ? "جارٍ التوليد..." : "استراتيجية تسويقية من أخبار الشهر"}</p>
                                </button>
                            )}
                        </div>

                        <div className="rounded-lg border border-slate-200 bg-white p-6">
                            <h3 className="mb-4 text-lg font-semibold text-slate-900">التقارير المحفوظة</h3>
                            
                            {reportsLoading && (
                                <div className="flex h-20 items-center justify-center">
                                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-red border-t-transparent" />
                                </div>
                            )}

                            {!reportsLoading && reports.length === 0 && (
                                <div className="text-center py-8">
                                    <div className="text-4xl mb-2">📁</div>
                                    <p className="text-slate-600">لا توجد تقارير محفوظة بعد</p>
                                    <p className="text-sm text-slate-500 mt-1">أنشئ أول تقرير لك باستخدام الأزرار أعلاه</p>
                                </div>
                            )}

                            {!reportsLoading && reports.length > 0 && (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-slate-200">
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">العنوان</th>
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">النوع</th>
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">الحالة</th>
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">الحجم</th>
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">التاريخ</th>
                                                <th className="pb-3 pr-4 text-right font-medium text-slate-900">الإجراءات</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {reports.map((report) => (
                                                <tr key={report.id} className="border-b border-slate-100 last:border-b-0">
                                                    <td className="py-3 pr-4">
                                                        <div className="font-medium text-slate-900">{report.title}</div>
                                                    </td>
                                                    <td className="py-3 pr-4">
                                                        <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-slate-100 text-slate-800">
                                                            {report.report_type}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 pr-4">
                                                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium ${
                                                            report.status === 'completed' ? 'bg-green-100 text-green-800' :
                                                            report.status === 'pending' ? 'bg-blue-100 text-blue-800' :
                                                            'bg-red-100 text-red-800'
                                                        }`}>
                                                            {report.status === 'pending' && (
                                                                <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent inline-block" />
                                                            )}
                                                            {report.status === 'completed' && '✓ '}
                                                            {report.status === 'completed' && 'مكتمل'}
                                                            {report.status === 'pending' && 'قيد الإنشاء'}
                                                            {report.status === 'failed' && '✗ '}
                                                            {report.status === 'failed' && 'فشل'}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 pr-4">
                                                        {report.file_size ? `${(report.file_size / 1024).toFixed(1)} KB` : '-'}
                                                    </td>
                                                    <td className="py-3 pr-4">
                                                        {new Date(report.created_at).toLocaleDateString('ar-SA')}
                                                    </td>
                                                    <td className="py-3 pr-4">
                                                        <div className="flex gap-2">
                                                            {report.status === 'completed' && (
                                                                <button
                                                                    onClick={() => handleDownloadReport(report.id)}
                                                                    className="text-blue-600 hover:text-blue-800"
                                                                    title="تحميل"
                                                                >
                                                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                                    </svg>
                                                                </button>
                                                            )}
                                                            <button
                                                                onClick={() => handleDeleteReport(report.id)}
                                                                className="text-red-600 hover:text-red-800"
                                                                title="حذف"
                                                            >
                                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                </svg>
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </section>
                )}
                {/* Awareness Campaign Tab */}
                {activeTab === "campaign" && (
                    <section className="space-y-4">
                        {campaignLoading && (
                            <div className="flex h-64 flex-col items-center justify-center gap-4 rounded-2xl border border-slate-200 bg-white shadow-sm">
                                <div className="h-10 w-10 animate-spin rounded-full border-2 border-brand-red border-t-transparent" />
                                <p className="text-sm text-slate-600">جارٍ تحليل أخبار الشهر وبناء الاستراتيجية التسويقية... قد يستغرق ذلك دقيقة إلى ثلاث دقائق.</p>
                            </div>
                        )}

                        {!campaignLoading && !campaign && !error && (
                            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
                                <div className="mb-3 text-4xl">📣</div>
                                <p className="text-slate-600">اضغط زر «حملة توعية» في تبويب توليد التقارير لبناء الاستراتيجية.</p>
                                <button
                                    onClick={handleGenerateCampaign}
                                    className="mt-4 rounded-full bg-brand-red px-5 py-2 text-sm font-medium text-white hover:bg-brand-redDark"
                                >
                                    توليد الحملة الآن
                                </button>
                            </div>
                        )}

                        {!campaignLoading && campaign && (
                            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm ring-1 ring-slate-900/5">
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 bg-slate-50/60 px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <img src="/mawadda-logo.png" alt="شعار مركز المودة" className="h-10 w-10 object-contain" />
                                        <div>
                                            <h3 className="text-lg font-bold text-brand-redDark">{campaign.title}</h3>
                                            <p className="text-xs text-slate-500">
                                                {new Date(campaign.date).toLocaleDateString("ar-SA", { dateStyle: "long" })}
                                                {typeof campaign.articles_analyzed === "number" && ` • تحليل ${campaign.articles_analyzed} مقالاً`}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={handleGenerateCampaign}
                                            className="rounded-lg bg-brand-red px-4 py-2 text-sm font-medium text-white hover:bg-brand-redDark"
                                        >
                                            إعادة التوليد
                                        </button>
                                        <button
                                            onClick={() => { window.print(); }}
                                            className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
                                        >
                                            طباعة / حفظ PDF
                                        </button>
                                    </div>
                                </div>
                                <article
                                    className="px-6 py-6 sm:px-10 sm:py-8 leading-relaxed"
                                    dir="rtl"
                                    dangerouslySetInnerHTML={{ __html: renderMarkdown(campaign.content) }}
                                />
                            </div>
                        )}
                    </section>
                )}
            </main>


            </div>
        </ProtectedRoute>
    );
}
