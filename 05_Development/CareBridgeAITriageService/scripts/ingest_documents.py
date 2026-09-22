"""CLI script to chunk and ingest documents into pgvector database."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RAW_DOCS_DIR
from app.services.ingestion_service import get_ingestion_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Ingest maternal medical documents into pgvector database.")
    parser.add_argument(
        "--dir",
        type=str,
        default=str(RAW_DOCS_DIR),
        help="Directory containing PDF, DOCX, Markdown, or TXT documents to ingest",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Single PDF, DOCX, Markdown, or TXT document to ingest",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-ingestion of documents even if they already exist in database",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=False,
        help="Use deterministic offline embeddings without calling Gemini API (0s latency, no quota limit)",
    )
    args = parser.parse_args()

    if args.offline:
        from app.config import GEMINI_SETTINGS
        GEMINI_SETTINGS.enabled = False
        logger.info("Chế độ OFFLINE được kích hoạt: Sử dụng thuật toán vector nội bộ, không gọi Gemini API.")

    service = get_ingestion_service()

    if args.file:
        target_file = Path(args.file)
        logger.info(f"Starting ingestion for single file: {target_file}")
        count = await service.ingest_file(target_file)
        print("\n" + "=" * 60)
        print("           KẾT QUẢ NẠP TÀI LIỆU VÀO VECTOR DB")
        print("=" * 60)
        print(f"Trạng thái: Thành công")
        print(f"File đã xử lý: {target_file.name}")
        print(f"Tổng số chunks đã tạo & lưu Vector: {count}")
        print("=" * 60 + "\n")
    else:
        target_dir = Path(args.dir)
        logger.info(f"Starting ingestion from directory: {target_dir} (skip_existing={not args.force})")
        result = await service.ingest_directory(target_dir, skip_existing=not args.force)

        print("\n" + "=" * 60)
        print("           KẾT QUẢ NẠP TÀI LIỆU VÀO VECTOR DB")
        print("=" * 60)
        print(f"Trạng thái: {'Thành công' if result.success else 'Có lỗi'}")
        print(f"Tổng số file mới đã nạp: {result.total_files_processed}")
        print(f"Tổng số file bỏ qua (đã có sẵn): {len(result.skipped_files)}")
        print(f"Tổng số chunks đã tạo & lưu Vector: {result.total_chunks_created}")
        if result.processed_files:
            print(f"Danh sách file mới: {', '.join(result.processed_files[:10])}{'...' if len(result.processed_files) > 10 else ''}")
        if result.errors:
            print(f"Lỗi: {result.errors}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
