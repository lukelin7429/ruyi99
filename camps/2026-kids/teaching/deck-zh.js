/* 中文單語投影片引擎（需先在頁面定義 const NOTES=[["主講人","口白"], ...]） */
const slides=[...document.querySelectorAll('.slide')];
const bar=document.getElementById('bar'),count=document.getElementById('count');
const notesBox=document.getElementById('notes'),notesBody=notesBox.querySelector('.body'),notesWho=notesBox.querySelector('.who');
let i=0,notesOn=false;
function show(n){slides[i].classList.remove('active');i=Math.max(0,Math.min(slides.length-1,n));
  slides[i].classList.add('active');bar.style.width=((i+1)/slides.length*100)+'%';
  count.textContent=(i+1)+' / '+slides.length;if(notesOn)renderNotes();}
function renderNotes(){const n=NOTES[i]||['','（本頁無口白）'];notesWho.textContent=n[0];notesBody.textContent=n[1];}
function next(){show(i+1)}function prev(){show(i-1)}
function toggleNotes(){notesOn=!notesOn;notesBox.classList.toggle('on',notesOn);if(notesOn)renderNotes();}
document.addEventListener('keydown',e=>{
 if(['ArrowRight','ArrowDown',' ','PageDown'].includes(e.key)){e.preventDefault();next();}
 else if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();prev();}
 else if(e.key==='Home')show(0);else if(e.key==='End')show(slides.length-1);
 else if(e.key.toLowerCase()==='f'){if(!document.fullscreenElement)document.documentElement.requestFullscreen();else document.exitFullscreen();}
 else if(e.key.toLowerCase()==='n')toggleNotes();});
document.getElementById('nextZ').onclick=next;document.getElementById('prevZ').onclick=prev;
count.textContent='1 / '+slides.length;
bar.style.width=(1/slides.length*100)+'%';
