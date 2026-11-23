// Bandeau « sujet » toujours visible en haut + mini-écran d'oscilloscope flottant :
// dès que la vraie face de l'oscillo sort de l'écran (on est descendu vers la plaque), son écran reste visible en bas à droite.
const Dock = (() => {
  let visible = true, mini = null, mctx = null;
  function init() {
    const face = document.getElementById("face-scope");
    mini = document.getElementById("dock-canvas"); mctx = mini.getContext("2d");
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(es => { visible = es[0].isIntersecting; document.getElementById("dock").classList.toggle("show", !visible); update(); }, { threshold: 0.15 }).observe(face);
    }
    document.getElementById("subject-toggle").onclick = () => document.getElementById("subject-bar").classList.toggle("collapsed");
    document.getElementById("dock-up").onclick = () => face.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function setSubject(m) {
    const bar = document.getElementById("subject-text");
    if (!m) { bar.innerHTML = "<b>Mode libre</b> — pose ce que tu veux ; les écrans réagissent au câblage."; return; }
    const r = m.reglages || {}, esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
    bar.innerHTML = `<b>${esc(m.titre)}</b> — ${esc(m.objectif)}` + (r.gbf ? `<span class="reg">GBF : ${esc(r.gbf)}</span>` : "") + (r.psu ? `<span class="reg">Alim : ${esc(r.psu.split("·").slice(0, 2).join("·"))}</span>` : "");
  }
  function update() {
    if (visible || !mini) return;
    const src = document.querySelector("#face-scope canvas");
    if (!src) return;
    mini.width = src.width; mini.height = src.height;
    mctx.drawImage(src, 0, 0);
  }
  return { init, setSubject, update };
})();
