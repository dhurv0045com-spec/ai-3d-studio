/* Aurex GestureEngine v2 — MediaPipe hand control for Three.js viewer */
/* eslint-disable no-unused-vars */
var PARTS = { meshes: [], index: -1 };

function _partsClearVisuals() {
  PARTS.meshes.forEach(function(mesh) {
    if (!mesh || !mesh.material || !mesh.userData || !mesh.userData._baseMaterial) { return; }
    mesh.material = mesh.userData._baseMaterial;
  });
}

function _partsCollectMeshes() {
  PARTS.meshes = [];
  PARTS.index = -1;
  if (!currentObject) { return; }
  currentObject.traverse(function(node) {
    if (!node || !node.isMesh || !node.material) { return; }
    if (!node.userData._baseMaterial) { node.userData._baseMaterial = node.material; }
    PARTS.meshes.push(node);
  });
}

function _partsFocus(index) {
  if (!PARTS.meshes.length) { return; }
  PARTS.index = (index + PARTS.meshes.length) % PARTS.meshes.length;
  PARTS.meshes.forEach(function(mesh, i) {
    if (!mesh || !mesh.userData || !mesh.userData._baseMaterial) { return; }
    var baseMat = mesh.userData._baseMaterial;
    if (i === PARTS.index) {
      var hi = baseMat.clone ? baseMat.clone() : baseMat;
      if (hi.emissive && hi.emissive.clone) { hi.emissive = hi.emissive.clone().addScalar(0.14); }
      hi.opacity = 1;
      hi.transparent = false;
      mesh.material = hi;
    } else {
      var dim = baseMat.clone ? baseMat.clone() : baseMat;
      dim.opacity = 0.16;
      dim.transparent = true;
      mesh.material = dim;
    }
  });
  var active = PARTS.meshes[PARTS.index];
  if (active) {
    var box = new THREE.Box3().setFromObject(active);
    var center = box.getCenter(new THREE.Vector3());
    sph.tTargetX = center.x;
    sph.tTargetY = center.y;
    sph.tTargetZ = center.z;
    var size = box.getSize(new THREE.Vector3());
    var maxDim = Math.max(size.x, size.y, size.z);
    if (maxDim > 0) { sph.tRadius = Math.max(2.2, Math.min(14, maxDim * 2.8)); }
  }
  if (typeof toast === 'function') {
    toast('Part ' + (PARTS.index + 1) + ' / ' + PARTS.meshes.length, 'info');
  }
}

function _partsCycleFocus() {
  var ge = window.GestureEngine || window.HAND;
  if (!ge || !ge.settings || !ge.settings.partControl) { return; }
  if (!PARTS.meshes.length) { _partsCollectMeshes(); }
  if (!PARTS.meshes.length) { return; }
  _partsFocus(PARTS.index + 1);
}

function _partsClearFocus() {
  _partsClearVisuals();
  PARTS.index = -1;
  sph.tTargetX = 0;
  sph.tTargetY = 0;
  sph.tTargetZ = 0;
}

var GestureEngine = (function() {
  var LOCK_FRAMES = 4;
  var RELEASE_FRAMES = 6;
  var BUFFER_SIZE = 6;
  var ONE_SHOT_COOLDOWN = 1200;
  var RELEASE_INERTIA_FRAMES = 18;

  var GESTURES = {
    ORBIT:       { emoji: '🖐️', label: 'ORBIT',       color: '#00d4ff', continuous: true },
    ZOOM:        { emoji: '🤏', label: 'ZOOM',        color: '#f0c040', continuous: true },
    PAN:         { emoji: '✊', label: 'PAN',         color: '#f59e0b', continuous: true },
    PART_CYCLE:  { emoji: '✌️', label: 'PART CYCLE',  color: '#c084fc', continuous: false },
    INSPECT:     { emoji: '☝️', label: 'INSPECT',     color: '#c084fc', continuous: true },
    WIREFRAME:   { emoji: '🤘', label: 'WIREFRAME',   color: '#4ade80', continuous: false },
    SAVE:        { emoji: '👍', label: 'SAVE',        color: '#4ade80', continuous: false },
    FIT:         { emoji: '🖐️', label: 'FIT',         color: '#4ade80', continuous: false },
    RESET:       { emoji: '🌊', label: 'RESET',       color: '#4ade80', continuous: false },
    ROLL_ORBIT:  { emoji: '🔄', label: 'ROLL',        color: '#00d4ff', continuous: true }
  };

  var engine = {
    enabled: false,
    machineState: 'IDLE',
    lockedGesture: null,
    releaseFramesLeft: 0,
    hands: null,
    cam: null,
    video: null,
    skeletonCanvas: null,
    skeletonCtx: null,
    previewWrap: null,
    previewExpanded: false,
    frameBuffer: [],
    lastTrack: { x: null, y: null, z: null, pinch: null, roll: null, spread: null },
    waveHistory: [],
    calSamples: [],
    calStartedAt: 0,
    fpsCounter: { frames: 0, lastTs: 0, fps: 0 },
    gestureLog: [],
    oneShotFired: {},
    inspectTooltip: null,
    raycaster: null,
    mouse2d: null,
    inertiaRaf: null,
    settings: {
      sensitivity: 1.0,
      showPreview: true,
      twoHand: true,
      partControl: true,
      inertia: true,
      adaptiveSpeed: true
    },
    calibration: { palmWidth: 0.14, ready: false },
    vel: { theta: 0, phi: 0, zoom: 0, panX: 0, panY: 0, panZ: 0, roll: 0 },
    ui: { panel: null, hud: null, calOverlay: null }
  };

  var HAND = engine;

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  function dist3(a, b) {
    return Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2) + Math.pow((a.z || 0) - (b.z || 0), 2));
  }

  function vecSub(a, b) { return { x: a.x - b.x, y: a.y - b.y, z: (a.z || 0) - (b.z || 0) }; }

  function vecLen(v) { return Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z); }

  function jointAngle(a, b, c) {
    var ab = vecSub(b, a);
    var cb = vecSub(b, c);
    var dot = ab.x * cb.x + ab.y * cb.y + ab.z * cb.z;
    var lab = vecLen(ab);
    var lcb = vecLen(cb);
    if (lab < 1e-6 || lcb < 1e-6) { return 180; }
    return Math.acos(clamp(dot / (lab * lcb), -1, 1)) * (180 / Math.PI);
  }

  function classifyFingers(lm) {
    var palmWidth = dist3(lm[5], lm[17]);
    if (palmWidth < 0.02) { palmWidth = 0.14; }
    var wrist = lm[0];

    /* Works for upright hand, tilted hand, and palm-facing-camera */
    function fingerExtended(tipIdx, pipIdx, mcpIdx) {
      var dTip = dist3(wrist, lm[tipIdx]);
      var dPip = dist3(wrist, lm[pipIdx]);
      var dMcp = dist3(wrist, lm[mcpIdx]);
      var reach = dist3(lm[tipIdx], lm[mcpIdx]) > palmWidth * 0.42;
      var extByWrist = dTip > dPip * 1.06 && dTip > dMcp * 0.92;
      var extByY = lm[tipIdx].y < lm[pipIdx].y && lm[pipIdx].y < lm[mcpIdx].y;
      var ang = jointAngle(wrist, lm[pipIdx], lm[tipIdx]);
      return reach && (extByWrist || extByY || ang > 150);
    }

    var thumbExt = dist3(wrist, lm[4]) > dist3(wrist, lm[2]) * 1.05 ||
      Math.abs(lm[4].x - lm[2].x) > palmWidth * 0.18;
    var indexExt = fingerExtended(8, 6, 5);
    var middleExt = fingerExtended(12, 10, 9);
    var ringExt = fingerExtended(16, 14, 13);
    var pinkyExt = fingerExtended(20, 18, 17);

    var palmCenter = {
      x: (lm[0].x + lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 5,
      y: (lm[0].y + lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 5,
      z: (lm[0].z + lm[5].z + lm[9].z + lm[13].z + lm[17].z) / 5
    };

    var v1 = vecSub(lm[5], lm[0]);
    var v2 = vecSub(lm[17], lm[0]);
    var nx = v1.y * v2.z - v1.z * v2.y;
    var ny = v1.z * v2.x - v1.x * v2.z;
    var nz = v1.x * v2.y - v1.y * v2.x;
    var nlen = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    var palmNormal = { x: nx / nlen, y: ny / nlen, z: nz / nlen };

    var count = (thumbExt ? 1 : 0) + (indexExt ? 1 : 0) + (middleExt ? 1 : 0) +
      (ringExt ? 1 : 0) + (pinkyExt ? 1 : 0);

    return {
      thumb: thumbExt,
      index: indexExt,
      middle: middleExt,
      ring: ringExt,
      pinky: pinkyExt,
      count: count,
      palmWidth: palmWidth,
      wristPos: { x: wrist.x, y: wrist.y, z: wrist.z || 0 },
      palmCenter: palmCenter,
      palmNormal: palmNormal
    };
  }

  function pinchDistance(lm, palmWidth) {
    var d = dist3(lm[4], lm[8]);
    return d / Math.max(palmWidth, 0.05);
  }

  function spreadDistance(lm) {
    return dist3(lm[8], lm[20]);
  }

  function classifyGesture(lm, fingers, ctx) {
    var pw = fingers.palmWidth / Math.max(engine.calibration.palmWidth, 0.05);
    var pinchNorm = pinchDistance(lm, fingers.palmWidth);
    var spread = spreadDistance(lm) / Math.max(fingers.palmWidth, 0.05);

    if (fingers.count >= 5 && spread > 0.95) { return 'FIT'; }

    if (fingers.index && fingers.middle && !fingers.ring && !fingers.pinky) { return 'PART_CYCLE'; }

    if (fingers.index && fingers.pinky && !fingers.middle && !fingers.ring) { return 'WIREFRAME'; }

    if (fingers.index && !fingers.middle && !fingers.ring && !fingers.pinky) { return 'INSPECT'; }

    if (fingers.thumb && !fingers.index && !fingers.middle && fingers.count <= 2 &&
        (fingers.wristPos.y - lm[4].y) > fingers.palmWidth * 0.35) {
      return 'SAVE';
    }

    if (pinchNorm < 0.42 && fingers.thumb && fingers.index) { return 'ZOOM'; }

    if (fingers.count <= 1 && !fingers.index) { return 'PAN'; }

    if (fingers.count >= 4) {
      if (ctx && ctx.waveDetected) { return 'RESET'; }
      if (ctx && Math.abs(ctx.rollDelta) > 0.02) { return 'ROLL_ORBIT'; }
      return 'ORBIT';
    }

    return 'ORBIT';
  }

  function pushBuffer(gesture) {
    engine.frameBuffer.push(gesture);
    if (engine.frameBuffer.length > BUFFER_SIZE) { engine.frameBuffer.shift(); }
  }

  function bufferAgreement(gesture) {
    if (!engine.frameBuffer.length) { return 0; }
    var n = 0;
    for (var i = 0; i < engine.frameBuffer.length; i++) {
      if (engine.frameBuffer[i] === gesture) { n += 1; }
    }
    return n / engine.frameBuffer.length;
  }

  function dominantInBuffer() {
    var counts = {};
    engine.frameBuffer.forEach(function(g) {
      counts[g] = (counts[g] || 0) + 1;
    });
    var best = null;
    var bestN = 0;
    for (var k in counts) {
      if (counts[k] > bestN) { bestN = counts[k]; best = k; }
    }
    return { name: best, count: bestN };
  }

  function logGestureEvent(name) {
    var entry = { t: Date.now(), g: name };
    engine.gestureLog.unshift(entry);
    if (engine.gestureLog.length > 5) { engine.gestureLog.pop(); }
    updateGestureLogUI();
  }

  function sensScale() {
    var s = engine.settings.sensitivity || 1;
    if (!engine.settings.adaptiveSpeed || !currentObject) { return s; }
    return s * clamp(sph.tRadius / 6, 0.55, 1.25);
  }

  function applyOrbit(dx, dy) {
    var s = sensScale();
    engine.vel.theta += (dx * 2.8 * s - engine.vel.theta) * 0.28;
    engine.vel.phi   += (dy * 2.8 * s - engine.vel.phi)   * 0.28;
    sph.tTheta -= engine.vel.theta;
    sph.tPhi   -= engine.vel.phi;
    sph.tPhi = clamp(sph.tPhi, 0.08, Math.PI - 0.08);
  }

  function applyZoom(delta) {
    var s = sensScale();
    engine.vel.zoom += (delta * 95 * s - engine.vel.zoom) * 0.35;
    sph.tRadius = clamp(sph.tRadius - engine.vel.zoom, 1.2, 22);
  }

  function applyPan(dx, dy, dz) {
    var s = sensScale();
    engine.vel.panX += (dx * 9 * s - engine.vel.panX) * 0.3;
    engine.vel.panY += (dy * 7 * s - engine.vel.panY) * 0.3;
    engine.vel.panZ += ((dz || 0) * 6 * s - engine.vel.panZ) * 0.3;
    sph.tTargetX -= engine.vel.panX;
    sph.tTargetY += engine.vel.panY;
    sph.tTargetZ -= engine.vel.panZ;
  }

  function applyRoll(dRoll) {
    var s = sensScale();
    engine.vel.roll += (dRoll * 1.4 * s - engine.vel.roll) * 0.28;
    sph.tTheta -= engine.vel.roll;
  }

  function tickInertia() {
    if (!engine.settings.inertia) { return; }
    var mag = Math.abs(engine.vel.theta) + Math.abs(engine.vel.phi) +
      Math.abs(engine.vel.zoom) + Math.abs(engine.vel.panX) + Math.abs(engine.vel.panY);
    if (engine.machineState === 'RELEASING' || (engine.machineState === 'TRACKING' && mag > 0.0008)) {
      sph.tTheta -= engine.vel.theta;
      sph.tPhi   -= engine.vel.phi;
      sph.tPhi = clamp(sph.tPhi, 0.08, Math.PI - 0.08);
      sph.tRadius = clamp(sph.tRadius - engine.vel.zoom, 1.2, 22);
      sph.tTargetX -= engine.vel.panX;
      sph.tTargetY -= engine.vel.panY;
      sph.tTargetZ -= engine.vel.panZ;
      engine.vel.theta *= 0.88;
      engine.vel.phi   *= 0.88;
      engine.vel.zoom  *= 0.88;
      engine.vel.panX  *= 0.88;
      engine.vel.panY  *= 0.88;
      engine.vel.panZ  *= 0.88;
      engine.vel.roll  *= 0.88;
      if (engine.machineState === 'RELEASING') {
        engine.releaseFramesLeft -= 1;
        if (engine.releaseFramesLeft <= 0 || mag < 0.0008) {
          engine.machineState = engine.enabled ? 'TRACKING' : 'IDLE';
          engine.lockedGesture = null;
          zeroVel();
        }
      }
    }
    if (engine.enabled) {
      engine.inertiaRaf = requestAnimationFrame(tickInertia);
    }
  }

  function zeroVel() {
    engine.vel.theta = 0;
    engine.vel.phi = 0;
    engine.vel.zoom = 0;
    engine.vel.panX = 0;
    engine.vel.panY = 0;
    engine.vel.panZ = 0;
    engine.vel.roll = 0;
  }

  function canFireOneShot(name) {
    var now = Date.now();
    if (engine.oneShotFired[name] && now - engine.oneShotFired[name] < ONE_SHOT_COOLDOWN) {
      return false;
    }
    engine.oneShotFired[name] = now;
    return true;
  }

  function fireOneShot(name) {
    if (!canFireOneShot(name)) { return; }
    logGestureEvent(name);
    if (name === 'PART_CYCLE') { _partsCycleFocus(); }
    if (name === 'WIREFRAME' && typeof toggleWireframe === 'function') { toggleWireframe(); }
    if (name === 'SAVE' && typeof showSaveModal === 'function') { showSaveModal(); }
    if (name === 'FIT') { fitModelToView(); }
    if (name === 'RESET' && typeof resetCamera === 'function') { resetCamera(); }
    flashHudOneShot();
  }

  function fitModelToView() {
    if (!currentObject) {
      if (typeof resetCamera === 'function') { resetCamera(); }
      return;
    }
    var box = new THREE.Box3().setFromObject(currentObject);
    var size = box.getSize(new THREE.Vector3());
    var maxDim = Math.max(size.x, size.y, size.z);
    var center = box.getCenter(new THREE.Vector3());
    sph.tTargetX = center.x;
    sph.tTargetY = center.y;
    sph.tTargetZ = center.z;
    sph.tRadius = clamp(maxDim * 2.2, 2.5, 16);
    sph.tTheta = 0.55;
    sph.tPhi = 1.05;
    _partsClearFocus();
    if (typeof toast === 'function') { toast('Fit to model', 'ok'); }
  }

  function ensureRaycaster() {
    if (!engine.raycaster) {
      engine.raycaster = new THREE.Raycaster();
      engine.mouse2d = new THREE.Vector2();
    }
  }

  function inspectAtLandmark(lm) {
    if (!engine.settings.partControl || !currentObject || !camera) { return; }
    ensureRaycaster();
    var tip = lm[8];
    engine.mouse2d.x = (1 - tip.x) * 2 - 1;
    engine.mouse2d.y = -(tip.y * 2 - 1);
    engine.raycaster.setFromCamera(engine.mouse2d, camera);
    var hits = engine.raycaster.intersectObject(currentObject, true);
    if (!hits.length) {
      hideInspectTooltip();
      return;
    }
    var mesh = hits[0].object;
    var name = mesh.name || mesh.parent.name || 'Mesh';
    showInspectTooltip(name, tip.x, tip.y);
    mesh.traverseAncestors(function() {});
    if (mesh.userData && mesh.userData._baseMaterial) {
      PARTS.meshes.forEach(function(m, i) {
        if (m === mesh) { _partsFocus(i); }
      });
    }
  }

  function showInspectTooltip(text, nx, ny) {
    if (!engine.inspectTooltip) {
      engine.inspectTooltip = document.createElement('div');
      engine.inspectTooltip.className = 'ge-inspect-tip';
      var host = document.getElementById('studio-center');
      if (host) { host.appendChild(engine.inspectTooltip); }
    }
    var wrap = document.getElementById('studio-center');
    if (!wrap) { return; }
    engine.inspectTooltip.textContent = text;
    engine.inspectTooltip.style.left = ((1 - nx) * wrap.clientWidth - 8) + 'px';
    engine.inspectTooltip.style.top = (ny * wrap.clientHeight - 28) + 'px';
    engine.inspectTooltip.style.opacity = '1';
  }

  function hideInspectTooltip() {
    if (engine.inspectTooltip) { engine.inspectTooltip.style.opacity = '0'; }
  }

  function updateHud(gesture, confidence) {
    if (!engine.ui.hud) { ensureHud(); }
    var hud = engine.ui.hud;
    if (!hud || engine.machineState === 'CALIBRATING' || engine.machineState === 'IDLE') {
      if (hud) { hud.classList.remove('visible'); }
      return;
    }
    var meta = GESTURES[gesture] || { emoji: '✋', label: 'TRACKING', color: '#8899aa' };
    hud.classList.add('visible');
    hud.querySelector('.ge-hud-emoji').textContent = meta.emoji;
    hud.querySelector('.ge-hud-name').textContent = meta.label;
    hud.querySelector('.ge-hud-name').style.color = meta.color;
    hud.querySelector('.ge-hud-bar-fill').style.width = Math.round(confidence * 100) + '%';
    hud.querySelector('.ge-hud-bar-fill').style.background = meta.color;
  }

  function flashHudOneShot() {
    if (!engine.ui.hud) { return; }
    engine.ui.hud.classList.add('oneshot');
    setTimeout(function() { engine.ui.hud.classList.remove('oneshot'); }, 800);
  }

  function updatePanelStatus(gesture, confidence) {
    if (!engine.ui.panel) { return; }
    var strip = engine.ui.panel.querySelector('#ge-live-status');
    if (!strip) { return; }
    if (!gesture) {
      strip.innerHTML = '<span class="ge-dim">No hand detected</span>';
      return;
    }
    var meta = GESTURES[gesture] || { emoji: '✋', label: gesture };
    var pips = '';
    var filled = Math.round(confidence * 4);
    for (var i = 0; i < 4; i++) {
      pips += '<span class="ge-pip' + (i < filled ? ' on' : '') + '"></span>';
    }
    strip.innerHTML = '<span class="ge-live-emoji">' + meta.emoji + '</span>' +
      '<span class="ge-live-name" style="color:' + (meta.color || '#fff') + '">' + meta.label + '</span>' +
      '<span class="ge-pips">' + pips + '</span>';
  }

  function updateGestureLogUI() {
    if (!engine.ui.panel) { return; }
    var logEl = engine.ui.panel.querySelector('#ge-gesture-log');
    if (!logEl) { return; }
    logEl.innerHTML = engine.gestureLog.map(function(e) {
      var d = new Date(e.t);
      return '<div class="ge-log-line"><span>' + d.toLocaleTimeString() + '</span> ' + e.g + '</div>';
    }).join('');
  }

  function drawSkeleton(lm, gesture) {
    if (!engine.skeletonCtx || !engine.settings.showPreview) { return; }
    var ctx = engine.skeletonCtx;
    var w = engine.skeletonCanvas.width;
    var h = engine.skeletonCanvas.height;
    ctx.clearRect(0, 0, w, h);
    var col = (GESTURES[gesture] && GESTURES[gesture].color) || '#00d4ff';
    try {
      var conns = window.HAND_CONNECTIONS;
      if (typeof drawConnectors === 'function' && conns) {
        drawConnectors(ctx, lm, conns, { color: col, lineWidth: 3 });
      }
      if (typeof drawLandmarks === 'function') {
        drawLandmarks(ctx, lm, { color: '#ffffff', lineWidth: 1, radius: 3 });
      }
    } catch (eDraw) {}
    var pill = document.getElementById('ge-preview-pill');
    if (pill && gesture) {
      var meta = GESTURES[gesture];
      pill.textContent = meta ? meta.label : gesture;
      pill.style.color = meta ? meta.color : '#f0c040';
    }
  }

  function processSingleHand(lm, handedness) {
    var fingers = classifyFingers(lm);
    var cx = fingers.palmCenter.x;
    var cy = fingers.palmCenter.y;
    var cz = fingers.palmCenter.z;

    var dx = engine.lastTrack.x == null ? 0 : cx - engine.lastTrack.x;
    var dy = engine.lastTrack.y == null ? 0 : cy - engine.lastTrack.y;
    var dz = engine.lastTrack.z == null ? 0 : cz - engine.lastTrack.z;

    engine.waveHistory.push(dx);
    if (engine.waveHistory.length > 8) { engine.waveHistory.shift(); }
    var waveDetected = false;
    if (engine.waveHistory.length >= 4) {
      var rapid = 0;
      for (var wi = 1; wi < engine.waveHistory.length; wi++) {
        if (Math.abs(engine.waveHistory[wi]) > 0.04) { rapid += 1; }
      }
      waveDetected = rapid >= 3 && fingers.count >= 4;
    }

    var rollNow = Math.atan2(fingers.palmNormal.y, fingers.palmNormal.x);
    var rollDelta = engine.lastTrack.roll == null ? 0 : rollNow - engine.lastTrack.roll;
    if (rollDelta > Math.PI) { rollDelta -= Math.PI * 2; }
    if (rollDelta < -Math.PI) { rollDelta += Math.PI * 2; }

    var gesture = classifyGesture(lm, fingers, { waveDetected: waveDetected, rollDelta: rollDelta });
    pushBuffer(gesture);

    if (engine.machineState === 'CALIBRATING') {
      drawSkeleton(lm, 'ORBIT');
      var elapsed = Date.now() - engine.calStartedAt;
      if (fingers.count >= 2 || dist3(lm[0], lm[9]) > fingers.palmWidth * 0.5) {
        engine.calSamples.push(fingers.palmWidth);
      }
      var need = 5;
      var pct = Math.min(100, Math.round((engine.calSamples.length / need) * 100));
      updateCalOverlayProgress(pct, 'Hold steady… ' + engine.calSamples.length + '/' + need);
      if (engine.calSamples.length >= need && elapsed > 800) {
        finishCalibration();
      } else if (elapsed > 12000) {
        skipCalibration();
      }
      engine.lastTrack = { x: cx, y: cy, z: cz, pinch: null, roll: rollNow, spread: null };
      return;
    }

    var dom = dominantInBuffer();
    var conf = dom.count / BUFFER_SIZE;

    if (engine.machineState === 'TRACKING' || engine.machineState === 'IDLE') {
      if (dom.count >= LOCK_FRAMES) {
        if (!engine.lockedGesture) {
          engine.lockedGesture = dom.name;
          engine.machineState = 'LOCKED';
          logGestureEvent('lock:' + dom.name);
          var gMeta = GESTURES[dom.name];
          if (gMeta && !gMeta.continuous) { fireOneShot(dom.name); }
        }
      } else if (!engine.lockedGesture) {
        engine.machineState = 'TRACKING';
      }
    }

    if (engine.machineState === 'LOCKED') {
      if (bufferAgreement(engine.lockedGesture) < (LOCK_FRAMES / BUFFER_SIZE)) {
        engine.disagreeCount = (engine.disagreeCount || 0) + 1;
      } else {
        engine.disagreeCount = 0;
      }
      if ((engine.disagreeCount || 0) >= RELEASE_FRAMES) {
        engine.machineState = 'RELEASING';
        engine.releaseFramesLeft = RELEASE_INERTIA_FRAMES;
        engine.lockedGesture = null;
        engine.disagreeCount = 0;
      }
    }

    var active = engine.lockedGesture || dom.name;
    updateHud(active, conf);
    updatePanelStatus(active, conf);

    var pinchNorm = pinchDistance(lm, fingers.palmWidth);
    var sens = sensScale();

    /* Apply camera immediately while tracking (don't wait for full lock) */
    var moveGesture = active;
    if (engine.machineState === 'TRACKING' && dom.name) {
      moveGesture = dom.name;
    }

    if (moveGesture === 'ORBIT' || active === 'ORBIT') {
      applyOrbit(dx, dy);
    } else if (moveGesture === 'ZOOM' || active === 'ZOOM') {
      var dp = engine.lastTrack.pinch == null ? 0 : pinchNorm - engine.lastTrack.pinch;
      applyZoom(dp);
    } else if (moveGesture === 'PAN' || active === 'PAN') {
      applyPan(dx, dy, dz);
    } else if (moveGesture === 'ROLL_ORBIT' || active === 'ROLL_ORBIT') {
      applyOrbit(dx * 0.35, dy * 0.35);
      applyRoll(rollDelta);
    } else if (moveGesture === 'INSPECT' || active === 'INSPECT') {
      inspectAtLandmark(lm);
    } else if (moveGesture !== 'ORBIT') {
      hideInspectTooltip();
    }

    engine.lastTrack = {
      x: cx, y: cy, z: cz,
      pinch: pinchNorm,
      roll: rollNow,
      spread: spreadDistance(lm)
    };

    drawSkeleton(lm, active);
  }

  function classifyHandPose(lm) {
    var fingers = classifyFingers(lm);
    var pinchNorm = pinchDistance(lm, fingers.palmWidth);
    if (pinchNorm < 0.42 && fingers.thumb && fingers.index) { return 'ZOOM'; }
    if (fingers.count <= 1) { return 'PAN'; }
    if (fingers.count >= 4) { return 'ORBIT'; }
    if (fingers.index && !fingers.middle) { return 'INSPECT'; }
    return 'ORBIT';
  }

  function processTwoHands(a, b) {
    if (!engine.settings.twoHand) {
      processSingleHand(a);
      return;
    }
    var fa = classifyFingers(a);
    var fb = classifyFingers(b);
    var poseA = classifyHandPose(a);
    var poseB = classifyHandPose(b);
    var midX = (fa.palmCenter.x + fb.palmCenter.x) * 0.5;
    var midY = (fa.palmCenter.y + fb.palmCenter.y) * 0.5;
    var midZ = (fa.palmCenter.z + fb.palmCenter.z) * 0.5;

    if (poseA === 'ORBIT' && poseB === 'INSPECT') {
      processSingleHand(a);
      inspectAtLandmark(b);
      return;
    }

    if (poseA === 'PAN' && poseB === 'PAN') {
      var dx = engine.lastTrack.x == null ? 0 : midX - engine.lastTrack.x;
      var dy = engine.lastTrack.y == null ? 0 : midY - engine.lastTrack.y;
      var dz = engine.lastTrack.z == null ? 0 : midZ - engine.lastTrack.z;
      applyPan(dx, dy, dz);
      engine.machineState = 'LOCKED';
      engine.lockedGesture = 'PAN';
      updateHud('PAN', 1);
      engine.lastTrack = { x: midX, y: midY, z: midZ, pinch: null, roll: null, spread: null };
      drawSkeleton(a, 'PAN');
      return;
    }

    if (poseA === 'ZOOM' && poseB === 'ZOOM') {
      var pinchA = pinchDistance(a, fa.palmWidth);
      var pinchB = pinchDistance(b, fb.palmWidth);
      var handDist = dist3(fa.palmCenter, fb.palmCenter);
      var dp = engine.lastTrack.pinch == null ? 0 : handDist - engine.lastTrack.pinch;
      applyZoom(dp * 1.2);
      if (camera && camera.fov !== undefined) {
        camera.fov = clamp(45 + (sph.tRadius - 6) * 0.8, 38, 58);
        camera.updateProjectionMatrix();
      }
      engine.lockedGesture = 'ZOOM';
      updateHud('ZOOM', 1);
      engine.lastTrack = { x: midX, y: midY, z: midZ, pinch: handDist, roll: null, spread: null };
      return;
    }

    var dx2 = engine.lastTrack.x == null ? 0 : midX - engine.lastTrack.x;
    var dy2 = engine.lastTrack.y == null ? 0 : midY - engine.lastTrack.y;
    applyOrbit(dx2, dy2);

    var vecA = vecSub(a[9], a[0]);
    var vecB = vecSub(b[9], b[0]);
    var angA = Math.atan2(vecA.y, vecA.x);
    var angB = Math.atan2(vecB.y, vecB.x);
    var twist = angB - angA;
    if (twist > Math.PI) { twist -= Math.PI * 2; }
    if (twist < -Math.PI) { twist += Math.PI * 2; }
    if (engine.lastTrack.roll != null) {
      applyRoll((twist - engine.lastTrack.roll) * 0.5);
    }

    var dist = dist3(fa.palmCenter, fb.palmCenter);
    if (poseA !== 'ZOOM' && poseB !== 'ZOOM') {
      var dd = engine.lastTrack.pinch == null ? 0 : dist - engine.lastTrack.pinch;
      applyZoom(dd * 0.85);
    }

    engine.lockedGesture = 'ORBIT';
    updateHud('ORBIT', 0.85);
    engine.lastTrack = { x: midX, y: midY, z: midZ, pinch: dist, roll: twist, spread: null };
    drawSkeleton(a, 'ORBIT');
  }

  function onResults(res) {
    if (!engine.enabled) { return; }
    engine.fpsCounter.frames += 1;
    var now = performance.now();
    if (now - engine.fpsCounter.lastTs > 1000) {
      engine.fpsCounter.fps = engine.fpsCounter.frames;
      engine.fpsCounter.frames = 0;
      engine.fpsCounter.lastTs = now;
      var fpsEl = engine.ui.panel && engine.ui.panel.querySelector('#ge-fps');
      if (fpsEl) { fpsEl.textContent = engine.fpsCounter.fps + ' fps'; }
    }

    if (!res || !res.multiHandLandmarks || !res.multiHandLandmarks.length) {
      engine.lastTrack = { x: null, y: null, z: null, pinch: null, roll: null, spread: null };
      if (engine.machineState === 'CALIBRATING') {
        var el = Date.now() - engine.calStartedAt;
        updateCalOverlayProgress(0, el > 3000 ? 'Move hand closer to camera' : 'Show your open hand to the camera');
        if (el > 15000) { skipCalibration(); }
      } else if (engine.machineState !== 'RELEASING') {
        engine.machineState = engine.enabled ? 'TRACKING' : 'IDLE';
        engine.lockedGesture = null;
      }
      updateHud(null, 0);
      updatePanelStatus(engine.machineState === 'CALIBRATING' ? 'CALIBRATING' : null, 0);
      if (engine.ui.hud) {
        clearTimeout(engine.hudHideTimer);
        engine.hudHideTimer = setTimeout(function() {
          if (engine.ui.hud) { engine.ui.hud.classList.remove('visible'); }
        }, 2000);
      }
      return;
    }

    if (res.multiHandLandmarks.length >= 2) {
      processTwoHands(res.multiHandLandmarks[0], res.multiHandLandmarks[1]);
    } else {
      processSingleHand(res.multiHandLandmarks[0]);
    }
  }

  function loadCalibration() {
    try {
      var raw = localStorage.getItem('aurex_gesture_calibration');
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && parsed.palmWidth) {
          engine.calibration = parsed;
          engine.calibration.ready = true;
        }
      }
    } catch (e) {}
  }

  function ensureStyles() {
    if (document.getElementById('ge-styles')) { return; }
    var st = document.createElement('style');
    st.id = 'ge-styles';
    st.textContent = [
      '#gesture-hud{position:absolute;left:14px;bottom:72px;z-index:4;opacity:0;pointer-events:none;',
      'transition:opacity .2s ease,transform .2s ease;transform:translateY(8px);}',
      '#gesture-hud.visible{opacity:1;transform:translateY(0);}',
      '#gesture-hud.oneshot{filter:drop-shadow(0 0 12px rgba(74,222,128,.8));}',
      '.ge-hud-emoji{font-size:42px;line-height:1;margin-bottom:4px;}',
      '.ge-hud-name{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:2px;font-weight:600;}',
      '.ge-hud-bar{width:120px;height:3px;background:rgba(255,255,255,.08);border-radius:2px;margin-top:8px;overflow:hidden;}',
      '.ge-hud-bar-fill{height:100%;width:0%;transition:width .15s ease;}',
      '#ge-panel{position:absolute;left:12px;bottom:56px;width:280px;max-height:72vh;overflow:auto;',
      'background:rgba(10,14,23,.88);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);',
      'border:1px solid rgba(255,215,0,.15);border-radius:16px;padding:14px;z-index:5;display:none;',
      'box-shadow:0 16px 48px rgba(0,0,0,.55);animation:geSlideUp .28s ease;}',
      '#ge-panel.shown{display:block;}',
      '@keyframes geSlideUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}',
      '.ge-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}',
      '.ge-title{font-family:"JetBrains Mono",monospace;font-size:9px;letter-spacing:2px;color:rgba(240,192,64,.9);}',
      '.ge-cal-dot{width:8px;height:8px;border-radius:50%;background:#f59e0b;display:inline-block;margin-left:6px;}',
      '.ge-cal-dot.ready{background:#4ade80;}',
      '.ge-recalib{font-size:9px;color:var(--tx-3);cursor:pointer;margin-left:auto;margin-right:8px;}',
      '.ge-recalib:hover{color:var(--gold);}',
      '.ge-status-strip{background:rgba(255,255,255,.03);border-radius:8px;padding:8px 10px;margin-bottom:10px;',
      'display:flex;align-items:center;gap:8px;min-height:36px;}',
      '.ge-live-emoji{font-size:20px;}.ge-live-name{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:1px;}',
      '.ge-dim{font-size:10px;color:var(--tx-4);}.ge-pips{display:flex;gap:3px;margin-left:auto;}',
      '.ge-pip{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.12);}',
      '.ge-pip.on{background:var(--cyan);}',
      '.ge-gesture-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px;}',
      '.ge-gchip{border:1px solid rgba(255,255,255,.07);border-radius:8px;padding:6px 8px;font-size:9px;',
      'color:var(--tx-2);transition:border-color .15s,background .15s;}',
      '.ge-gchip:hover{border-color:rgba(0,212,255,.35);background:rgba(0,212,255,.05);}',
      '.ge-gchip b{display:block;font-size:11px;color:var(--tx-1);margin-bottom:2px;}',
      '.ge-settings{border-top:1px solid rgba(255,255,255,.06);padding-top:8px;}',
      '.ge-row{display:flex;align-items:center;justify-content:space-between;margin:6px 0;font-size:11px;color:var(--tx-2);}',
      '.ge-row input[type=range]{width:130px;}',
      '.ge-foot{font-size:9px;color:var(--tx-4);margin-top:8px;display:flex;justify-content:space-between;}',
      '.ge-log{margin-top:6px;max-height:60px;overflow:auto;}',
      '.ge-log-line{font-size:9px;color:var(--tx-3);padding:2px 0;}',
      '#ge-cal-overlay{position:absolute;inset:0;z-index:6;display:flex;align-items:center;justify-content:center;',
      'background:rgba(4,6,12,.72);backdrop-filter:blur(6px);flex-direction:column;gap:12px;}',
      '#ge-cal-overlay.hidden{display:none;}',
      '.ge-cal-icon{font-size:64px;animation:gePulse 1.2s ease infinite;}',
      '@keyframes gePulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}',
      '.ge-cal-txt{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--gold);letter-spacing:1px;text-align:center;max-width:90%;}',
      '.ge-cal-bar{width:200px;height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden;}',
      '.ge-cal-bar-fill{height:100%;width:0%;background:linear-gradient(90deg,#00d4ff,#f0c040);transition:width .15s;}',
      '.ge-cal-skip{margin-top:8px;padding:6px 14px;font-size:10px;font-family:"JetBrains Mono",monospace;',
      'background:transparent;border:1px solid rgba(255,215,0,.35);color:var(--gold);border-radius:6px;cursor:pointer;}',
      '.ge-cal-skip:hover{background:rgba(255,215,0,.1);}',
      '#ge-preview-wrap{position:absolute;right:12px;bottom:72px;z-index:10;border-radius:12px;overflow:hidden;',
      'border:1px solid rgba(255,255,255,.08);box-shadow:0 8px 24px rgba(0,0,0,.45);cursor:pointer;}',
      '#ge-preview-wrap.hidden{display:none;}',
      '#hand-video,#hand-skeleton-canvas{display:block;}',
      '.ge-preview-pill{position:absolute;top:-22px;left:0;right:0;text-align:center;font-size:9px;',
      'font-family:"JetBrains Mono",monospace;color:var(--gold);letter-spacing:1px;}',
      '.ge-inspect-tip{position:absolute;z-index:7;padding:4px 8px;border-radius:6px;font-size:10px;',
      'font-family:"JetBrains Mono",monospace;background:rgba(10,14,23,.92);border:1px solid rgba(192,132,252,.4);',
      'color:#e9d5ff;pointer-events:none;transition:opacity .15s;white-space:nowrap;}',
      '#hand-panel{display:none!important;}'
    ].join('');
    document.head.appendChild(st);
  }

  function ensureHud() {
    if (engine.ui.hud) { return; }
    var host = document.getElementById('studio-center');
    if (!host) { return; }
    var hud = document.createElement('div');
    hud.id = 'gesture-hud';
    hud.innerHTML = '<div class="ge-hud-emoji">✋</div><div class="ge-hud-name">TRACKING</div>' +
      '<div class="ge-hud-bar"><div class="ge-hud-bar-fill"></div></div>';
    host.appendChild(hud);
    engine.ui.hud = hud;
  }

  function ensureCalOverlay() {
    if (engine.ui.calOverlay) { return; }
    var host = document.getElementById('studio-center');
    if (!host) { return; }
    var ov = document.createElement('div');
    ov.id = 'ge-cal-overlay';
    ov.className = 'hidden';
    ov.innerHTML =
      '<div class="ge-cal-icon">✋</div>' +
      '<div class="ge-cal-txt">Show your open hand to the camera</div>' +
      '<div class="ge-cal-bar"><div class="ge-cal-bar-fill"></div></div>' +
      '<button type="button" class="ge-cal-skip">Skip calibration</button>';
    host.appendChild(ov);
    ov.querySelector('.ge-cal-skip').addEventListener('click', function() {
      skipCalibration();
    });
    engine.ui.calOverlay = ov;
  }

  function showCalOverlay() {
    ensureCalOverlay();
    engine.calSamples = [];
    engine.calStartedAt = Date.now();
    engine.machineState = 'CALIBRATING';
    engine.calibration.ready = false;
    if (engine.ui.calOverlay) {
      engine.ui.calOverlay.classList.remove('hidden');
      updateCalOverlayProgress(0, 'Show your open hand to the camera');
    }
    updateCalDot();
  }

  function updateCalOverlayProgress(pct, msg) {
    if (!engine.ui.calOverlay) { return; }
    var bar = engine.ui.calOverlay.querySelector('.ge-cal-bar-fill');
    var txt = engine.ui.calOverlay.querySelector('.ge-cal-txt');
    if (bar) { bar.style.width = Math.min(100, Math.max(0, pct)) + '%'; }
    if (txt && msg) { txt.textContent = msg; }
  }

  function finishCalibration() {
    if (!engine.calSamples.length) { return false; }
    engine.calSamples.sort(function(a, b) { return a - b; });
    engine.calibration.palmWidth = engine.calSamples[Math.floor(engine.calSamples.length / 2)];
    engine.calibration.ready = true;
    try {
      localStorage.setItem('aurex_gesture_calibration', JSON.stringify(engine.calibration));
    } catch (e) {}
    hideCalOverlay();
    engine.machineState = 'TRACKING';
    updateCalDot();
    if (typeof toast === 'function') { toast('Calibrated! Move your hand to control.', 'ok'); }
    return true;
  }

  function skipCalibration() {
    engine.calibration.palmWidth = engine.calibration.palmWidth || 0.14;
    engine.calibration.ready = true;
    hideCalOverlay();
    engine.machineState = 'TRACKING';
    updateCalDot();
    if (typeof toast === 'function') { toast('Hand control ready (default calibration)', 'ok'); }
  }

  function hideCalOverlay() {
    if (engine.ui.calOverlay) {
      engine.ui.calOverlay.classList.add('hidden');
      engine.ui.calOverlay.style.boxShadow = 'inset 0 0 60px rgba(74,222,128,.25)';
      setTimeout(function() {
        if (engine.ui.calOverlay) { engine.ui.calOverlay.style.boxShadow = ''; }
      }, 400);
    }
  }

  function buildGestureGrid() {
    var html = '';
    var keys = ['ORBIT', 'ZOOM', 'PAN', 'PART_CYCLE', 'INSPECT', 'WIREFRAME', 'SAVE', 'FIT', 'RESET', 'ROLL_ORBIT'];
    keys.forEach(function(k) {
      var g = GESTURES[k];
      var action = g.continuous ? 'Hold + move' : 'One-shot';
      html += '<div class="ge-gchip"><b>' + g.emoji + ' ' + g.label + '</b>' + action + '</div>';
    });
    return html;
  }

  function ensurePanel() {
    if (engine.ui.panel) { return engine.ui.panel; }
    ensureStyles();
    var wrap = document.getElementById('studio-center') || document.body;
    var p = document.createElement('div');
    p.id = 'ge-panel';
    p.innerHTML =
      '<div class="ge-head">' +
        '<span class="ge-title">✋ HAND CONTROL <span class="ge-cal-dot" id="ge-cal-dot"></span></span>' +
        '<span class="ge-recalib" id="ge-recalib">Recalibrate</span>' +
        '<button class="ctrl-btn" style="padding:3px 8px;font-size:9px" onclick="toggleHandControl()">OFF</button>' +
      '</div>' +
      '<div class="ge-status-strip" id="ge-live-status"><span class="ge-dim">No hand detected</span></div>' +
      '<div class="ge-gesture-grid">' + buildGestureGrid() + '</div>' +
      '<div class="ge-settings">' +
        '<div class="ge-row"><label>Sensitivity</label><input id="ge-sens" type="range" min="0.4" max="2.2" step="0.05" value="1.0"></div>' +
        '<div class="ge-row"><label>Inertia</label><input id="ge-inertia" type="checkbox" checked></div>' +
        '<div class="ge-row"><label>Camera preview</label><input id="ge-prev" type="checkbox" checked></div>' +
        '<div class="ge-row"><label>Two-hand mode</label><input id="ge-two" type="checkbox" checked></div>' +
        '<div class="ge-row"><label>Part gestures</label><input id="ge-parts" type="checkbox" checked></div>' +
        '<div class="ge-row"><label>Adaptive speed</label><input id="ge-adaptive" type="checkbox" checked></div>' +
      '</div>' +
      '<div class="ge-foot"><span id="ge-fps">-- fps</span><span>Gesture log ▼</span></div>' +
      '<div class="ge-log" id="ge-gesture-log"></div>';
    wrap.appendChild(p);
    engine.ui.panel = p;

    p.querySelector('#ge-sens').addEventListener('input', function(e) {
      engine.settings.sensitivity = parseFloat(e.target.value) || 1;
    });
    p.querySelector('#ge-inertia').addEventListener('change', function(e) {
      engine.settings.inertia = !!e.target.checked;
    });
    p.querySelector('#ge-prev').addEventListener('change', function(e) {
      engine.settings.showPreview = !!e.target.checked;
      syncPreviewVisibility();
    });
    p.querySelector('#ge-two').addEventListener('change', function(e) {
      engine.settings.twoHand = !!e.target.checked;
    });
    p.querySelector('#ge-parts').addEventListener('change', function(e) {
      engine.settings.partControl = !!e.target.checked;
      if (!e.target.checked) { _partsClearFocus(); }
    });
    p.querySelector('#ge-adaptive').addEventListener('change', function(e) {
      engine.settings.adaptiveSpeed = !!e.target.checked;
    });
    p.querySelector('#ge-recalib').addEventListener('click', function() {
      engine.calibration.ready = false;
      showCalOverlay();
    });

    updateCalDot();
    return p;
  }

  function updateCalDot() {
    var dot = document.getElementById('ge-cal-dot');
    if (dot) { dot.classList.toggle('ready', !!engine.calibration.ready); }
  }

  function ensurePreview() {
    if (engine.previewWrap) { return; }
    var host = document.getElementById('studio-center');
    if (!host) { return; }
    var wrap = document.createElement('div');
    wrap.id = 'ge-preview-wrap';
    wrap.innerHTML = '<div class="ge-preview-pill" id="ge-preview-pill">TRACKING</div>';
    var v = document.createElement('video');
    v.id = 'hand-video';
    v.playsInline = true;
    v.muted = true;
    v.autoplay = true;
    v.setAttribute('playsinline', '');
    v.style.transform = 'scaleX(-1)';
    v.style.objectFit = 'cover';
    var c = document.createElement('canvas');
    c.id = 'hand-skeleton-canvas';
    wrap.appendChild(v);
    wrap.appendChild(c);
    host.appendChild(wrap);
    engine.previewWrap = wrap;
    engine.video = v;
    engine.skeletonCanvas = c;
    engine.skeletonCtx = c.getContext('2d');
    setPreviewSize(false);
    wrap.addEventListener('click', function() {
      engine.previewExpanded = !engine.previewExpanded;
      setPreviewSize(engine.previewExpanded);
    });
    syncPreviewVisibility();
  }

  function setPreviewSize(big) {
    var w = big ? 400 : 200;
    var h = big ? 300 : 150;
    if (engine.video) {
      engine.video.style.width = w + 'px';
      engine.video.style.height = h + 'px';
    }
    if (engine.skeletonCanvas) {
      engine.skeletonCanvas.width = w;
      engine.skeletonCanvas.height = h;
      engine.skeletonCanvas.style.width = w + 'px';
      engine.skeletonCanvas.style.height = h + 'px';
      engine.skeletonCanvas.style.position = 'absolute';
      engine.skeletonCanvas.style.left = '0';
      engine.skeletonCanvas.style.top = '0';
      engine.skeletonCanvas.style.pointerEvents = 'none';
      engine.skeletonCanvas.style.transform = 'scaleX(-1)';
    }
  }

  function syncPreviewVisibility() {
    if (!engine.previewWrap) { return; }
    engine.previewWrap.classList.toggle('hidden', !engine.settings.showPreview);
  }

  function start() {
    try {
      ensureStyles();
      ensureHud();
      ensurePanel();
      ensurePreview();
      loadCalibration();
      var panel = ensurePanel();
      if (panel) { panel.classList.add('shown'); }

      if (!engine.calibration.ready) {
        showCalOverlay();
      } else {
        engine.machineState = 'TRACKING';
        hideCalOverlay();
      }

      engine.lastTrack = { x: null, y: null, z: null, pinch: null, roll: null, spread: null };
      engine.frameBuffer = [];
      zeroVel();

      var HandsCtor = window.Hands;
      var MpCamera = window.Camera;
      if (!HandsCtor || !MpCamera) {
        if (typeof toast === 'function') {
          toast('Hand control unavailable — reload the page (MediaPipe not loaded)', 'err');
        }
        return false;
      }

      if (engine.hands && engine.hands.close) {
        try { engine.hands.close(); } catch (eClose) {}
      }
      engine.hands = new HandsCtor({
        locateFile: function(file) {
          return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/' + file;
        }
      });
      engine.hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      engine.hands.onResults(onResults);

      var v = engine.video;
      if (!v) {
        if (typeof toast === 'function') { toast('Hand preview failed to initialize', 'err'); }
        return false;
      }

      v.play && v.play().catch(function() {});

      if (engine.cam && engine.cam.stop) {
        try { engine.cam.stop(); } catch (eStop) {}
      }
      engine.cam = new MpCamera(v, {
        onFrame: async function() {
          if (!engine.enabled || !engine.hands || !v) { return; }
          if (v.readyState < 2 || !v.videoWidth) { return; }
          try {
            await engine.hands.send({ image: v });
          } catch (eSend) {}
        },
        width: 640,
        height: 480
      });

      var started = engine.cam.start();
      if (started && typeof started.then === 'function') {
        started.catch(function(err) {
          if (typeof toast === 'function') {
            toast('Camera blocked: ' + (err.message || 'permission denied'), 'err');
          }
          engine.enabled = false;
          stop();
          syncHandButton();
        });
      }

      if (engine.inertiaRaf) { cancelAnimationFrame(engine.inertiaRaf); }
      engine.inertiaRaf = requestAnimationFrame(tickInertia);
      syncPreviewVisibility();
      return true;
    } catch (e) {
      if (typeof toast === 'function') { toast('Hand control error: ' + (e.message || e), 'err'); }
      return false;
    }
  }

  function stop() {
    try {
      if (engine.cam && engine.cam.stop) { engine.cam.stop(); }
    } catch (e1) {}
    engine.cam = null;
    try {
      if (engine.hands && engine.hands.close) { engine.hands.close(); }
    } catch (e2) {}
    engine.hands = null;
    if (engine.inertiaRaf) { cancelAnimationFrame(engine.inertiaRaf); }
    engine.inertiaRaf = null;
    engine.machineState = 'IDLE';
    engine.lockedGesture = null;
    zeroVel();
    hideInspectTooltip();
    if (engine.ui.panel) { engine.ui.panel.classList.remove('shown'); }
    if (engine.ui.hud) { engine.ui.hud.classList.remove('visible'); }
    if (engine.previewWrap) { engine.previewWrap.classList.add('hidden'); }
    try {
      if (engine.video && engine.video.srcObject) {
        var tracks = engine.video.srcObject.getTracks ? engine.video.srcObject.getTracks() : [];
        tracks.forEach(function(t) { try { t.stop(); } catch (e3) {} });
        engine.video.srcObject = null;
      }
    } catch (e4) {}
  }

  function syncHandButton() {
    var btn = document.getElementById('btn-hand');
    if (btn) {
      btn.classList.toggle('active', engine.enabled);
      btn.classList.toggle('hand', engine.enabled);
    }
  }

  function toggle() {
    engine.enabled = !engine.enabled;
    syncHandButton();
    if (engine.enabled) {
      if (typeof toast === 'function') { toast('Hand control: ON — allow camera access', 'info'); }
      if (!start()) {
        engine.enabled = false;
        syncHandButton();
      }
    } else {
      stop();
      if (typeof toast === 'function') { toast('Hand control: OFF', 'default'); }
    }
  }

  engine.toggle = toggle;
  engine.start = start;
  engine.stop = stop;
  engine.syncHandButton = syncHandButton;
  engine.skipCalibration = skipCalibration;

  return engine;
})();

var HAND = GestureEngine;
window.GestureEngine = GestureEngine;
window.HAND = HAND;

function toggleHandControl() {
  if (!window.GestureEngine || typeof GestureEngine.toggle !== 'function') {
    if (typeof toast === 'function') {
      toast('Hand control failed to load — refresh the page', 'err');
    }
    return;
  }
  GestureEngine.toggle();
}
function startHandControl() {
  if (!GestureEngine || typeof GestureEngine.start !== 'function') { return; }
  if (!GestureEngine.enabled) {
    GestureEngine.enabled = true;
    if (!GestureEngine.start()) { GestureEngine.enabled = false; }
    if (GestureEngine.syncHandButton) { GestureEngine.syncHandButton(); }
  }
}
function stopHandControl() {
  if (!GestureEngine || typeof GestureEngine.stop !== 'function') { return; }
  if (GestureEngine.enabled) {
    GestureEngine.enabled = false;
    GestureEngine.stop();
    if (GestureEngine.syncHandButton) { GestureEngine.syncHandButton(); }
  }
}
