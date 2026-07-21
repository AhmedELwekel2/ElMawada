"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../../contexts/AuthContext";
import ProtectedRoute from "../../components/ProtectedRoute";
import { Shield, Edit, Trash2, Users, BarChart3, Activity, RefreshCw, FileText, Calendar } from "lucide-react";

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserUsage {
  daily_limit: number;
  weekly_limit: number;
  monthly_limit: number;
  magazine_limit: number;
  daily_used: number;
  weekly_used: number;
  monthly_used: number;
  magazine_used: number;
}

interface UserUsageStats {
  user_id: number;
  username: string;
  full_name: string;
  role: string;
  current_month: string;
  limits: {
    daily: number;
    weekly: number;
    monthly: number;
    magazine: number;
  };
  current_month_usage: {
    daily: number;
    weekly: number;
    monthly: number;
    magazine: number;
  };
  all_time_usage: {
    daily: number;
    weekly: number;
    monthly: number;
    magazine: number;
  };
  usage_records: Array<{
    id: number;
    report_type: string;
    month: string;
    count: number;
    created_at: string;
  }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function AdminUsersPage() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userUsage, setUserUsage] = useState<UserUsage | null>(null);
  const [userUsageStats, setUserUsageStats] = useState<UserUsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState({
    is_active: true,
    role: "user"
  });

  useEffect(() => {
    if (user?.role !== "admin") {
      return;
    }
    fetchUsers();
  }, [token, user]);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/users`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
      } else {
        setError("فشل في جلب قائمة المستخدمين");
      }
    } catch (err) {
      setError("حدث خطأ أثناء الاتصال بالخادم");
    } finally {
      setLoading(false);
    }
  };

  const fetchUserUsage = async (userId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/users/${userId}/usage-stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Store full stats data (including usage_records)
        setUserUsageStats(data);
        // Transform data to match UserUsage interface
        setUserUsage({
          daily_limit: data.limits.daily,
          weekly_limit: data.limits.weekly,
          monthly_limit: data.limits.monthly,
          magazine_limit: data.limits.magazine,
          daily_used: data.current_month_usage.daily,
          weekly_used: data.current_month_usage.weekly,
          monthly_used: data.current_month_usage.monthly,
          magazine_used: data.current_month_usage.magazine
        });
      }
    } catch (err) {
      console.error("Error fetching user usage:", err);
    }
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setUserUsage(null);
    setUserUsageStats(null);
    setEditForm({
      is_active: user.is_active,
      role: user.role
    });
    setShowEditModal(true);
    fetchUserUsage(user.id);
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;

    try {
      const response = await fetch(`${API_BASE}/api/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editForm),
      });

      if (response.ok) {
        await fetchUsers();
        setShowEditModal(false);
        setSelectedUser(null);
      } else {
        setError("فشل في تحديث بيانات المستخدم");
      }
    } catch (err) {
      setError("حدث خطأ أثناء تحديث بيانات المستخدم");
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm("هل أنت متأكد من حذف هذا المستخدم؟")) return;

    try {
      const response = await fetch(`${API_BASE}/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await fetchUsers();
      } else {
        setError("فشل في حذف المستخدم");
      }
    } catch (err) {
      setError("حدث خطأ أثناء حذف المستخدم");
    }
  };

  const resetUserUsage = async (userId: number, resetType: string = "current_month") => {
    try {
      const response = await fetch(`${API_BASE}/api/users/${userId}/reset-usage`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reset_type: resetType }),
      });

      if (response.ok) {
        const data = await response.json();
        alert(`تم إعادة تعيين إحصائيات الاستخدام بنجاح\n\nنوع الإعادة التعيين: ${data.reset_type}\nالمستخدم: ${data.username}`);
        // Refresh usage data to show updated statistics
        fetchUserUsage(userId);
      } else {
        setError("فشل في إعادة تعيين إحصائيات الاستخدام");
      }
    } catch (err) {
      setError("حدث خطأ أثناء إعادة تعيين إحصائيات الاستخدام");
    }
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

  // Check if user is admin, if not show unauthorized message
  if (user?.role !== "admin") {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-slate-100 flex items-center justify-center">
          <div className="text-center">
            <Shield className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-red-600">غير مصرح لك</h2>
            <p className="text-gray-600 mt-2">هذه الصفحة متاحة فقط للمشرفين</p>
          </div>
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
              className="block w-full rounded-lg px-3 py-2 text-right hover:bg-white/10"
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
                className="block w-full rounded-lg px-3 py-2 text-right bg-white/90 text-brand-redDark shadow-sm"
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
        <div className="flex-1">
          {/* Header */}
          <div className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="py-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <Shield className="h-8 w-8 text-brand-red ml-3" />
                    <h1 className="text-2xl font-bold text-gray-900">لوحة تحكم المشرف</h1>
                  </div>
                  <div className="text-sm text-gray-500">
                    إدارة المستخدمين والصلاحيات
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">{error}</h3>
                </div>
              </div>
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Users className="h-8 w-8 text-blue-500" />
                </div>
                <div className="mr-4">
                  <p className="text-sm font-medium text-gray-500">إجمالي المستخدمين</p>
                  <p className="text-2xl font-bold text-gray-900">{users.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <Activity className="h-8 w-8 text-green-500" />
                </div>
                <div className="mr-4">
                  <p className="text-sm font-medium text-gray-500">المستخدمون النشطون</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.is_active).length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <BarChart3 className="h-8 w-8 text-purple-500" />
                </div>
                <div className="mr-4">
                  <p className="text-sm font-medium text-gray-500">المشرفون</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.role === "admin").length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <BarChart3 className="h-8 w-8 text-blue-500" />
                </div>
                <div className="mr-4">
                  <p className="text-sm font-medium text-gray-500">المحررون (معتمدون)</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {users.filter(u => u.role === "editor").length}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <BarChart3 className="h-8 w-8 text-amber-500" />
                </div>
                <div className="mr-4">
                  <p className="text-sm font-medium text-gray-500">بانتظار الموافقة</p>
                  <p className="text-2xl font-bold text-amber-600">
                    {users.filter(u => u.role === "viewer").length}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Users Table */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">قائمة المستخدمين</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      المستخدم
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      البريد الإلكتروني
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      الدور
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      الحالة
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      تاريخ الإنشاء
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      الإجراءات
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {user.full_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              @{user.username}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {user.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          user.role === 'admin' 
                            ? 'bg-purple-100 text-purple-800' 
                            : user.role === 'editor'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {user.role === 'admin' ? 'مشرف' : user.role === 'editor' ? 'محرر (معتمد)' : 'مشاهد (غير معتمد)'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          user.is_active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {user.is_active ? 'نشط' : 'غير نشط'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(user.created_at).toLocaleDateString('ar-SA')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {user.role === 'viewer' && (
                          <button
                            onClick={async () => {
                              try {
                                const response = await fetch(`${API_BASE}/api/users/${user.id}`, {
                                  method: 'PUT',
                                  headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json',
                                  },
                                  body: JSON.stringify({ role: 'editor' }),
                                });
                                if (response.ok) {
                                  await fetchUsers();
                                } else {
                                  setError("فشل في ترقية المستخدم");
                                }
                              } catch (err) {
                                setError("حدث خطأ أثناء ترقية المستخدم");
                              }
                            }}
                            className="bg-green-500 text-white px-3 py-1 rounded-md text-xs font-medium hover:bg-green-600 ml-2"
                          >
                            ✓ اعتماد
                          </button>
                        )}
                        <button
                          onClick={() => handleEditUser(user)}
                          className="text-brand-red hover:text-brand-redDark ml-2"
                        >
                          <Edit className="h-4 w-4 inline" />
                        </button>
                        {user.role !== 'admin' && (
                          <button
                            onClick={() => handleDeleteUser(user.id)}
                            className="text-red-600 hover:text-red-900 ml-2"
                          >
                            <Trash2 className="h-4 w-4 inline" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        </div>
      </div>

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                تعديل بيانات المستخدم: {selectedUser.full_name}
              </h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    الحالة
                  </label>
                  <select
                    value={editForm.is_active.toString()}
                    onChange={(e) => setEditForm({...editForm, is_active: e.target.value === 'true'})}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="true">نشط</option>
                    <option value="false">غير نشط</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    الدور
                  </label>
                  <select
                    value={editForm.role}
                    onChange={(e) => setEditForm({...editForm, role: e.target.value})}
                    className="w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="viewer">مشاهد (غير معتمد)</option>
                    <option value="editor">محرر (معتمد)</option>
                    <option value="admin">مشرف</option>
                  </select>
                </div>

                {userUsage && (
                  <div className="bg-gray-50 p-4 rounded-md">
                    <h4 className="font-medium text-gray-900 mb-2">إحصائيات الاستخدام</h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <div>اليومي: {userUsage.daily_used}/{userUsage.daily_limit}</div>
                      <div>الأسبوعي: {userUsage.weekly_used}/{userUsage.weekly_limit}</div>
                      <div>الشهري: {userUsage.monthly_used}/{userUsage.monthly_limit}</div>
                      <div>المجلة: {userUsage.magazine_used}/{userUsage.magazine_limit}</div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="space-y-2">
                        <button
                          onClick={() => {
                            if (confirm("هل أنت متأكد من إعادة تعيين استخدام الشهر الحالي فقط؟")) {
                              resetUserUsage(selectedUser.id, "current_month");
                            }
                          }}
                          className="w-full bg-orange-500 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-orange-600"
                        >
                          إعادة تعيين الشهر الحالي
                        </button>
                        
                        <div className="text-xs font-medium text-gray-700 mt-3 mb-2">سجل التقارير المستخدمة:</div>
                        <div className="max-h-32 overflow-y-auto bg-white rounded border p-2">
                          {(() => {
                            // Use real usage records from the API
                            const records = userUsageStats?.usage_records || [];
                            
                            if (records.length === 0) {
                              return <div className="text-xs text-gray-500 text-center py-2">لا توجد تقارير مستخدمة بعد</div>;
                            }
                            
                            return records.map(record => (
                              <div key={record.id} className="flex justify-between items-center text-xs py-1 border-b border-gray-100 last:border-0">
                                <span className="font-medium">
                                  {record.report_type === 'daily' ? 'تقرير يومي' :
                                   record.report_type === 'weekly' ? 'تقرير أسبوعي' :
                                   record.report_type === 'monthly' ? 'تقرير شهري' :
                                   record.report_type === 'magazine' ? 'مجلة شهرية' : record.report_type}
                                  <span className="text-gray-400 mr-1">({record.month})</span>
                                </span>
                                <span className="text-gray-600">
                                  {record.count} {record.count === 1 ? 'مرة' : 'مرات'}
                                </span>
                              </div>
                            ));
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleUpdateUser}
                  className="flex-1 bg-brand-red text-white py-2 px-4 rounded-md hover:bg-brand-redDark"
                >
                  حفظ التغييرات
                </button>
                <button
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-400"
                >
                  إلغاء
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </ProtectedRoute>
  );
}