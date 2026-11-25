// Test d'interface sans navigateur (jsdom) : charge out/labdec_app.html, joue un câblage complet avec les câbles posés à la main,
// vérifie que l'écran calculé est celui du corrigé, puis teste zoom, extraits du sujet, boîte E12, refus de câbles incohérents.
// jsdom n'est pas une dépendance du projet : JSDOM=/chemin/vers/node_modules/jsdom node tests/ui_smoke_test.js
const fs = require("fs"), path = require("path");
let JSDOM; try { ({ JSDOM } = require(process.env.JSDOM || "jsdom")); } catch (e) { console.log("jsdom absent : test d'interface ignoré (installer jsdom pour le lancer)"); process.exit(0); }
const html = fs.readFileSync(path.join(__dirname, "..", "out", "labdec_app.html"), "utf8");
const errors = [];
const dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, url: "http://localhost/",
  beforeParse(w) {
    const ctx = new Proxy({}, { get: (t, k) => k === "canvas" ? {} : k === "measureText" ? () => ({ width: 10 }) : () => ctx, set: () => true });
    w.HTMLCanvasElement.prototype.getContext = () => ctx;
    w.addEventListener("error", e => errors.push(e.message));
    w.ResizeObserver = class { observe() {} };
    w.IntersectionObserver = class { observe() {} };
    w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = () => {};
  } });
const w = dom.window, ev = s => w.eval(s);
let fails = 0;
const ok = (c, msg) => { console.log((c ? "ok   " : "ÉCHEC ") + msg); if (!c) fails++; };

setTimeout(() => {
  ok(errors.length === 0, "aucune erreur JavaScript au chargement" + (errors.length ? " : " + errors[0] : ""));
  ev(`Lesson.load("tp2-B1-inverseur")`);
  ok(ev(`state.placedCables.length`) === 0 && ev(`state.placedWires.length`) === 0, "montage chargé de zéro (aucun câble, aucun fil)");

  // 1. mauvais câbles refusés
  ev(`Cables.clickPort("gbf.out1"); Cables.pickHole("VB.main")`);
  ok(ev(`state.placedCables.length`) === 0, "BNC du GBF → douille banane VB : refusé");
  ev(`Cables.clickPort("psu.ch2_plus"); Cables.clickPort("psu.gnd")`);
  ok(ev(`state.placedCables.length`) === 0, "prise inutilisée (⏚ châssis) : refusée");
  ev(`Cables.cancel()`);   // la première extrémité reste armée après un mauvais 2e clic : Échap / annuler
  ev(`Cables.pickHole("BNC1.core"); Cables.pickHole("BNC2.core")`);
  ok(ev(`state.placedCables.length`) === 0, "deux douilles de plaque entre elles : refusé");

  // 2. les câbles du TP2 posés à la main (clic sur les prises puis sur les douilles)
  const cab = (a, b) => ev(`(${JSON.stringify([a, b])}).forEach(e => /^(scope|gbf|psu)\\./.test(e) ? Cables.clickPort(e) : e.indexOf(".") > 0 ? Cables.pickHole(e) : Cables.clickConn(e))`);
  cab("gbf.out1", "BNC1"); cab("gbf.out1", "scope.ch1"); cab("scope.ch2", "BNC2.shield");
  cab("psu.ch2_plus", "VC"); cab("psu.ch3_moins", "VB"); cab("psu.ch2_moins", "MASSE"); cab("psu.ch2_moins", "psu.ch3_plus");
  ok(ev(`state.placedCables.length`) === 7, "7 câbles posés (A à G) : " + ev(`state.placedCables.map(c => c.id).join("")`));
  cab("gbf.out1", "scope.ch2");
  ok(ev(`state.placedCables.length`) === 7, "3e câble sur la sortie du GBF refusé (le T n'a que 2 sorties)");

  const cols = ev(`state.placedCables.map(c => c.couleur).join(",")`);
  ok(ev(`state.placedCables.every(c => c.couleur)`), "chaque câble a une couleur : " + cols);
  ok(ev(`state.placedCables.find(c => c.vers === "VC").couleur`) === "rouge" && ev(`state.placedCables.find(c => c.vers === "VB").couleur`) === "noir", "bananes : + rouge, − noir");
  ok(w.document.querySelectorAll(".conn-hit").length === 7 && !!w.document.getElementById("anchor-BNC1"), "7 douilles réelles cliquables (BNC1, BNC2, VB, VC, MASSE + banane rouge et noire de gauche)");
  ev(`Cables.cancel(); Cables.clickPort("scope.ch1"); Cables.clickConn("BNC2")`);
  ok(ev(`state.placedCables.length`) === 7, "voie 1 déjà câblée : pas de 2e câble sur la même BNC");
  ev(`Cables.cancel()`);

  cab("psu.ch1_plus", "BANANE_ROUGE"); cab("psu.ch1_moins", "BANANE_NOIRE");
  ok(ev(`state.placedCables.filter(c => /BANANE_/.test(c.vers)).length`) === 2, "les 2 bananes rouge et noire de gauche reçoivent chacune un câble");
  ev(`Cables.removeAt("BANANE_ROUGE"); Cables.removeAt("BANANE_NOIRE")`);

  // 3. câblage de la plaque = corrigé, SANS les câbles du corrigé : tout dépend des câbles posés
  ev(`(() => { const m = curMontage(); const w = wiringOfSolution(m); state.placedWires = (m.fils||[]).map(x => ({n:x.n,de:x.de,vers:x.vers,couleur:x.couleur||"rouge"}));
     state.placedComps = Object.entries(m.composants).filter(([,c]) => c.type==="resistor").map(([name,c]) => ({name,type:"resistor",a:c.a,b:c.b,ohm:c.ohm,etiquette:ohmLabel(c.ohm)}));
     state.placedChips = JSON.parse(JSON.stringify(m.puces)); state.gbf.on = true; state.psu.ch[2].on = true; state.psu.ch[3].on = true; state.psu.ch[2].v = 15; state.psu.ch[3].v = 15;
     renderPlacedElements(); })()`);
  const g = ev(`getAnalysis().gain`), ph = ev(`getAnalysis().phaseDeg`), pw = ev(`getAnalysis().powered`);
  ok(Math.abs(g - 20) < 0.5 && pw, `inverseur câblé à la main : |Vs/Ve| = ${g && g.toFixed(2)} (attendu 20), AOP alimenté = ${pw}`);
  ok(ev(`circuitMatch().status`) === "ok", "écran conforme au corrigé");
  ok(ev(`state.progress["tp2-B1-inverseur"]`) === "ok", "montage marqué validé");

  // 4. un câble de moins : l'écran réagit
  ev(`Cables.removeIndex(state.placedCables.findIndex(c => c.de === "scope.ch2"))`);   // voie 2 ↔ BNC2
  ok(ev(`circuitMatch().status`) === "bad", "sans le câble de la voie 2 : écran différent de l'attendu");
  cab("scope.ch2", "BNC2.core");
  ok(ev(`circuitMatch().status`) === "ok", "câble de la voie 2 reposé : écran conforme");
  ev(`Cables.removeIndex(state.placedCables.findIndex(c => c.vers === "MASSE"))`);   // câble vers la douille MASSE
  ok(/FLOTTANTE/.test(ev(`getAnalysis().warnings.join(" ")`)) || !ev(`getAnalysis().powered`) || ev(`circuitMatch().status`) !== "ok", "alim sans masse : détecté");

  // 5. corrigé : étapes câbles
  ev(`Lesson.putSolution(curMontage()); renderPlacedElements()`);
  ok(ev(`state.placedCables.length`) === 7 && ev(`circuitMatch().status`) === "ok", "« tout poser » inclut les câbles");
  ok(/Câble A/.test(w.document.getElementById("p-corr").textContent), "étapes « câble » dans le corrigé");

  // 6. boîte E12 et pose de résistances
  const opts = w.document.getElementById("resistor-val-input").options.length;
  ok(opts >= 61, `liste de résistances de la barre d'outils : ${opts} valeurs (10 Ω → 1 MΩ)`);
  ok(w.document.querySelectorAll("#p-compo .chip[data-r='']").length >= 61, "boîte E12 du panneau Composants");
  ev(`Lesson.clearWiring(); renderPlacedElements(); state.tool="resistor"; state.armedRef=null; state.resistorVal=4700;`);
  const click = id => w.document.querySelector(`.h-target[data-id="${id}"]`).dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  click("T1a10"); click("T1a12"); ev(`state.resistorVal=330`); click("T1a20"); click("T1a22");
  ok(ev(`state.placedComps.map(c => c.name + "=" + c.ohm).join(",")`) === "R1=4700,R2=330", "deux résistances libres (R1, R2) : " + ev(`state.placedComps.map(c => c.name + "=" + c.ohm).join(",")`));

  // 6b. petits câbles qui pendent de la plaque + retour d'erreur
  ev(`Lesson.clearWiring(); renderPlacedElements(); state.tool="wire";`);
  ok(w.document.querySelectorAll(".lead-hit").length === 9, "9 petits câbles pendent sous les 9 trous des connecteurs (dont les 2 bananes de gauche)");
  const leadClick = hid => w.document.querySelector(`.lead-hit[data-lead="${hid}"]`).dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  leadClick("BNC1.core"); click("T1g53");
  ok(ev(`state.placedWires.map(x => x.de + ">" + x.vers + ":" + x.couleur).join()`) === "BNC1.core>T1g53:rouge", "bout du cordon → trou : fil posé, couleur du cordon : " + ev(`state.placedWires.map(x => x.de + ">" + x.vers + ":" + x.couleur).join()`));
  ok(w.document.querySelectorAll(".lead-hit").length === 8, "le cordon branché ne pend plus");
  leadClick("BNC1.shield"); leadClick("VB.main");
  ok(ev(`state.placedWires.length`) === 2, "un cordon peut aussi être enfiché sur un autre (2 fils)");
  ev(`Feedback.openForm()`);
  ok(w.document.getElementById("fb").classList.contains("show"), "formulaire « Signaler une erreur » ouvert");
  const u = ev(`Feedback.issueUrl({montage:"tp2-B1-inverseur", type:"Erreur dans un montage (fil, résistance, trou, câble)", description:"R2 faux", etat:Feedback.stateSummary(), version:"test"})`);
  ok(/issues\/new\?template=retour-montage\.yml/.test(u) && /montage=tp2-B1-inverseur/.test(u) && u.length < 7000, "lien d'Issue pré-rempli (" + u.length + " caractères)");
  ev(`Feedback.openHelp()`); ok(w.document.getElementById("help").classList.contains("show"), "aide ouverte");
  ev(`document.querySelectorAll(".modal.show").forEach(m => m.classList.remove("show"))`);

  // 7. sujet + zoom
  ev(`Lesson.load("tp2-B2-non-inverseur")`);
  const imgs = w.document.querySelectorAll("#p-sujet figure.sj img").length;
  ok(imgs >= 3, `onglet Sujet : ${imgs} extraits du vrai sujet`);
  ok(w.document.querySelectorAll("#p-quest figure.sj img").length >= 1, "onglet Questions : extrait des questions du sujet");
  ev(`Zoom.toggleInst(document.querySelector('.inst[data-inst="gbf"]'))`);
  ok(w.document.querySelector('.inst[data-inst="gbf"]').classList.contains("zoomed") && w.document.querySelectorAll(".zoom-side img").length >= 1, "zoom GBF : face agrandie + annexe du sujet");
  ev(`Zoom.close()`);
  ok(!w.document.querySelector(".inst.zoomed"), "zoom fermé");
  ev(`Zoom.showImage("data:image/gif;base64,R0lGODlhAQABAAAAACw=", "t")`);
  ok(w.document.getElementById("lightbox").classList.contains("show"), "agrandissement d'une capture du sujet");
  // 8. appareils éteints au chargement, annuler chronologique, une puce à la fois, LED, nœuds où qu'on câble
  ev(`Lesson.load("tp2-C-association")`);
  ok(!ev(`state.gbf.on`) && !ev(`[1,2,3].some(k => state.psu.ch[k].on)`), "montage chargé : GBF et alim réglés mais ÉTEINTS");
  ev(`Lesson.putSolution(curMontage()); renderPlacedElements()`);
  ok(ev(`state.placedChips.length`) === 2, "association : 2 puces posées");
  ev(`delChip(0)`); ok(ev(`state.placedChips.length`) === 1, "× sur une puce : supprime cette puce seulement");
  ev(`History.undo(); renderPlacedElements()`); ok(ev(`state.placedChips.length`) === 2, "annuler : la puce revient");
  ev(`Lesson.load("tp1-D1-led")`);
  ev(`state.placedWires.push({n:1,de:"T1a10",vers:"T1a20",couleur:"rouge"}); renderPlacedElements()`);
  cab("gbf.out1", "BNC1.core");
  ev(`History.undo(); renderPlacedElements()`);
  ok(ev(`state.placedCables.length`) === 0 && ev(`state.placedWires.length`) === 1, "annuler retire la DERNIÈRE action (le câble), pas le dernier fil");
  ev(`Lesson.load("tp1-D1-led"); Lesson.putSolution(curMontage()); state.gbf.on = true; renderPlacedElements()`);
  ok(ev(`state.placedComps.some(c => c.type === "led")`) && ev(`getAnalysis().rec.leds.LED.avg`) > 1e-3, "TP1 D : la LED est posée par le corrigé et s'allume");
  ok(ev(`circuitMatch().status`) === "ok", "TP1 D : écran conforme");
  ev(`Lesson.load("tp2-B1-inverseur"); Lesson.putSolution(curMontage());
      { const sh = h => h.replace(/^(T1[a-j])(\\d+)$/, (m, a, r) => a + (+r - 10));
        state.placedChips.forEach(c => c.rangee_broche1 -= 10);
        state.placedComps.forEach(c => { c.a = sh(c.a); c.b = sh(c.b); });
        state.placedWires.forEach(w => { w.de = sh(w.de); w.vers = sh(w.vers); }); renderPlacedElements(); }`);
  ok(ev(`nodeChecklist().allOk`) && ev(`circuitMatch().status`) === "ok", "montage décalé de 10 rangées : nœuds et écran validés (aucun trou imposé)");
  ev(`{ const r = state.placedComps.find(c => c.name === "R1"); [r.a, r.b] = [r.b, r.a]; renderPlacedElements(); }`);
  ok(ev(`nodeChecklist().allOk`), "R1 posée dans l'autre sens : toujours valide");
  ev(`state.placedWires.push({n:99,de:"T1a10",vers:"T1h39",couleur:"rouge"}); renderPlacedElements()`);
  ok(/une seule patte par trou/.test(w.document.getElementById("alerts-box").textContent), "deux pattes dans le même trou : signalé");
  // 9. questions TP3, multimètre, TP4 blanc, panne, documentation
  ev(`Lesson.load("tp3-C-compteur"); Lesson.showTab("quest")`);
  ok(ev(`document.querySelectorAll("#p-quest [data-q]").length`) === 2, "TP3 compteur : questions « à prédire » présentes");
  ev(`document.querySelector("#p-quest [data-q='1']").click()`);
  ok(/250\.0 Hz/.test(ev(`document.getElementById("rev1").textContent`)), "réponse calculée : Q1 = 250 Hz");
  ev(`Lesson.load("tp1-B1-pont-diviseur"); Lesson.putSolution(curMontage()); state.gbf.on = true; state.gbf.vpp = 2; state.gbf.load = "highz";
      state.dmm.v = curMontage().fils.find(w => w.de === "BNC2.core").vers; state.dmm.com = "TOP-L1-20"; state.dmm.mode = "ac"; renderPlacedElements()`);
  ok(/70\.\d+ mV/.test(ev(`document.querySelector(".dmm-lcd").textContent`)), "multimètre V~ TRMS sur le pont : ≈ 70 mV");
  ev(`Train.startTp4()`); ok(/masqué/.test(ev(`document.getElementById("p-corr").textContent`)), "TP4 blanc : corrigé masqué");
  ev(`Lesson.putSolution(curMontage()); state.gbf.on = true; if (state.preset.gbf) state.gbf.load = state.preset.gbf.load; [1,2,3].forEach(k => { if (state.preset.psu && state.preset.psu[k] != null) state.psu.ch[k].on = true; }); renderPlacedElements(); document.getElementById("tr-end").click()`);
  ok(/20\.0 \/ 20/.test(ev(`document.getElementById("train-modal").textContent`)), "TP4 blanc avec le bon montage : 20 / 20");
  ev(`Train.startPanne()`); ok(ev(`circuitMatch().status`) !== "ok" || !ev(`nodeChecklist().allOk`), "panne : le montage tiré est bien faux");
  ev(`Lesson.putSolution(curMontage()); renderPlacedElements()`);
  ok(/Panne trouvée/.test(ev(`document.getElementById("train-modal").textContent`)), "panne réparée : détectée");
  ev(`Docs.open()`); ok(ev(`document.querySelectorAll("#docs-modal a").length`) >= 6, "documentation des appareils : liens vers les manuels");
  // 9. pose d'une puce à la main : toujours sur de vrais trous, jamais par-dessus une autre puce
  const clickH = id => w.document.querySelector(`.h-target[data-id="${id}"]`).dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const allPinsOnBoard = () => ev(`state.placedChips.every(ch => { for (let p = 1; p <= CHIPS_LIB[ch.modele].dip; p++) { const h = HOLE_MAP.get(Engine.pinHole(ch, p, CHIPS_LIB)); if (!h || h.t !== "strip") return false; } return true; })`);
  ev(`Lesson.load("tp1-B1-pont-diviseur"); state.placedChips = []; renderPlacedElements(); state.tool = "chip"; state.chipVal = "74LS00"; state.armedRef = null`);
  clickH("T1j3");   // trop bas : la puce sortirait de la plaque
  ok(ev(`state.placedChips.length`) === 1 && allPinsOnBoard(), "puce posée trop bas : calée dans la plaque, toutes les broches sur de vrais trous");
  ok(ev(`state.placedChips[0].rangee_broche1`) === 7, "74LS00 cliquée rangée 3 : broche 1 ramenée en rangée 7 (7 rangées de haut)");
  ok(ev(`Engine.pinHole(state.placedChips[0], 7, CHIPS_LIB)`) === "T1j1" && ev(`Engine.pinHole(state.placedChips[0], 8, CHIPS_LIB)`) === "T1a1", "GND (broche 7) en T1j1 et broche 8 en T1a1 : de part et d'autre de la fente");
  ev(`state.chipVal = "TL081"`); clickH("T1j5");   // recouvre U1 (rangées 1 à 7)
  ok(ev(`state.placedChips.length`) === 1, "puce par-dessus une autre : refusée");
  ok(/chevaucherait U1/.test(ev(`document.getElementById("active-pointer-info").textContent`)), "refus expliqué à l'écran");
  clickH("T1j20");
  ok(ev(`state.placedChips.length`) === 2 && allPinsOnBoard(), "TL081 posée plus haut : acceptée, broches sur de vrais trous");
  ev(`state.chipVal = "74LS00"`); clickH("T1j63");
  ok(ev(`state.placedChips.every(c => c.rangee_broche1 <= 63)`) && allPinsOnBoard(), "puce cliquée tout en haut de la plaque : reste dans la plaque");
  // 10. câbles d'appareils : un clic ne crée rien, deux clics en créent un ; double-clic = décrocher pour déplacer
  const rects = { "gbf.out1": [650, 200], "BNC1": [470, 450], "BNC2": [530, 450], "scope.ch1": [400, 200], "psu.ch2_plus": [800, 210], "VC": [590, 450] };
  w.Element.prototype.getBoundingClientRect = function () {
    if (this.id === "lv-centre") return { left: 0, top: 0, width: 1000, height: 800, right: 1000, bottom: 800 };
    const p = rects[(this.dataset && this.dataset.port) || (this.id || "").replace(/^anchor-/, "")];
    return p ? { left: p[0] - 4, top: p[1] - 4, width: 8, height: 8, right: p[0] + 4, bottom: p[1] + 4 } : { left: 0, top: 0, width: 0, height: 0, right: 0, bottom: 0 };
  };
  const dbl = (x, y, el) => (el || w.document.getElementById("lv-centre")).dispatchEvent(new w.MouseEvent("dblclick", { bubbles: true, clientX: x, clientY: y }));
  const cabs = () => ev(`state.placedCables.map(c => c.id + ":" + c.de + ">" + c.vers + ":" + c.couleur).join(" ")`);
  ev(`Lesson.load("tp2-B1-inverseur"); state.tool = "wire"; Cables.cancel()`);
  ev(`Cables.clickPort("gbf.out1")`);
  ok(ev(`state.placedCables.length`) === 0 && ev(`state.cableFirst`) === "gbf.out1" && ev(`state.tool`) === "cable", "câble : un seul clic sur une prise n'en crée aucun (il arme seulement)");
  ev(`Cables.pickHole("BNC1.core")`);
  ok(ev(`state.placedCables.length`) === 1 && ev(`state.cableFirst`) === null, "câble : le 2e clic crée UN câble");
  const before = cabs();
  dbl(300, 600);   // double-clic dans le vide
  ok(cabs() === before && ev(`state.cableFirst`) === null, "double-clic dans le vide : rien ne bouge");
  dbl(471, 440);   // près du bout BNC 1
  ok(ev(`state.placedCables.length`) === 0 && ev(`state.cableFirst`) === "gbf.out1", "double-clic sur le câble : bout BNC 1 décroché, bout GBF reste armé");
  ok(/décroché/.test(ev(`document.getElementById("cable-msg").textContent`)), "message : « décroché … clique la nouvelle prise »");
  ev(`Cables.pickHole("BNC2.core")`);
  ok(cabs() === "A:gbf.out1>BNC2:jaune", "déplacé vers BNC 2 : même lettre A, même couleur, un seul câble (" + cabs() + ")");
  dbl(650, 215);   // près du bout GBF
  ok(ev(`state.cableFirst`) === "BNC2" && ev(`state.placedCables.length`) === 0, "double-clic près du GBF : c'est le bout GBF qui se décroche");
  ev(`Cables.pickHole("BNC2.core")`);   // reclic sur le bout resté armé
  ok(cabs() === "A:gbf.out1>BNC2:jaune", "reclic sur le bout armé : le câble revient identique");
  dbl(531, 440);
  w.document.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  ok(cabs() === "A:gbf.out1>BNC2:jaune" && ev(`state.cableFirst`) === null, "Échap pendant un déplacement : le câble est remis");
  dbl(531, 440); ev(`Cables.clickPort("psu.ch2_plus")`);   // BNC ↔ banane : refusé
  ok(cabs() === "A:gbf.out1>BNC2:jaune" && ev(`state.cableFirst`) === null, "déplacement vers une prise incompatible : refusé, le câble d'origine est remis");
  ev(`Cables.clickPort("scope.ch1"); Cables.pickHole("BNC1.core")`);   // 2e câble B
  ok(ev(`state.placedCables.length`) === 2, "2e câble posé (B)");
  dbl(531, 440); ev(`Cables.pickHole("BNC1.core")`);   // BNC 1 est déjà pris par B (1 seul câble par BNC)
  ok(ev(`state.placedCables.length`) === 2 && /un câble/.test(ev(`document.getElementById("cable-msg").textContent`)), "déplacement vers une BNC déjà prise : refusé, 2 câbles conservés");
  ev(`state.tool = "delete"`); const n2 = cabs(); dbl(531, 440);
  ok(cabs() === n2 && ev(`state.cableFirst`) === null, "gomme active : le double-clic ne décroche pas");
  ev(`state.tool = "cable"`); dbl(531, 440); ok(ev(`state.cableFirst`) !== null, "(un câble est décroché)");
  ev(`Lesson.load("tp2-A-suiveur")`);
  ok(ev(`state.placedCables.length`) === 0 && ev(`state.cableFirst`) === null, "changer de montage pendant un déplacement : aucun ancien câble ne réapparaît");
  ok(errors.length === 0, "aucune erreur JavaScript pendant le test" + (errors.length ? " : " + errors.join(" | ") : ""));
  console.log(fails ? `\n${fails} ÉCHEC(S)` : "\nTOUS LES TESTS D'INTERFACE PASSENT");
  process.exit(fails ? 1 : 0);
}, 400);
