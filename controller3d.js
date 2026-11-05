// ANA Preset Knob — cena 3D em tela cheia (Three.js r160)
// Controlador desenhado de forma esquemática (layout da APC Key 25 mk2), uma
// tela flutuante "ANA 2" e animações que mostram a função executada.
//
// window.dev3d = {
//   hit(id, on)               acende/solta um controle
//   knob(id, graus)           gira um knob
//   bindings(mapa)            {id: 'prev'|'next'|'knob'} marca controles mapeados
//   layout(esq, dir)          largura (px) das sidebars abertas → reenquadra
//   action(dir, origemId, n)  anima a troca de preset (dir -1/+1)
//   progress(id, frac, dir)   anel de progresso do knob até o próximo preset
// }
import * as THREE from 'three';
import { OrbitControls } from '/vendor/OrbitControls.js';

const host = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
host.append(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, 1.6, 0.1, 300);
const TARGET = new THREE.Vector3(0, 1.6, -2.5);
const VIEW_DIR = new THREE.Vector3(0, 0.78, 0.63).normalize();
camera.position.copy(TARGET).addScaledVector(VIEW_DIR, 52);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(TARGET);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 26; controls.maxDistance = 120;
controls.minPolarAngle = 0.15; controls.maxPolarAngle = 1.3;

scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(-10, 26, 14);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 18, bottom: -18, near: 1, far: 80 });
scene.add(sun);

const LIGHT = new THREE.Color('#ffffff'), ACCENT = new THREE.Color('#e8743b'), PREV = new THREE.Color('#3b82f6'), NEXT = new THREE.Color('#22c55e');
const std = (c, r = 0.6, m = 0.05) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });

// ---------------------------------------------------------------- corpo
const body = new THREE.Mesh(new THREE.BoxGeometry(31, 1.4, 21.4), std('#1d1f24', 0.75));
body.position.set(0, -0.7, 0.4); body.receiveShadow = true; body.castShadow = true;
scene.add(body);
for (const x of [-15.75, 15.75]) {
  const side = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.6, 21.6), std('#c8382c', 0.5));
  side.position.set(x, -0.6, 0.4); scene.add(side);
}
const floor = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), new THREE.ShadowMaterial({ opacity: 0.22 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -1.45; floor.receiveShadow = true; scene.add(floor);

// ---------------------------------------------------------------- grupos instanciados
const groups = [];
const byId = new Map();
const dummy = new THREE.Object3D(), tmp = new THREE.Color();

function group(geo, mat, items) {
  const mesh = new THREE.InstancedMesh(geo, mat, items.length);
  mesh.castShadow = true; mesh.receiveShadow = true;
  const g = { mesh, ids: [], base: [], pos: [], glow: [], held: [], bind: [] };
  items.forEach((it, i) => {
    g.ids.push(it.id); g.base.push(new THREE.Color(it.color)); g.pos.push(it.pos);
    g.glow.push(0); g.held.push(false); g.bind.push(null);
    if (it.id) byId.set(it.id, { g, i });
    mesh.setColorAt(i, g.base[i]);
    place(g, i, 0);
  });
  scene.add(mesh); groups.push(g);
  return g;
}
function place(g, i, press) {
  const [x, y, z] = g.pos[i];
  dummy.position.set(x, y - press, z); dummy.updateMatrix();
  g.mesh.setMatrixAt(i, dummy.matrix);
}
const rounded = (w, h, d, r) => {
  const s = new THREE.Shape(), x = -w / 2, z = -d / 2;
  s.moveTo(x + r, z); s.lineTo(x + w - r, z); s.quadraticCurveTo(x + w, z, x + w, z + r);
  s.lineTo(x + w, z + d - r); s.quadraticCurveTo(x + w, z + d, x + w - r, z + d);
  s.lineTo(x + r, z + d); s.quadraticCurveTo(x, z + d, x, z + d - r);
  s.lineTo(x, z + r); s.quadraticCurveTo(x, z, x + r, z);
  const g = new THREE.ExtrudeGeometry(s, { depth: h, bevelEnabled: true, bevelSize: 0.06, bevelThickness: 0.06, bevelSegments: 2 });
  g.rotateX(Math.PI / 2); g.translate(0, h, 0);
  return g;
};

const pads = [];
for (let n = 0; n < 40; n++) {
  const c = n % 8, r = Math.floor(n / 8);
  pads.push({ id: 'c-note-' + n, color: '#555a64', pos: [-13.6 + c * 1.62, 0.02, -3.1 - r * 1.32] });
}
group(rounded(1.38, 0.32, 1.08, 0.12), std('#ffffff', 0.45), pads);
group(rounded(1.2, 0.2, 0.45, 0.08), std('#ffffff', 0.5),
  [...Array(8)].map((_, i) => ({ id: 'c-note-' + (64 + i), color: '#9a3b3b', pos: [-13.6 + i * 1.62, 0.02, -1.55] })));
group(rounded(0.95, 0.22, 0.62, 0.08), std('#ffffff', 0.5),
  [82, 83, 84, 85, 86, 81, 98].map((n, i) => ({ id: 'c-note-' + n, color: '#666b75', pos: [-0.3, 0.02, -8.4 + i * 1.12] })));
group(rounded(1.5, 0.2, 0.55, 0.08), std('#ffffff', 0.5),
  ['k-cc-64', null, null, 'c-note-91', 'c-note-93'].map((id, i) => ({ id, color: '#666b75', pos: [2.2 + i * 2.4, 0.02, -1.55] })));

const WHITE = [0, 2, 4, 5, 7, 9, 11], BLACK = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 };
const KW = 29.4 / 15, wk = [], bk = [];
let wi = 0;
for (let n = 0; n <= 24; n++) {
  const pc = n % 12, oct = Math.floor(n / 12);
  if (WHITE.includes(pc)) { wk.push({ id: 'key-' + n, color: '#f3f3f1', pos: [-14.7 + KW * (wi + 0.5), 0, 5.6] }); wi++; }
  else bk.push({ id: 'key-' + n, color: '#18181a', pos: [-14.7 + KW * (oct * 7 + BLACK[pc] + 1), 0.55, 3.75] });
}
group(new THREE.BoxGeometry(KW - 0.08, 0.7, 9), std('#ffffff', 0.35), wk).mesh.position.y = 0.05;
group(new THREE.BoxGeometry(KW * 0.58, 0.6, 5.3), std('#ffffff', 0.4), bk).mesh.position.y = 0.05;

// knobs
const knobs = new Map();
const knobGeo = new THREE.CylinderGeometry(0.95, 1.05, 1.1, 40);
const capGeo = new THREE.CylinderGeometry(0.82, 0.82, 0.08, 40);
const lineGeo = new THREE.BoxGeometry(0.12, 0.06, 0.7);
const ringGeo = new THREE.TorusGeometry(1.25, 0.08, 10, 48);
for (let i = 0; i < 8; i++) {
  const id = 'c-cc-' + (48 + i), x = 3.3 + (i % 4) * 2.75, z = -7.9 + Math.floor(i / 4) * 3.0;
  const k = new THREE.Group(); k.position.set(x, 0.55, z);
  const spin = new THREE.Group(); k.add(spin);
  const m = new THREE.Mesh(knobGeo, std('#17181b', 0.55)); m.castShadow = true; spin.add(m);
  const cap = new THREE.Mesh(capGeo, std('#2b2d33', 0.4)); cap.position.y = 0.58; spin.add(cap);
  const ln = new THREE.Mesh(lineGeo, std('#eceef2', 0.3)); ln.position.set(0, 0.64, -0.42); spin.add(ln);
  const ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: ACCENT, transparent: true, opacity: 0.35 }));
  ring.rotation.x = Math.PI / 2; ring.position.y = -0.45; ring.visible = false; k.add(ring);
  const arc = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({ color: ACCENT }));
  arc.rotation.x = -Math.PI / 2; arc.position.y = -0.43; k.add(arc);
  scene.add(k);
  knobs.set(id, { k, spin, ring, arc, mat: m.material, angle: 0, target: 0, glow: 0, frac: 0, shown: 0, dir: 1 });
}
function arcGeo(frac, dir) {
  if (frac <= 0.001) return new THREE.BufferGeometry();
  const len = Math.PI * 2 * Math.min(frac, 1);
  return new THREE.RingGeometry(1.17, 1.38, 48, 1, dir > 0 ? Math.PI / 2 - len : Math.PI / 2, len);
}

// ---------------------------------------------------------------- tela flutuante "ANA 2"
const SCR_W = 1024, SCR_H = 300;
const scrCanvas = document.createElement('canvas'); scrCanvas.width = SCR_W; scrCanvas.height = SCR_H;
const scrCtx = scrCanvas.getContext('2d');
const scrTex = new THREE.CanvasTexture(scrCanvas); scrTex.colorSpace = THREE.SRGBColorSpace;
scrTex.anisotropy = 4;
const screen = new THREE.Mesh(new THREE.PlaneGeometry(15, 15 * SCR_H / SCR_W),
  new THREE.MeshBasicMaterial({ map: scrTex, transparent: true }));
screen.position.set(0, 6.2, -14.2); screen.rotation.x = -0.18;
scene.add(screen);
const scr = { t: 1, dir: 0, label: '', count: 0, name: null, sub: '' };

function roundRect(c, x, y, w, h, r) {
  c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
}
function drawScreen() {
  const c = scrCtx, a = Math.max(0, 1 - scr.t);
  c.clearRect(0, 0, SCR_W, SCR_H);
  roundRect(c, 6, 6, SCR_W - 12, SCR_H - 12, 28);
  c.fillStyle = 'rgba(22,24,29,0.92)'; c.fill();
  c.lineWidth = 4; c.strokeStyle = a > 0 ? `rgba(232,116,59,${0.35 + 0.65 * a})` : 'rgba(255,255,255,0.12)'; c.stroke();
  c.fillStyle = '#9aa0ab'; c.font = '600 30px -apple-system, Segoe UI, sans-serif';
  c.textAlign = 'left'; c.fillText('ANA 2 · PRESET', 48, 66);
  const col = d => scr.dir === d && a > 0 ? (d < 0 ? '#3b82f6' : '#22c55e') : 'rgba(236,238,242,0.35)';
  const arrow = (cx, d) => {
    const s = 46 * (1 + (scr.dir === d ? 0.25 * a : 0));
    c.beginPath(); c.moveTo(cx + d * s, 175); c.lineTo(cx - d * s * 0.7, 175 - s); c.lineTo(cx - d * s * 0.7, 175 + s);
    c.closePath(); c.fillStyle = col(d); c.fill();
  };
  arrow(110, -1); arrow(SCR_W - 110, 1);
  c.save(); c.beginPath(); c.rect(200, 90, SCR_W - 400, 180); c.clip();
  const off = scr.dir * (1 - Math.min(1, scr.t * 2.2)) * 160;
  c.globalAlpha = a > 0 ? 1 : 0.55;
  c.fillStyle = '#eceef2'; c.textAlign = 'center';
  const main = scr.name || scr.label || 'aguardando';
  let fs = 62; c.font = `700 ${fs}px -apple-system, Segoe UI, sans-serif`;
  while (c.measureText(main).width > SCR_W - 440 && fs > 26) { fs -= 2; c.font = `700 ${fs}px -apple-system, Segoe UI, sans-serif`; }
  c.fillText(main, SCR_W / 2 + off, 192);
  if (scr.sub) { c.font = '500 26px -apple-system, Segoe UI, sans-serif'; c.fillStyle = '#9aa0ab'; c.fillText(scr.sub, SCR_W / 2 + off, 240); }
  if (scr.count > 1 && a > 0 && !scr.sub) {
    c.font = '600 32px -apple-system, Segoe UI, sans-serif'; c.fillStyle = '#e8743b';
    c.fillText('×' + scr.count, SCR_W / 2 + off, 240);
  }
  c.restore();
  scrTex.needsUpdate = true;
}
drawScreen();

// ---------------------------------------------------------------- efeitos
const fx = [];
const chevGeo = (() => {
  const s = new THREE.Shape();
  s.moveTo(0, 0.55); s.lineTo(0.55, 0); s.lineTo(0, -0.55); s.lineTo(-0.22, -0.55); s.lineTo(0.33, 0);
  s.lineTo(-0.22, 0.55); s.closePath();
  return new THREE.ShapeGeometry(s);
})();

function labelSprite(text, color) {
  const cv = document.createElement('canvas'); cv.width = 640; cv.height = 128;
  const c = cv.getContext('2d');
  roundRect(c, 4, 14, 632, 100, 50); c.fillStyle = 'rgba(20,22,27,0.88)'; c.fill();
  c.lineWidth = 5; c.strokeStyle = color; c.stroke();
  c.fillStyle = '#fff'; c.font = '700 54px -apple-system, Segoe UI, sans-serif';
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, 320, 66);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
  sp.scale.set(7, 1.4, 1); sp.renderOrder = 10;
  return sp;
}

function sourcePos(id) {
  const ref = id && byId.get(id);
  if (ref) { const [x, y, z] = ref.g.pos[ref.i]; return new THREE.Vector3(x, y + 0.6, z); }
  const kn = id && knobs.get(id); if (kn) return kn.k.position.clone().add(new THREE.Vector3(0, 0.9, 0));
  return new THREE.Vector3(0, 1, -2);
}

function action(dir, id, count = 1) {
  const color = dir < 0 ? PREV : NEXT, css = dir < 0 ? '#3b82f6' : '#22c55e';
  const text = dir < 0 ? '◀  Preset anterior' : 'Próximo preset  ▶';
  const from = sourcePos(id);
  const sp = labelSprite(text, css); sp.position.copy(from).add(new THREE.Vector3(0, 1.2, 0));
  scene.add(sp); fx.push({ kind: 'label', obj: sp, t: 0, life: 1.6, from: sp.position.clone() });
  const to = new THREE.Vector3(dir < 0 ? -6.2 : 6.2, 6.6, -14.0);
  for (let k = 0; k < 4; k++) {
    const m = new THREE.Mesh(chevGeo, new THREE.MeshBasicMaterial({ color, transparent: true, depthTest: false, side: THREE.DoubleSide }));
    m.renderOrder = 9; m.scale.setScalar(1.5); m.userData.flip = dir < 0;
    scene.add(m);
    const mid = from.clone().lerp(to, 0.5).add(new THREE.Vector3(dir * 3, 6, 0));
    fx.push({ kind: 'chev', obj: m, t: -k * 0.09, life: 0.75, curve: new THREE.QuadraticBezierCurve3(from.clone(), mid, to) });
  }
  const wave = new THREE.Mesh(new THREE.RingGeometry(0.6, 0.8, 40),
    new THREE.MeshBasicMaterial({ color, transparent: true, side: THREE.DoubleSide, depthTest: false }));
  wave.rotation.x = -Math.PI / 2; wave.position.copy(from).add(new THREE.Vector3(0, -0.2, 0)); wave.renderOrder = 8;
  scene.add(wave); fx.push({ kind: 'wave', obj: wave, t: 0, life: 0.7 });
  setTimeout(() => { scr.t = 0; scr.dir = dir; scr.count = count; scr.label = dir < 0 ? 'anterior' : 'próximo'; }, 520);
  if (id && byId.has(id)) { const { g, i } = byId.get(id); g.glow[i] = 1; }
}

function stepFx(dt) {
  for (let n = fx.length - 1; n >= 0; n--) {
    const f = fx[n]; f.t += dt;
    const u = f.t / f.life;
    if (f.t < 0) { f.obj.visible = false; continue; }
    f.obj.visible = true;
    if (f.kind === 'label') {
      f.obj.position.copy(f.from).add(new THREE.Vector3(0, u * 1.6, 0));
      f.obj.material.opacity = u < 0.15 ? u / 0.15 : Math.max(0, 1 - (u - 0.6) / 0.4);
    } else if (f.kind === 'chev') {
      const e = Math.min(1, u); f.obj.position.copy(f.curve.getPoint(e * e * (3 - 2 * e)));
      f.obj.lookAt(camera.position); if (f.obj.userData.flip) f.obj.rotateZ(Math.PI);
      f.obj.material.opacity = 1 - Math.max(0, (u - 0.75) / 0.25);
    } else if (f.kind === 'wave') {
      f.obj.scale.setScalar(1 + u * 2.4); f.obj.material.opacity = 1 - u;
    }
    if (u >= 1) {
      scene.remove(f.obj);
      if (f.obj.geometry !== chevGeo) f.obj.geometry.dispose();
      if (f.obj.material.map) f.obj.material.map.dispose();
      f.obj.material.dispose();
      fx.splice(n, 1);
    }
  }
  if (scr.t < 1) { scr.t = Math.min(1, scr.t + dt / 1.4); drawScreen(); }
}

// ---------------------------------------------------------------- clique com o mouse
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
let downAt = null;
function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(groups.map(g => g.mesh), false)[0];
  if (!hit) return null;
  const g = groups.find(x => x.mesh === hit.object);
  return { g, i: hit.instanceId };
}
renderer.domElement.addEventListener('pointerdown', ev => { downAt = [ev.clientX, ev.clientY]; });
renderer.domElement.addEventListener('pointerup', ev => {
  if (!downAt || Math.hypot(ev.clientX - downAt[0], ev.clientY - downAt[1]) > 5) return;
  const p = pick(ev); if (!p) return;
  const kind = p.g.bind[p.i];
  if (kind === 'prev' || kind === 'next') {
    window.dispatchEvent(new CustomEvent('virtual-arrow', { detail: { dir: kind === 'prev' ? -1 : 1, id: p.g.ids[p.i] } }));
  }
});
renderer.domElement.addEventListener('pointermove', ev => {
  const p = pick(ev); const k = p && p.g.bind[p.i];
  renderer.domElement.style.cursor = (k === 'prev' || k === 'next') ? 'pointer' : '';
});

// ---------------------------------------------------------------- enquadramento com sidebars
const frame = { l: 0, r: 0, tl: 0, tr: 0, anim: 0 };
function applyFrame() {
  const W = host.clientWidth, H = host.clientHeight;
  camera.setViewOffset(W, H, -(frame.l - frame.r) / 2, 0, W, H);
  camera.updateProjectionMatrix();
}
function fitDistance() {
  const W = host.clientWidth, H = host.clientHeight;
  const free = Math.max(320, W - frame.tl - frame.tr);
  const vfov = THREE.MathUtils.degToRad(camera.fov);
  const hfovFree = 2 * Math.atan(Math.tan(vfov / 2) * free / H);
  const dW = 18.5 / Math.tan(hfovFree / 2), dH = 17.5 / Math.tan(vfov / 2);
  return THREE.MathUtils.clamp(Math.max(dW, dH), 30, 115);
}
let distFrom = 0, distTo = 0;
function setDist(d) {
  const dir = camera.position.clone().sub(controls.target).normalize();
  camera.position.copy(controls.target).addScaledVector(dir, d);
}
function layout(l, r) {
  frame.tl = l; frame.tr = r; frame.anim = 0.0001;
  distFrom = camera.position.distanceTo(controls.target); distTo = fitDistance();
}

// ---------------------------------------------------------------- API
window.dev3d = {
  hit(id, on) {
    const ref = byId.get(id);
    if (ref) { const { g, i } = ref; g.held[i] = !!on; if (on) g.glow[i] = 1; return true; }
    const kn = knobs.get(id); if (kn && on) { kn.glow = 1; return true; }
    return false;
  },
  knob(id, deg) { const kn = knobs.get(id); if (kn) { kn.target = -THREE.MathUtils.degToRad(deg); kn.glow = 1; } },
  bindings(map) {
    for (const g of groups) g.bind.fill(null);
    for (const kn of knobs.values()) kn.ring.visible = false;
    for (const [id, kind] of Object.entries(map)) {
      const ref = byId.get(id); if (ref) ref.g.bind[ref.i] = kind;
      const kn = knobs.get(id); if (kn && kind === 'knob') kn.ring.visible = true;
    }
  },
  progress(id, frac, dir) { const kn = knobs.get(id); if (kn) { kn.frac = frac; if (dir) kn.dir = dir; } },
  preset(name, index, total) {
    scr.name = name; scr.sub = (index != null && total) ? `${index + 1} / ${total}` : '';
    scr.t = Math.min(scr.t, 0.35); drawScreen();
  },
  layout, action,
};

// ---------------------------------------------------------------- loop
function resize() {
  renderer.setSize(host.clientWidth, host.clientHeight, false);
  renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%';
  camera.aspect = host.clientWidth / host.clientHeight;
  applyFrame();
  if (!frame.anim) { distTo = fitDistance(); setDist(distTo); }
}
new ResizeObserver(resize).observe(host); resize();

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  if (frame.anim) {
    frame.anim = Math.min(1, frame.anim + dt / 0.45);
    const e = 1 - Math.pow(1 - frame.anim, 3);
    frame.l += (frame.tl - frame.l) * Math.min(1, dt * 9);
    frame.r += (frame.tr - frame.r) * Math.min(1, dt * 9);
    setDist(distFrom + (distTo - distFrom) * e);
    if (frame.anim >= 1) { frame.l = frame.tl; frame.r = frame.tr; frame.anim = 0; }
    applyFrame();
  }
  for (const g of groups) {
    for (let i = 0; i < g.ids.length; i++) {
      if (!g.held[i] && g.glow[i] > 0) g.glow[i] = Math.max(0, g.glow[i] - dt * 3.2);
      const glow = g.held[i] ? 1 : g.glow[i];
      const bind = g.bind[i];
      if (bind === 'prev' || bind === 'next') tmp.copy(bind === 'prev' ? PREV : NEXT).lerp(LIGHT, glow * 0.65);
      else tmp.copy(g.base[i]).lerp(ACCENT, glow);
      g.mesh.setColorAt(i, tmp);
      place(g, i, glow * 0.12);
    }
    g.mesh.instanceColor.needsUpdate = true; g.mesh.instanceMatrix.needsUpdate = true;
  }
  for (const kn of knobs.values()) {
    kn.angle += (kn.target - kn.angle) * Math.min(1, dt * 14);
    kn.spin.rotation.y = kn.angle;
    kn.glow = Math.max(0, kn.glow - dt * 2.5);
    kn.mat.emissive.copy(ACCENT).multiplyScalar(kn.glow * 0.45);
    const want = kn.ring.visible ? kn.frac : 0;
    if (Math.abs(want - kn.shown) > 0.004) {
      kn.shown += (want - kn.shown) * Math.min(1, dt * 16);
      kn.arc.geometry.dispose(); kn.arc.geometry = arcGeo(kn.shown, kn.dir);
      kn.arc.material.color.copy(kn.dir < 0 ? PREV : NEXT);
    }
  }
  stepFx(dt);
  controls.update();
  renderer.render(scene, camera);
});
document.body.classList.add('webgl-ok');
