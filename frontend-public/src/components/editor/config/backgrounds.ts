import type { BackgroundEntry } from '../types';

export const BGS: Record<string, BackgroundEntry> = {
  solid_dark:{n:"Solid Dark",r:(c,w,h)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);}},
  gradient_midnight:{n:"Midnight",r:(c,w,h)=>{const g=c.createLinearGradient(0,0,0,h);g.addColorStop(0,"#0B0D11");g.addColorStop(1,"#1C1F26");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  gradient_warm:{n:"Warm Glow",r:(c,w,h,p)=>{const g=c.createLinearGradient(0,0,w*.5,h);g.addColorStop(0,"#0B0D11");g.addColorStop(1,(p?.p ?? "#FBBF24")+"15");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  gradient_radial:{n:"Radial",r:(c,w,h,p)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);const g=c.createRadialGradient(w*.5,h*.6,0,w*.5,h*.6,w*.6);g.addColorStop(0,(p?.p ?? "#FBBF24")+"12");g.addColorStop(1,"transparent");c.fillStyle=g;c.fillRect(0,0,w,h);}},
  dot_grid:{n:"Dot Grid",r:(c,w,h)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);c.fillStyle="rgba(255,255,255,0.04)";for(let x=0;x<w;x+=24)for(let y=0;y<h;y+=24){c.beginPath();c.arc(x,y,1,0,Math.PI*2);c.fill();}}},
  topo:{n:"Topographic",r:(c,w,h,p)=>{c.fillStyle="#0B0D11";c.fillRect(0,0,w,h);c.strokeStyle=(p?.p ?? "#FBBF24")+"08";c.lineWidth=1;for(let i=0;i<12;i++){const cx=w*(.3+Math.sin(i*1.2)*.3),cy=h*(.3+Math.cos(i*.8)*.3);for(let r=30;r<200;r+=25){c.beginPath();c.ellipse(cx,cy,r*1.5,r,i*.3,0,Math.PI*2);c.stroke();}}}},
};
