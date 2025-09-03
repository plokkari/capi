/* Minimal floating particles that can switch "vibe" colors.
   Exposes: window.BaraParticles.setVibe('neutral' | 'up' | 'down')
*/
(function(){
  const cvs = document.getElementById("particles");
  if (!cvs) return;
  const ctx = cvs.getContext("2d", { alpha: true });
  const DPR = Math.max(1, window.devicePixelRatio || 1);

  let W = 0, H = 0, N = 100;        // number of particles
  let parts = [];
  let vibe = "neutral";            // 'neutral' | 'up' | 'down'
  let mouse = { x: 0, y: 0 };

  function hexToRgb(h){
    h = h.replace("#",""); if (h.length===3) h = h.split("").map(s=>s+s).join("");
    const n = parseInt(h,16); return { r:(n>>16)&255, g:(n>>8)&255, b:n&255 };
  }
  function cssVar(name, fallback){ 
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function mix(a,b,t){ return { r:a.r+(b.r-a.r)*t, g:a.g+(b.g-a.g)*t, b:a.b+(b.b-a.b)*t }; }

  const palette = () => {
    const accent1 = hexToRgb(cssVar("--accent1", "#d44aff"));
    const accent2 = hexToRgb(cssVar("--accent2", "#6aa8ff"));
    const ok      = hexToRgb(cssVar("--ok",      "#49e39e"));
    const bad     = hexToRgb(cssVar("--bad",     "#ff6b7a"));
    if (vibe === "up")   return [ok, accent2];
    if (vibe === "down") return [bad, accent1];
    return [accent1, accent2]; // neutral
  };

  function resize(){
    W = Math.floor(window.innerWidth * DPR);
    H = Math.floor(window.innerHeight * DPR);
    cvs.width = W; cvs.height = H;
    cvs.style.width = `${W / DPR}px`;
    cvs.style.height = `${H / DPR}px`;
  }

  function spawn(i=0){
    const speed = (Math.random()*0.25 + 0.05) * DPR; // very slow
    parts[i] = {
      x: Math.random()*W, y: Math.random()*H,
      vx: (Math.random()*2-1)*speed, vy: (Math.random()*2-1)*speed,
      r: (Math.random()*2 + 1) * DPR,  // instead of 1.5 + 0.6
      t: Math.random(), // color mix factor [0..1]
      a: Math.random()*0.35 + 0.15     // instead of 0.25 + 0.08
    };
  }

  function init(){
    resize();
    parts.length = N;
    for (let i=0;i<N;i++) spawn(i);
    loop();
  }

  function draw(){
    ctx.clearRect(0,0,W,H);
    const [c1, c2] = palette();
    for (let i=0;i<N;i++){
      const p = parts[i];
      // parallax (tiny) towards mouse
      const px = p.x + (mouse.x*0.03*DPR - W*0.015);
      const py = p.y + (mouse.y*0.03*DPR - H*0.015);

      const col = mix(c1, c2, (p.t + performance.now()/12000 + i*0.03) % 1);
      ctx.fillStyle = `rgba(${col.r|0},${col.g|0},${col.b|0},${p.a})`;
      ctx.beginPath();
      ctx.arc(px, py, p.r, 0, Math.PI*2);
      ctx.fill();

      p.x += p.vx; p.y += p.vy;
      // soft screen wrap
      if (p.x < -10) p.x = W+10; else if (p.x > W+10) p.x = -10;
      if (p.y < -10) p.y = H+10; else if (p.y > H+10) p.y = -10;
    }
  }

  function loop(){
    draw();
    requestAnimationFrame(loop);
  }

  window.addEventListener("resize", resize);
  window.addEventListener("mousemove", (e)=>{ mouse.x = e.clientX; mouse.y = e.clientY; });

  window.BaraParticles = {
    setVibe(v){ vibe = v || "neutral"; }
  };

  init();
})();
