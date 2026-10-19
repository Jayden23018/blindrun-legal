// 助盲跑官网脚本。只做两件事（SPEC §7）：
// ① 浏览器不支持 CSS 滚动动画时，用 IntersectionObserver 让区块进入视口时淡入一次；
// ② 点「复制」把邮箱复制到剪贴板。
// 这个文件加载失败时两件事都不发生，页面内容不受影响。
(function () {
  'use strict';

  var supportsScrollAnimation = window.CSS && CSS.supports && CSS.supports('animation-timeline: view()');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!supportsScrollAnimation && !reduceMotion && 'IntersectionObserver' in window) {
    // 已经在首屏里的区块先标成可见，再加 js-reveal：两步在同一帧里完成，首屏不会先出现再闪没
    document.querySelectorAll('.reveal').forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('is-visible');
    });
    document.documentElement.classList.add('js-reveal');
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px' });
    document.querySelectorAll('.reveal:not(.is-visible)').forEach(function (el) { observer.observe(el); });
  }

  var status = document.getElementById('copy-status');
  function announce(text) {
    if (!status) return;
    // 先清空再写：连点两次时读屏软件也会再播报一次
    status.textContent = '';
    window.setTimeout(function () { status.textContent = text; }, 50);
  }
  document.querySelectorAll('[data-copy]').forEach(function (button) {
    // 按钮在 HTML 里默认 hidden：JS 没跑起来时不留一个点了没反应的按钮
    if (!navigator.clipboard) return;
    button.hidden = false;
    button.addEventListener('click', function () {
      navigator.clipboard.writeText(button.getAttribute('data-copy')).then(function () {
        announce('已复制');
      }, function () {
        announce('复制失败，请长按邮箱地址手动复制');
      });
    });
  });
})();
