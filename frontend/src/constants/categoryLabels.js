export const CATEGORY_LABELS = {
  battery_issue: '배터리 문제',
  network_issue: '네트워크 문제',
  display_issue: '화면 문제',
  software_issue: '소프트웨어 문제',
  overheating: '발열',
  sound_issue: '사운드 문제',
  delivery_delay: '배송 지연',
  wrong_item: '오배송',
  poor_quality: '품질 불량',
  damaged_packaging: '포장 파손',
  size_issue: '크기 불만',
  missing_parts: '구성품 누락',
  not_as_described: '상품 불일치',
  customer_service: '고객 서비스',
  price_issue: '가격 불만',
  positive_review: '긍정 리뷰',
  other: '기타',
};

export function getCategoryLabel(name) {
  return CATEGORY_LABELS[name] || name;
}
