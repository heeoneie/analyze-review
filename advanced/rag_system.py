"""
Level 4-2: RAG (Retrieval-Augmented Generation) System
Vector DB를 사용한 동적 Few-shot Learning
"""

import sys
from uuid import uuid4

import pandas as pd
from openai import OpenAI
from utils.json_utils import extract_json_from_text

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("⚠️  필요한 패키지가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요:")
    print("pip install sentence-transformers chromadb")
    sys.exit(1)

import config


class RAGReviewAnalyzer:
    """RAG 기반 리뷰 분석기"""

    def __init__(self, collection_name="review_examples", embedding_model="all-MiniLM-L6-v2"):
        """
        Args:
            collection_name: ChromaDB 컬렉션 이름
            embedding_model: Sentence Transformer 모델 이름
        """
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.llm_model = config.LLM_MODEL
        self.temperature = config.LLM_TEMPERATURE

        # Embedding 모델 초기화
        print(f"📦 Embedding 모델 로딩: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)

        # ChromaDB 초기화
        print("💾 Vector DB 초기화...")
        self.chroma_client = chromadb.Client(Settings(
            anonymized_telemetry=False
        ))

        # 컬렉션 생성 또는 가져오기
        self.collection_name = collection_name
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            print(f"✓ 기존 컬렉션 로드: {collection_name} ({self.collection.count()}개 문서)")
        except ValueError:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "Review categorization examples"}
            )
            print(f"✓ 새 컬렉션 생성: {collection_name}")

    def add_examples(self, review_text, category, metadata=None):
        """Vector DB에 예시 추가"""
        embedding = self.embedding_model.encode(review_text).tolist()

        doc_id = f"review_{uuid4()}"
        self.collection.add(
            embeddings=[embedding],
            documents=[review_text],
            metadatas=[{
                "category": category,
                **(metadata or {})
            }],
            ids=[doc_id]
        )

    def load_ground_truth(self, ground_truth_file):
        """Ground Truth 데이터를 Vector DB에 로드"""
        print(f"\n📂 Ground Truth 로딩: {ground_truth_file}")

        df = pd.read_csv(ground_truth_file)

        # manual_label이 있는 것만 필터
        df = df[df['manual_label'].notna()]

        print(f"   {len(df)}개 예시 추가 중...")

        for _, row in df.iterrows():
            self.add_examples(
                review_text=row['review_text'],
                category=row['manual_label'],
                metadata={'rating': str(row['rating'])}
            )

        print(f"✓ 완료! 총 {self.collection.count()}개 예시")

    def retrieve_similar(self, review_text, n_results=3):
        """유사한 리뷰 검색"""
        embedding = self.embedding_model.encode(review_text).tolist()

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )

        # 결과 포맷팅
        similar_examples = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                similar_examples.append({
                    'text': doc,
                    'category': results['metadatas'][0][i]['category'],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })

        return similar_examples

    def categorize_with_rag(self, review_text, n_examples=3):
        """RAG 기반 리뷰 분류"""
        # 1. 유사한 예시 검색
        similar_examples = self.retrieve_similar(review_text, n_results=n_examples)

        # 2. Few-shot 프롬프트 구성
        examples_text = ""
        if similar_examples:
            examples_text = "Similar examples from past reviews:\n\n"
            for i, example in enumerate(similar_examples, 1):
                examples_text += f"{i}. Review: \"{example['text'][:150]}...\"\n"
                examples_text += f"   Category: {example['category']}\n\n"

        prompt = f"""{examples_text}

Now, categorize this new review:

Review: "{review_text}"

Categories:
- delivery_delay: Shipping/delivery took too long
- wrong_item: Received incorrect product
- poor_quality: Product quality is bad
- damaged_packaging: Package or product was damaged
- size_issue: Size doesn't fit
- missing_parts: Parts are missing
- not_as_described: Product doesn't match description
- customer_service: Customer service issues
- price_issue: Price-related complaints
- other: Cannot be categorized

Based on the similar examples above, select the most appropriate category.

Output JSON:
{{
  "category": "category_name",
  "confidence": 0.9,
  "reasoning": "brief explanation"
}}
"""

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing e-commerce customer feedback with retrieval-augmented generation."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )

        result = extract_json_from_text(response.choices[0].message.content)
        result['retrieved_examples'] = similar_examples
        return result

    def categorize_batch(self, reviews_list, n_examples=3):
        """여러 리뷰 배치 분류"""
        results = []

        print(f"\n🤖 RAG 기반 분석 시작 (검색 예시: {n_examples}개)")
        for idx, review in enumerate(reviews_list):
            print(f"   [{idx+1}/{len(reviews_list)}] 분석 중...", end='\r')

            try:
                result = self.categorize_with_rag(review, n_examples=n_examples)
                results.append({
                    'review_number': idx + 1,
                    'category': result['category'],
                    'brief_issue': result.get('reasoning', ''),
                    'confidence': result.get('confidence', 0),
                    'retrieved_examples': len(result.get('retrieved_examples', []))
                })
            except Exception as e:  # pylint: disable=broad-except
                # Keep batch processing even if a single review fails.
                print(f"\n   ⚠️  에러 발생 (Review {idx+1}): {e}")
                results.append({
                    'review_number': idx + 1,
                    'category': 'other',
                    'brief_issue': 'Error during analysis',
                    'confidence': 0
                })

        print("\n✓ 완료!")
        return {'categories': results}

    def clear_database(self):
        """Vector DB 초기화"""
        if self.collection is None:
            print("⚠️  컬렉션이 초기화되지 않았습니다.")
            return

        collection_name = self.collection.name
        try:
            self.chroma_client.delete_collection(collection_name)
            self.collection = None
            print(f"✓ 컬렉션 '{collection_name}' 삭제됨")
        except ValueError as e:
            print(f"⚠️  컬렉션을 찾을 수 없습니다: {e}")
            self.collection = None
        except Exception as e:  # pylint: disable=broad-except
            # ChromaDB can raise various runtime errors; log and continue cleanup.
            print(f"⚠️  컬렉션 삭제 중 오류 발생: {e}")


def demo():
    """RAG 시스템 데모"""
    print("="*80)
    print("  RAG 기반 리뷰 분석 시스템 데모")
    print("="*80)

    # RAG 분석기 초기화
    analyzer = RAGReviewAnalyzer()

    # 예시 데이터 추가 (실제로는 Ground Truth 로드)
    print("\n1. 예시 데이터 추가")
    examples = [
        ("Package took 3 weeks to arrive", "delivery_delay"),
        ("Delivery was extremely slow", "delivery_delay"),
        ("Shipping took forever", "delivery_delay"),
        ("Received wrong color", "wrong_item"),
        ("Got blue instead of red", "wrong_item"),
        ("This is not what I ordered", "wrong_item"),
        ("Product broke after 2 days", "poor_quality"),
        ("Cheap material, fell apart", "poor_quality"),
        ("Quality is terrible", "poor_quality"),
    ]

    for text, category in examples:
        analyzer.add_examples(text, category)

    print(f"✓ {len(examples)}개 예시 추가됨")

    # 테스트 리뷰
    print("\n2. 테스트 리뷰 분석")
    test_reviews = [
        "Package arrived one month late!",
        "Received completely different item",
        "Product quality is awful, broke immediately"
    ]

    for review in test_reviews:
        print(f"\n📝 리뷰: {review}")

        result = analyzer.categorize_with_rag(review, n_examples=2)

        print(f"   분류: {result['category']}")
        print(f"   신뢰도: {result.get('confidence', 'N/A')}")
        print(f"   이유: {result.get('reasoning', 'N/A')}")

        if 'retrieved_examples' in result:
            print("   참고한 예시:")
            for i, ex in enumerate(result['retrieved_examples'], 1):
                print(f"      {i}. [{ex['category']}] {ex['text'][:50]}...")


def main():
    """실제 Ground Truth로 RAG 시스템 구축"""
    import argparse

    parser = argparse.ArgumentParser(description='RAG 기반 리뷰 분석')
    parser.add_argument('--demo', action='store_true',
                        help='데모 모드 실행')
    parser.add_argument('--load-ground-truth', type=str,
                        help='Ground Truth CSV 파일 경로')
    parser.add_argument('--clear', action='store_true',
                        help='Vector DB 초기화')
    args = parser.parse_args()

    if args.demo:
        demo()
        return

    analyzer = RAGReviewAnalyzer()

    if args.clear:
        analyzer.clear_database()
        return

    if args.load_ground_truth:
        analyzer.load_ground_truth(args.load_ground_truth)
        print("\n✓ RAG 시스템 준비 완료!")
        print("   이제 이 시스템을 사용하여 리뷰를 분류할 수 있습니다.")
    else:
        print("\n사용법:")
        print("  --demo: 데모 실행")
        print("  --load-ground-truth evaluation/evaluation_dataset.csv: Ground Truth 로드")
        print("  --clear: Vector DB 초기화")


if __name__ == "__main__":
    main()
