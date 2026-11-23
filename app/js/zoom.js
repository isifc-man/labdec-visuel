// Zoom : (1) un appareil en grand, avec à côté ses réglages demandés par le montage et l'annexe du sujet qui le concerne ;
//        (2) une capture du sujet en plein écran (clic = 100 % / ajusté).
// Ouvrir : bouton 🔍 de l'appareil, ou double-clic sur le fond de la face. Fermer : Échap, clic hors de l'appareil, ou ✕.
const Zoom = (() => {
  let cur = null, lb = null;
  const esc = s => String(s == null ? "" : s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  function side(inst) {
    const key = inst.dataset.inst, m = curMontage(), box = inst.querySelector(".zoom-side") || inst.appendChild(Object.assign(document.createElement("div"), { className: "zoom-side" }));
    const r = (m && m.reglages) || {}, txt = r[key];
    const names = { scope: "oscilloscope", gbf: "générateur", psu: "alimentation" };
    let h = `<h4>${names[key] || key}${m ? " — " + esc(m.titre) : ""}</h4>`;
    h += txt ? `<p><b>Réglage indiqué par le montage</b><br>${esc(txt)}</p>` : `<p class="mut">Pas de réglage particulier indiqué pour ce montage.</p>`;
    if (m && m.objectif) h += `<p class="mut">${esc(m.objectif)}</p>`;
    const keys = (typeof SUJET !== "undefined" && SUJET && SUJET.annexes[key]) || [];
    keys.forEach(k => { const p = SUJET.pieces[k]; h += `<figure class="sj"><figcaption>${esc(p.t)} (clique pour agrandir)</figcaption><img src="${p.img}" alt="${esc(p.t)}" data-k="${k}"></figure>`; });
    if (!keys.length) h += `<p class="mut">L'annexe du sujet n'est pas incluse dans cette version.</p>`;
    box.innerHTML = h;
    box.querySelectorAll("img").forEach(i => i.onclick = () => showImage(i.src, i.alt));
  }

  function openInst(inst) {
    if (cur) close();
    cur = inst; side(inst);
    inst.classList.add("zoomed"); document.body.classList.add("zoom-on");
    const b = inst.querySelector(".zoom-btn"); if (b) b.textContent = "✕ fermer";
    window.dispatchEvent(new Event("resize"));
  }
  function close() {
    if (lb && lb.classList.contains("show")) { lb.classList.remove("show"); return; }
    if (!cur) return;
    cur.classList.remove("zoomed"); document.body.classList.remove("zoom-on");
    const b = cur.querySelector(".zoom-btn"); if (b) b.textContent = "🔍 zoom";
    cur = null;
    window.dispatchEvent(new Event("resize"));
  }
  function toggleInst(inst) { if (!inst) return; if (cur === inst) close(); else openInst(inst); }

  function showImage(src, title) {
    if (!lb) {
      lb = document.createElement("div"); lb.id = "lightbox";
      lb.innerHTML = `<div class="lb-bar"><b id="lb-title"></b><span class="sp"></span><button class="btn sm" id="lb-fit">100 % / ajusté</button><button class="btn sm" id="lb-x">✕ fermer</button></div><div class="lb-body"><img id="lb-img" alt=""></div>`;
      document.body.appendChild(lb);
      lb.querySelector("#lb-x").onclick = () => lb.classList.remove("show");
      lb.querySelector("#lb-fit").onclick = () => lb.classList.toggle("full");
      lb.querySelector("#lb-img").onclick = () => lb.classList.toggle("full");
      lb.addEventListener("click", e => { if (e.target === lb || e.target.classList.contains("lb-body")) lb.classList.remove("show"); });
    }
    lb.querySelector("#lb-img").src = src; lb.querySelector("#lb-title").textContent = title || "";
    lb.classList.remove("full"); lb.classList.add("show");
  }

  function init() {
    document.querySelectorAll(".inst").forEach(inst => {
      const cap = inst.querySelector(".cap"), b = document.createElement("button");
      b.className = "btn sm zoom-btn"; b.textContent = "🔍 zoom"; b.title = "Agrandir cet appareil (ou double-clic sur le fond de la face)";
      b.onclick = () => toggleInst(inst);
      cap.appendChild(b);
    });
    document.getElementById("zoom-backdrop").onclick = () => close();
  }
  return { init, toggleInst, showImage, close };
})();
