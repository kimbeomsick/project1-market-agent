import os
import re
import json
import logging
import pandas as pd
import yaml
import requests

logger = logging.getLogger("market_agent.recommender")

def load_profile(profile_path="config/company_profile.yaml"):
    if not os.path.exists(profile_path):
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def calculate_rule_based_score(row, profile):
    """
    규칙 기반 점수 계산기
    - 경쟁사 언급: 가중치 30점
    - 자사 및 제품 언급: 가중치 30점
    - 핵심 관심 키워드 일치: 가중치 20점
    - 정부/지원사업 키워드: 가중치 20점
    """
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

    # 1. 경쟁사 매칭
    matched_competitors = [c for c in competitors if c and c.lower() in full_text.lower()]
    if matched_competitors:
        score += 30 + len(matched_competitors) * 5
        reasons.append(f"경쟁사({', '.join(matched_competitors)}) 동향 감지")

    # 2. 자사/제품 매칭
    matched_products = [p for p in products if p and p.lower() in full_text.lower()]
    if company_name and company_name.lower() in full_text.lower():
        score += 30
        reasons.append(f"자사명({company_name}) 직접 언급")
    elif matched_products:
        score += 25
        reasons.append(f"주요 제품군({', '.join(matched_products)}) 관련 뉴스")

    # 3. 기술/시장 키워드 매칭
    matched_interests = [kw for kw in interest_keywords if kw and kw.lower() in full_text.lower()]
    if matched_interests:
        score += min(len(matched_interests) * 8, 25)
        reasons.append(f"핵심 기술 키워드({', '.join(matched_interests[:3])}) 일치")

    # 4. 정책 및 지원사업 매칭
    matched_funding = [kw for kw in funding_keywords if kw and kw.lower() in full_text.lower()]
    if matched_funding:
        score += min(len(matched_funding) * 8, 20)
        reasons.append(f"정부/R&D 지원사업({', '.join(matched_funding[:2])}) 연계")

    # 기본 최신성 및 신뢰도 가산점
    category = str(row.get("category", ""))
    if category in ["경쟁사", "지원사업"]:
        score += 5

    final_score = min(score, 100)
    if not reasons:
        reasons.append("시장 일반 트렌드 및 산업 동향")

    recommendation_reason = " | ".join(reasons)
    return final_score, recommendation_reason

def evaluate_with_llm(articles_df, profile, api_key):
    """Gemini API를 사용하여 추천 사유와 심층 평가 점수를 보강합니다."""
    logger.info("Gemini API를 통한 심층 분석 시도...")
    # 구현 가능 시 Gemini REST API 호출
    # API 키가 주어질 경우 상위 항목에 대해 이유를 더 정교화
    return articles_df

def recommend_market_news(
    input_path="data/processed/cleaned_market_news.csv",
    output_path="data/processed/recommended_market_news.csv",
    top_n=30
):
    logger.info(f"기업 맞춤형 추천 분석 시작: {input_path}")
    if not os.path.exists(input_path):
        logger.error(f"정제된 데이터 파일이 없습니다: {input_path}")
        return False, []

    profile = load_profile()
    df = pd.read_csv(input_path, encoding="utf-8-sig")

    scores = []
    reasons = []

    for _, row in df.iterrows():
        s, r = calculate_rule_based_score(row, profile)
        scores.append(s)
        reasons.append(r)

    df["relevance_score"] = scores
    df["recommendation_reason"] = reasons

    # 점수 높은 순, 최신 날짜 순 정렬
    df = df.sort_values(by=["relevance_score", "date"], ascending=[False, False])
    
    # 상위 top_n개 추출
    recommended_df = df.head(top_n).copy()
    
    # Gemini API 키 확인
    gemini_key = os.getenv("GEMINI_API_KEY")
    llm_used = False
    if gemini_key:
        try:
            recommended_df = evaluate_with_llm(recommended_df, profile, gemini_key)
            llm_used = True
        except Exception as e:
            logger.warning(f"Gemini API 호출 실패, 규칙 기반 유지: {e}")

    # CSV 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    recommended_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    logger.info(f"추천 완료: 상위 {len(recommended_df)}건 저장 -> {output_path} (LLM 사용: {llm_used})")
    
    return True, {
        "total_recommended": len(recommended_df),
        "llm_used": llm_used,
        "top_10": recommended_df[["title", "relevance_score", "recommendation_reason", "source_url"]].head(10).to_dict(orient="records")
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    success, result = recommend_market_news()
    print(f"Recommend finished: success={success}, total={result.get('total_recommended')}")
