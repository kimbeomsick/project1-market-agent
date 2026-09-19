import os
import csv
import logging
import datetime
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger("market_agent.crawler")

def load_company_profile(profile_path="config/company_profile.yaml"):
    if not os.path.exists(profile_path):
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def fetch_rss_feed(query, category="시장동향"):
    """Google News RSS 피드 등을 활용하여 검색어 기반 뉴스를 수집합니다."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    articles = []
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                desc = item.findtext("description", "")
                source_name = item.findtext("source", "웹 뉴스")
                
                # HTML 제거
                soup = BeautifulSoup(desc, "html.parser")
                clean_desc = soup.get_text().strip()
                
                # 날짜 파싱
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                if pub_date:
                    try:
                        dt = datetime.datetime.strptime(pub_date[:16], "%a, %d %b %Y")
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                
                articles.append({
                    "article_id": f"rss_{abs(hash(link + title)) % 1000000:06d}",
                    "category": category,
                    "title": title,
                    "date": date_str,
                    "content": clean_desc if clean_desc else title,
                    "summary": clean_desc[:200] if clean_desc else title,
                    "source_url": link,
                    "source_name": source_name,
                    "company_tag": query,
                    "keywords": query,
                    "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "has_null": "N",
                    "is_duplicate_seed": "N",
                    "data_origin": "rss_crawl"
                })
    except Exception as e:
        logger.warning(f"RSS 수집 중 예외 발생 ({query}): {e}")
    return articles

def load_fallback_data(fallback_path="data/fallback/fallback_market_news.csv"):
    """수집 실패 또는 부족 시 fallback CSV 데이터를 로드합니다."""
    logger.info(f"Fallback 데이터 로드 시도: {fallback_path}")
    articles = []
    if not os.path.exists(fallback_path):
        logger.error(f"Fallback 파일 없음: {fallback_path}")
        return articles
    
    with open(fallback_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.lstrip('\ufeff'): v for k, v in row.items()}
            articles.append(clean_row)
    logger.info(f"Fallback 데이터 {len(articles)}건 로드 완료")
    return articles

def collect_market_data(output_path="data/raw/crawled_market_news.csv", min_required=200):
    """시장/경쟁사/지원사업 데이터를 수집하고 최소 수량 미달 시 fallback과 병합합니다."""
    profile = load_company_profile()
    keywords = profile.get("interest_keywords", []) + profile.get("competitors", []) + profile.get("funding_keywords", [])
    if not keywords:
        keywords = ["AI 비전 품질검사", "스마트팩토리", "VisionForge", "AI 바우처", "제조업 AX"]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    all_articles = []
    logger.info("실시간 RSS 수집 시작...")
    
    for kw in keywords[:8]:  # 상위 주요 키워드 대상 수집
        cat = "경쟁사" if kw in profile.get("competitors", []) else ("지원사업" if kw in profile.get("funding_keywords", []) else "시장동향")
        fetched = fetch_rss_feed(kw, category=cat)
        all_articles.extend(fetched)
    
    logger.info(f"실시간 수집된 건수: {len(all_articles)}건")
    
    # 200건 미만일 경우 fallback 데이터 활용
    if len(all_articles) < min_required:
        logger.warning(f"수집 건수({len(all_articles)})가 목표치({min_required}) 미만이므로 Fallback 데이터를 병합합니다.")
        fallback_articles = load_fallback_data()
        all_articles.extend(fallback_articles)
    
    if not all_articles:
        logger.error("데이터 수집 및 Fallback 모두 실패")
        return False, 0
    
    # CSV 저장
    fieldnames = [
        "article_id", "category", "title", "date", "content", "summary",
        "source_url", "source_name", "company_tag", "keywords",
        "collected_at", "has_null", "is_duplicate_seed", "data_origin"
    ]
    
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for art in all_articles:
            writer.writerow(art)
            
    logger.info(f"총 {len(all_articles)}건 저장 완료 -> {output_path}")
    return True, len(all_articles)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
    success, count = collect_market_data()
    print(f"Crawl finished. Success: {success}, Count: {count}")
