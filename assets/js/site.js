// 如意精舍 — interactions: mobile nav, scroll reveal, inline video lightbox
(function(){
  // mobile nav
  var hamb=document.querySelector('.hamb'), nav=document.querySelector('.nav');
  if(hamb&&nav){hamb.addEventListener('click',function(){nav.classList.toggle('show');});}

  // site-wide motion: make EVERY list/grid cascade its items in (not pop as one block).
  // Runs before the reveal collector so the existing engine animates the promoted children.
  var STAGGER='.cards,.chaplist,.video-grid,.feat-grid,.es-grid,.es-learn,.gallery,'+
              '.m-gallery,.audlist,.tiers,.obj2,.vidwall,.timeline';
  [].slice.call(document.querySelectorAll(STAGGER)).forEach(function(g){
    g.classList.remove('rvl'); g.classList.add('in');   // container visible; its children animate
    var n=0;
    [].slice.call(g.children).slice(0,24).forEach(function(ch){  // cap for long lists (perf)
      if(ch.nodeType!==1) return;
      ch.classList.add('rvl');
      if(!ch.style.transitionDelay) ch.style.transitionDelay=Math.min(n*55,400)+'ms';
      n++;
    });
  });

  // 今日一句 — pick a quote by today's date (same for everyone that day; auto-rotates)
  var dd=document.getElementById('daily-data');
  if(dd){
    try{
      var qs=JSON.parse(dd.textContent);
      if(qs.length){
        var now=new Date(), start=new Date(now.getFullYear(),0,0);
        var day=Math.floor((now-start)/86400000);
        var pick=qs[((day%qs.length)+qs.length)%qs.length];
        var qe=document.getElementById('daily-q'), pe=document.getElementById('daily-plain'), se=document.getElementById('daily-src');
        if(qe)qe.textContent=pick.q;
        if(pe)pe.textContent=pick.plain;
        if(se)se.textContent='——《'+pick.src+'》';
      }
    }catch(e){}
  }

  // 每日一題 — daily quiz question, same for everyone that day; no name, instant feedback.
  // Pool = hand-written general-knowledge bank + auto-generated "guess the sutra" questions from the daily-quote data.
  var dqRoot=document.getElementById('dq');
  if(dqRoot){
    try{
      var escDq=function(s){ return String(s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];}); };
      var bankEl=document.getElementById('dq-bank');
      var bank=bankEl?JSON.parse(bankEl.textContent):[];
      var quotesEl=document.getElementById('daily-data');
      var quotes=quotesEl?JSON.parse(quotesEl.textContent):[];
      var srcSet=[];
      quotes.forEach(function(qt){ if(srcSet.indexOf(qt.src)===-1) srcSet.push(qt.src); });
      var now2=new Date(), start2=new Date(now2.getFullYear(),0,0);
      var day2=Math.floor((now2-start2)/86400000);
      function seededShuffle(arr,seed){
        var a=arr.slice();
        for(var k=a.length-1;k>0;k--){
          seed=(seed*9301+49297)%233280;
          var j=Math.floor((seed/233280)*(k+1));
          var t=a[k]; a[k]=a[j]; a[j]=t;
        }
        return a;
      }
      var quoteQs=quotes.map(function(qt,i){
        var distractors=srcSet.filter(function(s){ return s!==qt.src; });
        var seed=day2*97+i*7+1;
        var picks=seededShuffle(distractors,seed).slice(0,3);
        var options=seededShuffle(picks.concat([qt.src]),seed+1);
        return { type:"choice", q:"以下經文出自哪一部經論？「"+qt.q+"」", options:options, answer:options.indexOf(qt.src), explain:qt.plain, source:"每日一句．"+qt.src };
      });
      var pool=bank.concat(quoteQs);
      if(pool.length){
        var dqPick=pool[((day2%pool.length)+pool.length)%pool.length];
        var LETTERS=["A","B","C","D","E","F"];
        var qEl=document.getElementById('dq-q'), cEl=document.getElementById('dq-choices'), fEl=document.getElementById('dq-feedback');
        if(qEl) qEl.textContent=dqPick.q;
        if(cEl){
          cEl.innerHTML='';
          var opts = dqPick.type==="tf" ? ["是","否"] : dqPick.options;
          var correctIdx = dqPick.type==="tf" ? (dqPick.answer ? 0 : 1) : dqPick.answer;
          opts.forEach(function(opt,i){
            var b=document.createElement('button');
            b.className='dq-choice';
            b.innerHTML='<span class="dq-letter">'+LETTERS[i]+'</span><span>'+escDq(opt)+'</span>';
            b.addEventListener('click',function(){
              if(cEl.getAttribute('data-locked')) return;
              cEl.setAttribute('data-locked','1');
              var isCorrect=(i===correctIdx);
              b.classList.add(isCorrect?'good':'bad');
              if(!isCorrect) cEl.children[correctIdx].classList.add('good');
              [].slice.call(cEl.children).forEach(function(x){ x.disabled=true; });
              if(fEl){
                fEl.style.display='block';
                fEl.innerHTML=(isCorrect?'✅ 答對了。':'❌ 再想想。')+' '+escDq(dqPick.explain||'')+(dqPick.source?'（出自：'+escDq(dqPick.source)+'）':'');
              }
            });
            cEl.appendChild(b);
          });
        }
      }
    }catch(e){}
  }

  // scroll reveal (getBoundingClientRect — robust in preview frames)
  var els=[].slice.call(document.querySelectorAll('.rvl'));
  function reveal(){
    var h=window.innerHeight||document.documentElement.clientHeight;
    for(var i=els.length-1;i>=0;i--){
      var el=els[i];
      if(el.getBoundingClientRect().top < h-60){
        el.classList.add('in');
        // clear the stagger delay once revealed, so hover transitions are immediate (no lag)
        (function(e){setTimeout(function(){e.style.transitionDelay='';},1100);})(el);
        els.splice(i,1);
      }
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
  // native <audio> against a direct file URL (R2-hosted audio) — no third-party
  // preview iframe involved, plays reliably on iOS Safari
  function openAudioSrc(url){
    if(!lb)return;
    lb.classList.add('audio');lb.classList.add('audio-native');
    lbBox.innerHTML='<audio controls autoplay preload="metadata" style="width:100%" src="'+url+'"></audio>';
    lb.classList.add('open');document.body.style.overflow='hidden';
  }
  function closeLb(){
    if(!lb)return;lb.classList.remove('open','audio-native');lbBox.innerHTML='';document.body.style.overflow='';
  }
  document.addEventListener('click',function(e){
    var t=e.target.closest('[data-yt]');
    if(t){e.preventDefault();openLb(t.getAttribute('data-yt'));}
    var s=e.target.closest('[data-audio-src]');
    if(s){e.preventDefault();openAudioSrc(s.getAttribute('data-audio-src'));}
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
