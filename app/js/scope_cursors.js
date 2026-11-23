// Glisser-déposer des curseurs de l'oscillo (extrait tel quel de l'ancienne app ; utilise `canvas` défini dans scope.js)
// 5. DRAG & DROP DES CURSEURS SUR LE CANVAS DE L'OSCILLOSCOPE
canvas.addEventListener("pointerdown", e => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (e.clientX - rect.left) * scaleX;
  const my = (e.clientY - rect.top) * scaleY;

  const gx = 20, gy = 30, gw = 600, gh = 360;
  const dx = gw / 10.0, dy = gh / 8.0;
  const cx = gx + gw / 2.0, cy = gy + gh / 2.0;

  const curX1px = cx + state.scope.curX1 * dx;
  const curX2px = cx + state.scope.curX2 * dx;
  const curY1px = cy - state.scope.curY1 * dy;
  const curY2px = cy - state.scope.curY2 * dy;

  if (Math.abs(mx - curX1px) < 15) state.scope.draggingCursor = "x1";
  else if (Math.abs(mx - curX2px) < 15) state.scope.draggingCursor = "x2";
  else if (Math.abs(my - curY1px) < 15) state.scope.draggingCursor = "y1";
  else if (Math.abs(my - curY2px) < 15) state.scope.draggingCursor = "y2";
});

window.addEventListener("pointermove", e => {
  if (!state.scope.draggingCursor) return;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (e.clientX - rect.left) * scaleX;
  const my = (e.clientY - rect.top) * scaleY;

  const gx = 20, gy = 30, gw = 600, gh = 360;
  const dx = gw / 10.0, dy = gh / 8.0;
  const cx = gx + gw / 2.0, cy = gy + gh / 2.0;

  if (state.scope.draggingCursor === "x1") {
    state.scope.curX1 = Math.max(-5, Math.min(5, (mx - cx) / dx));
  } else if (state.scope.draggingCursor === "x2") {
    state.scope.curX2 = Math.max(-5, Math.min(5, (mx - cx) / dx));
  } else if (state.scope.draggingCursor === "y1") {
    state.scope.curY1 = Math.max(-4, Math.min(4, (cy - my) / dy));
  } else if (state.scope.draggingCursor === "y2") {
    state.scope.curY2 = Math.max(-4, Math.min(4, (cy - my) / dy));
  }
  triggerScopeRedraw();
});

window.addEventListener("pointerup", () => {
  state.scope.draggingCursor = null;
});

