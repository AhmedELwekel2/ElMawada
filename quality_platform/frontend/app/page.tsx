import Link from "next/link";
import { ArrowLeft, Newspaper, ShieldCheck, Target } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900" dir="rtl">

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-primary via-brand-secondary to-brand-dark pt-32 pb-20 text-white sm:pt-40 sm:pb-24">
        {/* Abstract background shapes */}
        <div className="absolute -top-[20%] -right-[10%] h-[500px] w-[500px] rounded-full bg-white/5 blur-3xl"></div>
        <div className="absolute -bottom-[20%] -left-[10%] h-[600px] w-[600px] rounded-full bg-brand-primary/20 blur-3xl"></div>

        <div className="mx-auto max-w-7xl px-6 relative z-10">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-8 items-center">
            <div className="max-w-2xl animate-fade-in">
              <div className="mb-6 inline-flex items-center rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm font-medium backdrop-blur-md">
                <span className="flex h-2 w-2 rounded-full bg-green-400 ml-2"></span>
                جزء من منظومة Transformix AI
              </div>
              <h1 className="mb-6 text-5xl font-black leading-tight sm:text-6xl lg:text-7xl">
                مركز المودة <br />
                <span className="text-white/80">للإرشاد الأسري وفض النزاعات</span>
              </h1>
              <p className="mb-10 text-lg leading-relaxed text-white/90 sm:text-xl">
                أخبار ومحتوى متخصص في الصحة النفسية والإرشاد الأسري ورفاهية الأسرة.
              </p>
              <div className="flex flex-col gap-4 sm:flex-row">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-8 py-4 text-center text-lg font-bold text-brand-primary shadow-xl transition-transform hover:scale-105"
                >
                  <ArrowLeft className="h-5 w-5" />
                  ابدأ الآن مجاناً
                </Link>
                <a
                  href="#features"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/30 bg-white/10 px-8 py-4 text-center text-lg font-bold text-white backdrop-blur-md transition-colors hover:bg-white/20"
                >
                  استكشف المميزات
                </a>
              </div>
            </div>

            {/* Aaref 3D Character */}
            <div className="relative mx-auto w-full max-w-lg lg:max-w-none animate-zoom-in flex items-center justify-center">
              {/* Soft glow behind character */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="h-72 w-72 rounded-full bg-white/10 blur-3xl sm:h-96 sm:w-96"></div>
              </div>

              {/* Speech Bubble */}
              <div
                className="absolute -top-2 right-4 z-20 sm:right-10 sm:-top-4"
                style={{ animation: 'float 3s ease-in-out infinite' }}
              >
                <div className="relative rounded-2xl bg-white px-6 py-3 shadow-xl">
                  <p className="text-lg font-bold text-brand-primary sm:text-xl" dir="rtl">
                    👋 اهلاً، أنا عارف!
                  </p>
                  {/* Speech bubble triangle */}
                  <div className="absolute -bottom-3 right-8 h-0 w-0 border-l-[12px] border-r-[12px] border-t-[14px] border-l-transparent border-r-transparent border-t-white"></div>
                </div>
              </div>

              {/* Aaref Avatar Image */}
              <img
                src="/avatar.png"
                alt="عارف - مساعد مركز المودة"
                className="relative z-10 h-[360px] w-auto drop-shadow-2xl sm:h-[440px] lg:h-[500px] object-contain"
                style={{
                  animation: 'float 4s ease-in-out infinite',
                  filter: 'drop-shadow(0 20px 40px rgba(0,0,0,0.3))'
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="bg-white py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-base font-bold uppercase tracking-wider text-brand-primary">
              المميزات الرئيسية
            </h2>
            <p className="mt-2 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
              ماذا يقدّم النظام؟
            </p>
          </div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: "أخبار نفسية وأسرية",
                desc: "تغطية يومية مركّزة على الصحة النفسية للأفراد والأسر فقط، دون تشتيت في مواضيع أخرى.",
                icon: <Target className="h-6 w-6 text-brand-primary" />,
              },
              {
                title: "مصادر موثوقة",
                desc: "تجميع تلقائي من جهات رسمية ودولية متخصصة ومنصات موثوقة في شؤون الأسرة والصحة النفسية.",
                icon: <ShieldCheck className="h-6 w-6 text-brand-primary" />,
              },
              {
                title: "تقارير بالذكاء الاصطناعي",
                desc: "ملخصات يومية وأسبوعية وشهرية ومجلة PDF جاهزة للمشاركة، مولّدة آلياً.",
                icon: <Newspaper className="h-6 w-6 text-brand-primary" />,
              },
            ].map((feature, idx) => (
              <div
                key={idx}
                className="group relative flex flex-col gap-4 rounded-2xl border border-slate-100 bg-white p-8 shadow-sm transition-all hover:shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:-translate-y-1 animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-redSoft transition-colors group-hover:bg-brand-primary group-hover:text-white">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-900">{feature.title}</h3>
                <p className="text-base leading-relaxed text-slate-600">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Target Audience Section (Glassmorphism on Red) */}
      <section className="relative overflow-hidden bg-brand-primary py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 relative z-10">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-3xl font-black tracking-tight text-white sm:text-4xl">
              لمن صُمّمت هذه المنصة؟
            </h2>
            <p className="mt-4 text-lg text-white/80">
              أدوات مصممة لدعم الأخصائيين النفسيين والمرشدين الأسريين والأسر.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 pl-4 pr-4">
            {["الأخصائيون النفسيون", "المرشدون الأسريون", "الآباء والأمهات", "الباحثون الاجتماعيون", "الجمعيات الأسرية", "المهتمون بالأسرة"].map((audience, idx) => (
              <div key={idx} className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-white/20 bg-white/10 p-6 backdrop-blur-md transition-transform hover:scale-105">
                <div className="h-10 w-10 text-white opacity-80">
                  <span className="text-2xl font-black">0{idx + 1}</span>
                </div>
                <span className="text-sm font-bold text-white text-center">{audience}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 py-12 text-slate-400">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-slate-900 font-bold text-sm">
              Q
            </div>
            <span className="text-lg font-bold text-white">مركز المودة</span>
          </div>
          <p className="text-sm">
            © {new Date().getFullYear()} منظومة Transformix AI. جميع الحقوق محفوظة.
          </p>
        </div>
      </footer>
    </div>
  );
}