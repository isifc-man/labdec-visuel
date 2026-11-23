// Démarrage : faces d'appareils, plaque, menu, barre d'outils de la plaque.
window.addEventListener("DOMContentLoaded", () => {
  Scope.init(document.getElementById("face-scope"));
  Gbf.init(document.getElementById("face-gbf"));
  Psu.init(document.getElementById("face-psu"));
  buildBoardGeometry();
  setupBoardInteractions();
  Cables.init();
  if (window.ResizeObserver) { const rz = new ResizeObserver(() => Cables.redraw()); ["lv-centre", "instruments", "boardzone"].forEach(i => rz.observe(document.getElementById(i))); }
  Zoom.init();
  Feedback.init();
  Dock.init();
  Lesson.init();
  setupToolbar();
  Lesson.load("tp2-B1-inverseur");
});

function setupToolbar() {
  document.querySelectorAll(".t-btn").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".t-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.tool = btn.dataset.tool; state.armedRef = null; Cables.cancel(); syncToolbar();
  }));
  // boîte de résistances E12 complète (10 Ω → 1 MΩ) dans la liste déroulante de la barre d'outils
  const sel = document.getElementById("resistor-val-input");
  sel.innerHTML = E12_ALL.map(v => `<option value="${v}">${ohmLabel(v)}</option>`).join("");
  sel.value = String(state.resistorVal);
  document.querySelectorAll(".color-dot").forEach(d => d.addEventListener("click", () => {
    document.querySelectorAll(".color-dot").forEach(x => x.classList.remove("active"));
    d.classList.add("active"); state.wireColor = d.dataset.color; state.cableColorSet = true;
  }));
  document.getElementById("resistor-val-input").addEventListener("change", e => { state.resistorVal = +e.target.value; state.armedRef = null; });
  document.getElementById("chip-val-input").addEventListener("change", e => { state.chipVal = e.target.value; state.armedRef = null; });
  document.getElementById("btn-undo").addEventListener("click", () => {
    if (state.placedWires.length) state.placedWires.pop(); else if (state.placedComps.length) state.placedComps.pop(); else if (state.placedChips.length) state.placedChips.pop(); else state.placedCables.pop();
    Cables.cancel(); renderPlacedElements();
  });
  document.getElementById("btn-zero").addEventListener("click", () => {
    Lesson.clearWiring(); if (state.currentMontage) { state.progress[state.currentMontage] = "todo"; saveProgress(); }
    renderPlacedElements(); Lesson.paintNav();
  });
  document.getElementById("btn-factory").addEventListener("click", () => {
    const f = factoryInstruments(); state.gbf = f.gbf; state.psu = f.psu; state.scope = f.scope; refreshAll();
  });
  syncToolbar();
}
