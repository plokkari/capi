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
  addEventListener('scroll', ()=>{
    const y = scrollY + 120;
    let current = '#home';
    sections.forEach(s=>{ if(s && y >= s.offsetTop) current = '#'+s.id; });
    document.querySelectorAll('.pill').forEach(b=>{
      b.classList.toggle('active', (b.getAttribute('href') === current));
    });
  });
}

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
function boot(){
  initReveal();
  initParallax();
  initScrollSpy();
  initSmoothLinks();
  initMemeChart();
}

document.addEventListener('DOMContentLoaded', boot);
