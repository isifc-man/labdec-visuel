// Documentation des appareils : liens vers les manuels officiels Keysight et résumé des menus utiles en TP.
// Les résumés renvoient aux pages des manuels (éditions consultées en novembre 2026).
const Docs = (() => {
  const L = (href, txt) => `<a href="${href}" target="_blank" rel="noopener">${txt}</a>`;
  const HTML = `<div class="modal-bar"><b>📘 Documentation des appareils</b><button class="btn sm" data-close>✕ fermer</button></div>
  <div class="docs">
  <h4>Oscilloscope Keysight DSOX1202A (InfiniiVision 1000 X)</h4>
  <p>${L("https://www.keysight.com/find/1000X-Series-manual", "Manuel utilisateur (site Keysight)")} · ${L("https://www.ece.ucdavis.edu/~lewis/112/scope_user_guide.pdf", "copie PDF du guide 1000 X")} · ${L("https://www.keysight.com/us/en/product/DSOX1202A/oscilloscope-70-mhz-2-channels.html", "fiche produit")}</p>
  <ul>
   <li><b>Voies</b> (touches 1 / 2) : couplage DC ou AC, rapport de sonde (1:1 avec les câbles BNC du TP). Molette du haut = V/div, du bas = position.</li>
   <li><b>Horizontal</b> : grande molette = s/div, petite = position (décale l'instant de déclenchement).</li>
   <li><b>Trigger</b> : niveau = molette (appui = 50 %) ; menu Trigger → type Front, <b>source</b> (voie 1/2), <b>front</b> montant/descendant, <b>mode Auto</b> (affiche même sans déclenchement, image instable) ou <b>Normal</b> (attend un déclenchement).</li>
   <li><b>Meas</b> : Crête-crête, Max, Min, Amplitude, Moyenne, Efficace, Période, Fréquence, Largeur, Rapport cyclique, Temps de montée/descente, Retard, Phase. Les mesures se font <b>sur ce qui est affiché</b> : choisis bien calibre et base de temps.</li>
   <li><b>Cursors</b> : curseurs X (temps, 1/ΔX) et Y (tension) ; on déplace le curseur actif avec la molette Entry.</li>
   <li><b>Auto Scale</b> (à éviter sauf signal perdu), <b>Run/Stop</b>, <b>Single</b> (fige la prochaine acquisition déclenchée), <b>Default Setup</b>.</li>
   <li>Dans le simulateur : Trigger puis touches de côté 1 (source), 2 (front), 3 (Auto/Normal) ; Meas puis touche 1 = page de mesures suivante ; Cursors puis touche 1 = curseur actif.</li>
  </ul>
  <h4>Générateur Keysight EDU33211A (EDU33210)</h4>
  <p>${L("https://www.keysight.com/us/en/assets/9921-01386/user-manuals/EDU33210-Series-Trueform-Arbitrary-Waveform-Generator-Users-Guide.pdf", "Manuel utilisateur EDU33210 (PDF Keysight)")} · ${L("https://www.keysight.com/us/en/product/EDU33211A/waveform-generator-20mhz-1-channel.html", "fiche produit")}</p>
  <ul>
   <li><b>[Waveform]</b> : Sine, Square, Ramp (symétrie 50 % = triangle), Pulse… <b>[Parameter]</b> : fréquence, amplitude, offset (saisie au pavé puis unité sur une touche de côté). <b>[Units]</b> : Amplitude/Offset ou Haut/Bas, Vpp/Vrms/dBm.</li>
   <li><b>Channel [Setup] → Output Load</b> : 50 Ω ou High Z. La résistance de sortie est toujours 50 Ω : ce réglage ne change que l'<b>affichage</b>. Réglé sur 50 Ω mais branché sur un circuit à haute impédance → la vraie tension vaut le <b>double</b> de l'affichage.</li>
   <li><b>Limites</b> : Vpp &lt; 2 × (Vmax − |offset|), avec Vmax = 5 V sur 50 Ω, 10 V en High Z.</li>
   <li><b>Channel [On/Off]</b> : connecte la sortie 1.</li>
   <li><b>Sync</b> (menu [Trigger] → Sync ON/OFF, activée par défaut) : créneau compatible TTL (charge &gt; 1 kΩ), haut pendant la 1re moitié de chaque période. Désactivée, elle reste à l'état bas.</li>
  </ul>
  <h4>Alimentation Keysight EDU36311A</h4>
  <p>${L("https://www.keysight.com/find/EDU36311A-manuals", "Manuels (site Keysight)")} · ${L("https://people.ece.ubc.ca/eng-services/files/manuals/Man_PowerSupply_KEY-EDU36311A.pdf", "copie PDF du guide utilisateur")}</p>
  <ul>
   <li><b>Voies</b> : 1 = 0–6 V / 5 A ; 2 et 3 = 0–30 V / 1 A, flottantes. Touche de voie = sélection ; molettes Voltage / Current, ou pavé + Enter.</li>
   <li><b>On</b> sous chaque voie ; <b>All On/Off</b> pour toutes. Affichage <b>CV</b> (tension régulée), <b>CC</b> (limite de courant atteinte : la tension chute), UR (non régulée).</li>
   <li><b>Tracking</b> : la voie 3 suit la tension de la voie 2 (pratique pour ±15 V). Pour −15 V : borne + de la voie 3 au 0 V commun.</li>
   <li><b>Meter View</b> : une voie ou les trois à l'écran.</li>
  </ul>
  <h4>Plaque, câbles</h4>
  <ul><li>Annexes des sujets TP1 (GBF, oscilloscope, platine) et TP2 (alimentation) : ce sont les références à avoir dans ton cahier.</li></ul>
  <p class="mut">Les manuels sont en anglais ; ces résumés sont tirés des chapitres « Front panel » / « Menu reference » de chaque manuel.</p>
  </div>`;
  function open() {
    let el = document.getElementById("docs-modal");
    if (!el) { el = document.createElement("div"); el.id = "docs-modal"; el.className = "modal"; el.innerHTML = `<div class="modal-card wide">${HTML}</div>`; document.body.appendChild(el);
      el.addEventListener("click", e => { if (e.target === el || e.target.dataset.close != null) el.classList.remove("show"); }); }
    el.classList.add("show");
  }
  return { open };
})();
