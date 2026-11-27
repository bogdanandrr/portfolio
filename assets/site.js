// Homepage tiles (video[data-tile]): nothing but the poster is downloaded until a tile is really on screen.
// Then its clip loads and plays; at most MAX_PLAYING play at once (the ones closest to the middle of the
// screen), the rest pause. With "reduce motion" on, the tiles stay on their posters.
//
// Project pages (video[data-autoplay]) play muted while on screen; a .sound-toggle button turns the sound
// of its video on/off (only one video plays sound at a time).
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var MAX_PLAYING = 2;
  var ON_SCREEN = 0.5;   // share of a tile that must be visible (a tile peeking in under the hero doesn't count)

  function play(v) {
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  }

  // ---- homepage tiles
  var tiles = Array.prototype.slice.call(document.querySelectorAll('video[data-tile]'));

  function load(v) {
    if (v.getAttribute('data-loaded')) return;
    v.setAttribute('data-loaded', '1');
    Array.prototype.forEach.call(v.querySelectorAll('source[data-src]'), function (s) {
      s.src = s.getAttribute('data-src');
    });
    v.preload = 'auto';
    v.load();
  }

  if (tiles.length && !reduce && 'IntersectionObserver' in window) {
    var visible = [];
    var queued = false;

    var update = function () {
      queued = false;
      var mid = window.innerHeight / 2;
      var chosen = visible
        .map(function (v) {
          var r = v.getBoundingClientRect();
          return { v: v, d: Math.abs(r.top + r.height / 2 - mid) };
        })
        .sort(function (a, b) { return a.d - b.d; })
        .slice(0, MAX_PLAYING)
        .map(function (x) { return x.v; });
      tiles.forEach(function (v) {
        if (chosen.indexOf(v) !== -1) {
          load(v);
          if (v.paused) play(v);
        } else if (!v.paused) {
          v.pause();
        }
      });
    };
    var schedule = function () {
      if (!queued) { queued = true; requestAnimationFrame(update); }
    };

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var i = visible.indexOf(e.target);
        var on = e.isIntersecting && e.intersectionRatio >= ON_SCREEN - 0.001;
        if (on && i === -1) visible.push(e.target);
        if (!on && i !== -1) visible.splice(i, 1);
      });
      schedule();
    }, { threshold: [0, ON_SCREEN, 0.6, 1] });
    tiles.forEach(function (v) { io.observe(v); });

    // which tiles are closest to the middle changes while scrolling (only matters with more than MAX_PLAYING on screen)
    window.addEventListener('scroll', function () {
      if (visible.length > MAX_PLAYING) schedule();
    }, { passive: true });
    window.addEventListener('resize', schedule);
  }

  // ---- project pages
  var videos = Array.prototype.slice.call(document.querySelectorAll('video[data-autoplay]'));

  if (!reduce) {
    if ('IntersectionObserver' in window) {
      var io2 = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { e.target.preload = 'auto'; play(e.target); }
          else e.target.pause();
        });
      }, { rootMargin: '200px 0px', threshold: 0.01 });
      videos.forEach(function (v) { io2.observe(v); });
    } else {
      videos.forEach(function (v) { v.preload = 'auto'; play(v); });
    }
  }

  function setSound(box, on) {
    var v = box.querySelector('video');
    var btn = box.querySelector('.sound-toggle');
    v.muted = !on;
    box.classList.toggle('sound-on', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', on ? 'Turn sound off' : 'Turn sound on');
    if (on) { v.preload = 'auto'; play(v); }
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.sound-toggle');
    if (!btn) return;
    var box = btn.closest('.is-video');
    var turnOn = !box.classList.contains('sound-on');
    if (turnOn) {
      document.querySelectorAll('.is-video.sound-on').forEach(function (other) {
        if (other !== box) setSound(other, false);
      });
    }
    setSound(box, turnOn);
  });
})();
