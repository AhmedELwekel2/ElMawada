"""System/user prompt builders for the generation nodes.

Ported from the original generation functions and re-themed for the
**Family & Society** (الأسرة والمجتمع) identity so output quality, Arabic
formatting, and section structure are preserved; only the topic/voice changes.
Each builder returns ``(system_message, user_prompt)``.
"""
from ._legacy import build_keyword_instruction_block

# Daily category filter values surfaced by the Family & Society categorizer.
FAMILY_CATEGORIES = (
    "الأسرة والطفولة",
    "الصحة والرفاهية",
    "المجتمع والقطاع غير الربحي",
    "الإحصاء والدراسات",
    "أخبار عامة",
)


def _articles_block(articles, limit, excerpt_len):
    block = ""
    for i, article in enumerate(articles[:limit], 1):
        if not article:
            continue
        title = article.get("title", "No title")
        source = (
            article.get("source", {}).get("name", "Unknown source")
            if article.get("source")
            else "Unknown source"
        )
        full_content = article.get("full_content", article.get("description", "No content"))
        published_date = article.get("publishedAt", "Unknown date")
        url = article.get("url", "")
        if full_content and len(full_content) > excerpt_len:
            full_content = full_content[:excerpt_len] + "..."
        block += f"""
ARTICLE {i}:
Title: {title}
Source: {source}
Date: {published_date}
URL: {url}
Content: {full_content or 'No content available'}
---
"""
    return block


def daily_blog(articles, category=None, keywords=None):
    max_daily_articles = min(len(articles), 40)
    news_content = _articles_block(articles, max_daily_articles, 450)

    if category in FAMILY_CATEGORIES:
        intro_target = f"أهم تطورات {category} اليوم"
    else:
        intro_target = "أهم أخبار الأسرة والمجتمع اليوم"

    system_message = (
        "You are a professional Arabic writer. "
        "You write concise, structured daily blog reports about family, parenting, social wellbeing, "
        "and community affairs in MODERN STANDARD ARABIC. "
        "All visible content, headings, and paragraphs must be in Arabic, but you may read/analyze English source text. "
        "Keep the style صحفي احترافي وسهل القراءة، واستخدم عناوين Markdown."
    )

    keyword_guidance = build_keyword_instruction_block(keywords)

    user_prompt = f"""
    {keyword_guidance}

    اكتب تقريرًا يوميًا موجزًا بأسلوب مدونة عن {intro_target} باللغة العربية الفصحى،
    مستخدمًا البنية التالية **بالضبط** باستخدام Markdown. اجعل النص مركزًا وغنيًا بالمعلومات.

# [اكتب عنوانًا عربيًا جذابًا لليوم]

## نظرة سريعة
[فقرة من 80–120 كلمة تلخص أهم محاور اليوم والعناوين الرئيسية في أخبار الأسرة والمجتمع]

## أبرز الأخبار
[2-3 فقرات قصيرة، كل منها 80–120 كلمة، تربط بين أهم التحديثات في شؤون الأسرة والمجتمع]

## تطورات لافتة
[قائمة نقطية من 6–8 عناصر مختصرة، كل عنصر 1–2 جملة، تشير إلى جهات أو مبادرات أو دراسات أو أرقام محددة]

## الأثر المجتمعي
[1–2 فقرة عن تأثير الأخبار على الأسرة والمجتمع وجودة الحياة]

## ما الذي نترقبه لاحقًا
[3–5 نقاط حول المبادرات المتوقعة أو الاتجاهات الصاعدة في مجال الأسرة والمجتمع]

متطلبات أساسية:
- استخدم عناوين الأقسام العربية أعلاه كما هي مع تنسيق Markdown (##).
- امزج المعلومات من عدة مقالات، ولا تكتفِ بسردها واحدة تلو الأخرى.
- اذكر الأسماء والأرقام والدراسات والجهات والمنظمات كلما أمكن ذلك.
- اجعل الأسلوب صحفيًا احترافيًا وواضحًا، مناسبًا لتقرير يومي عن الأسرة والمجتمع.
- ركّز دائمًا على صلة المحتوى بشؤون الأسرة والمجتمع وجودة الحياة.

مقالات للتحليل ({max_daily_articles} مقالاً):
{news_content}
"""
    return system_message, user_prompt


def periodic_blog(articles, blog_theme="combined", time_period="weekly", keywords=None):
    article_count = min(len(articles), 30)
    news_content = _articles_block(articles, article_count, 600)

    period_adj = "أسبوعية" if time_period == "weekly" else "شهرية"
    period_cap = "هذا الأسبوع" if time_period == "weekly" else "هذا الشهر"
    period_next = "الأسبوع القادم" if time_period == "weekly" else "الشهر القادم"

    if blog_theme == "management":
        blog_focus = "الأسرة والمجتمع والقطاع غير الربحي"
        blog_angle = (
            "ركّز على تطورات شؤون الأسرة والطفولة، والمبادرات المجتمعية، والعمل التطوعي، "
            "والسياسات والبرامج المتعلقة بالأسرة والمجتمع. "
            "الجمهور المستهدف هو صنّاع القرار في الشأن الأسري، والجهات المجتمعية، والمهتمون بالقطاع. "
            "أبرز البرامج والشراكات والمبادرات والممارسات الملهمة في خدمة الأسرة والمجتمع."
        )
    elif blog_theme == "combined":
        blog_focus = "أخبار الأسرة والمجتمع الشاملة"
        blog_angle = (
            "ركّز على كافة جوانب الأسرة والمجتمع بما في ذلك الأسرة والطفولة، الصحة والرفاهية، "
            "المجتمع والقطاع غير الربحي، والإحصاءات والدراسات. "
            "الجمهور المستهدف هو المتابعون الشاملون لشؤون الأسرة والمجتمع والمهتمون بجميع مستجداتها. "
            "أبرز أهم الأخبار والقرارات والدراسات والمبادرات المجتمعية."
        )
    else:  # improvement
        blog_focus = "الصحة والرفاهية وجودة الحياة"
        blog_angle = (
            "ركّز على الصحة النفسية والبدنية، والتغذية، وجودة الحياة الأسرية، "
            "والدراسات والإحصاءات الداعمة، والمبادرات التطويرية. "
            "الجمهور المستهدف هو المهتمون برفاهية الأسرة، ومقدمو الخدمات المجتمعية. "
            "أبرز الاتجاهات الصاعدة، والدراسات الحديثة، وأفضل الممارسات في رعاية الأسرة."
        )

    system_message = (
        "You are a professional Arabic family & society blogger. "
        "You always write engaging, insightful blog posts in MODERN STANDARD ARABIC about family, parenting, "
        "social wellbeing, the nonprofit sector, and quality-of-life developments. "
        "Use clear structure, strong headings in Arabic, and actionable insights. "
        "Always use proper markdown formatting for headers, and keep the tone صحفي احترافي وجذّاب."
    )

    keyword_guidance = build_keyword_instruction_block(keywords)

    user_prompt = f"""
    {keyword_guidance}

    اكتب تدوينة {period_adj} عربية شاملة عن {blog_focus} خلال {period_cap}،
    مستخدمًا البنية التالية **بالضبط** باستخدام Markdown:

    # [اكتب عنوانًا عربيًا جذابًا]

    ## مقدمة
    [مقدمة مشوّقة من 150 كلمة تقريبًا تجذب القارئ وتشرح سياق التقرير]

    ## أهم قصة في {period_cap}
    [250–300 كلمة تغطي التطور الأهم في أخبار الأسرة والمجتمع لهذا {period_cap}]

    ## تطور رئيسي ثانٍ
    [250–300 كلمة عن ثاني أهم تطور]

    ## اتجاهات بارزة
    [200–250 كلمة عن أبرز الاتجاهات والأنماط الملحوظة]

    ## تركيز على مبادرة أو دراسة
    [200–250 كلمة تبرز مبادرات أو جهات أو دراسات محددة]

    ## ملخصات سريعة
    [200–250 كلمة تغطي 6–8 تطورات إضافية بشكل موجز]

    ## مرصد المجتمع
    [150–200 كلمة عن البرامج، الشراكات، والمبادرات المجتمعية]

    ## ما الذي ينتظرنا لاحقًا
    [100–150 كلمة تستشرف ما قد يحدث في {period_next}]

    ## خلاصة
    [فقرة ختامية قصيرة بأهم الرسائل والتوصيات]

    زاوية التغطية:
    {blog_angle}

    متطلبات أساسية:
    - يجب استخدام عناوين الأقسام العربية أعلاه كما هي مع تنسيق Markdown (##).
    - استشهد بما لا يقل عن 15–20 مقالًا مختلفًا داخل التدوينة.
    - اذكر أسماء الجهات، الدراسات، الأرقام، التواريخ، والمصادر كلما أمكن.
    - اجعل الأسلوب عربيًا صحفيًا مهنيًا وجذابًا.
    - اجعل كل قسم غنيًا بالمعلومات وقابلًا للاستخدام للمهتمين بشؤون الأسرة والمجتمع.
    - أمامك {article_count} مقالًا، فاستخدم هذا التنوع في بناء الصورة الكلية.

    محتوى المقالات للتحليل ({article_count} مقالاً):
    {news_content}

    اكتب التدوينة باللغة العربية الفصحى فقط، بدون أي فقرات تفسيرية باللغة الإنجليزية.
    """
    return system_message, user_prompt


def magazine(articles):
    """Build the monthly Family & Society magazine prompt.

    ``articles`` should be the same ``articles[:40]`` list the node uses to
    rebuild the ``article_index → article`` map for image back-filling, so the
    ``Article N`` numbering here matches that map exactly.
    """
    articles_context = ""
    for i, article in enumerate(articles[:40]):
        title = article.get("title", "No title")
        content = (article.get("full_content", "") or "")[:1000]
        image_url = (
            article.get("urlToImage")
            or article.get("image_url")
            or article.get("image")
            or ""
        )
        source = (
            article.get("source", {}).get("name", "")
            if isinstance(article.get("source"), dict)
            else str(article.get("source", ""))
        )
        articles_context += (
            f"Article {i+1}: {title}\nSource: {source}\nImage: {image_url}\n"
            f"Content: {content}\n\n"
        )

    system_message = (
        "You are the Editor-in-Chief of a professional monthly Family & Society report. "
        "Your goal is to maintain a professional, insightful, and visionary tone. "
        "Critical page layout rule: Each article (including the first one) must fit exactly on one A4 page. "
        "NO EXCEPTIONS - All 8 articles must be between 300-350 words TOTAL (Lead + Main Content). "
        "Strict Enforcement: Count words for each article. If any article exceeds 350 words, it will overflow the page. "
        "If any article is under 270 words, it will have excessive whitespace. "
        "Target 310-330 words per article for optimal page fill without overflow. "
        "The first article is NOT special - it must follow the same word count rules as all other articles. "
        "Balance depth with brevity - provide comprehensive coverage but adhere to the strict 300-350 word limit. "
        "Output ONLY valid JSON matching the specified structure. "
        "CRITICAL: ALL text content (titles, subtitles, leads, articles, editors_note, highlights, locations) MUST be written in MODERN STANDARD ARABIC (العربية الفصحى). "
        "You may read English source articles but ALL output MUST be in Arabic."
    )

    user_prompt = f"""
    أنشئ محتوى مجلة الأسرة والمجتمع الشهرية بناءً على هذه المقالات:
    {articles_context}

    أعد كائن JSON بهذه البنية بالضبط (بدون markdown، فقط JSON):
    {{
        "title": "مجلة الأسرة والمجتمع: [عنوان جذاب بالعربية]",
        "subtitle": "[عنوان فرعي جذاب بالعربية]",
        "date": "[الشهر والسنة الحاليين بالعربية]",
        "highlights": [
            {{"title": "[عنوان 1 بالعربية]", "description": "[وصف قصير بالعربية]"}},
            {{"title": "[عنوان 2 بالعربية]", "description": "[وصف قصير بالعربية]"}},
            {{"title": "[عنوان 3 بالعربية]", "description": "[وصف قصير بالعربية]"}}
        ],
        "editors_note": "[حد أقصى 150 كلمة بالعربية. تعليق تحريري مهني وبصيرة حول أخبار الأسرة والمجتمع.]",
        "articles": [
            {{
                "category": "[واحدة من: الأسرة والطفولة, الصحة والرفاهية, المجتمع والقطاع غير الربحي, الإحصاء والدراسات]",
                "title": "[عنوان مجلة جذاب بالعربية]",
                "location": "[الموقع/المنطقة بالعربية، مثال: السعودية / الرياض]",
                "lead": "[فقرة افتتاحية جذابة بالعربية، 2-3 جمل (حوالي 40-50 كلمة). عدد الكلمات هذا مشمول في إجمالي 300-350.]",
                "content": "[المحتوى الرئيسي بتنسيق HTML بالعربية مع عناوين فرعية <h3> وفقرات <p>. عدد الكلمات الإجمالي (الافتتاحية + المحتوى) يجب أن يكون 300-350 كلمة بالضبط. المحتوى الرئيسي 250-300 كلمة. أنشئ 3-4 فقرات (حوالي 80 كلمة لكل منها) مع عنوانين فرعيين.]",
                "article_index": "[رقم المقال الأصلي من القائمة أعلاه، مثلاً 3 أو 7]",
                "source": "[اسم المصدر الأصلي]",
                "score": "[درجة الأهمية 1-10]"
            }},
            ... (أنشئ بالضبط 8 مقالات مميزة. لا تتجاوز 8.)
        ]
    }}

    مهم جداً:
    1. تأكد من أن جميع علامات الاقتباس المزدوجة داخل قيم النصوص مهرّبة بشكل صحيح بعلامة backslash (\\").
    2. لا تستخدم فواصل أسطر markdown أو فواصل زائدة تجعل JSON غير صالح.
    3. يجب أن يكون الإخراج سلسلة JSON واحدة صالحة.
    4. حقل article_index إلزامي لكل مقال - يجب أن يطابق رقم المقال في القائمة أعلاه (1-40). هذا يُستخدم لربط الصورة الصحيحة بشكل مباشر.
    5. تطبيق صارم لعدد الكلمات لجميع المقالات (بدون استثناءات):
       - إجمالي عدد الكلمات لكل مقالة (الافتتاحية + المحتوى) يجب أن يكون بين 300-350 كلمة.
       - الحد الأدنى: 300 كلمة.
       - الحد الأقصى: 350 كلمة.
       - النطاق المثالي: 310-330 كلمة لكل مقالة.
    6. جميع النصوص يجب أن تكون باللغة العربية الفصحى.
    """
    return system_message, user_prompt
