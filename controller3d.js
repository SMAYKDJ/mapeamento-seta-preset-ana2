// Controlador em 3D (Three.js) — layout da APC Key 25 mk2, desenhado de forma esquemática.
// Expõe window.dev3d = { hit(id, on), knob(id, graus), bindings(mapa) }.
// Peças repetidas usam InstancedMesh (um draw call por grupo).
import * as THREE from 'three';
import { OrbitControls } from '/vendor/OrbitControls.js';

const host = document.getElementById('dev3dhost');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
host.append(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1.6, 0.1, 200);
camera.position.set(0, 30, 31);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.5);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 22; controls.maxDistance = 60;
controls.minPolarAngle = 0.15; controls.maxPolarAngle = 1.25;

scene.add(new THREE.HemisphereLight(0xffffff, 0x30343c, 1.6));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(-10, 26, 14);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 16, bottom: -16, near: 1, far: 70 });
scene.add(sun);

const ACCENT = new THREE.Color('#e8743b'), PREV = new THREE.Color('#3b82f6'), NEXT = new THREE.Color('#22c55e');
const std = (c, r = 0.6, m = 0.05) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });

// ---------- corpo
const body = new THREE.Mesh(new THREE.BoxGeometry(31, 1.4, 21.4), std('#1d1f24', 0.75));
body.position.set(0, -0.7, 0.4); body.receiveShadow = true; body.castShadow = true;
scene.add(body);
for (const x of [-15.75, 15.75]) {
  const side = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.6, 21.6), std('#c8382c', 0.5));
  side.position.set(x, -0.6, 0.4); scene.add(side);
}
const floor = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.ShadowMaterial({ opacity: 0.22 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -1.45; floor.receiveShadow = true; scene.add(floor);

// ---------- grupos instanciados
const groups = [];          // {mesh, ids[], base[], pos[], glow[], held[], bind[]}
const byId = new Map();     // id -> {g, i}
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

// pads 8x5 (nota 0 = canto inferior esquerdo)
const pads = [];
for (let n = 0; n < 40; n++) {
  const c = n % 8, r = Math.floor(n / 8);
  pads.push({ id: 'c-note-' + n, color: '#555a64', pos: [-13.6 + c * 1.62, 0.02, -3.1 - r * 1.32] });
}
group(rounded(1.38, 0.32, 1.08, 0.12), std('#ffffff', 0.45), pads);

// botões vermelhos sob os pads
group(rounded(1.2, 0.2, 0.45, 0.08), std('#ffffff', 0.5),
  [...Array(8)].map((_, i) => ({ id: 'c-note-' + (64 + i), color: '#9a3b3b', pos: [-13.6 + i * 1.62, 0.02, -1.55] })));

// soft keys + stop all + shift
group(rounded(0.95, 0.22, 0.62, 0.08), std('#ffffff', 0.5),
  [82, 83, 84, 85, 86, 81, 98].map((n, i) => ({ id: 'c-note-' + n, color: '#666b75', pos: [-0.3, 0.02, -8.4 + i * 1.12] })));

// transporte (sustain, oct-, oct+, play, rec)
group(rounded(1.5, 0.2, 0.55, 0.08), std('#ffffff', 0.5),
  ['k-cc-64', null, null, 'c-note-91', 'c-note-93'].map((id, i) => ({ id, color: '#666b75', pos: [2.2 + i * 2.4, 0.02, -1.55] })));

// teclado: 15 brancas + 10 pretas
const WHITE = [0, 2, 4, 5, 7, 9, 11], BLACK = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 };
const KW = 29.4 / 15, wk = [], bk = [];
let wi = 0;
for (let n = 0; n <= 24; n++) {
  const pc = n % 12, oct = Math.floor(n / 12);
  if (WHITE.includes(pc)) { wk.push({ id: 'key-' + n, color: '#f3f3f1', pos: [-14.7 + KW * (wi + 0.5), 0, 5.6] }); wi++; }
  else bk.push({ id: 'key-' + n, color: '#18181a', pos: [-14.7 + KW * (oct * 7 + BLACK[pc] + 1), 0.55, 3.75] });
}
group(new THREE.BoxGeometry(KW - 0.08, 0.7, 9), std("#ffffff", 0.35), wk).mesh.position.y = 0.05;
group(new THREE.BoxGeometry(KW * 0.58, 0.6, 5.3), std("#ffffff", 0.4), bk).mesh.position.y = 0.05;

// knobs (individuais: giram)
const knobs = new Map();
const knobGeo = new THREE.CylinderGeometry(0.95, 1.05, 1.1, 40);
const capGeo = new THREE.CylinderGeometry(0.82, 0.82, 0.08, 40);
const lineGeo = new THREE.BoxGeometry(0.12, 0.06, 0.7);
const ringGeo = new THREE.TorusGeometry(1.25, 0.08, 10, 48);
for (let i = 0; i < 8; i++) {
  const id = 'c-cc-' + (48 + i), x = 3.3 + (i % 4) * 2.75, z = -7.9 + Math.floor(i / 4) * 3.0;
  const k = new THREE.Group(); k.position.set(x, 0.55, z);
  const m = new THREE.Mesh(knobGeo, std('#17181b', 0.55)); m.castShadow = true; k.add(m);
  const cap = new THREE.Mesh(capGeo, std('#2b2d33', 0.4)); cap.position.y = 0.58; k.add(cap);
  const ln = new THREE.Mesh(lineGeo, std('#eceef2', 0.3)); ln.position.set(0, 0.64, -0.42); k.add(ln);
  const ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: ACCENT }));
  ring.rotation.x = Math.PI / 2; ring.position.y = -0.45; ring.visible = false; k.add(ring);
  scene.add(k);
  knobs.set(id, { k, ring, mat: m.material, angle: 0, target: 0, glow: 0 });
}

// ---------- API usada pela página
window.dev3d = {
  hit(id, on) {
    const ref = byId.get(id);
    if (ref) { const { g, i } = ref; g.held[i] = !!on; if (on) g.glow[i] = 1; return true; }
    const kn = knobs.get(id); if (kn && on) { kn.glow = 1; return true; }
    return false;
  },
  knob(id, deg) { const kn = knobs.get(id); if (kn) { kn.target = -THREE.MathUtils.degToRad(deg); kn.glow = 1; } },
  bindings(map) {   // map: id -> 'prev' | 'next' | 'knob'
    for (const g of groups) g.bind.fill(null);
    for (const kn of knobs.values()) kn.ring.visible = false;
    for (const [id, kind] of Object.entries(map)) {
      const ref = byId.get(id); if (ref) ref.g.bind[ref.i] = kind;
      const kn = knobs.get(id); if (kn && kind === 'knob') kn.ring.visible = true;
    }
  },
};

// ---------- clique com o mouse nos controles mapeados (◀ ▶) troca o preset
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
  if (!downAt || Math.hypot(ev.clientX - downAt[0], ev.clientY - downAt[1]) > 5) return;  // foi arrasto
  const p = pick(ev); if (!p) return;
  const kind = p.g.bind[p.i];
  if (kind === 'prev' || kind === 'next') {
    p.g.glow[p.i] = 1;
    window.dispatchEvent(new CustomEvent('virtual-arrow', { detail: kind === 'prev' ? -1 : 1 }));
  }
});
renderer.domElement.addEventListener('pointermove', ev => {
  const p = pick(ev); const k = p && p.g.bind[p.i];
  renderer.domElement.style.cursor = (k === 'prev' || k === 'next') ? 'pointer' : '';
});

// ---------- loop
function resize() {
  const w = host.clientWidth, h = Math.round(w * 0.6);
  renderer.setSize(w, h, false); renderer.domElement.style.width = '100%'; renderer.domElement.style.height = h + 'px';
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host); resize();

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  for (const g of groups) {
    let dirty = false;
    for (let i = 0; i < g.ids.length; i++) {
      if (!g.held[i] && g.glow[i] > 0) { g.glow[i] = Math.max(0, g.glow[i] - dt * 3.2); }
      const glow = g.held[i] ? 1 : g.glow[i];
      const bind = g.bind[i];
      tmp.copy(bind === 'prev' ? PREV : bind === 'next' ? NEXT : g.base[i]).lerp(ACCENT, glow);
      g.mesh.setColorAt(i, tmp);
      place(g, i, glow * 0.12);
      dirty = true;
    }
    if (dirty) { g.mesh.instanceColor.needsUpdate = true; g.mesh.instanceMatrix.needsUpdate = true; }
  }
  for (const kn of knobs.values()) {
    kn.angle += (kn.target - kn.angle) * Math.min(1, dt * 14);
    kn.k.rotation.y = kn.angle;
    kn.glow = Math.max(0, kn.glow - dt * 2.5);
    kn.mat.emissive.copy(ACCENT).multiplyScalar(kn.glow * 0.45);
  }
  controls.update();
  renderer.render(scene, camera);
});
document.getElementById('dev2d').classList.add('hidden');
host.classList.remove('hidden');
