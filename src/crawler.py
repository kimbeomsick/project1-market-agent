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

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [crawler] %(message)s")
        
        fh = logging.FileHandler("logs/crawler.log", mode="a", encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

def load_company_profile(profile_path="config/company_profile.yaml"):
    if not os.path.exists(profile_path):
        return {}
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def fetch_rss_feed(source_name, url, category, company_tag=""):
    """
    공개 RSS 피드를 안전하게 수집합니다. 타임아웃/오류 발생 시 빈 리스트를 반환하여 파이프라인 중단을 방지합니다.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    articles = []
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                pub_date = item.findtext("pubDate", "").strip()
                desc = item.findtext("description", "").strip()
                source_tag = item.findtext("source", source_name).strip()

                if not title:
                    continue

                # HTML 태그 정리
                soup = BeautifulSoup(desc, "html.parser")
                clean_desc = soup.get_text().strip()

                # 날짜 정규화
                date_str = datetime.datetime.now().strftime("%Y-%m-%d")
                if pub_date:
                    try:
                        # RFC 822 형식 등 파싱 시도
                        dt = datetime.datetime.strptime(pub_date[:16], "%a, %d %b %Y")
                        date_str = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                articles.append({
                    "article_id": f"live_{abs(hash(link + title)) % 1000000:06d}",
                    "category": category,
                    "title": title,
                    "date": date_str,
                    "content": clean_desc if clean_desc else title,
                    "summary": clean_desc[:200] if clean_desc else title,
                    "source_url": link,
                    "source_name": source_tag if source_tag else source_name,
                    "company_tag": company_tag,
                    "keywords": company_tag,
                    "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "has_null": "N",
                    "is_duplicate_seed": "N",
                    "data_origin": "live_rss"
                })
            logger.info(f"[{source_name}] RSS 수집 성공: {len(articles)}건")
        else:
            logger.warning(f"[{source_name}] HTTP {resp.status_code} 응답")
    except Exception as e:
        logger.warning(f"[{source_name}] 수집 중 예외 발생 (무시하고 계속 진행): {e}")
    return articles

def load_fallback_data(fallback_path="data/fallback/fallback_market_news.csv"):
    """
    Fallback 합성 데이터셋을 로드하고 data_origin을 명시합니다.
    """
    articles = []
    if not os.path.exists(fallback_path):
        logger.error(f"Fallback 파일이 존재하지 않습니다: {fallback_path}")
        return articles

    with open(fallback_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.lstrip('\ufeff'): (v if v is not None else "") for k, v in row.items()}
            # data_origin 명시
            clean_row["data_origin"] = "fallback_dataset"
            articles.append(clean_row)
    logger.info(f"Fallback 데이터 {len(articles)}건 로드 완료")
    return articles

def collect_market_data(output_path="data/raw/crawled_market_news.csv", min_required=200):
    setup_logger()
    logger.info("=" * 50)
    logger.info(">>> 시장·경쟁사·정책 정보 수집 시작 (crawler.py)")
    logger.info("=" * 50)

    profile = load_company_profile()
    competitors = profile.get("competitors", ["VisionForge", "InspectAI", "FactoryMind", "QualiBot"])
    interest_keywords = profile.get("interest_keywords", ["AI", "스마트팩토리", "품질검사", "자동화", "클라우드", "제조 AX"])
    funding_keywords = profile.get("funding_keywords", ["창업지원", "AI 바우처", "스마트공장", "R&D", "사업화 자금"])

    # 수집 소스 정의 (source_plan.md 기준)
    sources = []
    
    # 1. 기술 및 시장동향 피드
    for kw in interest_keywords[:4]:
        encoded = urllib.parse.quote(kw)
        sources.append({
            "name": f"Google News ({kw})",
            "url": f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko",
            "category": "시장동향",
            "tag": kw
        })

    # 2. 경쟁사 모니터링 피드
    for comp in competitors[:4]:
        encoded = urllib.parse.quote(f"{comp} AI")
        sources.append({
            "name": f"Google News (경쟁사 {comp})",
            "url": f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko",
            "category": "경쟁사",
            "tag": comp
        })

    # 3. 정부지원 및 정책 피드
    for fk in funding_keywords[:3]:
        encoded = urllib.parse.quote(f"제조업 {fk}")
        sources.append({
            "name": f"Google News (정부지원 {fk})",
            "url": f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko",
            "category": "지원사업",
            "tag": fk
        })
    
    # 4. 정책브리핑 RSS
    sources.append({
        "name": "대한민국 정책브리핑 (korea.kr)",
        "url": "https://www.korea.kr/rss/deptNews.do?sectId=dept_news",
        "category": "지원사업",
        "tag": "정부정책"
    })

    live_articles = []
    failed_sources = []

    # 소스별 순차 수집 (하나가 실패해도 계속 진행)
    for src in sources:
        items = fetch_rss_feed(src["name"], src["url"], src["category"], company_tag=src["tag"])
        if items:
            live_articles.extend(items)
        else:
            failed_sources.append(src["name"])

    live_count = len(live_articles)
    logger.info(f"실시간 수집 완료: 총 {live_count}건 수집 (성공 {len(sources) - len(failed_sources)}개 소스, 실패 {len(failed_sources)}개 소스)")

    final_articles = list(live_articles)
    fallback_count = 0

    # 목표 건수(200건) 미달 시 Fallback 데이터 병합
    if live_count < min_required:
        logger.warning(f"수집 건수({live_count}건)가 목표치({min_required}건)에 도달하지 못하여 Fallback 데이터를 병합합니다.")
        fallback_data = load_fallback_data()
        fallback_count = len(fallback_data)
        final_articles.extend(fallback_data)

    # 디렉토리 생성 및 CSV 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fieldnames = [
        "article_id", "category", "title", "date", "content", "summary",
        "source_url", "source_name", "company_tag", "keywords",
        "collected_at", "has_null", "is_duplicate_seed", "data_origin"
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for art in final_articles:
            writer.writerow(art)

    logger.info(f"최종 저장 완료: 총 {len(final_articles)}건 -> {output_path}")

    report = {
        "live_count": live_count,
        "fallback_count": fallback_count,
        "total_count": len(final_articles),
        "failed_sources": failed_sources,
        "output_file": output_path
    }
    return True, report

if __name__ == "__main__":
    success, report = collect_market_data()
    print("=== Crawler Report ===")
    print(f"Total Collected: {report['total_count']} (Live: {report['live_count']}, Fallback: {report['fallback_count']})")
    print(f"Failed Sources Count: {len(report['failed_sources'])}")
    print(f"Output File: {report['output_file']}")
