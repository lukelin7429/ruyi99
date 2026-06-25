// 如意精舍 — interactions: mobile nav, scroll reveal, inline video lightbox
(function(){
  // mobile nav
  var hamb=document.querySelector('.hamb'), nav=document.querySelector('.nav');
  if(hamb&&nav){hamb.addEventListener('click',function(){nav.classList.toggle('show');});}

  // scroll reveal (getBoundingClientRect — robust in preview frames)
  var els=[].slice.call(document.querySelectorAll('.rvl'));
  function reveal(){
    var h=window.innerHeight||document.documentElement.clientHeight;
    for(var i=els.length-1;i>=0;i--){
      var el=els[i];
      if(el.getBoundingClientRect().top < h-60){el.classList.add('in');els.splice(i,1);}
    }
  }
  reveal();
  window.addEventListener('scroll',reveal,{passive:true});
  window.addEventListener('resize',reveal);

  // inline video lightbox (never pop out to YouTube)
  var lb=document.getElementById('lb'), lbBox=document.getElementById('lb-box');
  function openLb(id){
    if(!lb)return;
    lb.classList.remove('audio');
    lbBox.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&rel=0" allow="autoplay; encrypted-media; fullscreen" allowfullscreen></iframe>';
    lb.classList.add('open');document.body.style.overflow='hidden';
  }
  function openDrive(id){
    if(!lb)return;
    lb.classList.add('audio');
    lbBox.innerHTML='<iframe src="https://drive.google.com/file/d/'+id+'/preview" allow="autoplay"></iframe>';
    lb.classList.add('open');document.body.style.overflow='hidden';
  }
  function closeLb(){
    if(!lb)return;lb.classList.remove('open');lbBox.innerHTML='';document.body.style.overflow='';
  }
  document.addEventListener('click',function(e){
    var t=e.target.closest('[data-yt]');
    if(t){e.preventDefault();openLb(t.getAttribute('data-yt'));}
    var d=e.target.closest('[data-drive]');
    if(d){e.preventDefault();openDrive(d.getAttribute('data-drive'));}
    if(e.target.closest('#lb-close')||e.target.id==='lb'){closeLb();}
  });
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeLb();});

  // photo carousels (supports multiple on a page)
  document.querySelectorAll('.carousel').forEach(function(car){
    var slides=car.querySelectorAll('.slide'),dots=car.querySelectorAll('.dot'),cur=0,timer;
    function go(i){
      cur=(i+slides.length)%slides.length;
      slides.forEach(function(s,k){s.classList.toggle('on',k===cur);});
      dots.forEach(function(d,k){d.classList.toggle('on',k===cur);});
    }
    function start(){timer=setInterval(function(){go(cur+1);},5000);}
    function reset(){clearInterval(timer);start();}
    car.querySelectorAll('.car-nav').forEach(function(b){
      b.addEventListener('click',function(){go(cur+parseInt(b.getAttribute('data-d'),10));reset();});
    });
    dots.forEach(function(d){d.addEventListener('click',function(){go(parseInt(d.getAttribute('data-i'),10));reset();});});
    if(slides.length>1)start();
  });
})();
