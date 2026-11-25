const search=document.getElementById('search');
if(search) search.addEventListener('input',()=>{const q=search.value.toLowerCase();document.querySelectorAll('.movie-card').forEach(card=>{card.style.display=card.dataset.title.includes(q)?'':'none';});});
