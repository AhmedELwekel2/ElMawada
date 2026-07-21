"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../../contexts/AuthContext";
import ProtectedRoute from "../../components/ProtectedRoute";
import { BarChart3, FileText, Calendar, TrendingUp, AlertCircle, RefreshCw, Newspaper } from "lucide-react";

interface UsageStats {
  daily_limit: number;
  weekly_limit: number;
  monthly_limit: number;
  magazine_limit: number;
  current_month: string;
  usage: {
    daily: number;
    weekly: number;
    monthly: number;
    magazine: number;
  };
}

interface UsageRecord {
  id: number;
  report_type: string;
  month: string;
  count: number;
  created_at: string;
  updated_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function UsagePage() {
  const { token, user } = useAuth();
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [usageRecords, setUsageRecords] = useState<UsageRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchUsageData();
  }, [token]);

  const fetchUsageData = async () => {
    try {
      setLoading(true);
      setError("");

      // Fetch usage limits
      const limitsResponse = await fetch(`${API_BASE}/api/auth/usage-limits`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      let hasError = false;

      if (limitsResponse.ok) {
        const limitsData = await limitsResponse.json();
        setUsageStats(limitsData);
      } else {
        hasError = true;
      }

      // Fetch usage records
      const recordsResponse = await fetch(`${API_BASE}/api/auth/usage-records`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (recordsResponse.ok) {
        const recordsData = await recordsResponse.json();
        setUsageRecords(recordsData.records || []);
      } else {
        hasError = true;
      }

      // Only set error if both requests failed
      if (hasError) {
        setError("فشل في جلب بيانات التقارير");
      } else {
        setError(""); // Clear error if at least one request succeeded
      }

    } catch (err) {
      setError("حدث خطأ أثناء الاتصال بالخادم");
    } finally {
      setLoading(false);
    }
  };

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === 0) return 0;
    return Math.round((used / limit) * 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getReportTypeLabel = (type: string) => {
    switch (type) {
      case 'daily': return 'تقرير يومي';
      case 'weekly': return 'تقرير أسبوعي';
      case 'monthly': return 'تقرير شهري';
      case 'magazine': return 'مجلة شهرية';
      default: return type;
    }
  };

  const getMonthName = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const months = [
      'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ];
    return `${months[parseInt(month) - 1]} ${year}`;
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-slate-100 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-red"></div>
        </div>
      </ProtectedRoute>
    );
  }

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
              className="block w-full rounded-lg px-3 py-2 text-right bg-white/90 text-brand-redDark shadow-sm"
            >
              إحصائيات الاستخدام
            </a>
            <a
              href="/dashboard?tab=daily"
              className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
            >
              الأخبار اليومية
            </a>
            <a
              href="/dashboard?tab=weekly"
              className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
            >
              الأخبار الأسبوعية
            </a>
            <a
              href="/dashboard?tab=monthly"
              className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
            >
              الأخبار الشهرية
            </a>
            <a
              href="/dashboard?tab=reports"
              className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
            >
              توليد تقارير بالذكاء الاصطناعي
            </a>
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

        {/* Main Content */}
        <main className="flex-1 bg-slate-50 px-4 py-8 sm:px-8 lg:px-10">
          <header className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-brand-redDark">إحصائيات التقارير</h1>
              <button
                onClick={fetchUsageData}
                className="rounded-full bg-brand-red px-4 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-brand-redDark"
              >
                تحديث البيانات
              </button>
            </div>
          </header>

          <div className="space-y-6">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 text-red-500 ml-2" />
                <h3 className="text-sm font-medium text-red-800">{error}</h3>
              </div>
            </div>
          )}

          {usageStats && (
            <>
              {/* Usage Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
                {/* Daily Reports */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      <Calendar className="h-6 w-6 text-blue-500 ml-2" />
                      <h3 className="text-lg font-semibold text-gray-900">التقارير اليومية</h3>
                    </div>
                    <span className="text-sm text-gray-500">
                      {usageStats.usage.daily} / {usageStats.daily_limit}
                    </span>
                  </div>
                  
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>المستخدم</span>
                      <span>{getUsagePercentage(usageStats.usage.daily, usageStats.daily_limit)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(usageStats.usage.daily, usageStats.daily_limit))}`}
                        style={{ width: `${getUsagePercentage(usageStats.usage.daily, usageStats.daily_limit)}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    المتبقي: {Math.max(0, usageStats.daily_limit - usageStats.usage.daily)}
                  </div>
                </div>

                {/* Weekly Reports */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      <TrendingUp className="h-6 w-6 text-green-500 ml-2" />
                      <h3 className="text-lg font-semibold text-gray-900">التقارير الأسبوعية</h3>
                    </div>
                    <span className="text-sm text-gray-500">
                      {usageStats.usage.weekly} / {usageStats.weekly_limit}
                    </span>
                  </div>
                  
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>المستخدم</span>
                      <span>{getUsagePercentage(usageStats.usage.weekly, usageStats.weekly_limit)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(usageStats.usage.weekly, usageStats.weekly_limit))}`}
                        style={{ width: `${getUsagePercentage(usageStats.usage.weekly, usageStats.weekly_limit)}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    المتبقي: {Math.max(0, usageStats.weekly_limit - usageStats.usage.weekly)}
                  </div>
                </div>

                {/* Monthly Reports */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      <FileText className="h-6 w-6 text-purple-500 ml-2" />
                      <h3 className="text-lg font-semibold text-gray-900">التقارير الشهرية</h3>
                    </div>
                    <span className="text-sm text-gray-500">
                      {usageStats.usage.monthly} / {usageStats.monthly_limit}
                    </span>
                  </div>
                  
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>المستخدم</span>
                      <span>{getUsagePercentage(usageStats.usage.monthly, usageStats.monthly_limit)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(usageStats.usage.monthly, usageStats.monthly_limit))}`}
                        style={{ width: `${getUsagePercentage(usageStats.usage.monthly, usageStats.monthly_limit)}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    المتبقي: {Math.max(0, usageStats.monthly_limit - usageStats.usage.monthly)}
                  </div>
                </div>

                {/* Magazine Reports */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      <Newspaper className="h-6 w-6 text-emerald-500 ml-2" />
                      <h3 className="text-lg font-semibold text-gray-900">المجلات الشهرية</h3>
                    </div>
                    <span className="text-sm text-gray-500">
                      {usageStats.usage.magazine} / {usageStats.magazine_limit}
                    </span>
                  </div>
                  
                  <div className="mb-2">
                    <div className="flex justify-between text-sm text-gray-600 mb-1">
                      <span>المستخدم</span>
                      <span>{getUsagePercentage(usageStats.usage.magazine, usageStats.magazine_limit)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${getUsageColor(getUsagePercentage(usageStats.usage.magazine, usageStats.magazine_limit))}`}
                        style={{ width: `${getUsagePercentage(usageStats.usage.magazine, usageStats.magazine_limit)}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-600">
                    المتبقي: {Math.max(0, usageStats.magazine_limit - usageStats.usage.magazine)}
                  </div>
                </div>

              </div>

              {/* Usage Alerts */}
              {(getUsagePercentage(usageStats.usage.daily, usageStats.daily_limit) >= 90 ||
                getUsagePercentage(usageStats.usage.weekly, usageStats.weekly_limit) >= 90 ||
                getUsagePercentage(usageStats.usage.monthly, usageStats.monthly_limit) >= 90 ||
                getUsagePercentage(usageStats.usage.magazine, usageStats.magazine_limit) >= 90) && (
                <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <AlertCircle className="h-5 w-5 text-yellow-600 ml-2" />
                    <h3 className="text-sm font-medium text-yellow-800">
                      تنبيه: أنت على وشك الوصول إلى الحد الأقصى للاستخدام
                    </h3>
                  </div>
                  <p className="mt-2 text-sm text-yellow-700">
                    لقد استخدمت معظم رصيدك المتاح. يرجى مراجعة استخدامك أو الاتصال بالدعم الفني إذا كنت بحاجة إلى زيادة الحدود.
                  </p>
                </div>
              )}

              {/* Usage History */}
              <div className="bg-white shadow rounded-lg">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">سجل التقارير</h3>
                </div>
                
                {usageRecords.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>لا يوجد سجل تقارير متاح بعد</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            نوع التقرير
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            الشهر
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            عدد التقارير
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            آخر استخدام
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {usageRecords.map((record) => (
                          <tr key={record.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                                {getReportTypeLabel(record.report_type)}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {getMonthName(record.month)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {record.count}
                            </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {new Date(record.updated_at || record.created_at).toLocaleDateString('ar-SA')}
                              </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* User Info */}
              <div className="mt-8 bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">معلومات حسابك</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">اسم المستخدم:</span>
                    <span className="text-gray-900 mr-2">{user?.username}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">الدور:</span>
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full mr-2 ${
                      user?.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800' 
                        : user?.role === 'editor'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {user?.role === 'admin' ? 'مشرف' : user?.role === 'editor' ? 'محرر' : 'مشاهد'}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}