import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { claimStore } from '../api/client';

/**
 * 카카오 로그인이 켜졌을 때의 진입 화면.
 *
 * 두 단계다:
 *   1. 로그인 전 — 카카오 버튼만 보여준다.
 *   2. 로그인했지만 매장이 없음 — 기존 접속코드로 매장을 이관받는다.
 *
 * 2단계가 있는 이유: 지금 서비스를 쓰고 계신 사장님은 이미 접속코드를 알고
 * 있다. 카카오로 로그인한 뒤 그 코드를 한 번만 넣으면 매장이 계정에 붙는다.
 * 코드를 모르는 사람이 먼저 로그인해서 매장을 가져가는 것도 이걸로 막힌다.
 */
export default function LoginGate({ authenticated, onClaimed }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitClaim = async (event) => {
    event.preventDefault();
    if (!code.trim() || isSubmitting) return;

    setError(null);
    setIsSubmitting(true);
    try {
      const { data } = await claimStore(code.trim());
      onClaimed(data.store);
    } catch (err) {
      const status = err.response?.status;
      if (status === 401) setError('코드가 맞지 않습니다.');
      else if (status === 409) setError('이미 다른 계정에 연결된 매장입니다.');
      else setError('확인하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-5">
      <div className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-sm">
        <div>
          <h1 className="text-lg font-bold text-slate-900">리뷰 답글 만들기</h1>
          <p className="mt-1 text-sm text-slate-500">
            {authenticated
              ? '쓰고 계신 접속 코드를 한 번만 넣어 주세요. 다음부터는 필요 없습니다.'
              : '카카오로 로그인하면 바로 쓰실 수 있습니다.'}
          </p>
        </div>

        {!authenticated ? (
          // 브라우저를 카카오로 넘겨야 해서 fetch 가 아니라 이동이다.
          <a
            href="/api/auth/kakao/login"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#FEE500]
                       px-5 py-3 text-base font-semibold text-[#191600] transition hover:brightness-95"
          >
            카카오로 시작하기
          </a>
        ) : (
          <form onSubmit={submitClaim} className="space-y-3">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="접속 코드"
              autoComplete="off"
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base
                         text-slate-900 outline-none focus:border-slate-400"
            />
            <button
              type="submit"
              disabled={!code.trim() || isSubmitting}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900
                         px-5 py-3 text-base font-semibold text-white transition
                         hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isSubmitting && <Loader2 size={18} className="animate-spin" />}
              매장 연결하기
            </button>
          </form>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
