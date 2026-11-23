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
  ok(errors.length === 0, "aucune erreur JavaScript pendant le test" + (errors.length ? " : " + errors.join(" | ") : ""));
  console.log(fails ? `\n${fails} ÉCHEC(S)` : "\nTOUS LES TESTS D'INTERFACE PASSENT");
  process.exit(fails ? 1 : 0);
}, 400);
