// Inject header & footer partials and set year + nav setup
async function inject(id, file) {
  try {
    const host = document.getElementById(id);
    if (!host) return;
    const res = await fetch(file, { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status + " " + res.statusText);
    host.innerHTML = await res.text();
    if (id === "footer") {
      const y = document.getElementById("year");
      if (y) y.textContent = new Date().getFullYear();
    }
    if (id === "header") {
      // compute header height -> body padding
      const nav = document.querySelector(".nav");
      const h = nav?.offsetHeight || 64;
      document.documentElement.style.setProperty("--navH", h + "px");
      setupNav();
      setupHeaderShadow();
    }
  } catch (e) {
    console.error("Failed to load", file, e);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  inject("header", "partials/header.html");
  inject("footer", "partials/footer.html");

  // Panel entrance observer (for page-like transitions)
  const panels = document.querySelectorAll(".panel");
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if (e.isIntersecting) e.target.classList.add("enter");
    });
  }, { threshold: 0.28 });
  panels.forEach(p => io.observe(p));
});

function setupNav(){
  const links = Array.from(document.querySelectorAll(".pillNav a"));
  const isHome = /\/index\.html$|\/$/.test(location.pathname);

  // Smooth scroll ONLY on the home page for links that point to index.html#id or #id
  if (isHome) {
    links.forEach(a=>{
      const url = new URL(a.href, location.origin);
      if (url.pathname === location.pathname && url.hash) {
        a.addEventListener("click", (e)=>{
          const target = document.querySelector(url.hash);
          if (!target) return;
          e.preventDefault();
          const headerH = document.querySelector(".nav")?.offsetHeight || 70;
          const y = target.getBoundingClientRect().top + window.scrollY - (headerH + 12);
          window.scrollTo({ top: y, behavior: "smooth" });
        });
      }
    });

    // Active link highlight by section in view (home only)
    const sectionMap = new Map();
    links.forEach(a=>{
      const url = new URL(a.href, location.origin);
      if (url.pathname === location.pathname && url.hash) {
        const sec = document.querySelector(url.hash);
        if (sec) sectionMap.set(sec.id, a);
      }
    });

    const obs = new IntersectionObserver((entries)=>{
      entries.forEach(entry=>{
        const a = sectionMap.get(entry.target.id);
        if (a) a.classList.toggle("active", entry.isIntersecting);
      });
    }, { rootMargin: "-45% 0px -45% 0px", threshold: 0.01 });

    sectionMap.forEach((_, id)=> {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
  } else {
    // Not on home (e.g., arcade.html): mark the correct pill active
    links.forEach(a => a.classList.remove("active"));
    const active =
      location.pathname.endsWith("/arcade.html") ? links.find(a=>/arcade\.html$/.test(a.getAttribute("href")))
      : links.find(a=>/index\.html#home$/.test(a.getAttribute("href")));
    if (active) active.classList.add("active");
  }
}

function setupHeaderShadow(){
  const nav = document.querySelector(".nav");
  const marker = document.createElement("div");
  marker.style.position = "absolute";
  marker.style.top = "var(--navH)";
  marker.style.height = "1px";
  marker.style.width = "1px";
  marker.style.pointerEvents = "none";
  document.body.prepend(marker);
  const io = new IntersectionObserver(
    (entries)=>{ nav?.classList.toggle("scrolled", !entries[0].isIntersecting); },
    { rootMargin: "-1px 0px 0px 0px", threshold: 0 }
  );
  io.observe(marker);
}

// ------- Footer helper (copy contract) -------
document.addEventListener("click", (e)=>{
  const btn = e.target.closest(".copyChip");
  if (!btn) return;
  const sel = btn.getAttribute("data-copy");
  const target = sel ? document.querySelector(sel) : null;
  const text = target ? target.textContent.trim() : "";
  if (!text || text === "TBA") { btn.textContent = "No address yet"; setTimeout(()=>btn.textContent="Copy", 1500); return; }
  navigator.clipboard.writeText(text).then(()=>{
    const old = btn.textContent; btn.textContent = "Copied!";
    setTimeout(()=>btn.textContent = old, 1200);
  }).catch(()=>{
    const old = btn.textContent; btn.textContent = "Failed";
    setTimeout(()=>btn.textContent = old, 1200);
  });
});
