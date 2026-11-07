(()=>{
  'use strict';

  const API_BASE='https://api.iambandobandz.com';
  const ADMIN_BASE=API_BASE+'/api/v1/admin';
  const modules=['app-core.js','app-render.js','app-actions.js','app-io.js'];
  let booted=false;

  function el(tag,attrs={},text=''){
    const node=document.createElement(tag);
    Object.entries(attrs).forEach(([key,value])=>{
      if(key==='className') node.className=value;
      else if(key==='type') node.type=value;
      else node.setAttribute(key,value);
    });
    if(text) node.textContent=text;
    return node;
  }

  function createAuthGate(){
    const gate=el('section',{id:'serverAuthGate'});
    Object.assign(gate.style,{position:'fixed',inset:'0',zIndex:'99999',display:'grid',placeItems:'center',padding:'24px',background:'#080808',color:'#f4f0e8',fontFamily:'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'});
    const card=el('div');
    Object.assign(card.style,{width:'min(560px,100%)',border:'1px solid #343434',borderRadius:'18px',padding:'28px',background:'#111',boxShadow:'0 24px 80px rgba(0,0,0,.55)'});
    const eyebrow=el('div',{},'SERVER AUTHORITY / IAMBANDOBANDZ');
    Object.assign(eyebrow.style,{fontSize:'12px',letterSpacing:'.16em',opacity:'.68',marginBottom:'10px'});
    const title=el('h1',{},'OWNER AUTHORIZATION');
    Object.assign(title.style,{fontSize:'clamp(30px,7vw,52px)',lineHeight:'.95',margin:'0 0 16px'});
    const copy=el('p',{},'The owner control plane now fails closed behind the private API. Your admin credential is exchanged for a Secure, HttpOnly session cookie and is never stored by this page.');
    Object.assign(copy.style,{lineHeight:'1.55',opacity:'.82'});
    const status=el('p',{id:'serverAuthStatus','aria-live':'polite'},'Checking server session…');
    Object.assign(status.style,{padding:'12px 14px',border:'1px solid #2d2d2d',borderRadius:'10px',background:'#0b0b0b',fontSize:'14px'});
    const form=el('form',{id:'serverAuthForm'});
    Object.assign(form.style,{display:'grid',gap:'10px',marginTop:'14px'});
    const label=el('label',{for:'serverAdminToken'},'Admin credential');
    Object.assign(label.style,{fontSize:'13px',fontWeight:'700'});
    const input=el('input',{id:'serverAdminToken',name:'token',type:'password',autocomplete:'current-password',required:'required',spellcheck:'false'});
    Object.assign(input.style,{width:'100%',boxSizing:'border-box',border:'1px solid #3a3a3a',borderRadius:'10px',background:'#090909',color:'#fff',padding:'14px',fontSize:'16px'});
    const button=el('button',{type:'submit'},'AUTHORIZE OWNER');
    Object.assign(button.style,{border:'0',borderRadius:'10px',padding:'14px 18px',fontWeight:'900',cursor:'pointer',background:'#f4f0e8',color:'#080808'});
    const note=el('p',{},'Layer 1: server authorization. Layer 2: your existing encrypted local vault passphrase. The static page source remains public by design; privileged server APIs enforce authorization independently.');
    Object.assign(note.style,{fontSize:'12px',lineHeight:'1.5',opacity:'.62',marginBottom:'0'});
    form.append(label,input,button);
    card.append(eyebrow,title,copy,status,form,note);
    gate.append(card);
    document.body.append(gate);
    return {gate,form,input,button,status};
  }

  async function api(path,options={}){
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),5000);
    try{
      return await fetch(ADMIN_BASE+path,{
        ...options,
        credentials:'include',
        cache:'no-store',
        headers:{Accept:'application/json',...(options.headers||{})},
        signal:controller.signal
      });
    }finally{
      clearTimeout(timeout);
    }
  }

  function loadModules(){
    if(booted) return Promise.resolve();
    booted=true;
    let chain=Promise.resolve();
    for(const file of modules){
      chain=chain.then(()=>new Promise((resolve,reject)=>{
        const script=document.createElement('script');
        script.src='./'+file;
        script.onload=resolve;
        script.onerror=()=>reject(new Error('Failed to load '+file));
        document.body.appendChild(script);
      }));
    }
    return chain.then(addServerLogout);
  }

  function addServerLogout(){
    const actions=document.querySelector('.top-actions');
    if(!actions||document.getElementById('serverLogoutBtn')) return;
    const button=el('button',{id:'serverLogoutBtn',className:'btn btn-ghost',type:'button'},'SIGN OUT');
    button.addEventListener('click',async()=>{
      button.disabled=true;
      try{await api('/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});}catch(_){ }
      location.reload();
    });
    actions.appendChild(button);
  }

  function showFailure(status,message){
    status.textContent=message;
    status.style.borderColor='#6a3030';
  }

  const ui=createAuthGate();

  async function unlockUI(){
    ui.gate.remove();
    try{
      await loadModules();
    }catch(err){
      console.error(err);
      const fallback=createAuthGate();
      showFailure(fallback.status,'Authorized, but the local governor failed to boot: '+err.message);
      fallback.form.style.display='none';
    }
  }

  async function checkSession(){
    ui.form.style.display='none';
    ui.status.textContent='Checking server session…';
    try{
      const response=await api('/session');
      if(response.ok){
        await unlockUI();
        return;
      }
      ui.status.textContent=response.status===401?'Server session required.':'Admin API rejected the session check.';
      ui.form.style.display='grid';
      ui.input.focus();
    }catch(_){
      showFailure(ui.status,'Admin API is unavailable. Access is fail-closed until https://api.iambandobandz.com is healthy.');
      ui.form.style.display='grid';
      ui.button.textContent='RETRY / AUTHORIZE';
    }
  }

  ui.form.addEventListener('submit',async(event)=>{
    event.preventDefault();
    const token=ui.input.value;
    ui.input.value='';
    ui.button.disabled=true;
    ui.status.textContent='Authorizing…';
    try{
      const response=await api('/login',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({token})
      });
      if(!response.ok){
        let error='Authorization failed.';
        try{const body=await response.json();if(body?.error) error=body.error.replaceAll('_',' ')+'.';}catch(_){ }
        showFailure(ui.status,error);
        ui.button.disabled=false;
        ui.input.focus();
        return;
      }
      ui.status.textContent='Server authorization verified. Opening encrypted vault gate…';
      await unlockUI();
    }catch(_){
      showFailure(ui.status,'Admin API is unreachable. Nothing is unlocked.');
      ui.button.disabled=false;
      ui.input.focus();
    }
  });

  checkSession();
})();
