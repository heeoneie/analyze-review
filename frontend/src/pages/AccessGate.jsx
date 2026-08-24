import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { setAccessCode, verifyAccessCode } from '../api/client';

/** 공개 URL 남용을 막는 최소한의 잠금. 계정도 비밀번호도 아니고 매장용 코드 하나다. */
export default function AccessGate({ onUnlock }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [isChecking, setIsChecking] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (!code.trim() || isChecking) return;

    setError(null);
    setIsChecking(true);
    try {
      await verifyAccessCode(code.trim());
      setAccessCode(code.trim());
      onUnlock();
    } catch (err) {
      setError(
        err.response?.status === 401
          ? '코드가 맞지 않습니다.'
          : '확인하지 못했습니다. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-5">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-6 shadow-sm">
        <div>
          <h1 className="text-lg font-bold text-slate-900">리뷰 답글 만들기</h1>
          <p className="mt-1 text-sm text-slate-500">접속 코드를 한 번만 입력하면 됩니다.</p>
        </div>

        <input
          type="password"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          autoComplete="one-time-code"
          placeholder="접속 코드"
          className="w-full rounded-xl border border-slate-200 px-4 py-3 text-base
                     text-slate-900 outline-none focus:border-slate-400"
        />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={!code.trim() || isChecking}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-5 py-3
                     text-base font-semibold text-white transition hover:bg-slate-700
                     disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isChecking && <Loader2 size={18} className="animate-spin" />}
          들어가기
        </button>
      </form>
    </div>
  );
}
