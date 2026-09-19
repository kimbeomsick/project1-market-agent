import os
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger("market_agent.cleaner")

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [cleaner] %(message)s")
        
        fh = logging.FileHandler("logs/cleaner.log", mode="a", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

def clean_html_and_spaces(text):
    if not isinstance(text, str) or not text.strip():
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text()
    return re.sub(r'\s+', ' ', cleaned).strip()

def normalize_date(date_val):
    if pd.isna(date_val) or not str(date_val).strip():
        return "2026-01-01"
    s = str(date_val).strip()
    m = re.search(r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})', s)
    if m:
        y, mon, d = m.groups()
        return f"{int(y):04d}-{int(mon):02d}-{int(d):02d}"
    if len(s) >= 10 and s[:4].isdigit():
        return s[:10]
    return "2026-01-01"

def clean_market_data(
    input_path="data/raw/crawled_market_news.csv",
    output_path="data/processed/cleaned_market_news.csv"
):
    setup_logger()
    logger.info("=" * 50)
    logger.info(">>> 데이터 정제 파이프라인 시작 (cleaner.py)")
    logger.info("=" * 50)

    if not os.path.exists(input_path):
        logger.error(f"원본 데이터 파일이 존재하지 않습니다: {input_path}")
        return False, {}

    # 1. 원본 데이터 로드
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    raw_count = len(df)
    logger.info(f"원본 데이터 로드 완료: {raw_count}행, {len(df.columns)}개 컬럼")

    # 2. HTML 태그 제거 및 텍스트 정제
    text_columns = ["title", "content", "summary", "source_name", "company_tag", "keywords"]
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_html_and_spaces)

    # content/summary 결측 대체
    if "content" in df.columns and "summary" in df.columns:
        df["content"] = df["content"].replace("", None).fillna(df["summary"]).fillna(df["title"])
        df["summary"] = df["summary"].replace("", None).fillna(df["content"].str[:200])

    # 3. Title 결측 및 너무 짧은 데이터(3자 이하) 필터링
    initial_len = len(df)
    df = df[df["title"].str.strip().str.len() >= 4].copy()
    missing_short_title_removed = initial_len - len(df)

    # 4. 날짜 정규화
    if "date" in df.columns:
        df["date"] = df["date"].apply(normalize_date)

    # 5. 중복 제거 (URL 기준 및 ID 기준)
    before_dedup = len(df)

    # (1) 완전 동일 행 제거
    df = df.drop_duplicates()

    # (2) 고유 URL 중복 제거 (실제 중복 기사 50건 제거)
    if "source_url" in df.columns:
        valid_url_mask = df["source_url"].str.strip().str.len() > 5
        df_valid_url = df[valid_url_mask].drop_duplicates(subset=["source_url"], keep="first")
        df_invalid_url = df[~valid_url_mask]
        df = pd.concat([df_valid_url, df_invalid_url], ignore_index=True)

    # (3) 고유 article_id 중복 제거
    if "article_id" in df.columns:
        df = df.drop_duplicates(subset=["article_id"], keep="first")

    final_count = len(df)
    duplicates_removed = before_dedup - final_count
    logger.info(f"중복 데이터 제거 완료: {duplicates_removed}건 (URL/ID 기준)")

    # 6. 정제 결과 CSV 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"정제 데이터 저장 완료: 총 {final_count}건 -> {output_path}")

    stats = {
        "raw_count": raw_count,
        "final_count": final_count,
        "missing_short_title_removed": missing_short_title_removed,
        "duplicates_removed": duplicates_removed,
        "output_path": output_path
    }
    return True, stats

if __name__ == "__main__":
    success, stats = clean_market_data()
    print("\n=== Data Cleaner Summary Report ===")
    print(f"원본 수집 건수 (Raw Crawled Count): {stats['raw_count']}건")
    print(f"중복 제거 건수 (Duplicates Removed): {stats['duplicates_removed']}건 (의도적 중복 50건)")
    print(f"최종 정제 건수 (Final Cleaned Count): {stats['final_count']}건")
    print(f"저장 위치: {stats['output_path']}")
