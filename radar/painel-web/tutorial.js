/* ================= tutorial do primeiro uso =================
   Abre sozinho na primeira vez (depois da abertura animada) e pelo botão "?" do topo. Passos curtos, sem termos técnicos;
   o passo com `alvo` desenha um anel sobre o botão do topo de que fala. Visto = ls 'tutorial' (por navegador). */
const TUT=[
  {t:'Bem-vindo ao Kurokami Hunter',p:['Ele acompanha o preço dos jogos da sua lista de desejos em várias lojas, todos os dias.','E responde a pergunta que importa: <b>vale comprar agora ou é melhor esperar?</b>']},
  {t:'Cada jogo tem uma resposta',p:['<span class="tut-r" style="--b:#d63031;--c:#fff">Vale comprar</span> o preço de agora é bom para esse jogo.',
    '<span class="tut-r" style="--b:#262626;--c:#d2d2d2">Espere</span> ele costuma ficar mais barato, ou nem está em promoção.',
    '<span class="tut-r" style="--b:#1c1c1c;--c:#979797">Ainda não dá pra saber</span> falta histórico de preços para comparar.','Embaixo da resposta vem uma frase curta dizendo o motivo.']},
  {t:'Onde olhar',alvo:'.topbar .nav [data-tab="vale"][data-tabs]',p:['Em <b>Ofertas</b>:','<b>Destaques</b> mostra o melhor de hoje.','<b>Lista de desejos</b> mostra os seus jogos, separados pela resposta.','<b>Promoções</b> mostra tudo o que está em promoção.']},
  {t:'Quer saber mais de um jogo?',p:['Clique na capa. A ficha mostra a resposta e, em <b>por quê</b>, o histórico de preços e as contas.','Se não quiser os detalhes, a resposta já basta.']},
  {t:'Comprar e ser avisado',alvo:'.topbar .nav [data-tab="carr"]',p:['O <b>+</b> na capa põe o jogo no <b>Carrinho</b> da Steam.','O Hunter fica perto do relógio do Windows e avisa quando aparece uma promoção boa. Não precisa deixar esta página aberta.']},
];
let tutI=0;
function tutorial(i){tutI=i||0;let ov=document.getElementById('tutOv');
  if(!ov){ov=document.createElement('div');ov.id='tutOv';ov.className='tut-ov';ov.innerHTML='<div class="tut-anel" hidden></div><div class="tut-cx" role="dialog" aria-modal="true" aria-labelledby="tutT"></div>';document.body.appendChild(ov);
    ov.addEventListener('click',e=>{const b=e.target.closest('[data-tut]');if(b){const v=b.dataset.tut;v==='fim'?tutFim():tutorial(tutI+(+v));}});}
  const s=TUT[tutI],ult=tutI===TUT.length-1;
  ov.querySelector('.tut-cx').innerHTML=`<div class="tut-n">${tutI+1} de ${TUT.length}</div><h2 id="tutT">${s.t}</h2>${s.p.map(x=>`<p>${x}</p>`).join('')}
    <div class="tut-pts">${TUT.map((_,k)=>`<i${k===tutI?' class="on"':''}></i>`).join('')}</div>
    <div class="tut-ac">${ult?'':'<button class="tut-pula" data-tut="fim">Pular</button>'}<span></span>${tutI?'<button class="btn-ghost" data-tut="-1">Voltar</button>':''}<button class="btn-imp" data-tut="${ult?'fim':'1'}">${ult?'Começar':'Próximo'}</button></div>
    ${ult?'<div class="tut-dica">Para ver de novo, clique no <b>?</b> no alto da página.</div>':''}`;
  const an=ov.querySelector('.tut-anel'),a=s.alvo&&document.querySelector(s.alvo),r=a&&a.getBoundingClientRect();
  if(r&&r.width){an.hidden=false;Object.assign(an.style,{left:r.left-6+'px',top:r.top-6+'px',width:r.width+12+'px',height:r.height+12+'px'});}else an.hidden=true;
  ov.querySelector('.tut-ac .btn-imp').focus({preventScroll:true});}
function tutFim(){const ov=document.getElementById('tutOv');if(ov)ov.remove();ls.set('tutorial',1);}
/* aberto, segura as teclas: o painel por baixo não recebe nada (Enter e Tab só agem nos botões do tutorial) */
addEventListener('keydown',e=>{const ov=document.getElementById('tutOv');if(!ov)return;e.stopImmediatePropagation();
  if(e.key==='Escape'){tutFim();e.preventDefault();}
  else if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();const n=tutI+(e.key==='ArrowRight'?1:-1);if(n>=0&&n<TUT.length)tutorial(n);}
  else if(e.key==='Tab'){const b=[...ov.querySelectorAll('button')],i=b.indexOf(document.activeElement);e.preventDefault();b[(i+(e.shiftKey?-1:1)+b.length)%b.length].focus();}
  else if(e.key!=='Enter'&&e.key!==' ')e.preventDefault();},true);
addEventListener('resize',()=>{if(document.getElementById('tutOv'))tutorial(tutI);});
(function inicia(){const b=document.getElementById('btnTut');if(b)b.onclick=()=>tutorial(0);
  if(ls.get('tutorial',0))return;
  (function espera(){if(document.getElementById('abertura'))setTimeout(espera,300);else tutorial(0);})();})();
