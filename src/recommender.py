import os
import re
import json
import logging
import pandas as pd
import yaml
import requests

logger = logging.getLogger("market_agent.recommender")

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [recommender] %(message)s")
        
        fh = logging.FileHandler("logs/recommender.log", mode="a", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

def load_profile(profile_path="config/company_profile.yaml"):
    if not os.path.exists(profile_path):
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_gemini_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip():
        return key.strip()
    
    env_paths = [".env", "../.env"]
    for p in env_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    return None

def calculate_rule_based_score(row, profile):
    title = str(row.get("title", ""))
    content = str(row.get("content", ""))
    summary = str(row.get("summary", ""))
    full_text = f"{title} {summary} {content}"
    
    company_name = profile.get("company_name", "NovaFactory AI")
    products = profile.get("products", [])
    competitors = profile.get("competitors", [])
    interest_keywords = profile.get("interest_keywords", [])
    funding_keywords = profile.get("funding_keywords", [])

    score = 0
    reasons = []

    # 1. 경쟁사 매칭 (가중치 30)
    matched_competitors = [c for c in competitors if c and c.lower() in full_text.lower()]
    if matched_competitors:
        score += 30 + len(matched_competitors) * 5
        reasons.append(f"경쟁사({', '.join(matched_competitors)}) 동향")

    # 2. 자사/제품 매칭 (가중치 30)
    matched_products = [p for p in products if p and p.lower() in full_text.lower()]
    if company_name and company_name.lower() in full_text.lower():
        score += 30
        reasons.append(f"자사({company_name}) 직접 연관")
    elif matched_products:
        score += 25
        reasons.append(f"주요 제품군({', '.join(matched_products)}) 연계")

    # 3. 기술/시장 키워드 매칭 (가중치 25)
    matched_interests = [kw for kw in interest_keywords if kw and kw.lower() in full_text.lower()]
    if matched_interests:
        score += min(len(matched_interests) * 8, 25)
        reasons.append(f"핵심 기술 키워드({', '.join(matched_interests[:3])})")

    # 4. 정책 및 지원사업 매칭 (가중치 20)
    matched_funding = [kw for kw in funding_keywords if kw and kw.lower() in full_text.lower()]
    if matched_funding:
        score += min(len(matched_funding) * 8, 20)
        reasons.append(f"정부/R&D 지원사업({', '.join(matched_funding[:2])})")

    category = str(row.get("category", ""))
    if category in ["competitor", "경쟁사", "funding", "지원사업"]:
        score += 5

    final_score = min(score, 100)
    if not reasons:
        reasons.append("시장 일반 트렌드 및 산업 동향")

    recommendation_reason = " | ".join(reasons)
    return final_score, recommendation_reason

def evaluate_with_gemini(top_df, profile, api_key):
    """
    Google Gemini REST API를 호출하여 핵심 기사에 대한 AI 기반 맞춤 시사점 및 추천 사유를 생성합니다.
    """
    logger.info("🤖 Gemini AI를 호출하여 심층 분석 및 맞춤 인사이트 생성을 시작합니다...")
    
    models = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    
    company_name = profile.get("company_name", "NovaFactory AI")
    business_area = profile.get("business_area", "제조업 AI 비전 품질검사")
    
    articles_payload = []
    for idx, row in top_df.head(15).iterrows():
        articles_payload.append({
            "id": row.get("article_id"),
            "title": row.get("title"),
            "category": row.get("category"),
            "summary": row.get("summary", "")[:120]
        })

    prompt = f"""당신은 제조업 AI 비전 품질검사 기업 '{company_name}'({business_area})의 시장 전략 AI 수석 애널리스트입니다.
아래 기사 목록을 분석하여, 각 기사가 우리 회사(NovaFactory AI)에 미치는 사업적 영향과 대응 방향을 고려한 한 줄 맞춤 추천 사유(AI Insight)를 작성해주세요.

기사 목록:
{json.dumps(articles_payload, ensure_ascii=False, indent=2)}

반드시 아래 형식의 유효한 JSON 배열로만 응답하세요:
[
  {{"id": "기사ID", "ai_insight": "경쟁사 위협 또는 사업 기회에 대한 1문장 핵심 시사점", "score_bonus": 5}}
]
"""

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    insights_map = {}
    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=15)
            if resp.status_code == 200:
                resp_json = resp.json()
                text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                results = json.loads(text)
                for item in results:
                    insights_map[item.get("id")] = item.get("ai_insight")
                logger.info(f"✅ Gemini API ({model_name}) 심층 분석 완료: {len(insights_map)}건 반영 성공")
                break
            else:
                logger.warning(f"Gemini API ({model_name}) 실패: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Gemini API ({model_name}) 호출 중 예외: {e}")

    # 데이터프레임에 AI 인사이트 반영
    if insights_map:
        for idx, row in top_df.iterrows():
            art_id = row.get("article_id")
            if art_id in insights_map and insights_map[art_id]:
                top_df.at[idx, "recommendation_reason"] = f"🧠 AI 시사점: {insights_map[art_id]}"
                top_df.at[idx, "relevance_score"] = min(int(top_df.at[idx, "relevance_score"]) + 5, 100)

    return top_df, bool(insights_map)

def recommend_market_news(
    input_path="data/processed/cleaned_market_news.csv",
    output_path="data/processed/recommended_market_news.csv",
    top_n=30
):
    setup_logger()
    logger.info("=" * 50)
    logger.info(">>> 기업 맞춤 추천 및 스코어링 시작 (recommender.py)")
    logger.info("=" * 50)

    if not os.path.exists(input_path):
        logger.error(f"정제된 데이터 파일이 없습니다: {input_path}")
        return False, {}

    profile = load_profile()
    df = pd.read_csv(input_path, encoding="utf-8-sig")

    # 1. 규칙 기반 1차 스코어링
    scores = []
    reasons = []
    for _, row in df.iterrows():
        s, r = calculate_rule_based_score(row, profile)
        scores.append(s)
        reasons.append(r)

    df["relevance_score"] = scores
    df["recommendation_reason"] = reasons

    # 점수 높은 순 및 최신 일자 순 정렬
    df = df.sort_values(by=["relevance_score", "date"], ascending=[False, False])
    recommended_df = df.head(top_n).copy()

    # 2. Gemini API Key 확인 및 AI 심층 분석 적용
    api_key = get_gemini_api_key()
    llm_used = False
    if api_key:
        logger.info(f"🔑 Gemini API Key 감지됨 (Prefix: {api_key[:6]}...)")
        recommended_df, llm_used = evaluate_with_gemini(recommended_df, profile, api_key)
    else:
        logger.info("ℹ️ Gemini API Key 없음: 순수 규칙 기반(Rule Engine) 모드로 계속 진행합니다.")

    # 3. CSV 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    recommended_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"추천 데이터 저장 완료: 상위 {len(recommended_df)}건 -> {output_path} (LLM 사용: {llm_used})")

    report = {
        "total_recommended": len(recommended_df),
        "llm_used": llm_used,
        "output_path": output_path,
        "top_10": recommended_df[["title", "relevance_score", "recommendation_reason", "source_url"]].head(10).to_dict(orient="records")
    }
    return True, report

if __name__ == "__main__":
    success, report = recommend_market_news()
    print("\n=== Recommender Summary Report ===")
    print(f"Total Recommended: {report['total_recommended']}건")
    print(f"LLM AI Used: {report['llm_used']}")
    print(f"Output: {report['output_path']}")
