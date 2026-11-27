// Videos marked data-autoplay play (muted) only while on screen, so the page loads fast.
// A .sound-toggle button next to a video turns its sound on/off (only one video plays sound at a time).
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var videos = Array.prototype.slice.call(document.querySelectorAll('video[data-autoplay]'));

  function play(v) {
    v.preload = 'auto';
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  }

  if (!reduce) {
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) play(e.target);
          else e.target.pause();
        });
      }, { rootMargin: '200px 0px', threshold: 0.01 });
      videos.forEach(function (v) { io.observe(v); });
    } else {
      videos.forEach(play);
    }
  }

  function setSound(box, on) {
    var v = box.querySelector('video');
    var btn = box.querySelector('.sound-toggle');
    v.muted = !on;
    box.classList.toggle('sound-on', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', on ? 'Turn sound off' : 'Turn sound on');
    if (on) play(v);
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
