/* RAD IDE animation presets for web pages (written next to the page by the Design View - do not edit, it is
   replaced). Starts the radfx.css animations of the elements with class "radfx": see radfx.css for the
   data-radfx-* attributes. From code:  radfx.play(el)  radfx.stop(el)  radfx.play('#id')  */
(function () {
  'use strict';
  var PRESETS = ['fadeIn', 'fadeOut', 'move', 'slideIn', 'slideOut', 'bounce', 'shake', 'pulse', 'rotate', 'flip',
                 'scaleIn', 'scaleOut', 'zoom', 'colorTo', 'typewriter'];
  var EASE = { linear: 'linear', 'in': 'ease-in', out: 'cubic-bezier(.25,.8,.35,1)', inout: 'ease-in-out',
               back: 'cubic-bezier(.34,1.56,.64,1)', elastic: 'cubic-bezier(.5,1.8,.5,.8)', bounce: 'ease-out',
               sine: 'cubic-bezier(.37,0,.63,1)' };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function q(x) { return typeof x === 'string' ? document.querySelector(x) : x; }
  function preset(el) {
    for (var i = 0; i < PRESETS.length; i++) if (el.classList.contains('radfx-' + PRESETS[i])) return PRESETS[i];
    return '';
  }
  function setup(el) {
    var d = el.dataset, s = el.style;
    if (d.radfxDuration) s.setProperty('--radfx-dur', parseInt(d.radfxDuration, 10) + 'ms');
    if (d.radfxDelay) s.setProperty('--radfx-delay', parseInt(d.radfxDelay, 10) + 'ms');
    if (d.radfxRepeat !== undefined) s.setProperty('--radfx-repeat', d.radfxRepeat === '0' ? 'infinite' : d.radfxRepeat);
    if (d.radfxReverse !== undefined && d.radfxReverse !== 'false') s.setProperty('--radfx-dir', 'alternate');
    if (d.radfxEase && EASE[d.radfxEase]) s.setProperty('--radfx-ease', EASE[d.radfxEase]);
    if (d.radfxColor) s.setProperty('--radfx-color', d.radfxColor);
    if (d.radfxScale) s.setProperty('--radfx-scale', d.radfxScale);
    if (d.radfxDistance) s.setProperty('--radfx-dist', parseInt(d.radfxDistance, 10) + 'px');
    if (d.radfxDx) s.setProperty('--radfx-dx', parseInt(d.radfxDx, 10) + 'px');
    if (d.radfxDy) s.setProperty('--radfx-dy', parseInt(d.radfxDy, 10) + 'px');
    if (preset(el) === 'typewriter') s.setProperty('--radfx-chars', String(Math.max(1, (el.textContent || '').length)));
  }
  function play(x) {
    var el = q(x);
    if (!el) return;
    el.classList.remove('radfx-wait');
    el.classList.remove('radfx-play');
    void el.offsetWidth;                         // restart the CSS animation
    el.classList.add('radfx-play');
  }
  function stop(x) { var el = q(x); if (el) el.classList.remove('radfx-play'); }

  function init() {
    var all = Array.prototype.slice.call(document.querySelectorAll('.radfx'));
    var byId = {};
    all.forEach(function (el) {
      setup(el);
      if (el.id) byId[el.id] = el;
      var trig = el.dataset.radfxTrigger || 'load';
      var p = preset(el);
      if (trig !== 'load' && /In$|typewriter/.test(p)) el.classList.add('radfx-wait');
      if (reduced && /In$|typewriter/.test(p)) el.classList.remove('radfx-wait');
    });
    all.forEach(function (el) {
      var d = el.dataset, trig = d.radfxTrigger || 'load';
      var src = d.radfxSource ? (byId[d.radfxSource] || document.getElementById(d.radfxSource)) : el;
      if (trig === 'load') play(el);
      else if (trig === 'click' && src) src.addEventListener('click', function () { play(el); });
      else if (trig === 'hover' && src) {
        src.addEventListener('mouseenter', function () { play(el); });
        src.addEventListener('mouseleave', function () { if (d.radfxLeave !== 'none') stop(el); });
      } else if (trig === 'timer') {
        var ms = parseInt(d.radfxInterval || '3000', 10);
        if (ms > 0) setInterval(function () { play(el); }, ms);
      } else if (trig === 'visible' && 'IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (es) {
          es.forEach(function (e) { if (e.isIntersecting) { play(el); io.unobserve(el); } });
        }, { threshold: 0.15 });
        io.observe(el);
      } else if (trig === 'visible') play(el);
      else if (trig === 'after' && d.radfxAfter) {
        var prev = byId[d.radfxAfter] || document.getElementById(d.radfxAfter);
        if (prev) prev.addEventListener('animationend', function (e) { if (e.target === prev) play(el); });
      }
    });
  }
  window.radfx = { play: play, stop: stop, init: init, presets: PRESETS };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
