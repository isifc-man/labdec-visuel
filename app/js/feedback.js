// Aide + « Signaler une erreur » : ouvre une Issue GitHub pré-remplie (montage, type, état du câblage, version de l'app).
// Pas de serveur : les retours arrivent dans l'onglet Issues du dépôt ; `python tools/feedback.py` les rassemble.
const Feedback = (() => {
  const REPO = (typeof window !== "undefined" && window.LABDEC_REPO) || "isifc-man/labdec-visuel";
  const BUILD = "__BUILD__";
  const TYPES = ["Erreur dans un montage (fil, résistance, trou, câble)", "Écran d'appareil incorrect", "Énoncé ou question", "Bug de l'application", "Idée / amélioration"];
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function stateSummary() {
    const g = state.gbf, sc = state.scope;
    const W = state.placedWires.map(w => `${w.de}>${w.vers}(${w.couleur})`).join(" ; ") || "aucun";
    const R = state.placedComps.map(c => `${c.name}=${c.etiquette || c.ohm} ${c.a}-${c.b}`).join(" ; ") || "aucune";
    const C = state.placedChips.map(c => `${c.ref} ${c.modele} ${c.bloc} rangée ${c.rangee_broche1}`).join(" ; ") || "aucune";
    const K = state.placedCables.map(c => `${c.id}:${c.de}>${c.vers}`).join(" ; ") || "aucun";
    const P = [1, 2, 3].map(k => `V${k}=${state.psu.ch[k].on ? state.psu.ch[k].v + " V" : "off"}`).join(" ");
    let cm = ""; try { const m = circuitMatch(); cm = m ? m.text : ""; } catch (e) { /* sans importance */ }
    return `Fils : ${W}\nRésistances : ${R}\nPuces : ${C}\nCâbles d'appareils : ${K}\nGBF : ${g.on ? "ON" : "OFF"} ${g.wave} ${g.f} Hz ${g.vpp} Vpp charge ${g.load}\nAlim : ${P}\nOscillo : ${sc.tdiv} s/div ; V1 ${sc.ch[1].vdiv} V/div ; V2 ${sc.ch[2].vdiv} V/div\nÉcran : ${cm}`;
  }
  function report() {
    const m = curMontage();
    return { montage: m ? m.id : "mode libre", type: $("#fb-type").value, description: $("#fb-text").value.trim(), etat: $("#fb-state").checked ? stateSummary() : "(non joint)", version: BUILD };
  }
  const asText = r => `Montage : ${r.montage}\nType : ${r.type}\nVersion : ${r.version}\n\n${r.description}\n\n--- État ---\n${r.etat}\n\nLien : https://github.com/${REPO}`;
  function issueUrl(r) {
    const q = o => Object.entries(o).map(([k, v]) => k + "=" + encodeURIComponent(v)).join("&");
    return `https://github.com/${REPO}/issues/new?` + q({ template: "retour-montage.yml", title: `[retour] ${r.montage} : ${r.type}`.slice(0, 120), montage: r.montage, type: r.type, description: r.description, etat: r.etat.slice(0, 1800), version: r.version });
  }

  function ensure(id, html) {
    let el = document.getElementById(id);
    if (!el) { el = document.createElement("div"); el.id = id; el.className = "modal"; el.innerHTML = `<div class="modal-card">${html}</div>`; document.body.appendChild(el); el.addEventListener("click", e => { if (e.target === el || e.target.dataset.close != null) el.classList.remove("show"); }); }
    return el;
  }
  function openForm() {
    const el = ensure("fb", `<div class="modal-bar"><b>Signaler une erreur</b><button class="btn sm" data-close>✕ fermer</button></div>
      <p class="mut">Ton retour arrive dans les « Issues » du dépôt GitHub (compte GitHub gratuit nécessaire). Sans compte : « Copier le rapport » et envoie-le à la personne qui t'a donné le lien.</p>
      <label>Type <select id="fb-type">${TYPES.map(t => `<option>${esc(t)}</option>`).join("")}</select></label>
      <label>Montage <input id="fb-montage" readonly></label>
      <label>Ce qui ne va pas, et ce que tu attendais (fiche technique, sujet, banc réel…)<textarea id="fb-text" rows="6" placeholder="Ex. : R2 devrait valoir 20 kΩ d'après le sujet, l'app indique 9,1 kΩ"></textarea></label>
      <label class="chk"><input type="checkbox" id="fb-state" checked> joindre l'état de mon câblage et de mes réglages</label>
      <div class="row"><button class="btn" id="fb-gh">Ouvrir sur GitHub</button><button class="btn" id="fb-copy">Copier le rapport</button><span id="fb-msg" class="mut"></span></div>`);
    const m = curMontage(); el.querySelector("#fb-montage").value = m ? m.id : "mode libre";
    el.querySelector("#fb-gh").onclick = () => { const r = report(); if (r.description.length < 5) { el.querySelector("#fb-msg").textContent = "Décris l'erreur d'abord."; return; } window.open(issueUrl(r), "_blank", "noopener"); el.querySelector("#fb-msg").textContent = "Formulaire GitHub ouvert dans un nouvel onglet : clique « Submit new issue »."; };
    el.querySelector("#fb-copy").onclick = () => { const t = asText(report()); (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(() => { el.querySelector("#fb-msg").textContent = "Rapport copié."; }, () => { const ta = el.querySelector("#fb-text"); ta.value = t; ta.select(); el.querySelector("#fb-msg").textContent = "Copie manuelle : le rapport est dans la zone de texte."; }); };
    el.classList.add("show");
  }
  function openHelp() {
    ensure("help", `<div class="modal-bar"><b>S'entraîner en 6 gestes</b><button class="btn sm" data-close>✕ fermer</button></div>
      <ol class="how">
        <li><b>Choisis un montage</b> dans le menu de gauche (TP → montage). Tout part de zéro, comme sur la table.</li>
        <li><b>Lis le sujet</b> et les questions (onglets à droite), puis règle les appareils (🔍 zoom pour les agrandir).</li>
        <li><b>Câbles d'appareils</b> : clique une prise du GBF, de l'oscillo ou de l'alim, puis la grosse douille de la plaque (BNC 1, BNC 2, VB, VC, MASSE).</li>
        <li><b>Petits câbles de la plaque</b> : ceux qui pendent sous âme / blindage / VB / VC / MASSE. Clique le bout qui pend, puis le trou de la plaque où l'enficher.</li>
        <li><b>Composants</b> : résistances E12 (10 Ω → 1 MΩ) et puces dans le menu de gauche (sous les montages), fils avec l'outil « Fil ».</li>
        <li><b>Vérifie</b> : l'écran de l'oscillo se calcule à partir de ton câblage ; « Écran conforme » = validé. Bloqué ? Corrigé pas à pas (rôle → indice → poser).</li>
      </ol>
      <p class="mut">Une erreur dans un montage ou dans un écran ? Bouton <b>Signaler une erreur</b> en haut à droite : ton retour arrive directement chez l'auteur.</p>
      <div class="row"><button class="btn" data-close>C'est parti</button></div>`).classList.add("show");
    try { localStorage.setItem("labdec.help", "1"); } catch (e) { /* ignoré */ }
  }
  function init() {
    $("#btn-help").onclick = openHelp; $("#btn-feedback").onclick = openForm;
    window.addEventListener("keydown", e => { if (e.key === "Escape") document.querySelectorAll(".modal.show").forEach(m => m.classList.remove("show")); });
    let seen = false; try { seen = localStorage.getItem("labdec.help") === "1"; } catch (e) { /* ignoré */ }
    if (!seen) openHelp();
  }
  return { init, openForm, openHelp, issueUrl, stateSummary, asText };
})();
