<<<<<<< HEAD
/* =========================
   Starfield background
========================= */
(function(){
  const c = document.querySelector('canvas.stars'); 
  if(!c) return;
  const ctx = c.getContext('2d'); let w,h,stars=[];
  function resize(){
    w = c.width = innerWidth;
    h = c.height = innerHeight;
    stars = Array.from({length:120}, () => ({
      x: Math.random()*w,
      y: Math.random()*h,
      r: Math.random()*1.4 + 0.3,
      s: Math.random()*0.6 + 0.2
    }));
  }
  function draw(){
    ctx.clearRect(0,0,w,h);
    for(const s of stars){
      ctx.globalAlpha = 0.35 + Math.sin((performance.now()/1000)*s.s)*0.25;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }
  addEventListener('resize', resize);
  resize(); draw();
})();

/* =========================
   Loader (themed, gradient bar, rotating tips)
========================= */
document.addEventListener('DOMContentLoaded', ()=>{
  const loader = document.getElementById('loader');
  const fill   = document.getElementById('loadFill');
  const textEl = document.getElementById('loadText');
  const tipEl  = document.getElementById('loadTip');
  if(!loader || !fill) return;

  const tips = [
    "Warming up Flappybara’s wings…",
    "Counting $BARA one capy at a time…",
    "Greasing arcade joysticks…",
    "Polishing the leaderboard trophy…",
    "Teaching capybaras to HODL…",
    "Optimizing memes per second…",
  ];
  let tipIdx = 0;
  function showNextTip(){
    if(!tipEl) return;
    tipEl.style.animation = 'none';
    // force reflow to restart CSS animation
    // eslint-disable-next-line no-unused-expressions
    tipEl.offsetHeight;
    tipEl.textContent = tips[tipIdx % tips.length];
    tipEl.style.animation = '';
    tipIdx++;
  }
  showNextTip();
  const tipTimer = setInterval(showNextTip, 1100);

  // ~2.4–3.2s eased progress
  const total = 2400 + Math.random()*800;
  const t0 = performance.now();

  function tick(){
    const elapsed = performance.now() - t0;
    const t = Math.min(1, elapsed / total);
    const eased = 1 - Math.pow(1 - t, 3);
    const pct = Math.floor(eased * 100);

    fill.style.width = pct + '%';
    if(textEl){
      textEl.textContent = pct < 99 ? `LOADING ${pct}%` : 'READY!';
    }

    if (t < 1){
      requestAnimationFrame(tick);
    } else {
      clearInterval(tipTimer);
      loader.style.opacity='0';
      setTimeout(()=> loader.style.display='none', 320);
    }
  }
  requestAnimationFrame(tick);
});

/* =========================
   Reveal-on-scroll
========================= */
function initReveal(){
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting){
        e.target.classList.add('show');
        io.unobserve(e.target);
      }
    });
  }, {threshold:0.15});
  document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
}

/* =========================
   Hero parallax for #getBara
========================= */
function initParallax(){
  const img = document.getElementById('getBara');
  const home = document.getElementById('homeSection');
  if(!img || !home) return;

  let ticking = false;
  function onScroll(){
    if(!ticking){ requestAnimationFrame(update); ticking = true; }
  }
  function update(){
    const rect = home.getBoundingClientRect();
    const prog = Math.min(1, Math.max(0, (-rect.top)/(window.innerHeight*0.6)));
    img.style.transform = `translateY(${prog*80}px)`;
    img.style.opacity = (Math.max(0, 1 - prog*1.15)).toFixed(3);
    ticking = false;
  }
  addEventListener('scroll', onScroll, {passive:true});
  update();
}

/* =========================
   Scroll-spy (highlight nav pill)
========================= */
function initScrollSpy(){
  const sections = ['#home','#about','#arcade','#roadmap','#faq','#socials']
    .map(s=>document.querySelector(s)).filter(Boolean);

=======
/* ===== starfield background ===== */
(function stars(){
  const c = document.querySelector('.stars');
  if(!c) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const ctx = c.getContext('2d');
  function resize(){
    c.width = innerWidth * dpr;
    c.height = innerHeight * dpr;
    draw();
  }
  function draw(){
    ctx.clearRect(0,0,c.width,c.height);
    for(let i=0;i<150;i++){
      const x = Math.random()*c.width;
      const y = Math.random()*c.height;
      const r = Math.random()*1.5+0.2;
      ctx.fillStyle = `rgba(255,255,255,${Math.random()*0.8})`;
      ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fill();
    }
  }
  resize(); addEventListener('resize', resize);
})();

/* ===== loader (always on fresh load/refresh) ===== */
(function loader(){
  const wrap = document.getElementById('loader');
  if(!wrap) return;
  const fill = document.getElementById('loadFill');
  const text = document.getElementById('loadText');
  const tip  = document.getElementById('loadTip');
  const tips = [
    'Spawning flappy pipes…',
    'Feeding capybaras…',
    'Greasing Arcade joysticks…',
    'Counting leaderboard tickets…',
    'Warm-starting chart rockets…'
  ];
  tip.textContent = tips[Math.floor(Math.random()*tips.length)];
  let p = 0;
  const timer = setInterval(()=>{
    p += Math.random()*18;
    if(p > 100) p = 100;
    fill.style.width = p+'%';
    if(p >= 100){
      clearInterval(timer);
      setTimeout(()=> wrap.classList.add('hide'), 250);
      setTimeout(()=> wrap.style.display='none', 800);
    }
  }, 220);
})();

/* ===== smooth reveal on scroll ===== */
function initReveal(){
  const els = document.querySelectorAll('.reveal');
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting){ e.target.classList.add('revealed'); io.unobserve(e.target); }
    });
  }, { threshold: .1 });
  els.forEach(el=>io.observe(el));
}

/* ===== nav pills + smooth scrolling + active state ===== */
function initSmoothLinks(){
  document.querySelectorAll('.pill').forEach(a=>{
    a.addEventListener('click', (e)=>{
      const href = a.getAttribute('href') || '';
      if(href.startsWith('#')){
        e.preventDefault();
        document.querySelectorAll('.pill').forEach(x=>x.classList.remove('active'));
        a.classList.add('active');
        const el = document.querySelector(href);
        if(el) window.scrollTo({ top: el.offsetTop - 70, behavior: 'smooth' });
      }
    });
  });
}
function initScrollSpy(){
  const sections = ['#home','#about','#arcade','#how','#faq'].map(s=>document.querySelector(s)).filter(Boolean);
>>>>>>> 83a077ff9885a54abfe82ba752ed8933637b0471
  addEventListener('scroll', ()=>{
    const y = scrollY + 120;
    let current = '#home';
    sections.forEach(s=>{ if(s && y >= s.offsetTop) current = '#'+s.id; });
    document.querySelectorAll('.pill').forEach(b=>{
      b.classList.toggle('active', (b.getAttribute('href') === current));
    });
  });
}
<<<<<<< HEAD
   
/* =========================
   Smooth scroll for same-page anchors
========================= */
function initSmoothLinks(){
  document.querySelectorAll('a[href^="#"]').forEach(a=>{
    a.addEventListener('click', (e)=>{
      const targetId = a.getAttribute('href');
      const el = document.querySelector(targetId);
      if(el){
        e.preventDefault();
        window.scrollTo({ top: el.offsetTop - 70, behavior:'smooth' });
      }
    });
  });
}

/* =========================
   Meme Chart (placeholder live wiggle)
========================= */
function initMemeChart(){
  const el = document.getElementById('memeChart');
  if(!el || !window.Chart) return;

  const wrap = el.parentElement;               // .chart-wrap
  const h = wrap ? wrap.clientHeight : 320;    // gradient height
  const priceEl = document.getElementById('memePrice');
  const deltaEl = document.getElementById('memeDelta');
  const tfBtns  = document.querySelectorAll('.chip.tf');

  const ctx = el.getContext('2d');

  // gradient fill sized to wrapper
  let grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(122,92,255,.45)');
  grad.addColorStop(1, 'rgba(122,92,255,0)');

  // seed data (random walk)
  const N = 40;
  let base = 0.000123;
  let speed = 1.0;
  const data = [];
  for(let i=0;i<N;i++){
    base += (Math.random()-0.5) * 0.000003;
    data.push(Math.max(0, base));
  }
  const labels = Array.from({length:N}, (_,i)=> i.toString());

  const chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: '#9ecbff',
        borderWidth: 2,
        tension: 0.35,
        fill: true,
        backgroundColor: grad,
        pointRadius: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { display:false }, y: { display:false, grace: '8%' } },
      plugins: { legend: { display:false }, tooltip: { enabled:false } },
      animation: { duration: 220 }
    }
  });

  // refresh gradient once chart sizes to device pixels
  setTimeout(()=>{
    const h2 = wrap ? wrap.clientHeight : 320;
    grad = ctx.createLinearGradient(0, 0, 0, h2);
    grad.addColorStop(0, 'rgba(122,92,255,.45)');
    grad.addColorStop(1, 'rgba(122,92,255,0)');
    chart.data.datasets[0].backgroundColor = grad;
    chart.update('none');
  }, 0);

  function fmt(n){ return '$' + n.toFixed(6); }
  function updateUI(){
    const last = chart.data.datasets[0].data.at(-1);
    const first= chart.data.datasets[0].data[0];
    const chg  = ((last - first) / first) * 100;

    priceEl.textContent = fmt(last);
    deltaEl.textContent = (chg>=0? '+' : '') + chg.toFixed(2) + '%';
    deltaEl.classList.toggle('up', chg>=0);
    deltaEl.classList.toggle('down', chg<0);

    chart.data.datasets[0].borderColor = chg>=0 ? '#6BFF9D' : '#ff7f7f';
  }

  let timer;
  function start(){
    stop();
    timer = setInterval(()=>{
      const last = chart.data.datasets[0].data.at(-1);
      const next = Math.max(0, last + (Math.random()-0.5) * 0.000003 * speed);
      chart.data.datasets[0].data.push(next);
      chart.data.datasets[0].data.shift();
      chart.update('none');
      updateUI();
    }, 950);
  }
  function stop(){ if(timer) clearInterval(timer); }

  tfBtns.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      tfBtns.forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      speed = parseFloat(btn.dataset.speed || '1');
    });
  });

  updateUI(); start();
}

/* =========================
   Boot on page view
========================= */
=======

/* ===== parallax of GET $BARA image ===== */
function initParallax(){
  const img = document.getElementById('getBara');
  const scene = document.querySelector('.hero-scene');
  if(!img || !scene) return;
  function onScroll(){
    const rect = scene.getBoundingClientRect();
    // move image up/down slightly with scroll and fade out near bottom of hero
    const t = Math.min(Math.max((0 - rect.top) / 300, -1), 1);
    img.style.transform = `translateY(${t*40}px)`;
    // clip by section bottom visually handled by overflow hidden
  }
  addEventListener('scroll', onScroll, { passive:true });
  onScroll();
}

/* ===== meme chart (placeholder random walk; hook to live later) ===== */
function initMemeChart(){
  const el = document.getElementById('memeChart'); if(!el || !window.Chart) return;
  const wrap = el.parentElement;
  const h = wrap ? wrap.clientHeight : 260;
  const ctx = el.getContext('2d');
  let grad = ctx.createLinearGradient(0,0,0,h);
  grad.addColorStop(0,'rgba(122,92,255,.45)');
  grad.addColorStop(1,'rgba(122,92,255,0)');

  // seed random walk
  const labels = Array.from({length:80}, (_,i)=>i.toString());
  let v = 0.00012; // fake price
  const data = labels.map(()=> (v += (Math.random()-0.5)*v*0.15, v = Math.max(v, 0.00001)));

  const chart = new Chart(ctx,{
    type:'line',
    data:{ labels, datasets:[{ data, borderColor:'#9ecbff', borderWidth:2, tension:.35, fill:true, backgroundColor:grad, pointRadius:0 }]},
    options:{
      responsive:true, maintainAspectRatio:false,
      scales:{ x:{display:false}, y:{display:false, grace:'8%'} },
      plugins:{ legend:{display:false}, tooltip:{enabled:false} },
      animation:{ duration:220 }
    }
  });

  const priceEl = document.getElementById('memePrice');
  const deltaEl = document.getElementById('memeDelta');
  function updateUI(){
    const ds = chart.data.datasets[0].data;
    const last = ds.at(-1), first = ds[0];
    const chg = first ? ((last-first)/first)*100 : 0;
    priceEl.textContent = '$'+Number(last).toFixed(6);
    deltaEl.textContent = (chg>=0?'+':'')+chg.toFixed(2)+'%';
    deltaEl.classList.toggle('up', chg>=0);
    deltaEl.classList.toggle('down', chg<0);
    chart.data.datasets[0].borderColor = chg>=0 ? '#6BFF9D' : '#ff7f7f';
  }
  updateUI();

  let speed = 1.0;
  document.querySelectorAll('.chip.tf').forEach(b=>{
    b.addEventListener('click', ()=>{
      document.querySelectorAll('.chip.tf').forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      speed = parseFloat(b.dataset.speed || '1');
    });
  });

  function tick(){
    // push one new random point
    const last = chart.data.datasets[0].data.at(-1);
    let next = last + (Math.random()-0.5)*last*0.12;
    next = Math.max(next, 0.0000001);
    chart.data.labels.push((chart.data.labels.length+1).toString());
    chart.data.datasets[0].data.push(next);
    while(chart.data.labels.length > 100){ chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
    chart.update('none');
    updateUI();
    setTimeout(tick, 1100 / speed);
  }
  tick();
}

/* ===== boot ===== */
>>>>>>> 83a077ff9885a54abfe82ba752ed8933637b0471
function boot(){
  initReveal();
  initParallax();
  initScrollSpy();
  initSmoothLinks();
  initMemeChart();
}

<<<<<<< HEAD
/* =========================
   Swup page transitions
========================= */
document.addEventListener('DOMContentLoaded', ()=>{
  if(window.Swup){
    const swup = new Swup({ containers:['#swup'], animateHistoryBrowsing:true });
    swup.hooks.on('page:view', boot);
  }
  boot();
});
=======
document.addEventListener('DOMContentLoaded', boot);
>>>>>>> 83a077ff9885a54abfe82ba752ed8933637b0471
