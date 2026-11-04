const demo = "The FreshCheck platform uses Groq llama-3.3-70b-versatile for verification. The Groq API costs $0.59 per million tokens. Python version 3.12 is the latest release. The CEO of ExampleCloud is Alice Smith.";
const $ = (id) => document.getElementById(id);
const input = $('answer');
input.addEventListener('input', () => $('charCount').textContent = `${input.value.length.toLocaleString()} / 8,000 characters`);
$('loadDemo').onclick = () => { input.value = demo; input.dispatchEvent(new Event('input')); };
document.querySelectorAll('.nav').forEach(button => button.onclick = () => {
  document.querySelectorAll('.nav').forEach(item => item.classList.toggle('active', item === button));
  const page = button.dataset.page;
  $('title').textContent = page === 'Checker' ? 'Check an answer' : page === 'Graph / Timeline' ? 'Knowledge timeline' : 'Operations';
  $('checker').hidden = page !== 'Checker'; $('timeline').hidden = page !== 'Graph / Timeline'; $('ops').hidden = page !== 'Ops dashboard';
});
$('run').onclick = () => {
  const text = input.value.trim(); if (!text) { input.focus(); return; }
  const patterns = [/\$\s?\d[\d,.]*(?:\s*\/\s*\w+)?/g, /\b(?:version|v)\s?\d+(?:\.\d+){1,3}\b/gi, /\bCEO\s+(?:is|was)\s+[A-Z][\w .'-]+/g];
  const spans = [];
  patterns.forEach(pattern => { for (const match of text.matchAll(pattern)) { let start = Math.max(text.lastIndexOf('.', match.index), text.lastIndexOf('\n', match.index)) + 1; let end = text.indexOf('.', match.index + match[0].length); if (end < 0) end = text.length; spans.push({start, end, text:text.slice(start,end).trim()}); } });
  spans.sort((a,b)=>a.start-b.start);
  $('empty').hidden = true; const report = $('report'); report.hidden = false;
  const head = `<div class="panelHead"><div><span class="eyebrow">02 — FINDINGS</span><h3>Freshness report <span class="label">PREVIEW</span></h3></div><div class="summary"><b>${spans.length}</b><span>sample claims</span></div></div><div class="answerTabs"><button class="selected" id="originalTab">Original answer</button><button id="correctedTab">Corrected answer</button><span class="runTime">Preview only</span></div><div class="answerText" id="answerView"></div><div class="claimList" id="claimList"></div>`;
  report.innerHTML = head;
  const answerView = $('answerView');
  spans.forEach((span,index) => {const mark=document.createElement('mark');mark.className='unverifiable';mark.textContent=span.text;mark.onclick=()=>showClaim(span);answerView.append(mark);answerView.append(document.createTextNode(' '));});
  const list=$('claimList');spans.forEach((span,index)=>{const row=document.createElement('button');row.className='claimRow';row.innerHTML='<span class="dot unverifiable"></span><span class="claimCopy"><b>Sample claim '+(index+1)+'</b><small></small></span><strong>—</strong><span class="label">UNVERIFIABLE</span>';row.querySelector('small').textContent=span.text;row.onclick=()=>showClaim(span);list.append(row);});
  $('originalTab').onclick=()=>{answerView.textContent=text;};$('correctedTab').onclick=()=>{answerView.textContent='No corrections in preview. Live sources are required to suggest changes.';};
};
function showClaim(claim){$('detailTitle').textContent='Sample claim';$('detailText').textContent=claim.text;$('drawer').hidden=false;}
$('close').onclick=()=> $('drawer').hidden=true;
