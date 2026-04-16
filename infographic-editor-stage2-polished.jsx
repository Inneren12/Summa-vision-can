import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from "react";

/* ═══════════════════════════════════════════════════════════
   SUMMA VISION — INFOGRAPHIC EDITOR v1.2 (Stage 2 Polished)
   
   Stage 1: Canonical doc, command system, block-driven renderer,
            permissions, undo/redo, validation, import/export
   Stage 2: Chart blocks (bar, line, KPI, table, small multiples)
   Stage 2 Polish:
     1. Structured data editors for chart blocks (not just text fields)
     2. Chart-aware validation (empty series, mismatched lengths, NaN)
     3. Layout safety warnings (density, overflow, size compatibility)
     4. Schema guards per block type on import
     5. Expanded permissions model (metadata/data/style/structure)
   ═══════════════════════════════════════════════════════════ */

const TK = {
  font: { display: "'Bricolage Grotesque', system-ui", body: "'DM Sans', system-ui", data: "'JetBrains Mono', monospace" },
  c: { bgApp:"#0B0D11",bgSurf:"#15181E",bgHov:"#1C1F26",bgAct:"#22252D",brd:"#262A33",txtP:"#F3F4F6",txtS:"#8B949E",txtM:"#5C6370",acc:"#FBBF24",accM:"rgba(251,191,36,0.15)",err:"#E11D48",pos:"#0D9488",neg:"#E11D48" },
};
const PALETTES = {
  housing:{n:"Housing",p:"#22D3EE",s:"#3B82F6",a:"#FBBF24",pos:"#0D9488",neg:"#E11D48"},
  government:{n:"Government",p:"#3B82F6",s:"#A78BFA",a:"#FBBF24",pos:"#0D9488",neg:"#E11D48"},
  energy:{n:"Energy",p:"#2DD4BF",s:"#0D9488",a:"#F97316",pos:"#2DD4BF",neg:"#E11D48"},
  society:{n:"Society",p:"#A78BFA",s:"#22D3EE",a:"#FBBF24",pos:"#0D9488",neg:"#E11D48"},
  economy:{n:"Markets",p:"#F97316",s:"#FBBF24",a:"#3B82F6",pos:"#0D9488",neg:"#E11D48"},
  neutral:{n:"Neutral",p:"#94A3B8",s:"#8B949E",a:"#FBBF24",pos:"#0D9488",neg:"#E11D48"},
};
const BGS = {
  solid_dark:{n:"Solid Dark",r:(c,w,h)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);}},
  gradient_midnight:{n:"Midnight",r:(c,w,h)=>{const g=c.createLinearGradient(0,0,0,h);g.addColorStop(0,"#0B0D11");g.addColorStop(1,"#1C1F26");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  gradient_warm:{n:"Warm Glow",r:(c,w,h,p)=>{const g=c.createLinearGradient(0,0,w*.5,h);g.addColorStop(0,"#0B0D11");g.addColorStop(1,p.p+"15");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  gradient_radial:{n:"Radial",r:(c,w,h,p)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);const g=c.createRadialGradient(w*.5,h*.6,0,w*.5,h*.6,w*.6);g.addColorStop(0,p.p+"12");g.addColorStop(1,"transparent");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  dot_grid:{n:"Dot Grid",r:(c,w,h)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);c.fillStyle="rgba(255,255,255,0.04)";for(let x=0;x<w;x+=24)for(let y=0;y<h;y+=24){c.beginPath();c.arc(x,y,1,0,Math.PI*2);c.fill();}}},
  topo:{n:"Topographic",r:(c,w,h,p)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);c.strokeStyle=p.p+"08";c.lineWidth=1;for(let i=0;i<12;i++){const cx=w*(.3+Math.sin(i*1.2)*.3),cy=h*(.3+Math.cos(i*.8)*.3);for(let r=30;r<200;r+=25){c.beginPath();c.ellipse(cx,cy,r*1.5,r,i*.3,0,Math.PI*2);c.stroke();}}}},
};
const SIZES = {
  instagram_1080:{w:1080,h:1080,n:"IG 1:1"},instagram_port:{w:1080,h:1350,n:"IG 4:5"},
  twitter:{w:1200,h:675,n:"Twitter/X"},reddit:{w:1200,h:900,n:"Reddit"},
  linkedin:{w:1200,h:627,n:"LinkedIn"},story:{w:1080,h:1920,n:"Story"},
};

// ═══════════════════════════════════════════════════════════
// BLOCK REGISTRY — 13 types with schema guards
// ═══════════════════════════════════════════════════════════
const BREG = {
  eyebrow_tag:{cat:"text",name:"Eyebrow",status:"optional_default",allowedSections:["header"],maxPerSection:1,dp:{text:"STATISTICS CANADA · TABLE 18-10-0004"},cst:{maxChars:60,maxLines:1},ctrl:[{k:"text",t:"text",l:"Tag",ml:60}],
    guard:(p)=>typeof p.text==="string"},
  headline_editorial:{cat:"text",name:"Headline",status:"required_editable",allowedSections:["header"],maxPerSection:1,dp:{text:"Canadian Mortgage Rates\nHit 15-Year High",align:"left"},cst:{maxChars:80,maxLines:3},ctrl:[{k:"text",t:"textarea",l:"Headline",ml:80},{k:"align",t:"seg",l:"Align",opts:["left","center","right"]}],
    guard:(p)=>typeof p.text==="string"&&["left","center","right"].includes(p.align||"left")},
  subtitle_descriptor:{cat:"text",name:"Subtitle",status:"optional_default",allowedSections:["header","context"],maxPerSection:1,dp:{text:"Average 5-year fixed rate, March 2026"},cst:{maxChars:120,maxLines:2},ctrl:[{k:"text",t:"text",l:"Subtitle",ml:120}],
    guard:(p)=>typeof p.text==="string"},
  hero_stat:{cat:"data",name:"Hero Number",status:"required_editable",allowedSections:["hero"],maxPerSection:1,dp:{value:"6.73%",label:"5-year fixed rate"},cst:{maxChars:10},ctrl:[{k:"value",t:"text",l:"Value",ml:10},{k:"label",t:"text",l:"Label",ml:60}],
    guard:(p)=>typeof p.value==="string"},
  delta_badge:{cat:"data",name:"Delta Badge",status:"optional_default",allowedSections:["hero","context"],maxPerSection:1,dp:{value:"+247 bps since Jan 2022",direction:"negative"},cst:{maxChars:40},ctrl:[{k:"value",t:"text",l:"Delta",ml:40},{k:"direction",t:"seg",l:"Dir",opts:["positive","negative","neutral"]}],
    guard:(p)=>typeof p.value==="string"&&["positive","negative","neutral"].includes(p.direction||"neutral")},
  body_annotation:{cat:"text",name:"Annotation",status:"optional_available",allowedSections:["context","chart"],maxPerSection:2,dp:{text:"Rates represent posted rates from chartered banks"},cst:{maxChars:200,maxLines:4},ctrl:[{k:"text",t:"textarea",l:"Note",ml:200}],
    guard:(p)=>typeof p.text==="string"},
  source_footer:{cat:"text",name:"Source",status:"required_locked",allowedSections:["footer"],maxPerSection:1,dp:{text:"Source: Statistics Canada, Table 18-10-0004-01",methodology:""},cst:{maxChars:200},ctrl:[{k:"text",t:"text",l:"Source",ml:200},{k:"methodology",t:"text",l:"Method",ml:200}],
    guard:(p)=>typeof p.text==="string"},
  brand_stamp:{cat:"struct",name:"Brand",status:"required_locked",allowedSections:["footer"],maxPerSection:1,dp:{position:"bottom-right"},ctrl:[{k:"position",t:"seg",l:"Position",opts:["bottom-left","bottom-right"]}],
    guard:(p)=>["bottom-left","bottom-right"].includes(p.position)},
  bar_horizontal:{cat:"chart",name:"Ranked Bars",status:"required_editable",allowedSections:["chart"],maxPerSection:1,
    dp:{items:[{label:"Vancouver",value:12.8,flag:"🇨🇦",highlight:true},{label:"Toronto",value:10.2,flag:"🇨🇦",highlight:true},{label:"Hamilton",value:7.9,flag:"🇨🇦"},{label:"Victoria",value:7.6,flag:"🇨🇦"},{label:"Ottawa",value:5.8,flag:"🇨🇦"},{label:"Montreal",value:5.4,flag:"🇨🇦"},{label:"Calgary",value:4.2,flag:"🇨🇦"},{label:"Edmonton",value:3.5,flag:"🇨🇦"}],unit:"×",benchmarkValue:5.0,benchmarkLabel:"Affordable threshold",showBenchmark:true},
    ctrl:[{k:"unit",t:"text",l:"Unit suffix",ml:5},{k:"showBenchmark",t:"toggle",l:"Benchmark line"},{k:"benchmarkValue",t:"text",l:"Bench value",ml:10},{k:"benchmarkLabel",t:"text",l:"Bench label",ml:30}],
    guard:(p)=>Array.isArray(p.items)&&p.items.every(i=>typeof i.label==="string"&&typeof i.value==="number")},
  line_editorial:{cat:"chart",name:"Line Chart",status:"required_editable",allowedSections:["chart"],maxPerSection:1,
    dp:{series:[{label:"CPI All Items",data:[1.9,0.7,3.4,6.8,3.9,2.7,2.4,2.1],role:"primary"},{label:"BoC Target",data:[2,2,2,2,2,2,2,2],role:"benchmark"}],xLabels:["2019","2020","2021","2022","2023","2024","2025","2026"],yUnit:"%",showArea:true},
    ctrl:[{k:"yUnit",t:"text",l:"Y unit",ml:5},{k:"showArea",t:"toggle",l:"Area fill"}],
    guard:(p)=>Array.isArray(p.series)&&Array.isArray(p.xLabels)&&p.series.every(s=>Array.isArray(s.data))},
  comparison_kpi:{cat:"data",name:"KPI Compare",status:"required_editable",allowedSections:["chart","hero"],maxPerSection:1,
    dp:{items:[{label:"Population Growth",value:"3.2%",delta:"+1.4pp YoY",direction:"positive"},{label:"Net Immigration",value:"1.2M",delta:"+340K vs 2023",direction:"positive"},{label:"Housing Starts",value:"218K",delta:"−12% vs target",direction:"negative"}]},
    ctrl:[],
    guard:(p)=>Array.isArray(p.items)&&p.items.length>=2&&p.items.every(i=>typeof i.label==="string"&&typeof i.value==="string")},
  table_enriched:{cat:"chart",name:"Visual Table",status:"required_editable",allowedSections:["chart"],maxPerSection:1,
    dp:{columns:["Country","Individual","Corporate","Property","Consumption","Score"],rows:[{country:"Estonia",flag:"🇪🇪",vals:[2,2,1,18,100.0],rank:1},{country:"Latvia",flag:"🇱🇻",vals:[3,1,5,21,92.2],rank:2},{country:"New Zealand",flag:"🇳🇿",vals:[6,30,8,2,84.2],rank:3},{country:"Switzerland",flag:"🇨🇭",vals:[8,10,36,3,83.6],rank:4},{country:"Lithuania",flag:"🇱🇹",vals:[10,3,7,27,79.5],rank:5},{country:"Canada",flag:"🇨🇦",vals:[31,26,25,8,66.8],rank:17},{country:"U.S.",flag:"🇺🇸",vals:[17,20,28,4,66.5],rank:18},{country:"France",flag:"🇫🇷",vals:[33,33,31,31,50.2],rank:36}]},
    ctrl:[],
    guard:(p)=>Array.isArray(p.columns)&&Array.isArray(p.rows)&&p.rows.every(r=>Array.isArray(r.vals)&&r.vals.length===p.columns.length-1)},
  small_multiple:{cat:"chart",name:"Small Multiples",status:"required_editable",allowedSections:["chart"],maxPerSection:1,
    dp:{items:[{label:"New York",flag:"🇺🇸",data:[-0.5,-1.2,-3.1,-4.5,-5.8,-6.2,-5.1,-4.8]},{label:"London",flag:"🇬🇧",data:[-0.3,-0.8,-2.5,-3.8,-5.2,-6.8,-5.5,-4.2]},{label:"Frankfurt",flag:"🇩🇪",data:[-0.2,-0.5,-1.8,-3.2,-5.5,-8.1,-10.2,-7.5]},{label:"Shanghai",flag:"🇨🇳",data:[0.1,-0.2,-1.5,-2.8,-3.5,-4.2,-5.8,-4.1]},{label:"Hong Kong",flag:"🇭🇰",data:[-0.4,-1.0,-2.2,-4.1,-5.5,-7.2,-8.5,-6.8]},{label:"Tokyo",flag:"🇯🇵",data:[-0.1,-0.3,-1.2,-2.5,-4.8,-6.5,-9.8,-8.2]}],yUnit:"%"},
    ctrl:[{k:"yUnit",t:"text",l:"Y unit",ml:5}],
    guard:(p)=>Array.isArray(p.items)&&p.items.every(i=>typeof i.label==="string"&&Array.isArray(i.data))},
};

// ═══════════════════════════════════════════════════════════
// PERMISSIONS — expanded: metadata / data / style / structure
// ═══════════════════════════════════════════════════════════
const PERMS = {
  template: {
    switchTemplate:false, changePalette:false, changeBackground:false, changeSize:true,
    editBlock:(reg,key)=>{
      // Template mode: text/value content always editable, style/structure never
      const contentKeys = ["text","value","methodology","label","direction","items","series","xLabels","columns","rows"];
      if (reg.status==="required_locked") return ["text","value","methodology"].includes(key);
      return contentKeys.includes(key);
    },
    toggleVisibility:(reg)=>reg.status==="optional_default"||reg.status==="optional_available",
  },
  design: {
    switchTemplate:true, changePalette:true, changeBackground:true, changeSize:true,
    editBlock:()=>true, toggleVisibility:()=>true,
  },
};

// ═══════════════════════════════════════════════════════════
// CANONICAL DOCUMENT
// ═══════════════════════════════════════════════════════════
const SCHEMA_VERSION = 1;
function mkDoc(tid, tpl, over={}) {
  const blocks={}; let seq=0;
  const sections=tpl.sections.map(sec=>{
    const bids=sec.blockTypes.map(bt=>{
      const id=`blk_${String(++seq).padStart(3,"0")}`;
      blocks[id]={id,type:bt,props:{...BREG[bt].dp,...(over[bt]||{})},visible:true};
      return id;
    });
    return {id:sec.id,type:sec.type,blockIds:bids};
  });
  return {schemaVersion:SCHEMA_VERSION,templateId:tid,page:{size:tpl.defaultSize||"instagram_1080",background:tpl.defaultBg||"gradient_warm",palette:tpl.defaultPal||"housing"},sections,blocks,workflow:"draft",meta:{createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),version:1,history:[]}};
}

// Schema guard on import
function validateImport(doc) {
  if (!doc?.schemaVersion||!doc?.blocks||!doc?.sections) return "Missing required fields";
  for (const [id,b] of Object.entries(doc.blocks)) {
    const reg=BREG[b.type];
    if (!reg) return `Unknown block type: ${b.type}`;
    if (reg.guard && !reg.guard(b.props)) return `Invalid props for ${b.type} (${id})`;
  }
  return null; // valid
}

function migrateDoc(doc) {
  if(!doc.workflow) doc.workflow="draft";
  if(!doc.meta) doc.meta={createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),version:1,history:[]};
  if(!doc.meta.history) doc.meta.history=[];
  if(!doc.page) doc.page={size:"instagram_1080",background:"gradient_warm",palette:"housing"};
  return doc;
}

// ═══════════════════════════════════════════════════════════
// BLOCK RENDERERS
// ═══════════════════════════════════════════════════════════
const SECTION_LAYOUT = {
  header:(w,h,s,p)=>({x:p,y:p,w:w-p*2,h:130*s}),
  hero:(w,h,s,p)=>({x:p,y:h*.34,w:w-p*2,h:160*s}),
  context:(w,h,s,p)=>({x:p,y:h*.58,w:w-p*2,h:100*s}),
  chart:(w,h,s,p)=>({x:p,y:h*.22,w:w-p*2,h:h*.55}),
  footer:(w,h,s,p)=>({x:p,y:h-p-40*s,w:w-p*2,h:40*s}),
};

const BR = {
  eyebrow_tag:(ctx,p,x,y,w,h,pal,s)=>{ctx.font=`500 ${11*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtM;ctx.textAlign="left";ctx.fillText(p.text||"",x,y+14*s);return 20*s;},
  headline_editorial:(ctx,p,x,y,w,h,pal,s)=>{ctx.font=`700 ${42*s}px ${TK.font.display}`;ctx.fillStyle=TK.c.txtP;const al=p.align||"left";ctx.textAlign=al;const ax=al==="center"?x+w/2:al==="right"?x+w:x;const lines=(p.text||"").split("\n");lines.forEach((l,i)=>ctx.fillText(l,ax,y+42*s+i*50*s));return(lines.length*50+10)*s;},
  subtitle_descriptor:(ctx,p,x,y,w,h,pal,s)=>{ctx.font=`400 ${16*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="center";ctx.fillText(p.text||"",x+w/2,y+18*s);return 30*s;},
  hero_stat:(ctx,p,x,y,w,h,pal,s)=>{if(!p.value)return 0;ctx.strokeStyle=pal.p+"30";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,y-10*s);ctx.lineTo(x+w,y-10*s);ctx.stroke();ctx.font=`700 ${120*s}px ${TK.font.data}`;ctx.fillStyle=pal.p;ctx.textAlign="center";ctx.fillText(p.value,x+w/2,y+100*s);const nw=ctx.measureText(p.value).width;ctx.fillStyle=TK.c.acc;ctx.fillRect(x+w/2-nw/2,y+110*s,nw,3*s);if(p.label){ctx.font=`400 ${16*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="center";ctx.fillText(p.label,x+w/2,y+140*s);}return 150*s;},
  delta_badge:(ctx,p,x,y,w,h,pal,s)=>{if(!p.value)return 0;ctx.font=`700 ${14*s}px ${TK.font.data}`;ctx.fillStyle=p.direction==="negative"?pal.neg:p.direction==="positive"?pal.pos:TK.c.txtS;ctx.textAlign="center";ctx.fillText(p.value,x+w/2,y+16*s);return 24*s;},
  body_annotation:(ctx,p,x,y,w,h,pal,s)=>{if(!p.text)return 0;ctx.font=`400 ${13*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="center";const mw=w*.8;const words=p.text.split(" ");let ln="",lc=0;words.forEach(wd=>{const t=ln+wd+" ";if(ctx.measureText(t).width>mw&&ln){ctx.fillText(ln.trim(),x+w/2,y+16*s+lc*20*s);ln=wd+" ";lc++;}else ln=t;});if(ln){ctx.fillText(ln.trim(),x+w/2,y+16*s+lc*20*s);lc++;}return(lc*20+10)*s;},
  source_footer:(ctx,p,x,y,w,h,pal,s)=>{ctx.font=`500 ${10*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtM;ctx.textAlign="left";if(p.text)ctx.fillText(p.text,x,y+12*s);if(p.methodology)ctx.fillText(p.methodology,x,y+26*s);return 30*s;},
  brand_stamp:(ctx,p,x,y,w,h,pal,s)=>{const pos=p.position||"bottom-right";const bx=pos==="bottom-left"?x+8*s:x+w-8*s;ctx.textAlign=pos==="bottom-left"?"left":"right";ctx.font=`700 ${16*s}px ${TK.font.display}`;ctx.fillStyle=TK.c.acc;ctx.fillText("SUMMA",bx,y+16*s);const sw=ctx.measureText("SUMMA").width;ctx.font=`400 ${16*s}px ${TK.font.display}`;ctx.fillStyle=TK.c.txtS;ctx.fillText("VISION",bx+(pos==="bottom-left"?sw+4*s:-(sw+4*s)),y+16*s);return 20*s;},
  bar_horizontal:(ctx,p,x,y,w,h,pal,s)=>{const items=p.items||[];if(!items.length)return 0;const unit=p.unit||"",mx=Math.max(...items.map(i=>i.value)),lW=110*s,cL=x+lW,cW=w-lW,bH=Math.min((h/items.length)*.65,30*s),gap=h/items.length;items.forEach((it,i)=>{const by=y+i*gap+(gap-bH)/2,bW=(it.value/mx)*cW*.82;ctx.font=`500 ${13*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="right";ctx.fillText(`${it.flag||""} ${it.label}`,cL-12*s,by+bH/2+5*s);ctx.fillStyle=it.highlight?pal.p:pal.p+"50";ctx.beginPath();ctx.roundRect(cL,by,bW,bH,[0,2*s,2*s,0]);ctx.fill();ctx.font=`700 ${12*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtP;ctx.textAlign="left";ctx.fillText(`${it.value}${unit}`,cL+bW+8*s,by+bH/2+4*s);});if(p.showBenchmark&&p.benchmarkValue){const bv=parseFloat(p.benchmarkValue)||0,bx2=cL+(bv/mx)*cW*.82;ctx.setLineDash([4*s,4*s]);ctx.strokeStyle=TK.c.acc+"80";ctx.lineWidth=1.5*s;ctx.beginPath();ctx.moveTo(bx2,y-8*s);ctx.lineTo(bx2,y+h+8*s);ctx.stroke();ctx.setLineDash([]);ctx.font=`500 ${10*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.acc;ctx.textAlign="center";ctx.fillText(p.benchmarkLabel||"",bx2,y-14*s);}return h;},
  line_editorial:(ctx,p,x,y,w,h,pal,s)=>{const sr=p.series||[],xl=p.xLabels||[],yu=p.yUnit||"%";if(!sr.length)return 0;const cL=x,cR=x+w-70*s,cT=y,cB=y+h-30*s,cW=cR-cL,cH=cB-cT;const av=sr.flatMap(l=>l.data),yMn=Math.floor(Math.min(...av)-1),yMx=Math.ceil(Math.max(...av)+1),yR=yMx-yMn;for(let i=0;i<=5;i++){const v=yMn+(yR*i/5),ly=cB-(i/5)*cH;ctx.strokeStyle="rgba(255,255,255,0.06)";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cL,ly);ctx.lineTo(cR,ly);ctx.stroke();ctx.font=`500 ${10*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtM;ctx.textAlign="right";ctx.fillText(`${v.toFixed(1)}${yu}`,cL-6*s,ly+4*s);}ctx.textAlign="center";xl.forEach((lb,i)=>{ctx.fillText(lb,cL+(i/(xl.length-1))*cW,cB+18*s);});sr.forEach(line=>{const col=line.role==="primary"?pal.p:line.role==="benchmark"?TK.c.acc:pal.s;ctx.strokeStyle=col;ctx.lineWidth=(line.role==="primary"?2.5:1.5)*s;if(line.role==="benchmark")ctx.setLineDash([6*s,4*s]);else ctx.setLineDash([]);ctx.beginPath();line.data.forEach((v,i)=>{const lx=cL+(i/(line.data.length-1))*cW,ly=cB-((v-yMn)/yR)*cH;i===0?ctx.moveTo(lx,ly):ctx.lineTo(lx,ly);});ctx.stroke();ctx.setLineDash([]);if(line.role==="primary"&&p.showArea){ctx.fillStyle=col+"15";ctx.beginPath();line.data.forEach((v,i)=>{const lx=cL+(i/(line.data.length-1))*cW,ly=cB-((v-yMn)/yR)*cH;i===0?ctx.moveTo(lx,ly):ctx.lineTo(lx,ly);});ctx.lineTo(cR,cB);ctx.lineTo(cL,cB);ctx.closePath();ctx.fill();}const lv=line.data[line.data.length-1],elx=cR+8*s,ely=cB-((lv-yMn)/yR)*cH;ctx.font=`700 ${10*s}px ${TK.font.data}`;ctx.fillStyle=col;ctx.textAlign="left";ctx.fillText(`${lv}${yu}`,elx,ely-2*s);ctx.font=`400 ${9*s}px ${TK.font.body}`;ctx.fillText(line.label,elx,ely+10*s);});return h;},
  comparison_kpi:(ctx,p,x,y,w,h,pal,s)=>{const items=p.items||[];if(!items.length)return 0;const colW=w/items.length;items.forEach((st,i)=>{const cx=x+colW*i+colW/2;if(i>0){ctx.strokeStyle=TK.c.brd;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x+colW*i,y);ctx.lineTo(x+colW*i,y+h);ctx.stroke();}ctx.font=`500 ${13*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="center";ctx.fillText(st.label,cx,y+20*s);ctx.font=`700 ${48*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtP;ctx.fillText(st.value,cx,y+78*s);const vw=ctx.measureText(st.value).width;ctx.fillStyle=pal.p;ctx.fillRect(cx-vw/2,y+86*s,vw,3*s);ctx.font=`700 ${13*s}px ${TK.font.data}`;ctx.fillStyle=st.direction==="positive"?pal.pos:pal.neg;ctx.fillText(st.delta,cx,y+112*s);});return h;},
  table_enriched:(ctx,p,x,y,w,h,pal,s)=>{const cols=p.columns||[],rows=p.rows||[];if(!rows.length)return 0;const colW=w/(cols.length+1),rowH=Math.min(36*s,h/(rows.length+1));ctx.font=`600 ${9*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtS;ctx.textAlign="center";cols.forEach((c,i)=>ctx.fillText(c,x+colW*(i+1)+colW/2,y+12*s));rows.forEach((row,ri)=>{const ry=y+20*s+ri*rowH;if(ri%2===0){ctx.fillStyle="rgba(255,255,255,0.02)";ctx.fillRect(x,ry,w,rowH);}ctx.font=`700 ${11*s}px ${TK.font.data}`;ctx.fillStyle=pal.p;ctx.textAlign="right";ctx.fillText(`${row.rank}`,x+18*s,ry+rowH/2+4*s);ctx.font=`500 ${11*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtP;ctx.textAlign="left";ctx.fillText(`${row.flag} ${row.country}`,x+24*s,ry+rowH/2+4*s);row.vals.forEach((v,ci)=>{const ccx=x+colW*(ci+1)+colW/2;const isScore=ci===row.vals.length-1;if(isScore){const n=v/100;ctx.fillStyle=`rgba(${Math.round(255*(1-n))},${Math.round(255*n*.6)},80,0.15)`;}else{const n=Math.min((typeof v==="number"?v:0)/38,1);ctx.fillStyle=`rgba(${Math.round(147+n*80)},${Math.round(130-n*60)},${Math.round(220-n*100)},0.12)`;}ctx.fillRect(ccx-colW/2+2*s,ry+1*s,colW-4*s,rowH-2*s);ctx.font=isScore?`700 ${11*s}px ${TK.font.data}`:`500 ${10*s}px ${TK.font.data}`;ctx.fillStyle=isScore?TK.c.txtP:TK.c.txtS;ctx.textAlign="center";ctx.fillText(typeof v==="number"?v.toFixed(isScore?1:0):v,ccx,ry+rowH/2+4*s);});});return h;},
  small_multiple:(ctx,p,x,y,w,h,pal,s)=>{const items=p.items||[],yU=p.yUnit||"%";if(!items.length)return 0;const gc=3,gr=Math.ceil(items.length/gc),cW=w/gc,cH=h/gr,cp=14*s;const aV=items.flatMap(i=>i.data),yMn=Math.min(...aV)-1,yMx=Math.max(0,...aV)+.5,yR=yMx-yMn;items.forEach((it,idx)=>{const col=idx%gc,row=Math.floor(idx/gc),cx=x+col*cW,cy=y+row*cH,chL=cx+cp,chR=cx+cW-cp,chT=cy+28*s,chB=cy+cH-10*s,chW2=chR-chL,chH2=chB-chT;ctx.strokeStyle=TK.c.brd;ctx.lineWidth=1;ctx.strokeRect(cx+3*s,cy+3*s,cW-6*s,cH-6*s);ctx.font=`600 ${13*s}px ${TK.font.body}`;ctx.fillStyle=TK.c.txtP;ctx.textAlign="left";ctx.fillText(it.label,chL,cy+20*s);ctx.textAlign="right";ctx.fillText(it.flag,chR,cy+20*s);const zY=chB-((0-yMn)/yR)*chH2;ctx.strokeStyle="rgba(255,255,255,0.1)";ctx.beginPath();ctx.moveTo(chL,zY);ctx.lineTo(chR,zY);ctx.stroke();ctx.font=`500 ${8*s}px ${TK.font.data}`;ctx.fillStyle=TK.c.txtM;ctx.textAlign="right";ctx.fillText("0%",chL-3*s,zY+3*s);ctx.strokeStyle=pal.p;ctx.lineWidth=2*s;ctx.beginPath();it.data.forEach((v,i)=>{const lx=chL+(i/(it.data.length-1))*chW2,ly=chB-((v-yMn)/yR)*chH2;i===0?ctx.moveTo(lx,ly):ctx.lineTo(lx,ly);});ctx.stroke();const lv=it.data[it.data.length-1];ctx.font=`700 ${9*s}px ${TK.font.data}`;ctx.fillStyle=pal.neg;ctx.textAlign="right";ctx.fillText(`${lv.toFixed(1)}${yU}`,chR,chB-((lv-yMn)/yR)*chH2-6*s);});return h;},
};

function renderDoc(ctx,doc,w,h,pal){
  const s=w/1080,pad=64*s;
  ctx.fillStyle=TK.c.acc;ctx.fillRect(0,0,w,4*s);
  doc.sections.forEach(sec=>{const lf=SECTION_LAYOUT[sec.type];if(!lf)return;const la=lf(w,h,s,pad);let cy=0;sec.blockIds.forEach(bid=>{const b=doc.blocks[bid];if(!b||!b.visible)return;const fn=BR[b.type];if(!fn)return;cy+=fn(ctx,b.props,la.x,la.y+cy,la.w,la.h,pal,s);});});
}

// ═══════════════════════════════════════════════════════════
// TEMPLATES — 11
// ═══════════════════════════════════════════════════════════
const TPLS = {
  single_stat_hero:{fam:"Single Stat Hero",vr:"Number + Delta",desc:"Giant number with change",defaultPal:"housing",defaultBg:"gradient_warm",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}]},
  single_stat_note:{fam:"Single Stat Hero",vr:"Number + Note",desc:"Number with annotation",defaultPal:"housing",defaultBg:"gradient_radial",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"context",type:"context",blockTypes:["body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{body_annotation:{text:"Rates represent posted rates from chartered banks."}}},
  single_stat_minimal:{fam:"Single Stat Hero",vr:"Minimal",desc:"Clean, centered",defaultPal:"neutral",defaultBg:"solid_dark",defaultSize:"twitter",sections:[{id:"header",type:"header",blockTypes:["headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Bank of Canada\nHolds Rates Steady",align:"center"},hero_stat:{value:"4.50%",label:"Overnight rate"},source_footer:{text:"Source: Bank of Canada"}}},
  stat_comparison:{fam:"Single Stat Hero",vr:"Before / After",desc:"Two numbers contrasted",defaultPal:"economy",defaultBg:"gradient_midnight",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor","body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Cost of Living\nOutpaces Wages"},eyebrow_tag:{text:"INSIGHT · ECONOMY · 2026"},hero_stat:{value:"$74K",label:"Median household income"},delta_badge:{value:"+2.1% vs +4.8% CPI",direction:"negative"},subtitle_descriptor:{text:"Income grew 2.1% while cost of living rose 4.8%"},body_annotation:{text:"The gap between wage growth and inflation has widened for 3 consecutive years."},source_footer:{text:"Source: Statistics Canada, Labour Force Survey"}}},
  insight_card:{fam:"Insight Card",vr:"Fact + Context",desc:"Key insight with analysis",defaultPal:"government",defaultBg:"gradient_warm",defaultSize:"instagram_port",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Federal Deficit\nReaches Record High"},eyebrow_tag:{text:"CHARTED: · FISCAL POLICY"},hero_stat:{value:"$61.9B",label:"Projected deficit"},delta_badge:{value:"+$21.8B vs estimate",direction:"negative"},body_annotation:{text:"PBO projects deficit 40% higher than forecast."},source_footer:{text:"Source: Parliamentary Budget Officer, March 2026"}}},
  social_quote:{fam:"Insight Card",vr:"Social Post",desc:"Shareable stat",defaultPal:"society",defaultBg:"dot_grid",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Canada Added More People\nThan Any Year in History",align:"center"},hero_stat:{value:"1.27M",label:"Net population growth, 2025"},subtitle_descriptor:{text:"Equivalent to adding Calgary in one year"},source_footer:{text:"Source: Statistics Canada"}}},
  ranked_bar_simple:{fam:"Ranked Bars",vr:"Simple Ranking",desc:"Horizontal bars by value",defaultPal:"housing",defaultBg:"gradient_midnight",defaultSize:"reddit",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["bar_horizontal"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Housing Price-to-Income Ratio\nAcross Major Canadian Cities"},eyebrow_tag:{text:"RANKED: · HOUSING AFFORDABILITY · Q4 2025"},source_footer:{text:"Source: CMHC, Q4 2025"}}},
  line_area:{fam:"Line Editorial",vr:"Single + Area",desc:"Time series with area fill",defaultPal:"government",defaultBg:"gradient_warm",defaultSize:"twitter",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["line_editorial"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Canada's Inflation Journey:\nFrom Pandemic to New Normal"},eyebrow_tag:{text:"CHARTED: · CPI · 2019–2026"},source_footer:{text:"Source: Statistics Canada"}}},
  comparison_3kpi:{fam:"Comparison",vr:"3 KPI Cards",desc:"Three metrics side by side",defaultPal:"society",defaultBg:"gradient_radial",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["comparison_kpi"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Record Immigration Drives\nCanada's Population Surge"},eyebrow_tag:{text:"POPULATION GROWTH · 2025"},source_footer:{text:"Source: Statistics Canada, CMHC"}}},
  visual_table:{fam:"Visual Table",vr:"Heatmap Rankings",desc:"Table with conditional format",defaultPal:"neutral",defaultBg:"solid_dark",defaultSize:"instagram_port",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["table_enriched"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"The Best and Worst\nCountries for Taxes"},eyebrow_tag:{text:"RANKED: · TAX COMPETITIVENESS · 2024"},source_footer:{text:"Source: Tax Foundation"}}},
  small_multiples_grid:{fam:"Small Multiples",vr:"2×3 Grid",desc:"Same chart repeated",defaultPal:"economy",defaultBg:"gradient_midnight",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["small_multiple"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"A Rocky Month\nfor Global Stocks"},eyebrow_tag:{text:"CHARTED: · EQUITY INDEXES · FEB–MAR 2026"},source_footer:{text:"Source: FactSet, The New York Times"}}},
};

// ═══════════════════════════════════════════════════════════
// COMMAND SYSTEM
// ═══════════════════════════════════════════════════════════
const MAX_UNDO=50;
function reducer(state,action){
  const push=(newDoc,summary="")=>{const nv=(state.doc.meta.version||0)+1,now=new Date().toISOString();const hist=[...(state.doc.meta.history||[]).slice(-9),{version:state.doc.meta.version,savedAt:now,summary:summary||action.type}];return{...state,doc:{...newDoc,meta:{...newDoc.meta,updatedAt:now,version:nv,history:hist}},undoStack:[...state.undoStack,state.doc].slice(-MAX_UNDO),redoStack:[],dirty:true};};
  switch(action.type){
    case"UPDATE_PROP":{const{blockId,key,value}=action;const b=state.doc.blocks[blockId];if(!b)return state;return push({...state.doc,blocks:{...state.doc.blocks,[blockId]:{...b,props:{...b.props,[key]:value}}}},`Updated ${BREG[b.type]?.name||b.type}.${key}`);}
    case"UPDATE_DATA":{const{blockId,data}=action;const b=state.doc.blocks[blockId];if(!b)return state;return push({...state.doc,blocks:{...state.doc.blocks,[blockId]:{...b,props:{...b.props,...data}}}},`Updated ${BREG[b.type]?.name} data`);}
    case"TOGGLE_VIS":{const{blockId}=action;const b=state.doc.blocks[blockId];if(!b)return state;const r=BREG[b.type];if(r.status==="required_locked"||r.status==="required_editable")return state;return push({...state.doc,blocks:{...state.doc.blocks,[blockId]:{...b,visible:!b.visible}}},`${b.visible?"Hid":"Showed"} ${r?.name}`);}
    case"CHANGE_PAGE":{const{key,value}=action;return push({...state.doc,page:{...state.doc.page,[key]:value}},`Changed ${key} to ${value}`);}
    case"SWITCH_TPL":{const{tid}=action;const t=TPLS[tid];if(!t)return state;return{...state,doc:mkDoc(tid,t,t.overrides),undoStack:[...state.undoStack,state.doc].slice(-MAX_UNDO),redoStack:[],selectedBlockId:null,dirty:true};}
    case"IMPORT":{const err=validateImport(action.doc);if(err){console.error("Import validation:",err);return state;}return{...state,doc:migrateDoc(action.doc),undoStack:[],redoStack:[],selectedBlockId:null,dirty:false};}
    case"UNDO":{if(!state.undoStack.length)return state;return{...state,doc:state.undoStack[state.undoStack.length-1],undoStack:state.undoStack.slice(0,-1),redoStack:[...state.redoStack,state.doc],dirty:true};}
    case"REDO":{if(!state.redoStack.length)return state;return{...state,doc:state.redoStack[state.redoStack.length-1],undoStack:[...state.undoStack,state.doc],redoStack:state.redoStack.slice(0,-1),dirty:true};}
    case"SELECT":return{...state,selectedBlockId:action.blockId};
    case"SAVED":return{...state,dirty:false};
    default:return state;
  }
}
function initState(){return{doc:mkDoc("single_stat_hero",TPLS.single_stat_hero),undoStack:[],redoStack:[],selectedBlockId:null,dirty:false};}

// ═══════════════════════════════════════════════════════════
// STRUCTURED VALIDATION — chart-aware + layout safety
// ═══════════════════════════════════════════════════════════
function validate(doc){
  const R={errors:[],warnings:[],info:[],passed:[]};
  const blocks=Object.values(doc.blocks).filter(b=>b.visible);
  const types=blocks.map(b=>b.type);
  const sz=SIZES[doc.page.size]||SIZES.instagram_1080;

  // Required blocks
  ["source_footer","brand_stamp","headline_editorial"].forEach(req=>{
    if(types.includes(req))R.passed.push(`${BREG[req].name} present`);
    else R.errors.push(`${BREG[req].name} is required`);
  });
  // Empty content
  const hl=blocks.find(b=>b.type==="headline_editorial");
  if(hl&&!(hl.props.text||"").trim())R.errors.push("Headline is empty");
  const hs=blocks.find(b=>b.type==="hero_stat");
  if(hs&&!(hs.props.value||"").trim())R.errors.push("Hero number is empty");
  // Char/line limits
  blocks.forEach(b=>{const reg=BREG[b.type];if(!reg?.cst?.maxChars)return;const txt=(b.props.text||b.props.value||"").replace(/\n/g,""),mx=reg.cst.maxChars;if(txt.length>mx)R.errors.push(`${reg.name}: ${txt.length}/${mx} OVERFLOW`);else if(txt.length>mx*.9)R.warnings.push(`${reg.name}: ${txt.length}/${mx} chars`);});
  blocks.forEach(b=>{const reg=BREG[b.type];if(!reg?.cst?.maxLines)return;const lines=(b.props.text||"").split("\n").length;if(lines>reg.cst.maxLines)R.warnings.push(`${reg.name}: ${lines}/${reg.cst.maxLines} lines`);});
  // Slot compatibility
  doc.sections.forEach(sec=>{sec.blockIds.forEach(bid=>{const b=doc.blocks[bid];if(!b)return;const reg=BREG[b.type];if(reg&&!reg.allowedSections.includes(sec.type))R.errors.push(`${reg.name} not allowed in ${sec.type}`);});const counts={};sec.blockIds.forEach(bid=>{const b=doc.blocks[bid];if(!b||!b.visible)return;counts[b.type]=(counts[b.type]||0)+1;});Object.entries(counts).forEach(([t,c])=>{const reg=BREG[t];if(reg?.maxPerSection&&c>reg.maxPerSection)R.warnings.push(`${reg.name}: ${c}x in ${sec.type} (max ${reg.maxPerSection})`);});});

  // ── CHART-AWARE VALIDATION (Stage 2 Polish) ──
  blocks.forEach(b=>{
    if(b.type==="bar_horizontal"){
      const items=b.props.items||[];
      if(!items.length)R.errors.push("Ranked Bars: no data items");
      if(items.some(i=>typeof i.value!=="number"||isNaN(i.value)))R.errors.push("Ranked Bars: NaN value detected");
      if(items.some(i=>!i.label?.trim()))R.warnings.push("Ranked Bars: item missing label");
      if(items.length>25)R.warnings.push(`Ranked Bars: ${items.length} items — may be dense`);
      if(items.length>30)R.errors.push(`Ranked Bars: ${items.length} items exceeds max 30`);
      // Layout density for small sizes
      if(items.length>10&&(sz.h<800))R.warnings.push("Ranked Bars: too many items for this canvas height");
    }
    if(b.type==="line_editorial"){
      const sr=b.props.series||[],xl=b.props.xLabels||[];
      if(!sr.length)R.errors.push("Line Chart: no series data");
      sr.forEach(s=>{if(!s.data?.length)R.errors.push(`Line Chart: series "${s.label}" has no data`);if(s.data?.some(v=>typeof v!=="number"||isNaN(v)))R.errors.push(`Line Chart: NaN in "${s.label}"`);if(s.data?.length!==xl.length)R.warnings.push(`Line Chart: "${s.label}" has ${s.data?.length} points but ${xl.length} labels`);});
      if(xl.length>12)R.warnings.push(`Line Chart: ${xl.length} x-labels — may overlap`);
    }
    if(b.type==="comparison_kpi"){
      const items=b.props.items||[];
      if(items.length<2)R.errors.push("KPI Compare: need at least 2 items");
      if(items.length>4)R.warnings.push("KPI Compare: more than 4 items may be cramped");
      items.forEach((it,i)=>{if(!it.value?.trim())R.warnings.push(`KPI #${i+1}: empty value`);if(!it.label?.trim())R.warnings.push(`KPI #${i+1}: empty label`);});
    }
    if(b.type==="table_enriched"){
      const cols=b.props.columns||[],rows=b.props.rows||[];
      if(!rows.length)R.errors.push("Visual Table: no rows");
      rows.forEach((r,i)=>{if(r.vals?.length!==cols.length-1)R.warnings.push(`Table row ${i+1}: ${r.vals?.length} values, expected ${cols.length-1}`);});
      if(rows.length>12)R.warnings.push(`Visual Table: ${rows.length} rows — may overflow on ${sz.n}`);
    }
    if(b.type==="small_multiple"){
      const items=b.props.items||[];
      if(!items.length)R.errors.push("Small Multiples: no items");
      items.forEach((it,i)=>{if(!it.data?.length)R.errors.push(`Small Mult #${i+1}: no data`);if(!it.label?.trim())R.warnings.push(`Small Mult #${i+1}: no label`);});
      if(items.length>9)R.warnings.push("Small Multiples: more than 9 cells may be too dense");
    }
  });

  // ── LAYOUT SAFETY (Stage 2 Polish) ──
  // Headline width
  if(hl){const len=(hl.props.text||"").replace(/\n/g,"").length;if(len>60&&len<=80)R.info.push(`Headline ${len} chars — shorter may work better`);const lines=(hl.props.text||"").split("\n");const longest=Math.max(...lines.map(l=>l.length));if(longest>28)R.warnings.push(`Headline line ${longest} chars — may overflow small sizes`);}
  // Source placeholder
  const sf=blocks.find(b=>b.type==="source_footer");
  if(sf&&sf.props.text===BREG.source_footer.dp.text)R.warnings.push("Source is still default");
  // Contrast
  const pal=PALETTES[doc.page.palette];
  if(pal){const hex=pal.p.replace("#",""),r=parseInt(hex.substr(0,2),16),g=parseInt(hex.substr(2,2),16),b2=parseInt(hex.substr(4,2),16),lum=(0.299*r+0.587*g+0.114*b2)/255;if(lum<0.15)R.warnings.push("Primary color may be too dark on dark bg");}
  // Size-specific warnings
  if(sz.h<700&&types.includes("body_annotation"))R.info.push("Annotation may not fit on landscape sizes");
  if(sz.w<1100&&types.includes("table_enriched"))R.warnings.push("Visual Table may be cramped on narrow canvas");

  // Empty annotation
  blocks.forEach(b=>{if(b.type==="body_annotation"&&!(b.props.text||"").trim())R.warnings.push("Annotation block is empty");});

  return R;
}

// ═══════════════════════════════════════════════════════════
// DATA EDITOR COMPONENTS (Stage 2 Polish — structured, not textarea)
// ═══════════════════════════════════════════════════════════
function BarItemsEditor({items,onChange,editable}){
  const upd=(idx,key,val)=>{const next=[...items];next[idx]={...next[idx],[key]:val};onChange(next);};
  const del=(idx)=>onChange(items.filter((_,i)=>i!==idx));
  const add=()=>onChange([...items,{label:"New",value:0,flag:"",highlight:false}]);
  const sty={fontSize:"9px",fontFamily:TK.font.data,background:TK.c.bgSurf,color:TK.c.txtP,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",padding:"3px 5px",outline:"none",boxSizing:"border-box"};
  return(
    <div style={{display:"flex",flexDirection:"column",gap:"3px"}}>
      <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase"}}>DATA ITEMS ({items.length})</div>
      <div style={{maxHeight:"180px",overflowY:"auto"}}>
        {items.map((it,i)=>(
          <div key={i} style={{display:"flex",gap:"2px",alignItems:"center",marginBottom:"2px"}}>
            <input value={it.flag||""} onChange={e=>editable&&upd(i,"flag",e.target.value)} style={{...sty,width:"24px",textAlign:"center"}} disabled={!editable} title="Flag"/>
            <input value={it.label} onChange={e=>editable&&upd(i,"label",e.target.value)} style={{...sty,flex:1}} disabled={!editable} title="Label"/>
            <input type="number" value={it.value} onChange={e=>editable&&upd(i,"value",parseFloat(e.target.value)||0)} style={{...sty,width:"50px"}} disabled={!editable} title="Value"/>
            <button onClick={()=>editable&&upd(i,"highlight",!it.highlight)} style={{...sty,background:it.highlight?TK.c.acc+"30":TK.c.bgSurf,color:it.highlight?TK.c.acc:TK.c.txtM,cursor:editable?"pointer":"default",width:"18px",textAlign:"center"}} disabled={!editable} title="Highlight">★</button>
            {editable&&<button onClick={()=>del(i)} style={{...sty,color:TK.c.err,cursor:"pointer",width:"18px",textAlign:"center"}} title="Remove">×</button>}
          </div>
        ))}
      </div>
      {editable&&<button onClick={add} style={{fontSize:"8px",fontFamily:TK.font.data,background:TK.c.bgAct,color:TK.c.acc,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",padding:"3px 8px",cursor:"pointer",width:"100%"}}>+ ADD ITEM</button>}
    </div>
  );
}

function KPIItemsEditor({items,onChange,editable}){
  const upd=(idx,key,val)=>{const next=[...items];next[idx]={...next[idx],[key]:val};onChange(next);};
  const sty={fontSize:"9px",fontFamily:TK.font.data,background:TK.c.bgSurf,color:TK.c.txtP,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",padding:"3px 5px",outline:"none",boxSizing:"border-box"};
  return(
    <div style={{display:"flex",flexDirection:"column",gap:"3px"}}>
      <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase"}}>KPI CARDS ({items.length})</div>
      {items.map((it,i)=>(
        <div key={i} style={{padding:"4px",border:`1px solid ${TK.c.brd}`,borderRadius:"3px",marginBottom:"3px"}}>
          <input value={it.label} onChange={e=>editable&&upd(i,"label",e.target.value)} placeholder="Label" style={{...sty,width:"100%",marginBottom:"2px"}} disabled={!editable}/>
          <div style={{display:"flex",gap:"2px"}}>
            <input value={it.value} onChange={e=>editable&&upd(i,"value",e.target.value)} placeholder="Value" style={{...sty,flex:1}} disabled={!editable}/>
            <input value={it.delta} onChange={e=>editable&&upd(i,"delta",e.target.value)} placeholder="Delta" style={{...sty,flex:1}} disabled={!editable}/>
            <select value={it.direction} onChange={e=>editable&&upd(i,"direction",e.target.value)} style={{...sty,width:"50px"}} disabled={!editable}>
              <option value="positive">↑</option><option value="negative">↓</option><option value="neutral">–</option>
            </select>
          </div>
        </div>
      ))}
    </div>
  );
}

function LineSeriesEditor({series,xLabels,onChange,editable}){
  const updSeries=(idx,key,val)=>{const next=[...series];next[idx]={...next[idx],[key]:val};onChange({series:next,xLabels});};
  const updXL=(val)=>onChange({series,xLabels:val.split(",").map(s=>s.trim())});
  const sty={fontSize:"9px",fontFamily:TK.font.data,background:TK.c.bgSurf,color:TK.c.txtP,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",padding:"3px 5px",outline:"none",boxSizing:"border-box"};
  return(
    <div style={{display:"flex",flexDirection:"column",gap:"4px"}}>
      <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase"}}>X LABELS</div>
      <input value={xLabels.join(", ")} onChange={e=>editable&&updXL(e.target.value)} style={{...sty,width:"100%"}} disabled={!editable} title="Comma-separated labels"/>
      <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",marginTop:"4px"}}>SERIES ({series.length})</div>
      {series.map((s,i)=>(
        <div key={i} style={{padding:"4px",border:`1px solid ${TK.c.brd}`,borderRadius:"3px"}}>
          <div style={{display:"flex",gap:"2px",marginBottom:"2px"}}>
            <input value={s.label} onChange={e=>editable&&updSeries(i,"label",e.target.value)} style={{...sty,flex:1}} disabled={!editable} placeholder="Series name"/>
            <select value={s.role} onChange={e=>editable&&updSeries(i,"role",e.target.value)} style={{...sty,width:"70px"}} disabled={!editable}>
              <option value="primary">Primary</option><option value="benchmark">Benchmark</option><option value="secondary">Secondary</option>
            </select>
          </div>
          <input value={s.data.join(", ")} onChange={e=>editable&&updSeries(i,"data",e.target.value.split(",").map(v=>parseFloat(v.trim())||0))} style={{...sty,width:"100%"}} disabled={!editable} title="Comma-separated values"/>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════
export default function InfographicEditor(){
  const cvs=useRef(null);
  const [state,dispatch]=useReducer(reducer,null,initState);
  const [ltab,setLtab]=useState("templates");
  const [qaOpen,setQaOpen]=useState(true);
  const [qaMode,setQaMode]=useState("publish");
  const [mode,setMode]=useState("design");
  const fileRef=useRef(null);

  const{doc,selectedBlockId:selId,undoStack,redoStack,dirty}=state;
  const pal=PALETTES[doc.page.palette]||PALETTES.housing;
  const sz=SIZES[doc.page.size]||SIZES.instagram_1080;
  const selB=selId?doc.blocks[selId]:null;
  const selR=selB?BREG[selB.type]:null;
  const perms=PERMS[mode]||PERMS.design;

  const vr=useMemo(()=>validate(doc),[doc]);
  const dispErr=qaMode==="publish"?vr.errors:[];
  const errs=vr.errors.length,warns=vr.warnings.length;
  const canExp=errs===0;
  const si=errs>0?"🔴":warns>0?"🟡":"🟢";

  const render=useCallback(()=>{const c=cvs.current;if(!c)return;c.width=sz.w*2;c.height=sz.h*2;c.style.width="100%";c.style.height="auto";const ctx=c.getContext("2d");ctx.setTransform(2,0,0,2,0,0);(BGS[doc.page.background]||BGS.solid_dark).r(ctx,sz.w,sz.h,pal);renderDoc(ctx,doc,sz.w,sz.h,pal);},[doc,pal,sz]);
  useEffect(()=>{render();},[render]);

  const saveDraft=useCallback(()=>{if(!dirty)return;dispatch({type:"SAVED"});},[dirty]);
  useEffect(()=>{const h=e=>{if((e.ctrlKey||e.metaKey)&&e.key==="z"&&!e.shiftKey){e.preventDefault();dispatch({type:"UNDO"});}if((e.ctrlKey||e.metaKey)&&(e.key==="y"||(e.key==="z"&&e.shiftKey))){e.preventDefault();dispatch({type:"REDO"});}if((e.ctrlKey||e.metaKey)&&e.key==="s"){e.preventDefault();saveDraft();}};window.addEventListener("keydown",h);return()=>window.removeEventListener("keydown",h);},[saveDraft]);

  const exportJSON=()=>{const bl=new Blob([JSON.stringify(doc,null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(bl);a.download=`summa-${doc.templateId}-v${doc.meta.version}.json`;a.click();};
  const importJSON=e=>{const f=e.target.files?.[0];if(!f)return;const r=new FileReader();r.onload=ev=>{try{const p=JSON.parse(ev.target.result);const err=validateImport(p);if(err){alert(`Import error: ${err}`);return;}dispatch({type:"IMPORT",doc:p});}catch{alert("Invalid JSON");}};r.readAsText(f);e.target.value="";};
  const exportPNG=()=>{const c=cvs.current;if(!c)return;const a=document.createElement("a");a.href=c.toDataURL("image/png");a.download=`summa-${doc.templateId}-${doc.page.size}.png`;a.click();};

  const canEdit=(reg,k)=>perms.editBlock(reg,k);
  const canToggle=reg=>perms.toggleVisibility(reg);

  const fams={};Object.entries(TPLS).forEach(([id,t])=>{if(!fams[t.fam])fams[t.fam]=[];fams[t.fam].push({id,...t});});
  const tb=a=>({padding:"5px 7px",fontSize:"8px",fontFamily:TK.font.data,textTransform:"uppercase",letterSpacing:"0.4px",cursor:"pointer",background:a?TK.c.bgAct:"transparent",color:a?TK.c.acc:TK.c.txtM,border:"none",borderBottom:a?`2px solid ${TK.c.acc}`:"2px solid transparent",whiteSpace:"nowrap"});
  const badge=st=>{const c={required_locked:TK.c.err,required_editable:TK.c.acc,optional_default:TK.c.pos,optional_available:TK.c.txtM};const l={required_locked:"REQ·🔒",required_editable:"REQ",optional_default:"OPT·ON",optional_available:"OPT"};return{color:c[st]||TK.c.txtM,label:l[st]||st};};

  return(
    <div style={{fontFamily:TK.font.body,background:TK.c.bgApp,color:TK.c.txtP,height:"100vh",display:"flex",flexDirection:"column",overflow:"hidden"}}>
      {/* TOP BAR */}
      <div style={{padding:"6px 12px",borderBottom:`1px solid ${TK.c.brd}`,display:"flex",alignItems:"center",justifyContent:"space-between",flexShrink:0}}>
        <div style={{display:"flex",alignItems:"center",gap:"6px"}}>
          <span style={{fontFamily:TK.font.display,fontWeight:700,color:TK.c.acc,fontSize:"12px"}}>SUMMA</span>
          <span style={{fontFamily:TK.font.display,fontWeight:400,color:TK.c.txtS,fontSize:"12px"}}>VISION</span>
          <span style={{fontSize:"8px",color:TK.c.txtM,fontFamily:TK.font.data,padding:"2px 5px",background:TK.c.bgAct,borderRadius:"2px",marginLeft:"4px"}}>{TPLS[doc.templateId]?.fam} — {TPLS[doc.templateId]?.vr}</span>
          <div style={{display:"flex",gap:"1px",background:TK.c.bgSurf,borderRadius:"3px",padding:"1px",border:`1px solid ${TK.c.brd}`,marginLeft:"6px"}}>
            {["template","design"].map(m=><button key={m} onClick={()=>setMode(m)} style={{padding:"2px 7px",fontSize:"8px",fontFamily:TK.font.data,textTransform:"uppercase",background:mode===m?TK.c.bgAct:"transparent",color:mode===m?TK.c.acc:TK.c.txtM,border:"none",borderRadius:"2px",cursor:"pointer"}}>{m}</button>)}
          </div>
          <div style={{display:"flex",gap:"2px",marginLeft:"8px"}}>
            <button onClick={()=>dispatch({type:"UNDO"})} disabled={!undoStack.length} style={{padding:"2px 6px",fontSize:"10px",background:"transparent",border:"none",color:undoStack.length?TK.c.txtS:TK.c.txtM,cursor:undoStack.length?"pointer":"default",opacity:undoStack.length?1:.3}} title="Undo">↩</button>
            <button onClick={()=>dispatch({type:"REDO"})} disabled={!redoStack.length} style={{padding:"2px 6px",fontSize:"10px",background:"transparent",border:"none",color:redoStack.length?TK.c.txtS:TK.c.txtM,cursor:redoStack.length?"pointer":"default",opacity:redoStack.length?1:.3}} title="Redo">↪</button>
          </div>
          {dirty&&<span style={{fontSize:"7px",color:TK.c.acc,fontFamily:TK.font.data}}>●</span>}
        </div>
        <div style={{display:"flex",alignItems:"center",gap:"5px"}}>
          <span style={{fontSize:"9px"}} title={`${errs}err ${warns}warn`}>{si}</span>
          <span style={{fontSize:"7px",color:TK.c.txtM,fontFamily:TK.font.data}}>v{doc.meta.version}</span>
          <input ref={fileRef} type="file" accept=".json" onChange={importJSON} style={{display:"none"}}/>
          <button onClick={()=>fileRef.current?.click()} style={{padding:"3px 6px",fontSize:"8px",fontFamily:TK.font.data,background:TK.c.bgSurf,color:TK.c.txtS,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",cursor:"pointer"}}>IMPORT</button>
          <button onClick={exportJSON} style={{padding:"3px 6px",fontSize:"8px",fontFamily:TK.font.data,background:TK.c.bgSurf,color:TK.c.txtS,border:`1px solid ${TK.c.brd}`,borderRadius:"2px",cursor:"pointer"}}>JSON</button>
          <button onClick={saveDraft} disabled={!dirty} style={{padding:"3px 6px",fontSize:"8px",fontFamily:TK.font.data,background:dirty?TK.c.pos:TK.c.bgSurf,color:dirty?TK.c.bgApp:TK.c.txtM,border:`1px solid ${dirty?TK.c.pos:TK.c.brd}`,borderRadius:"2px",cursor:dirty?"pointer":"default",fontWeight:dirty?700:400,opacity:dirty?1:.5}} title="Ctrl+S">SAVE</button>
          <button onClick={exportPNG} disabled={!canExp} style={{padding:"3px 7px",fontSize:"8px",fontFamily:TK.font.data,background:canExp?TK.c.acc:TK.c.txtM,color:TK.c.bgApp,border:"none",borderRadius:"2px",cursor:canExp?"pointer":"not-allowed",fontWeight:700,opacity:canExp?1:.5}}>EXPORT</button>
        </div>
      </div>

      <div style={{display:"flex",flex:1,overflow:"hidden"}}>
        {/* LEFT */}
        <div style={{width:"220px",minWidth:"220px",borderRight:`1px solid ${TK.c.brd}`,display:"flex",flexDirection:"column"}}>
          <div style={{display:"flex",borderBottom:`1px solid ${TK.c.brd}`}}>
            {[["templates","Tpl"],["blocks","Blk"],["theme","Thm"]].map(([k,l])=><button key={k} onClick={()=>setLtab(k)} style={tb(ltab===k)}>{l}</button>)}
          </div>
          <div style={{flex:1,overflowY:"auto",padding:"8px"}}>
            {ltab==="templates"&&Object.entries(fams).map(([f,ts])=>(
              <div key={f} style={{marginBottom:"10px"}}>
                <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",letterSpacing:"0.4px",marginBottom:"3px"}}>{f}</div>
                {ts.map(t=><button key={t.id} onClick={()=>perms.switchTemplate&&dispatch({type:"SWITCH_TPL",tid:t.id})} disabled={!perms.switchTemplate} style={{display:"block",width:"100%",textAlign:"left",padding:"6px 8px",marginBottom:"2px",background:doc.templateId===t.id?TK.c.bgAct:TK.c.bgSurf,border:`1px solid ${doc.templateId===t.id?TK.c.acc+"40":TK.c.brd}`,borderRadius:"4px",cursor:perms.switchTemplate?"pointer":"not-allowed",color:TK.c.txtP,opacity:(!perms.switchTemplate&&doc.templateId!==t.id)?0.4:1}}>
                  <div style={{fontSize:"10px",fontWeight:500}}>{t.vr}</div>
                  <div style={{fontSize:"8px",color:TK.c.txtM,marginTop:"1px"}}>{t.desc}</div>
                </button>)}
              </div>
            ))}
            {ltab==="blocks"&&doc.sections.map(sec=>(
              <div key={sec.id} style={{marginBottom:"6px"}}>
                <div style={{fontSize:"7px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",padding:"2px 0"}}>{sec.type}</div>
                {sec.blockIds.map(bid=>{const b=doc.blocks[bid];if(!b)return null;const r=BREG[b.type],bd=badge(r.status);return(
                  <div key={bid} style={{display:"flex",alignItems:"center",gap:"3px",marginBottom:"1px"}}>
                    <button onClick={()=>dispatch({type:"SELECT",blockId:bid})} style={{flex:1,display:"flex",alignItems:"center",gap:"4px",textAlign:"left",padding:"4px 6px",fontSize:"9px",background:selId===bid?TK.c.bgAct:"transparent",border:selId===bid?`1px solid ${TK.c.acc}30`:"1px solid transparent",borderRadius:"3px",cursor:"pointer",color:b.visible?TK.c.txtP:TK.c.txtM,textDecoration:b.visible?"none":"line-through",opacity:b.visible?1:.5}}>
                      <span style={{fontSize:"6px",color:bd.color}}>{bd.label}</span><span>{r.name}</span>
                    </button>
                    {canToggle(r)&&<button onClick={()=>dispatch({type:"TOGGLE_VIS",blockId:bid})} style={{background:"none",border:"none",color:b.visible?TK.c.pos:TK.c.txtM,cursor:"pointer",fontSize:"10px",padding:"2px 4px"}}>{b.visible?"◉":"○"}</button>}
                  </div>
                );})}
              </div>
            ))}
            {ltab==="theme"&&(
              <>
                <div style={{marginBottom:"10px"}}>
                  <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",marginBottom:"3px"}}>Palette</div>
                  {Object.entries(PALETTES).map(([k,v])=><button key={k} onClick={()=>perms.changePalette&&dispatch({type:"CHANGE_PAGE",key:"palette",value:k})} style={{display:"flex",alignItems:"center",gap:"6px",width:"100%",textAlign:"left",padding:"4px 6px",marginBottom:"1px",fontSize:"9px",background:doc.page.palette===k?TK.c.bgAct:"transparent",border:doc.page.palette===k?`1px solid ${TK.c.acc}30`:"1px solid transparent",borderRadius:"3px",cursor:perms.changePalette?"pointer":"not-allowed",color:TK.c.txtP,opacity:perms.changePalette?1:0.5}}><div style={{width:"10px",height:"10px",borderRadius:"2px",background:v.p}}/>{v.n}</button>)}
                </div>
                <div style={{marginBottom:"10px"}}>
                  <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",marginBottom:"3px"}}>Background</div>
                  {Object.entries(BGS).map(([k,v])=><button key={k} onClick={()=>perms.changeBackground&&dispatch({type:"CHANGE_PAGE",key:"background",value:k})} style={{display:"block",width:"100%",textAlign:"left",padding:"4px 6px",marginBottom:"1px",fontSize:"9px",background:doc.page.background===k?TK.c.bgAct:"transparent",border:doc.page.background===k?`1px solid ${TK.c.acc}30`:"1px solid transparent",borderRadius:"3px",cursor:perms.changeBackground?"pointer":"not-allowed",color:TK.c.txtP,opacity:perms.changeBackground?1:0.5}}>{v.n}</button>)}
                </div>
                <div>
                  <div style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",marginBottom:"3px"}}>Size</div>
                  {Object.entries(SIZES).map(([k,v])=><button key={k} onClick={()=>dispatch({type:"CHANGE_PAGE",key:"size",value:k})} style={{display:"block",width:"100%",textAlign:"left",padding:"4px 6px",marginBottom:"1px",fontSize:"9px",background:doc.page.size===k?TK.c.bgAct:"transparent",border:doc.page.size===k?`1px solid ${TK.c.acc}30`:"1px solid transparent",borderRadius:"3px",cursor:"pointer",color:TK.c.txtP}}>{v.n} <span style={{color:TK.c.txtM}}>{v.w}×{v.h}</span></button>)}
                </div>
              </>
            )}
          </div>
          <div style={{padding:"4px 8px",borderTop:`1px solid ${TK.c.brd}`,fontSize:"7px",fontFamily:TK.font.data,color:TK.c.txtM}}>
            v{doc.schemaVersion} · {doc.sections.length}sec · {Object.keys(doc.blocks).length}blk
          </div>
        </div>

        {/* CENTER */}
        <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>
          <div style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",padding:"10px",background:`repeating-conic-gradient(${TK.c.bgSurf} 0% 25%, ${TK.c.bgApp} 0% 50%) 50% / 12px 12px`,overflow:"auto"}}>
            <div style={{maxWidth:"720px",width:"100%",boxShadow:"0 6px 32px rgba(0,0,0,0.5)",borderRadius:"2px",overflow:"hidden"}}>
              <canvas ref={cvs} style={{display:"block"}}/>
            </div>
          </div>
          {qaOpen?(
            <div style={{padding:"5px 12px",borderTop:`1px solid ${TK.c.brd}`,background:TK.c.bgSurf,flexShrink:0}}>
              <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"3px"}}>
                <span style={{fontSize:"7px",fontFamily:TK.font.data,color:TK.c.txtS,textTransform:"uppercase"}}>QA</span>
                <div style={{display:"flex",gap:"1px",background:TK.c.bgApp,borderRadius:"2px",padding:"1px"}}>
                  {["draft","publish"].map(m=><button key={m} onClick={()=>setQaMode(m)} style={{padding:"1px 6px",fontSize:"7px",fontFamily:TK.font.data,textTransform:"uppercase",background:qaMode===m?TK.c.bgAct:"transparent",color:qaMode===m?TK.c.acc:TK.c.txtM,border:"none",borderRadius:"2px",cursor:"pointer"}}>{m}</button>)}
                </div>
                <button onClick={()=>setQaOpen(false)} style={{marginLeft:"auto",background:"none",border:"none",color:TK.c.txtM,cursor:"pointer",fontSize:"9px"}}>✕</button>
              </div>
              <div style={{display:"flex",gap:"8px",overflowX:"auto",paddingBottom:"2px",flexWrap:"wrap"}}>
                {vr.passed.map((m,i)=><span key={`p${i}`} style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.pos,whiteSpace:"nowrap"}}>✅{m}</span>)}
                {dispErr.map((m,i)=><span key={`e${i}`} style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.err,whiteSpace:"nowrap"}}>❌{m}</span>)}
                {vr.warnings.map((m,i)=><span key={`w${i}`} style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.acc,whiteSpace:"nowrap"}}>⚠️{m}</span>)}
                {vr.info.map((m,i)=><span key={`i${i}`} style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,whiteSpace:"nowrap"}}>ℹ️{m}</span>)}
              </div>
            </div>
          ):(
            <button onClick={()=>setQaOpen(true)} style={{padding:"2px 12px",borderTop:`1px solid ${TK.c.brd}`,background:TK.c.bgSurf,border:"none",color:TK.c.txtM,cursor:"pointer",fontSize:"7px",fontFamily:TK.font.data,textAlign:"left",flexShrink:0}}>{si} QA</button>
          )}
        </div>

        {/* RIGHT INSPECTOR */}
        <div style={{width:"250px",minWidth:"250px",borderLeft:`1px solid ${TK.c.brd}`,display:"flex",flexDirection:"column"}}>
          <div style={{padding:"7px 10px",borderBottom:`1px solid ${TK.c.brd}`,fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtS,textTransform:"uppercase",letterSpacing:"0.3px",display:"flex",justifyContent:"space-between"}}>
            <span>Inspector {selR?`· ${selR.name}`:""}</span>
            {mode==="template"&&<span style={{color:TK.c.acc,fontSize:"7px"}}>TPL</span>}
          </div>
          <div style={{flex:1,overflowY:"auto",padding:"8px 10px"}}>
            {!selB&&<div style={{fontSize:"10px",color:TK.c.txtM,padding:"20px 0",textAlign:"center",lineHeight:1.6}}>Select a block<br/>from Blocks tab</div>}
            {selB&&selR&&(
              <div style={{display:"flex",flexDirection:"column",gap:"10px"}}>
                <div style={{display:"flex",gap:"6px",alignItems:"center"}}>
                  {(()=>{const b=badge(selR.status);return<span style={{fontSize:"8px",fontFamily:TK.font.data,color:b.color,padding:"2px 6px",background:TK.c.bgAct,borderRadius:"2px"}}>{b.label}</span>;})()}
                  {!selB.visible&&<span style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM}}>HIDDEN</span>}
                </div>

                {/* Standard controls */}
                {selR.ctrl.map(c=>{const ed=canEdit(selR,c.k);return(
                  <div key={c.k} style={{opacity:ed?1:.4}}>
                    <label style={{fontSize:"8px",fontFamily:TK.font.data,color:TK.c.txtM,textTransform:"uppercase",letterSpacing:"0.3px",display:"block",marginBottom:"2px"}}>
                      {c.l}{c.ml&&<span style={{float:"right",color:((selB.props[c.k]||"")+"").replace(/\n/g,"").length>c.ml*.9?TK.c.acc:TK.c.txtM}}>{((selB.props[c.k]||"")+"").replace(/\n/g,"").length}/{c.ml}</span>}
                    </label>
                    {c.t==="text"&&<input type="text" value={selB.props[c.k]??""} onChange={e=>ed&&dispatch({type:"UPDATE_PROP",blockId:selId,key:c.k,value:e.target.value})} maxLength={c.ml} disabled={!ed} style={{width:"100%",padding:"5px 7px",fontSize:"10px",fontFamily:TK.font.body,background:TK.c.bgSurf,color:TK.c.txtP,border:`1px solid ${TK.c.brd}`,borderRadius:"3px",outline:"none",boxSizing:"border-box"}}/>}
                    {c.t==="textarea"&&<textarea value={selB.props[c.k]??""} onChange={e=>ed&&dispatch({type:"UPDATE_PROP",blockId:selId,key:c.k,value:e.target.value})} maxLength={c.ml} rows={2} disabled={!ed} style={{width:"100%",padding:"5px 7px",fontSize:"10px",fontFamily:TK.font.body,background:TK.c.bgSurf,color:TK.c.txtP,border:`1px solid ${TK.c.brd}`,borderRadius:"3px",outline:"none",resize:"vertical",boxSizing:"border-box"}}/>}
                    {c.t==="seg"&&<div style={{display:"flex",gap:"1px",background:TK.c.bgSurf,borderRadius:"3px",padding:"1px",border:`1px solid ${TK.c.brd}`}}>{c.opts.map(o=><button key={o} onClick={()=>ed&&dispatch({type:"UPDATE_PROP",blockId:selId,key:c.k,value:o})} disabled={!ed} style={{flex:1,padding:"3px 2px",fontSize:"8px",fontFamily:TK.font.data,background:selB.props[c.k]===o?TK.c.bgAct:"transparent",color:selB.props[c.k]===o?TK.c.acc:TK.c.txtM,border:"none",borderRadius:"2px",cursor:ed?"pointer":"not-allowed",textTransform:"uppercase"}}>{o}</button>)}</div>}
                    {c.t==="toggle"&&<button onClick={()=>ed&&dispatch({type:"UPDATE_PROP",blockId:selId,key:c.k,value:!selB.props[c.k]})} disabled={!ed} style={{padding:"4px 8px",fontSize:"9px",fontFamily:TK.font.data,background:selB.props[c.k]?TK.c.acc+"20":TK.c.bgSurf,color:selB.props[c.k]?TK.c.acc:TK.c.txtM,border:`1px solid ${selB.props[c.k]?TK.c.acc+"40":TK.c.brd}`,borderRadius:"3px",cursor:ed?"pointer":"not-allowed",width:"100%",textAlign:"left"}}>{selB.props[c.k]?"✓ On":"○ Off"}</button>}
                  </div>
                );})}

                {/* ── STRUCTURED DATA EDITORS (Stage 2 Polish) ── */}
                {selB.type==="bar_horizontal"&&(
                  <BarItemsEditor items={selB.props.items||[]} onChange={items=>canEdit(selR,"items")&&dispatch({type:"UPDATE_DATA",blockId:selId,data:{items}})} editable={canEdit(selR,"items")}/>
                )}
                {selB.type==="comparison_kpi"&&(
                  <KPIItemsEditor items={selB.props.items||[]} onChange={items=>canEdit(selR,"items")&&dispatch({type:"UPDATE_DATA",blockId:selId,data:{items}})} editable={canEdit(selR,"items")}/>
                )}
                {selB.type==="line_editorial"&&(
                  <LineSeriesEditor series={selB.props.series||[]} xLabels={selB.props.xLabels||[]} onChange={data=>canEdit(selR,"series")&&dispatch({type:"UPDATE_DATA",blockId:selId,data})} editable={canEdit(selR,"series")}/>
                )}

                <div style={{marginTop:"4px",padding:"5px 7px",background:TK.c.bgSurf,borderRadius:"3px",fontSize:"7px",fontFamily:TK.font.data,color:TK.c.txtM,lineHeight:1.6}}>
                  <span style={{color:TK.c.txtS}}>TYPE</span> {selB.type} <span style={{color:TK.c.txtS}}>STATUS</span> {selR.status}<br/>
                  <span style={{color:TK.c.txtS}}>SECTIONS</span> {selR.allowedSections.join(",")} <span style={{color:TK.c.txtS}}>MAX</span> {selR.maxPerSection||"∞"}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
