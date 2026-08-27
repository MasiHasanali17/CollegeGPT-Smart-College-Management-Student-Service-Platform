// static/js/main.js
document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const askBtn = document.getElementById('ask-floating-btn');
  const modal = document.getElementById('chat-modal');
  const closeBtn = document.getElementById('chat-close');
  const clearBtn = document.getElementById('chat-clear');
  const chatInput = document.getElementById('chat-input');
  const chatBody = document.getElementById('chat-body');
  const sendBtn = document.getElementById('chat-send');

  // safety check in case elements are not on page
  function el(id){ return document.getElementById(id); }

  // Open / close modal
  if(askBtn) askBtn.addEventListener('click', () => modal.classList.remove('hidden'));
  if(closeBtn) closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
  if(clearBtn) clearBtn.addEventListener('click', () => {
    chatBody.innerHTML = '<div class="bot-msg">👋 Hi — I am Campus Genius. Ask anything about Parul University.</div>';
  });

  // Helpers to append messages
  function appendUser(text, target = chatBody){
    const d = document.createElement('div');
    d.className = 'user-msg';
    d.textContent = text;
    target.appendChild(d);
    target.scrollTop = target.scrollHeight;
  }
  function appendBot(html, target = chatBody){
    const d = document.createElement('div');
    d.className = 'bot-msg';
    d.innerHTML = html;
    target.appendChild(d);
    target.scrollTop = target.scrollHeight;
  }

  // send query to backend /ask
  async function sendQuery(q, targetBody = chatBody){
    if(!q || q.trim() === '') return;
    appendUser(q, targetBody);
    appendBot('Thinking...', targetBody);

    try{
      const res = await fetch('/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: q})
      });
      const data = await res.json();
      // replace last bot "Thinking..." text
      const bots = targetBody.querySelectorAll('.bot-msg');
      if(bots.length) bots[bots.length - 1].innerHTML = data.answer;
      else appendBot(data.answer, targetBody);
    }catch(e){
      const bots = targetBody.querySelectorAll('.bot-msg');
      if(bots.length) bots[bots.length - 1].innerHTML = 'Server error — try again later.';
    }
  }

  // small modal send
  if(sendBtn){
    sendBtn.addEventListener('click', () => {
      const q = chatInput.value.trim();
      if(!q) return;
      sendQuery(q, chatBody);
      chatInput.value = '';
    });
    chatInput.addEventListener('keydown', (e) => {
      if(e.key === 'Enter') sendBtn.click();
    });
  }

  // Large chat on chatbot page (if present)
  const bigInput = el('chat-input-large');
  const bigSend = el('chat-send-large');
  const bigBody = el('chat-body-large');

  if(bigSend && bigInput && bigBody){
    bigSend.addEventListener('click', async () => {
      const q = bigInput.value.trim(); if(!q) return;
      // append user
      const u = document.createElement('div'); u.className='user-msg'; u.textContent=q; bigBody.appendChild(u);
      const b = document.createElement('div'); b.className='bot-msg'; b.textContent='Thinking...'; bigBody.appendChild(b);
      bigBody.scrollTop = bigBody.scrollHeight;
      bigInput.value='';
      try{
        const res = await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
        const data = await res.json();
        b.innerHTML = data.answer;
      }catch(e){
        b.innerHTML = 'Server error — try again later.';
      }
    });
    bigInput.addEventListener('keydown', (e) => { if(e.key === 'Enter') bigSend.click(); });

    // quick chip buttons (if any)
    document.querySelectorAll('.chip').forEach(ch => {
      ch.addEventListener('click', () => {
        bigInput.value = ch.dataset.q || ch.textContent;
        bigSend.click();
      });
    });
  }

  // LOAD courses JSON into courses page and populate compare selects
  (async function loadCourses(){
    try{
      const resp = await fetch('/static/data/college_data.json');
      if(!resp.ok) return;
      const data = await resp.json();
      const courses = data.courses || [];
      // populate courses grid if exists
      const grid = el('courses-grid');
      if(grid){
        grid.innerHTML = '';
        courses.forEach((c, idx) => {
          const card = document.createElement('div'); card.className='course-card';
          const fee = c.fees_per_year || 'N/A';
          card.innerHTML = `
            <img src="${c.image || 'https://images.unsplash.com/photo-1525909002-1e2b39b3b4c5?auto=format&fit=crop&w=1000&q=60'}" alt="${c.course_name}">
            <h3>${c.course_name}</h3>
            <p class="muted">${c.duration} • ₹${fee}/yr</p>
            <div style="margin-top:12px"><button class="btn-ghost" onclick="location.href='/chatbot'">Ask AI</button> <button class="btn-primary" onclick="location.href='/compare'">Compare</button></div>`;
          grid.appendChild(card);
        });
      }
      // populate compare selects
      const selA = el('course-a'), selB = el('course-b');
      if(selA && selB){
        selA.innerHTML = '<option value="">Select Course</option>';
        selB.innerHTML = '<option value="">Select Course</option>';
        courses.forEach((c, i) => {
          const opt = `<option value="${i}">${c.course_name}</option>`;
          selA.insertAdjacentHTML('beforeend', opt);
          selB.insertAdjacentHTML('beforeend', opt);
        });
      }

      // hook compare button if present
      const compareBtn = el('compare-btn');
      if(compareBtn){
        compareBtn.addEventListener('click', () => {
          const a = selA.value, b = selB.value;
          if(!a || !b){ alert('Select two courses to compare.'); return; }
          if(a === b){ alert('Pick two different courses.'); return; }
          const ca = courses[parseInt(a)], cb = courses[parseInt(b)];
          const out = el('compare-result');
          if(!out) return;
          out.innerHTML = `
            <table class="compare-table" style="width:100%;border-collapse:collapse;color:#dbeafe">
              <tr style="border-bottom:1px solid rgba(255,255,255,0.04)"><th style="text-align:left;padding:8px">Feature</th><th style="padding:8px">${ca.course_name}</th><th style="padding:8px">${cb.course_name}</th></tr>
              <tr><td style="padding:8px">Duration</td><td style="padding:8px">${ca.duration}</td><td style="padding:8px">${cb.duration}</td></tr>
              <tr style="background:rgba(255,255,255,0.01)"><td style="padding:8px">Fees / year</td><td style="padding:8px">₹${ca.fees_per_year}</td><td style="padding:8px">₹${cb.fees_per_year}</td></tr>
              <tr><td style="padding:8px">Career</td><td style="padding:8px">${ca.course_name.includes('Computer')?'Software / Developer':'Management / Business'}</td><td style="padding:8px">${cb.course_name.includes('Computer')?'Software / Developer':'Management / Business'}</td></tr>
            </table>`;
          out.scrollIntoView({behavior:'smooth'});
        });
      }

    }catch(e){
      console.warn('Failed to load courses JSON', e);
    }
  })();

});