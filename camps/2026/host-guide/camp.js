/* 捲動揭示引擎 — 用 getBoundingClientRect（非 IntersectionObserver，超高網格/preview 才可靠） */
(function(){
  document.documentElement.classList.add('mtn');
  var els;
  function collect(){ els = Array.prototype.slice.call(document.querySelectorAll('.rvl')); }
  function tick(){
    if(!els) return;
    var vh = window.innerHeight || document.documentElement.clientHeight;
    for(var i=els.length-1;i>=0;i--){
      var el=els[i], r=el.getBoundingClientRect();
      if(r.top < vh*0.9 && r.bottom > 0){ el.classList.add('in'); els.splice(i,1); }
    }
  }
  function boot(){ collect(); tick(); }
  if(document.readyState!=='loading') boot();
  else document.addEventListener('DOMContentLoaded', boot);
  window.addEventListener('scroll', tick, {passive:true});
  window.addEventListener('resize', tick, {passive:true});
  // 交錯進場
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-stagger]').forEach(function(group){
      Array.prototype.slice.call(group.children).forEach(function(ch,i){
        if(ch.classList.contains('rvl')) ch.style.transitionDelay=(i*0.06)+'s';
      });
    });
    // 揭示後清除 delay，避免拖慢 hover
    setTimeout(function(){
      document.querySelectorAll('[data-stagger] .rvl').forEach(function(ch){ ch.style.transitionDelay=''; });
    },1600);
  });
})();
