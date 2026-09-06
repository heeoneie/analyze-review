import { useCallback, useEffect, useState } from 'react';
import {
  getAuthConfig, getMe, getReplyConfig, getAccessCode, clearAccessCode,
} from '../api/client';

/**
 * 화면을 열어도 되는지 판단한다.
 *
 * 계정 체계가 켜져 있으면 로그인 경로, 아직이면 기존 접속코드 경로를 탄다.
 * 서버 설정 하나로 갈리므로 사장님 화면이 어느 쪽으로든 끊기지 않는다.
 *
 * status:
 *   checking - 판단 중. 아무것도 그리지 않는다.
 *   login    - 카카오 로그인이 필요하거나 매장 연결이 필요하다.
 *   locked   - 접속코드가 필요하다.
 *   open     - 통과.
 *
 * 어느 방식으로 통과했는지(mode)를 들고 있어야 401 을 제대로 되돌린다.
 * 카카오 모드에서 세션이 끊겼는데 접속코드 화면을 띄우면, 코드를 넣어도
 * 세션이 살아나지 않아 사장님이 빠져나올 수 없다.
 */
export default function useAccessGate() {
  const [gate, setGate] = useState({ status: 'checking', required: false, mode: null });

  useEffect(() => {
    (async () => {
      let kakaoEnabled = false;
      try {
        const { data } = await getAuthConfig();
        kakaoEnabled = data.kakao_login_enabled;
      } catch {
        kakaoEnabled = false;
      }

      if (kakaoEnabled) {
        try {
          const { data } = await getMe();
          if (!data.authenticated) {
            setGate({ status: 'login', authenticated: false, mode: 'kakao' });
          } else if (!data.store) {
            setGate({ status: 'login', authenticated: true, mode: 'kakao' });
          } else {
            setGate({ status: 'open', required: false, mode: 'kakao' });
          }
        } catch {
          setGate({ status: 'login', authenticated: false, mode: 'kakao' });
        }
        return;
      }

      try {
        const { data } = await getReplyConfig();
        const locked = data.requires_code && !getAccessCode();
        setGate({
          status: locked ? 'locked' : 'open',
          required: data.requires_code,
          mode: 'code',
        });
      } catch {
        // 설정을 못 읽어도 화면은 띄운다. 코드가 틀리면 요청할 때 걸린다.
        setGate({ status: 'open', required: false, mode: 'code' });
      }
    })();
  }, []);

  // 게이트를 통과했다고 표시한다. 로그인·코드 입력이 끝난 뒤 호출한다.
  const open = useCallback(
    (required) => setGate((prev) => ({
      ...prev, status: 'open', required: required ?? prev.required,
    })),
    [],
  );

  // 요청이 401 로 튕겼을 때 되돌린다.
  //
  // 카카오 모드면 세션이 끊긴 것이므로 로그인 화면으로 보낸다. 접속코드
  // 화면을 띄우면 코드를 넣어도 세션이 안 살아나 빠져나올 길이 없다.
  // 접속코드 모드에서만 저장된 코드를 지우고 다시 잠근다.
  const lock = useCallback(() => {
    if (gate.mode === 'kakao') {
      setGate((prev) => ({ ...prev, status: 'login', authenticated: false }));
      return;
    }
    clearAccessCode();
    setGate((prev) => ({ ...prev, status: 'locked', required: true }));
  }, [gate.mode]);

  return { gate, open, lock };
}
