// Interactions souris sur la plaque (extrait de l'ancienne app)
function setupBoardInteractions() {
  const targets = document.getElementById("svg-targets");
  const rubberband = document.getElementById("svg-rubberband");
  const selMarker = document.getElementById("svg-sel");
  const inspAddr = document.getElementById("insp-addr");
  const inspDesc = document.getElementById("insp-desc");
  const inspBadge = document.getElementById("insp-badge");
  const pointerInfo = document.getElementById("active-pointer-info");

  targets.addEventListener("pointerover", e => {
    const hid = e.target.dataset.id;
    if (!hid) return;
    const h = HOLE_MAP.get(hid);
    if (!h) return;
    inspAddr.textContent = h.id;
    inspDesc.textContent = h.desc;
    inspBadge.textContent = `${h.x}, ${h.y}`;
    pointerInfo.textContent = `Trou : ${h.id} — ${h.desc}`;
  });

  targets.addEventListener("click", e => {
    if (e.target.dataset.conn) { Cables.clickConn(e.target.dataset.conn); return; }
    const hid = e.target.dataset.id;
    if (!hid) return;
    handleHoleClick(hid);
  });

  const masterSvg = document.getElementById("master-board-svg");
  masterSvg.addEventListener("pointermove", e => {
    if (!state.firstHole) return;
    const pt = masterSvg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const p = pt.matrixTransform(masterSvg.getScreenCTM().inverse());
    rubberband.setAttribute("x2", p.x);
    rubberband.setAttribute("y2", p.y);
  });

  function handleHoleClick(hid) {
    if (state.tool === "cable") { Cables.pickHole(hid); return; }
    if (state.tool === "delete") {
      const ce = HOLE_MAP.get(hid);
      if (ce && ce.t === "conn" && Cables.removeAt(hid.split(".")[0])) return;
      const wIdx = state.placedWires.findIndex(w => w.de === hid || w.vers === hid);
      if (wIdx >= 0) { state.placedWires.splice(wIdx, 1); renderPlacedElements(); return; }
      const rIdx = state.placedComps.findIndex(r => r.a === hid || r.b === hid);
      if (rIdx >= 0) { state.placedComps.splice(rIdx, 1); renderPlacedElements(); return; }
      return;
    }

    if (state.tool === "chip") {
      const h = HOLE_MAP.get(hid);
      if (!h || h.t !== "strip") return;
      const blk = hid.slice(0, 2);
      const rowMatch = hid.match(/\d+$/);
      if (!rowMatch) return;
      const cref = (state.armedRef && /^U/.test(state.armedRef)) ? state.armedRef : "U" + (state.placedChips.length + 1);
      state.placedChips = state.placedChips.filter(c => c.ref !== cref).concat([{
        ref: cref,
        modele: state.chipVal,
        bloc: blk,
        rangee_broche1: parseInt(rowMatch[0], 10),
        encoche: "haut"
      }]);
      state.armedRef = null;
      renderPlacedElements();
      resetSel();
      return;
    }

    if (!state.firstHole) {
      state.firstHole = hid;
      const h = HOLE_MAP.get(hid);
      selMarker.setAttribute("cx", h.x);
      selMarker.setAttribute("cy", h.y);
      selMarker.style.display = "block";
      rubberband.setAttribute("x1", h.x);
      rubberband.setAttribute("y1", h.y);
      rubberband.setAttribute("x2", h.x);
      rubberband.setAttribute("y2", h.y);
      rubberband.style.display = "block";
    } else {
      const h1 = state.firstHole, h2 = hid;
      if (h1 !== h2) {
        if (state.tool === "wire") {
          state.placedWires.push({ n: state.placedWires.length + 1, de: h1, vers: h2, couleur: state.wireColor });
        } else if (state.tool === "resistor") {
          const val = state.resistorVal;
          const rname = state.armedRef && /^R/.test(state.armedRef) ? state.armedRef : nextName("R", state.placedComps, "name");
          state.placedComps = state.placedComps.filter(c => c.name !== rname);
          state.armedRef = null;
          state.placedComps.push({
            name: rname,
            type: "resistor",
            a: h1, b: h2, ohm: val,
            etiquette: ohmLabel(val)
          });
        }
        renderPlacedElements();
      }
      resetSel();
    }
  }

  function resetSel() {
    state.firstHole = null;
    selMarker.style.display = "none";
    rubberband.style.display = "none";
  }
}

// 7. GESTION DES ONGLETS & CONTRÔLES INSTRUMENTS
