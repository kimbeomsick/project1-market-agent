import os
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger("market_agent.cleaner")

def clean_html_text(text):
    if not isinstance(text, str) or not text.strip():
        return ""
    # HTML 태그 제거
    soup = BeautifulSoup(text, "html.parser")
    clean_text = soup.get_text()
    # 공백 정규화
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def normalize_date(date_str):
    if not isinstance(date_str, str) or not date_str.strip():
        return "2026-01-01"
    clean_str = date_str.strip()
    # YYYY-MM-DD 형태 추출
    match = re.search(r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})', clean_str)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return clean_str[:10]

def clean_market_data(input_path="data/raw/crawled_market_news.csv", output_path="data/processed/cleaned_market_news.csv"):
    """
    원본 수집 데이터의 노이즈, HTML, 결측치, 중복을 제거하고 정규화합니다.
    """
    logger.info(f"데이터 정제 시작: {input_path}")
    if not os.path.exists(input_path):
        logger.error(f"입력 파일이 없습니다: {input_path}")
        return False, {}

    # CSV 로드
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    raw_count = len(df)
    
    # 1. Title 결측 및 짧은 제목 필터링 (최소 4자 이상)
    df["title"] = df["title"].fillna("").astype(str).apply(clean_html_text)
    df = df[df["title"].str.strip().str.len() >= 4].copy()
    valid_title_count = len(df)
    missing_title_count = raw_count - valid_title_count

    # 2. 본문 및 요약 HTML 정리
    if "content" in df.columns:
        df["content"] = df["content"].fillna("").astype(str).apply(clean_html_text)
    if "summary" in df.columns:
        df["summary"] = df["summary"].fillna("").astype(str).apply(clean_html_text)
    else:
        df["summary"] = df["content"].str[:200]

    # 3. 날짜 정규화
    if "date" in df.columns:
        df["date"] = df["date"].astype(str).apply(normalize_date)
    else:
        df["date"] = "2026-01-01"

    # 4. Source URL 결측 처리
    if "source_url" in df.columns:
        df["source_url"] = df["source_url"].fillna("").astype(str).str.strip()
    else:
        df["source_url"] = ""

    # 5. 중복 제거
    # (1) URL 중복 제거 (URL이 존재하는 경우)
    has_url_mask = df["source_url"].str.len() > 5
    df_with_url = df[has_url_mask].drop_duplicates(subset=["source_url"], keep="first")
    df_without_url = df[~has_url_mask]
    df = pd.concat([df_with_url, df_without_url], ignore_index=True)

    # (2) Title 중복 제거
    df = df.drop_duplicates(subset=["title"], keep="first")

    # (3) article_id 중복 제거
    if "article_id" in df.columns:
        df = df.drop_duplicates(subset=["article_id"], keep="first")

    final_count = len(df)
    duplicate_removed_count = valid_title_count - final_count

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    logger.info(f"정제 완료: 원본 {raw_count}건 -> 최종 {final_count}건 (결측치 {missing_title_count}건, 중복 {duplicate_removed_count}건 제거)")
    
    stats = {
        "raw_count": raw_count,
        "final_count": final_count,
        "missing_title_removed": missing_title_count,
        "duplicates_removed": duplicate_removed_count
    }
    return True, stats

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    success, stats = clean_market_data()
    print(f"Clean finished: {stats}")
