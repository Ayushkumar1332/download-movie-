const form=document.getElementById('uploadForm');
form.addEventListener('submit',async e=>{
 e.preventDefault(); const file=document.getElementById('videoFile').files[0]; if(!file)return;
 const status=document.getElementById('status'),bar=document.getElementById('progressBar'); const chunkSize=10*1024*1024; const count=Math.ceil(file.size/chunkSize);
 if(file.size>5*1024*1024*1024){status.textContent='File exceeds 5GB limit.';return;}
 const title=document.getElementById('title').value.trim()||file.name.replace(/\.[^/.]+$/,'');
 try{
 status.textContent='Preparing upload...';
 const start=await fetch('/api/upload/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:file.name,size:file.size,title,description:document.getElementById('description').value,category:document.getElementById('category').value,year:document.getElementById('year').value,language:document.getElementById('language').value,chunk_count:count})});
 const data=await start.json(); if(!start.ok)throw new Error(data.error||'Could not start upload');
 for(let i=0;i<count;i++){
  const chunk=file.slice(i*chunkSize,Math.min(file.size,(i+1)*chunkSize));const fd=new FormData();fd.append('chunk',chunk,'chunk.part');
  const res=await fetch(`/api/upload/chunk/${data.upload_id}/${i}`,{method:'POST',body:fd});const r=await res.json();if(!res.ok)throw new Error(r.error||`Chunk ${i+1} failed`);
  const pct=Math.round((i+1)/count*100);bar.style.width=pct+'%';status.textContent=`Uploading ${pct}% (${i+1}/${count} chunks)`;
 }
 status.textContent='Finishing upload...';const finish=new FormData();const poster=document.getElementById('poster').files[0];if(poster)finish.append('poster',poster);
 const res=await fetch(`/api/upload/finish/${data.upload_id}`,{method:'POST',body:finish});const out=await res.json();if(!res.ok)throw new Error(out.error||'Could not finish upload');status.textContent='Upload complete! Refreshing...';location.reload();
 }catch(err){status.textContent='Upload failed: '+err.message;}
});
