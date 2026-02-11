import { useState } from 'react';
import {
  Sparkles,
  Copy,
  RefreshCw,
  Check,
  MessageCircle,
  Tag,
  ArrowRight,
} from 'lucide-react';
import { generateReply } from '../api/client';

export default function ReplyPanel({ review, onClose }) {
  const [replyData, setReplyData] = useState(null);
  const [editedReply, setEditedReply] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const { data } = await generateReply(
        review.Reviews,
        review.Ratings,
        review.category || null
      );
      setReplyData(data);
      setEditedReply(data.reply);
    } catch (err) {
      setError('답변 생성에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedReply);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 border-t border-blue-100 pt-4 space-y-4">
      {/* 답변 생성 버튼 */}
      {!replyData && !isGenerating && (
        <button
          onClick={handleGenerate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-lg hover:bg-blue-600 transition-colors"
        >
          <Sparkles size={16} />
          AI 맞춤 답변 생성
        </button>
      )}

      {/* 로딩 */}
      {isGenerating && (
        <div className="flex items-center gap-3 py-4">
          <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span className="text-sm text-blue-600">맞춤 답변 생성 중...</span>
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* 생성된 답변 */}
      {replyData && (
        <div className="space-y-3">
          {/* 편집 가능한 답변 */}
          <div>
            <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5">
              <MessageCircle size={14} className="text-blue-500" />
              생성된 답변
            </label>
            <textarea
              value={editedReply}
              onChange={(e) => setEditedReply(e.target.value)}
              rows={5}
              className="w-full text-sm text-gray-800 border border-gray-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-300 resize-y"
            />
          </div>

          {/* 메타데이터 */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
            {replyData.tone && (
              <div className="bg-purple-50 rounded-lg px-3 py-2">
                <span className="text-purple-600 font-medium flex items-center gap-1">
                  <Tag size={12} /> 어조
                </span>
                <p className="text-purple-700 mt-0.5">{replyData.tone}</p>
              </div>
            )}
            {replyData.key_points_addressed?.length > 0 && (
              <div className="bg-green-50 rounded-lg px-3 py-2">
                <span className="text-green-600 font-medium flex items-center gap-1">
                  <Check size={12} /> 다룬 포인트
                </span>
                <ul className="text-green-700 mt-0.5">
                  {replyData.key_points_addressed.map((p, i) => (
                    <li key={i}>- {p}</li>
                  ))}
                </ul>
              </div>
            )}
            {replyData.suggested_action && (
              <div className="bg-amber-50 rounded-lg px-3 py-2">
                <span className="text-amber-600 font-medium flex items-center gap-1">
                  <ArrowRight size={12} /> 후속 조치
                </span>
                <p className="text-amber-700 mt-0.5">{replyData.suggested_action}</p>
              </div>
            )}
          </div>

          {/* 액션 버튼 */}
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                copied
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? '복사됨' : '복사'}
            </button>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={isGenerating ? 'animate-spin' : ''} />
              재생성
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
