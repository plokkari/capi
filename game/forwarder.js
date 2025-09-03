// forwarder.js — pygbag -> parent (anti-spam, idempotent)
(() => {
  if (window.__pc_forwarder_active) return;
  window.__pc_forwarder_active = true;

  const post = (m) => { try { top.postMessage(m, '*'); } catch {} };

  let lastStart = 0;
  let lastScoreVal = null;
  let lastScoreTs  = 0;

  function sendStart() {
    const now = Date.now();
    if (now - lastStart < 1000) return;     // 1 per second
    lastStart = now;
    post({ type: 'RUN_START' });
  }

  function sendScore(n) {
    const s = Number(n) || 0;
    const now = Date.now();
    if (s === lastScoreVal && now - lastScoreTs < 2000) return; // same score ≤1/2s
    lastScoreVal = s;
    lastScoreTs  = now;
    post({ type: 'SCORE', score: s });
  }

  function wrap(name, handler) {
    // wrap existing
    const prev = window[name];
    if (typeof prev === 'function' && !prev.__wrapped) {
      const w = function (...a) { handler(...a); return prev.apply(this, a); };
      w.__wrapped = true; window[name] = w;
    }
    // wrap future assignments
    let f = window[name];
    Object.defineProperty(window, name, {
      configurable: true,
      get(){ return f; },
      set(v){
        if (typeof v === 'function') {
          const w = function (...a) { handler(...a); return v.apply(this, a); };
          w.__wrapped = true; f = w; console.log('[forwarder] wrapped', name);
        } else f = v;
      }
    });
  }

  wrap('notify_run_start', () => sendStart());
  wrap('notify_score',     (n) => sendScore(n));

  console.log('[forwarder] active');
})();
