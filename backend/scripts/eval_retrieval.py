"""离线评测 RAG 检索命中率

输入一个包含问题与标准答案标注的 JSON 或 JSONL 文件，逐条调用
`search_similar()` 进行检索，并统计 hit@k、recall@k、MRR 等指标。

支持的样本字段：
- id: 可选，样本 ID
- question: 必填，查询文本
- expected_chunk_ids: 可选，标准 chunk id 列表
- expected_document_names: 可选，标准文档名列表
- expected_pages: 可选，标准页码列表

命中规则：
- 只要 top_k 结果中任意一条满足标准答案条件，即判定该样本命中
- 如果一个样本同时提供了多个标准字段，则按“任意一个匹配即可”处理

示例：
[
  {
    "id": "q1",
    "question": "驱逐舰05的纯电续航是多少",
    "expected_pages": [12]
  },
  {
    "id": "q2",
    "question": "快充时间是多少",
    "expected_chunk_ids": ["2f6d..."],
    "expected_document_names": ["BYD-QZJ05.pdf"]
  }
]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from statistics import mean
from typing import Any

# 将后端根目录加入 sys.path，确保能正确导入 app 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.rag.retriever import search_similar

settings = get_settings()


@dataclass
class EvalSample:
    """单条评测样本"""

    question: str
    sample_id: str | None = None
    expected_chunk_ids: list[str] | None = None
    expected_document_names: list[str] | None = None
    expected_pages: list[int] | None = None


@dataclass
class EvalResult:
    """单条评测结果"""

    sample_id: str | None
    question: str
    hit_at_k: bool
    rank: int | None
    top_similarity: float | None
    matched_result: dict[str, Any] | None
    retrieved: list[dict[str, Any]]


def load_samples(file_path: Path) -> list[EvalSample]:
    """加载评测样本，支持 JSON 数组和 JSONL 两种格式"""
    if not file_path.exists():
        raise FileNotFoundError(f"评测文件不存在: {file_path}")

    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if file_path.suffix.lower() == ".jsonl":
        raw_items = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        data = json.loads(text)
        if isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                raw_items = data["items"]
            elif "questions" in data and isinstance(data["questions"], list):
                raw_items = data["questions"]
            else:
                raise ValueError("JSON 文件需要是数组，或包含 items/questions 字段")
        elif isinstance(data, list):
            raw_items = data
        else:
            raise ValueError("不支持的评测文件格式")

    samples: list[EvalSample] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("每条评测样本都必须是对象")
        question = str(item.get("question", "")).strip()
        if not question:
            raise ValueError("评测样本缺少 question 字段")

        samples.append(
            EvalSample(
                sample_id=str(item.get("id")).strip() if item.get("id") is not None else None,
                question=question,
                expected_chunk_ids=_normalize_str_list(item.get("expected_chunk_ids")),
                expected_document_names=_normalize_str_list(item.get("expected_document_names")),
                expected_pages=_normalize_int_list(item.get("expected_pages")),
            )
        )

    return samples


def _normalize_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result or None
    raise ValueError("标准答案字段必须是字符串或字符串数组")


def _normalize_int_list(value: Any) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, bool):
                raise ValueError("页码字段不能包含布尔值")
            result.append(int(item))
        return result or None
    raise ValueError("页码字段必须是整数或整数数组")


def _match_sample(result: dict[str, Any], sample: EvalSample) -> bool:
    """判断检索结果是否命中样本标准答案"""
    matched = False

    if sample.expected_chunk_ids:
        matched = str(result.get("id")) in set(sample.expected_chunk_ids)
        if matched:
            return True

    if sample.expected_document_names:
        matched = str(result.get("document_name")) in set(sample.expected_document_names)
        if matched:
            if sample.expected_pages:
                return int(result.get("metadata", {}).get("page_number", -1)) in set(sample.expected_pages)
            return True

    if sample.expected_pages:
        page_number = result.get("metadata", {}).get("page_number")
        if page_number is not None and int(page_number) in set(sample.expected_pages):
            return True

    return False


async def evaluate_sample(db, sample: EvalSample, top_k: int) -> EvalResult:
    """评估单条样本的检索命中情况"""
    retrieved = await search_similar(db, sample.question, top_k=top_k)
    matched_result = None
    matched_rank = None

    for index, result in enumerate(retrieved, start=1):
        if _match_sample(result, sample):
            matched_result = result
            matched_rank = index
            break

    return EvalResult(
        sample_id=sample.sample_id,
        question=sample.question,
        hit_at_k=matched_result is not None,
        rank=matched_rank,
        top_similarity=float(retrieved[0]["similarity"]) if retrieved else None,
        matched_result=matched_result,
        retrieved=retrieved,
    )


async def run_evaluation(samples: list[EvalSample], top_k: int) -> list[EvalResult]:
    """执行离线评测"""
    results: list[EvalResult] = []
    async with AsyncSessionLocal() as db:
        for index, sample in enumerate(samples, start=1):
            print(f"[{index}/{len(samples)}] 评测: {sample.sample_id or sample.question}")
            results.append(await evaluate_sample(db, sample, top_k=top_k))
    return results


def build_summary(results: list[EvalResult], top_k: int) -> dict[str, Any]:
    """汇总评测指标"""
    total = len(results)
    hit_count = sum(1 for item in results if item.hit_at_k)
    ranks = [item.rank for item in results if item.rank is not None]
    reciprocal_ranks = [1.0 / item.rank for item in results if item.rank is not None]
    top_similarities = [item.top_similarity for item in results if item.top_similarity is not None]

    return {
        "total": total,
        "top_k": top_k,
        "hit_count": hit_count,
        "hit_rate": round(hit_count / total, 4) if total else 0.0,
        "recall_at_k": round(hit_count / total, 4) if total else 0.0,
        "mrr": round(mean(reciprocal_ranks), 4) if reciprocal_ranks else 0.0,
        "avg_rank": round(mean(ranks), 4) if ranks else 0.0,
        "avg_top_similarity": round(mean(top_similarities), 4) if top_similarities else 0.0,
    }


def print_summary(summary: dict[str, Any]) -> None:
    """打印评测汇总"""
    print("\n=== RAG 检索离线评测结果 ===")
    print(f"样本总数: {summary['total']}")
    print(f"top_k: {summary['top_k']}")
    print(f"命中数: {summary['hit_count']}")
    print(f"命中率(hit@k): {summary['hit_rate']:.4f}")
    print(f"召回率(recall@k): {summary['recall_at_k']:.4f}")
    print(f"MRR: {summary['mrr']:.4f}")
    print(f"平均命中排名: {summary['avg_rank']:.4f}")
    print(f"平均首条相似度: {summary['avg_top_similarity']:.4f}")


def print_details(results: list[EvalResult]) -> None:
    """打印每条样本的明细"""
    print("\n=== 样本明细 ===")
    for item in results:
        prefix = f"{item.sample_id}: " if item.sample_id else ""
        status = "命中" if item.hit_at_k else "未命中"
        rank_text = f"rank={item.rank}" if item.rank is not None else "rank=-"
        similarity_text = f"top_similarity={item.top_similarity:.4f}" if item.top_similarity is not None else "top_similarity=-"
        print(f"- {prefix}{item.question}")
        print(f"  {status}, {rank_text}, {similarity_text}")
        if item.matched_result is not None:
            matched_page = item.matched_result.get("metadata", {}).get("page_number", "未知")
            print(f"  命中块: doc={item.matched_result.get('document_name')}, page={matched_page}, chunk_id={item.matched_result.get('id')}")


def save_output(output_path: Path, summary: dict[str, Any], results: list[EvalResult]) -> None:
    """保存评测结果到 JSON 文件"""
    payload = {
        "summary": summary,
        "results": [asdict(item) for item in results],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存评测结果: {output_path}")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="RAG 检索离线评测脚本")
    parser.add_argument("dataset", help="评测数据文件，支持 JSON 或 JSONL")
    parser.add_argument("--top-k", type=int, default=settings.RAG_TOP_K, help="检索返回的文档块数量")
    parser.add_argument("--output", help="评测结果输出 JSON 文件路径")
    parser.add_argument("--no-details", action="store_true", help="不打印逐条明细")
    return parser.parse_args()


async def main() -> None:
    """脚本入口"""
    args = parse_args()
    dataset_path = Path(args.dataset).expanduser().resolve()
    samples = load_samples(dataset_path)

    if not samples:
        raise SystemExit("评测数据为空，无法执行评测")

    results = await run_evaluation(samples, top_k=args.top_k)
    summary = build_summary(results, top_k=args.top_k)
    print_summary(summary)

    if not args.no_details:
        print_details(results)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        save_output(output_path, summary, results)


if __name__ == "__main__":
    asyncio.run(main())
