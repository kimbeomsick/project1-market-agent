import os
import sys
import logging
import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import collect_market_data
from src.cleaner import clean_market_data
from src.recommender import recommend_market_news
from src.build_site import build_dashboard

def setup_logger():
    os.makedirs("logs", exist_ok=True)
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    
    logger = logging.getLogger("market_agent")
    logger.setLevel(logging.INFO)
    
    # 중복 핸들러 방지
    if not logger.handlers:
        # 파일 핸들러
        fh = logging.FileHandler("logs/pipeline.log", mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter(log_format))
        logger.addHandler(fh)
        
        # 콘솔 핸들러
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter(log_format))
        logger.addHandler(ch)
        
    return logger

def run():
    logger = setup_logger()
    logger.info("=" * 60)
    logger.info(">>> Project 1: Market Intelligence Pipeline 시작")
    logger.info("=" * 60)
    
    pipeline_status = {}

    # 1단계: 크롤링 및 데이터 수집
    logger.info("[Step 1/4] 데이터 수집 및 Fallback 처리")
    try:
        crawl_ok, crawl_info = collect_market_data(
            output_path="data/raw/crawled_market_news.csv",
            min_required=200
        )
        total_crawled = crawl_info.get("total_count", 0) if isinstance(crawl_info, dict) else (crawl_info if isinstance(crawl_info, int) else 0)
        if crawl_ok and total_crawled >= 200:
            pipeline_status["Crawl"] = f"SUCCESS ({total_crawled} items)"
            logger.info(f"Step 1 성공: {total_crawled}건 수집 완료")
        elif crawl_ok:
            pipeline_status["Crawl"] = f"WARNING ({total_crawled} items < 200 target)"
            logger.warning(f"Step 1 경고: 수집 건수 {total_crawled}건")
        else:
            pipeline_status["Crawl"] = "FAILED"
            logger.error("Step 1 실패: 데이터 수집 불가")
            return False
    except Exception as e:
        pipeline_status["Crawl"] = f"FAILED ({e})"
        logger.exception("Step 1 예외 발생")
        return False

    # 2단계: 데이터 정제 및 노이즈 제거
    logger.info("[Step 2/4] 데이터 정제 및 중복/결측치 처리")
    try:
        clean_ok, stats = clean_market_data(
            input_path="data/raw/crawled_market_news.csv",
            output_path="data/processed/cleaned_market_news.csv"
        )
        if clean_ok:
            pipeline_status["Clean"] = f"SUCCESS ({stats.get('final_count')} valid items)"
            logger.info(f"Step 2 성공: 원본 {stats.get('raw_count')}건 -> 정제 {stats.get('final_count')}건 (중복 제거: {stats.get('duplicates_removed')})")
        else:
            pipeline_status["Clean"] = "FAILED"
            logger.error("Step 2 실패: 정제 실패")
            return False
    except Exception as e:
        pipeline_status["Clean"] = f"FAILED ({e})"
        logger.exception("Step 2 예외 발생")
        return False

    # 3단계: 기업 맞춤 추천 및 스코어링
    logger.info("[Step 3/4] 기업 맞춤 추천 및 스코어링")
    try:
        rec_ok, rec_info = recommend_market_news(
            input_path="data/processed/cleaned_market_news.csv",
            output_path="data/processed/recommended_market_news.csv",
            top_n=30
        )
        if rec_ok:
            pipeline_status["Recommend"] = f"SUCCESS (Top {rec_info.get('total_recommended')} selected)"
            logger.info(f"Step 3 성공: 상위 {rec_info.get('total_recommended')}건 추천 추출 완료")
        else:
            pipeline_status["Recommend"] = "FAILED"
            logger.error("Step 3 실패: 추천 실패")
            return False
    except Exception as e:
        pipeline_status["Recommend"] = f"FAILED ({e})"
        logger.exception("Step 3 예외 발생")
        return False

    # 4단계: 정적 웹 대시보드 빌드 (GitHub Pages용)
    logger.info("[Step 4/4] docs/ 정적 대시보드 웹사이트 생성")
    try:
        build_ok = build_dashboard(
            recommended_path="data/processed/recommended_market_news.csv",
            docs_dir="docs",
            llm_used=rec_info.get("llm_used", False)
        )
        if build_ok:
            pipeline_status["BuildSite"] = "SUCCESS (docs/index.html ready)"
            logger.info("Step 4 성공: docs/index.html 및 docs/report.json 생성 완료")
        else:
            pipeline_status["BuildSite"] = "FAILED"
            logger.error("Step 4 실패: 대시보드 빌드 실패")
            return False
    except Exception as e:
        pipeline_status["BuildSite"] = f"FAILED ({e})"
        logger.exception("Step 4 예외 발생")
        return False

    logger.info("=" * 60)
    logger.info(">>> 파이프라인 전체 실행 완료 요약:")
    for step, status in pipeline_status.items():
        logger.info(f" - {step:12s}: {status}")
    logger.info("=" * 60)

    return True

if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
