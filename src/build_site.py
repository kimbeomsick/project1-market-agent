import os
import json
import logging
import datetime
import pandas as pd
import yaml

logger = logging.getLogger("market_agent.build_site")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ company_name }} - 시장 & 경쟁사 인텔리전스 대시보드</title>
    <!-- Fonts & Icons -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: #111827;
            --card-bg: #1f2937;
            --card-border: #374151;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-blue: #3b82f6;
            --accent-indigo: #6366f1;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --glow: rgba(59, 130, 246, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding-bottom: 60px;
        }

        /* Container */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }

        /* Header */
        header {
            background: linear-gradient(180deg, rgba(31, 41, 55, 0.8) 0%, rgba(11, 15, 25, 0) 100%);
            border-bottom: 1px solid rgba(55, 65, 81, 0.5);
            padding: 32px 0 24px 0;
            margin-bottom: 32px;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .logo-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-badge {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 800;
            color: #fff;
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
        }

        h1 {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .meta-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #60a5fa;
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 9999px;
        }

        /* Overview Grid */
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 22px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }

        .card-title {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-value {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
        }

        .tags-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }

        .tag {
            font-size: 12px;
            padding: 3px 8px;
            background: #374151;
            color: #d1d5db;
            border-radius: 6px;
        }

        .tag.highlight {
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        /* Section Title */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 18px;
        }

        .section-title {
            font-size: 18px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Top 10 Highlights */
        .top10-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 18px;
            margin-bottom: 40px;
        }

        .top-card {
            background: linear-gradient(145deg, #1f2937 0%, #111827 100%);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 20px;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .rank-badge {
            position: absolute;
            top: -10px;
            left: 18px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            color: white;
            font-weight: 800;
            font-size: 12px;
            padding: 2px 10px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        }

        .top-card-header {
            margin-top: 6px;
            margin-bottom: 10px;
        }

        .top-card-title {
            font-size: 16px;
            font-weight: 700;
            line-height: 1.4;
            color: #f3f4f6;
            margin-bottom: 8px;
        }

        .score-bar-wrap {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 10px 0;
        }

        .score-bar {
            flex-grow: 1;
            height: 6px;
            background: #374151;
            border-radius: 999px;
            overflow: hidden;
        }

        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #10b981);
            border-radius: 999px;
        }

        .score-text {
            font-size: 13px;
            font-weight: 700;
            color: #34d399;
        }

        .top-card-desc {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 12px;
            line-height: 1.5;
        }

        .top-card-reason {
            background: rgba(55, 65, 81, 0.4);
            border-left: 3px solid var(--accent-indigo);
            padding: 8px 12px;
            border-radius: 0 8px 8px 0;
            font-size: 12px;
            color: #c7d2fe;
            margin-bottom: 14px;
        }

        .top-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-muted);
            border-top: 1px solid rgba(55, 65, 81, 0.5);
            padding-top: 12px;
        }

        .btn-link {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .btn-link:hover {
            text-decoration: underline;
        }

        /* Full Table Section */
        .table-controls {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }

        .search-input {
            flex-grow: 1;
            min-width: 240px;
            background: #1f2937;
            border: 1px solid var(--card-border);
            padding: 10px 16px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 14px;
            outline: none;
        }

        .search-input:focus {
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        .filter-select {
            background: #1f2937;
            border: 1px solid var(--card-border);
            padding: 10px 16px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 14px;
            outline: none;
        }

        .table-wrap {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }

        th {
            background: #111827;
            color: var(--text-secondary);
            font-weight: 600;
            padding: 14px 16px;
            border-bottom: 1px solid var(--card-border);
            white-space: nowrap;
        }

        td {
            padding: 14px 16px;
            border-bottom: 1px solid rgba(55, 65, 81, 0.4);
            color: #e5e7eb;
        }

        tr:hover td {
            background: rgba(55, 65, 81, 0.3);
        }

        .badge-cat {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
            background: #374151;
            color: #9ca3af;
        }

        .badge-cat.경쟁사 { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
        .badge-cat.시장동향 { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
        .badge-cat.지원사업 { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }

        footer {
            text-align: center;
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 60px;
        }
    </style>
</head>
<body>

    <header>
        <div class="container header-content">
            <div class="logo-group">
                <div class="logo-badge">🤖</div>
                <div>
                    <h1>{{ company_name }} 시장·경쟁사 인텔리전스</h1>
                    <div class="subtitle">{{ business_area }} | 일일 자동 수집 & 맞춤 추천 리포트</div>
                </div>
            </div>
            <div class="meta-badge">
                <span>🔄 업데이트: {{ updated_at }}</span>
                <span>•</span>
                <span>분석 건수: {{ total_count }}건</span>
            </div>
        </div>
    </header>

    <main class="container">

        <!-- Company Profile & Stats Overview -->
        <section class="overview-grid">
            <div class="card">
                <div class="card-title">🏢 타깃 시장 & 제품군</div>
                <div class="card-value" style="font-size: 18px; margin-bottom: 8px;">{{ products[0] }}</div>
                <div class="tags-list">
                    {% for p in products %}
                    <span class="tag highlight">{{ p }}</span>
                    {% endfor %}
                    {% for tm in target_market %}
                    <span class="tag">{{ tm }}</span>
                    {% endfor %}
                </div>
            </div>

            <div class="card">
                <div class="card-title">🎯 주요 모니터링 경쟁사 ({{ competitors|length }})</div>
                <div class="tags-list" style="margin-top: 10px;">
                    {% for comp in competitors %}
                    <span class="tag highlight" style="background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.3);">{{ comp }}</span>
                    {% endfor %}
                </div>
            </div>

            <div class="card">
                <div class="card-title">🔍 핵심 관심 및 정부지원 키워드</div>
                <div class="tags-list" style="margin-top: 10px;">
                    {% for kw in interest_keywords %}
                    <span class="tag">{{ kw }}</span>
                    {% endfor %}
                    {% for fk in funding_keywords %}
                    <span class="tag" style="background: rgba(16, 185, 129, 0.15); color: #6ee7b7;">{{ fk }}</span>
                    {% endfor %}
                </div>
            </div>

            <div class="card">
                <div class="card-title">📊 분석 요약</div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 8px;">
                    <div>
                        <span class="card-value">{{ total_recommended }}</span>
                        <span style="font-size: 14px; color: var(--text-secondary);"> / 30건 선별</span>
                    </div>
                    <span class="meta-badge" style="font-size: 11px;">LLM 연동: {{ 'Gemini AI' if llm_used else 'Rule Engine' }}</span>
                </div>
            </div>
        </section>

        <!-- TOP 10 Recommendations -->
        <section style="margin-bottom: 48px;">
            <div class="section-header">
                <h2 class="section-title">🌟 TOP 10 핵심 추천 뉴스</h2>
                <span style="font-size: 13px; color: var(--text-secondary);">기업 적합도 및 사업 파급력 기반 랭킹</span>
            </div>

            <div class="top10-grid">
                {% for item in top10 %}
                <div class="top-card">
                    <div class="rank-badge">#{{ loop.index }} TOP PICK</div>
                    <div class="top-card-header">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span class="badge-cat {{ item.category }}">{{ item.category }}</span>
                            <span style="font-size: 12px; color: var(--text-muted);">{{ item.date }}</span>
                        </div>
                        <h3 class="top-card-title">{{ item.title }}</h3>
                        
                        <div class="score-bar-wrap">
                            <div class="score-bar">
                                <div class="score-fill" style="width: {{ item.relevance_score }}%;"></div>
                            </div>
                            <span class="score-text">{{ item.relevance_score }}점</span>
                        </div>
                    </div>

                    <p class="top-card-desc">{{ item.summary }}</p>
                    <div class="top-card-reason">💡 <strong>추천 사유:</strong> {{ item.recommendation_reason }}</div>

                    <div class="top-card-footer">
                        <span>출처: {{ item.source_name }}</span>
                        {% if item.source_url %}
                        <a href="{{ item.source_url }}" target="_blank" rel="noopener noreferrer" class="btn-link">원문 보기 ↗</a>
                        {% else %}
                        <span>원문 없음</span>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>

        <!-- Full Recommended List Table -->
        <section>
            <div class="section-header">
                <h2 class="section-title">📋 상위 30건 전체 추천 목록</h2>
            </div>

            <div class="table-controls">
                <input type="text" id="searchInput" class="search-input" placeholder="기사 제목, 추천 사유, 키워드 검색...">
                <select id="categoryFilter" class="filter-select">
                    <option value="">전체 카테고리</option>
                    <option value="경쟁사">경쟁사</option>
                    <option value="시장동향">시장동향</option>
                    <option value="지원사업">지원사업</option>
                </select>
            </div>

            <div class="table-wrap">
                <table id="newsTable">
                    <thead>
                        <tr>
                            <th style="width: 60px;">순위</th>
                            <th style="width: 90px;">카테고리</th>
                            <th>기사 제목 & 추천 사유</th>
                            <th style="width: 80px;">적합도</th>
                            <th style="width: 100px;">출처 / 일자</th>
                            <th style="width: 80px; text-align: center;">링크</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in all_recommended %}
                        <tr data-category="{{ item.category }}">
                            <td style="font-weight: 700; color: var(--text-muted);">{{ loop.index }}</td>
                            <td><span class="badge-cat {{ item.category }}">{{ item.category }}</span></td>
                            <td>
                                <div style="font-weight: 600; color: #f9fafb; margin-bottom: 4px;">{{ item.title }}</div>
                                <div style="font-size: 12px; color: #9ca3af;">{{ item.recommendation_reason }}</div>
                            </td>
                            <td><strong style="color: #34d399;">{{ item.relevance_score }}점</strong></td>
                            <td>
                                <div style="font-size: 12px;">{{ item.source_name }}</div>
                                <div style="font-size: 11px; color: var(--text-muted);">{{ item.date }}</div>
                            </td>
                            <td style="text-align: center;">
                                {% if item.source_url %}
                                <a href="{{ item.source_url }}" target="_blank" rel="noopener noreferrer" class="btn-link">보기 ↗</a>
                                {% else %}
                                -
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </section>

    </main>

    <footer>
        <div class="container">
            <p>Generated by <strong>Project 1: Market Agent</strong> &bull; Powered by Antigravity Automation &bull; Hosted on GitHub Pages</p>
        </div>
    </footer>

    <script>
        const searchInput = document.getElementById('searchInput');
        const categoryFilter = document.getElementById('categoryFilter');
        const rows = document.querySelectorAll('#newsTable tbody tr');

        function filterTable() {
            const query = searchInput.value.toLowerCase().trim();
            const cat = categoryFilter.value;

            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                const rowCat = row.getAttribute('data-category');
                const matchQuery = !query || text.includes(query);
                const matchCat = !cat || rowCat === cat;

                if (matchQuery && matchCat) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        searchInput.addEventListener('input', filterTable);
        categoryFilter.addEventListener('change', filterTable);
    </script>
</body>
</html>
"""

def load_yaml(path="config/company_profile.yaml"):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def build_dashboard(
    recommended_path="data/processed/recommended_market_news.csv",
    docs_dir="docs",
    llm_used=False
):
    logger.info(f"정적 대시보드 사이트 생성 시작: {recommended_path}")
    if not os.path.exists(recommended_path):
        logger.error(f"추천 데이터 파일이 없습니다: {recommended_path}")
        return False

    profile = load_yaml()
    df = pd.read_csv(recommended_path, encoding="utf-8-sig")
    
    # 결측치 채우기
    df["title"] = df["title"].fillna("")
    df["summary"] = df["summary"].fillna("")
    df["category"] = df["category"].fillna("시장동향")
    df["source_name"] = df["source_name"].fillna("뉴스 출처")
    df["source_url"] = df["source_url"].fillna("")
    df["relevance_score"] = df["relevance_score"].fillna(0).astype(int)
    df["recommendation_reason"] = df["recommendation_reason"].fillna("시장 트렌드")

    records = df.to_dict(orient="records")
    top10 = records[:10]

    os.makedirs(docs_dir, exist_ok=True)

    # 1. report.json 생성
    report_data = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "company_profile": profile,
        "total_analyzed": len(records),
        "llm_used": llm_used,
        "top_10": top10,
        "all_recommendations": records
    }
    json_path = os.path.join(docs_dir, "report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    logger.info(f"report.json 생성 완료 -> {json_path}")

    # 2. index.html 렌더링 (jinja2)
    from jinja2 import Template
    tmpl = Template(HTML_TEMPLATE)
    html_content = tmpl.render(
        company_name=profile.get("company_name", "NovaFactory AI"),
        business_area=profile.get("business_area", "제조업 AI 비전 품질검사"),
        products=profile.get("products", []),
        target_market=profile.get("target_market", []),
        competitors=profile.get("competitors", []),
        interest_keywords=profile.get("interest_keywords", []),
        funding_keywords=profile.get("funding_keywords", []),
        updated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        total_count=len(records),
        total_recommended=len(records),
        llm_used=llm_used,
        top10=top10,
        all_recommended=records
    )

    html_path = os.path.join(docs_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"index.html 생성 완료 -> {html_path}")

    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    success = build_dashboard()
    print(f"Build site finished: {success}")
