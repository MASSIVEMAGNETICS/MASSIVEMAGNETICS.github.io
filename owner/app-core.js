'use strict';
const MAX_ACTIVE=3, DB_NAME='amplification-governor', DB_VERSION=1, META_STORE='meta', VAULT_STORE='vault';
const STATES=['CANDIDATE','ACTIVE','VAULTED','MERGED','KILLED','SHIPPED','MONETIZED'];
let db=null, key=null, vault=null, idleTimer=null;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const now=()=>new Date().toISOString();
const uid=()=>crypto.randomUUID();
const clamp=(v,min,max)=>Math.max(min,Math.min(max,Number(v)||0));
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const fmtMoney=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(n)||0);
const fmtDate=s=>s?new Date(s).toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'}):'—';
const fmtDateTime=s=>s?new Date(s).toLocaleString():'—';
function toast(msg,bad=false){const t=$('#toast');t.textContent=msg;t.className='toast '+(bad?'bad':'good');setTimeout(()=>t.classList.add('hidden'),4200)}
function b64(bytes){return btoa(String.fromCharCode(...bytes))}
function unb64(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0))}
function openDB(){return new Promise((res,rej)=>{const r=indexedDB.open(DB_NAME,DB_VERSION);r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains(META_STORE))d.createObjectStore(META_STORE);if(!d.objectStoreNames.contains(VAULT_STORE))d.createObjectStore(VAULT_STORE)};r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
function idbGet(store,k){return new Promise((res,rej)=>{const tx=db.transaction(store,'readonly'),r=tx.objectStore(store).get(k);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
function idbSet(store,k,v){return new Promise((res,rej)=>{const tx=db.transaction(store,'readwrite');tx.objectStore(store).put(v,k);tx.oncomplete=()=>res();tx.onerror=()=>rej(tx.error)})}
async function deriveKey(pass,salt){const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:600000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt'])}
async function encryptVault(v){const iv=crypto.getRandomValues(new Uint8Array(12));const plain=new TextEncoder().encode(JSON.stringify(v));const cipher=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,plain));return {version:1,iv:b64(iv),ciphertext:b64(cipher),updatedAt:now()}}
async function decryptVault(rec,k){const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:unb64(rec.iv)},k,unb64(rec.ciphertext));return JSON.parse(new TextDecoder().decode(plain))}
function newVault(){return{schemaVersion:1,createdAt:now(),updatedAt:now(),ideas:[],events:[{id:uid(),at:now(),type:'SYSTEM_INIT',message:'Amplification Governor vault created. Governance law: max 3 ACTIVE branches; no silent deletion.'}],settings:{maxActive:3,preservationLaw:'Execution can terminate while knowledge is preserved.',governorLaw:'No new ACTIVE branch while all 3 ACTIVE slots are occupied.'}}}
async function saveVault(event=null){if(event)vault.events.unshift({id:uid(),at:now(),...event});vault.events=vault.events.slice(0,2000);vault.updatedAt=now();await idbSet(VAULT_STORE,'encrypted',await encryptVault(vault));renderAll();resetIdle()}
async function init(){db=await openDB();const meta=await idbGet(META_STORE,'crypto');const setup=!meta;$('#confirmField').classList.toggle('hidden',!setup);$('#setupCopy').classList.toggle('hidden',!setup);$('#unlockBtn').textContent=setup?'CREATE & UNLOCK VAULT':'UNLOCK VAULT';$('#unlockForm').dataset.setup=String(setup)}
$('#unlockForm').addEventListener('submit',async e=>{e.preventDefault();try{const pass=$('#passphrase').value;if(pass.length<10)throw new Error('Use at least 10 characters.');const setup=e.currentTarget.dataset.setup==='true';if(setup){if(pass!==$('#confirmPassphrase').value)throw new Error('Passphrases do not match.');const salt=crypto.getRandomValues(new Uint8Array(16));key=await deriveKey(pass,salt);vault=newVault();await idbSet(META_STORE,'crypto',{salt:b64(salt),createdAt:now()});await idbSet(VAULT_STORE,'encrypted',await encryptVault(vault));}else{const meta=await idbGet(META_STORE,'crypto');key=await deriveKey(pass,unb64(meta.salt));const rec=await idbGet(VAULT_STORE,'encrypted');vault=await decryptVault(rec,key)}$('#passphrase').value='';$('#confirmPassphrase').value='';$('#lockScreen').classList.add('hidden');$('#app').classList.remove('hidden');renderAll();resetIdle()}catch(err){toast(err.message||'Unlock failed',true)}});
function resetIdle(){clearTimeout(idleTimer);if(key)idleTimer=setTimeout(lockApp,15*60*1000)}
['click','keydown','touchstart'].forEach(ev=>document.addEventListener(ev,resetIdle,{passive:true}));
function lockApp(){key=null;vault=null;$('#app').classList.add('hidden');$('#lockScreen').classList.remove('hidden');$('#unlockForm').dataset.setup='false';$('#confirmField').classList.add('hidden');$('#setupCopy').classList.add('hidden');$('#unlockBtn').textContent='UNLOCK VAULT'}
