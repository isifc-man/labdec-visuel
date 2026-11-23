// Checklist de nœuds, alertes, tableau des liaisons (extrait de l'ancienne app)
function updateElectricalChecklist() {
  const m = MONTAGES[state.currentMontage];
  const checklistBox = document.getElementById("checklist-box");
  const scoreTag = document.getElementById("score-tag");
  const alertsBox = document.getElementById("alerts-box");

  if (!m || !m.noeuds) {
    checklistBox.innerHTML = "<div style='font-size:11px;color:var(--text-muted);'>Mode libre actif.</div>";
    scoreTag.textContent = "Libre";
    return;
  }

  const { uf, isPowered, isGndConnected } = evaluateCircuit();
  let done = 0, total = 0, html = "";
  const alerts = [];

  for (let [name, expected] of Object.entries(m.noeuds)) {
    total++;
    let ok = true;
    for (let i = 1; i < expected.length; i++) {
      if (!uf.c(expected[0], expected[i])) { ok = false; break; }
    }
    if (ok) {
      done++;
      html += `<div class="checklist-item done"><span>✓</span><div><b>Nœud ${name}</b> <span style="font-size:10px;opacity:0.8">${expected.slice(0, 2).join(", ")}...</span></div></div>`;
    } else {
      html += `<div class="checklist-item missing"><span>○</span><div><b>Nœud ${name}</b> <span style="font-size:10px;color:var(--text-muted)">Relier : ${expected.join(" — ")}</span></div></div>`;
    }
  }

  checklistBox.innerHTML = html;
  scoreTag.textContent = `${done} / ${total}`;
  scoreTag.style.background = done === total ? "var(--ok)" : "#0284c7";

  // Alertes en direct
  if (!isGndConnected) {
    alerts.push("<div class='alert-row alert-warn'>⚠️ Alimentation flottante : Borne MASSE (0V) non reliée à la plaque (TOP-L1) !</div>");
  }
  if (![1, 2, 3].some(k => state.psu.ch[k].on)) {
    alerts.push("<div class='alert-row alert-warn'>⚠️ Alimentation Keysight éteinte (bouton ALL OFF). L'AOP n'est pas alimenté.</div>");
  }
  if (!uf.c("BNC1.shield", "TOP_L_1")) {
    alerts.push("<div class='alert-row alert-warn'>⚠️ Blindage BNC 1 non relié à la masse (pas de retour référence signal).</div>");
  }
  if (state.placedChips.some(c => c.modele === "TL081") && !uf.c("U1.4", "VB.main") && !uf.c("U1.4", "N1_1_u")) {
    alerts.push("<div class='alert-row alert-err'>❌ Broche 4 TL081 (V−) non alimentée ! Sortie Vs = 0 V.</div>");
  }
  if (done === total && total > 0 && alerts.length === 0) {
    alerts.push("<div class='alert-row alert-ok'>🎉 PARFAIT ! Montage validé et signal stabilisé à l'oscilloscope !</div>");
  } else if (alerts.length === 0) {
    alerts.push("<div class='alert-row alert-ok'>✓ Aucun court-circuit. Câblage conforme en cours...</div>");
  }

  alertsBox.innerHTML = alerts.join("");
}

function updatePlacedTable() {
  let rows = "", idx = 1;
  state.placedChips.forEach(ch => {
    rows += `<tr><td>${idx++}</td><td>Puce</td><td>${ch.modele}</td><td>R.${ch.rangee_broche1}</td><td><button class="wire-del" onclick="delChip()">×</button></td></tr>`;
  });
  state.placedComps.forEach((c, i) => {
    rows += `<tr><td>${idx++}</td><td>${c.name} ${c.etiquette || ""}</td><td>${c.a}</td><td>${c.b}</td><td><button class="wire-del" onclick="delComp(${i})">×</button></td></tr>`;
  });
  state.placedCables.forEach((c, i) => {
    rows += `<tr><td>${idx++}</td><td>Câble ${c.id}</td><td>${Cables.label(c.de)}</td><td>${Cables.label(c.vers)}</td><td><button class="wire-del" onclick="Cables.removeIndex(${i})">×</button></td></tr>`;
  });
  state.placedWires.forEach((w, i) => {
    rows += `<tr><td>${idx++}</td><td>Fil</td><td>${w.de}</td><td>${w.vers}</td><td><button class="wire-del" onclick="delWire(${i})">×</button></td></tr>`;
  });
  document.getElementById("placed-tbody").innerHTML = rows;
  document.getElementById("placed-num").textContent = (idx - 1);
}

window.delWire = i => { state.placedWires.splice(i, 1); renderPlacedElements(); };
window.delComp = i => { state.placedComps.splice(i, 1); renderPlacedElements(); };
window.delChip = () => { state.placedChips = []; renderPlacedElements(); };

// 4. MOTEUR PHYSIQUE DE L'OSCILLOSCOPE & RENDU CANVAS
