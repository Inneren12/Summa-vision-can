import { TK } from '../config/tokens';
import type { BlockRenderer, RenderResult } from './types';

function rr(x: number, y: number, w: number, height: number, overflow = false, warnings: string[] = []): RenderResult {
  return {
    height,
    overflow,
    warnings,
    hitArea: { x, y, w, h: height },
  };
}

export const BR: Record<string, BlockRenderer> = {

  eyebrow_tag(ctx, p, x, y, w, h, pal, s) {
    ctx.font = `500 ${11 * s}px ${TK.font.data}`;
    ctx.fillStyle = TK.c.txtM;
    ctx.textAlign = "left";
    ctx.fillText(p.text || "", x, y + 14 * s);
    return rr(x, y, w, 20 * s);
  },

  headline_editorial(ctx, p, x, y, w, h, pal, s) {
    ctx.font = `700 ${42 * s}px ${TK.font.display}`;
    ctx.fillStyle = TK.c.txtP;
    const al = p.align || "left";
    ctx.textAlign = al;
    const ax = al === "center" ? x + w / 2 : al === "right" ? x + w : x;

    const maxW = w * 0.95;
    const manualLines = (p.text || "").split("\n");
    const allLines: string[] = [];

    manualLines.forEach((line: string) => {
      if (ctx.measureText(line).width <= maxW) {
        allLines.push(line);
        return;
      }
      const words = line.split(" ");
      let buffer = "";
      words.forEach((word: string) => {
        const test = buffer ? buffer + " " + word : word;
        if (ctx.measureText(test).width > maxW && buffer) {
          allLines.push(buffer);
          buffer = word;
        } else {
          buffer = test;
        }
      });
      if (buffer) allLines.push(buffer);
    });

    const warnings: string[] = [];
    let overflow = false;
    const consumedHeight = (allLines.length * 50 + 10) * s;
    if (consumedHeight > h) {
      overflow = true;
      warnings.push(`Headline needs ~${Math.round(consumedHeight)}px but only ${Math.round(h)}px available`);
    }

    allLines.forEach((line, i) => {
      ctx.fillText(line, ax, y + 42 * s + i * 50 * s);
    });

    return rr(x, y, w, consumedHeight, overflow, warnings);
  },

  subtitle_descriptor(ctx, p, x, y, w, h, pal, s) {
    if (!p.text) return rr(x, y, w, 0);
    ctx.font = `400 ${16 * s}px ${TK.font.body}`;
    ctx.fillStyle = TK.c.txtS;
    ctx.textAlign = "center";
    const maxW = w * 0.9;
    const words = (p.text as string).split(" ");
    let line = "";
    let lineCount = 0;
    words.forEach((word: string) => {
      const test = line + word + " ";
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line.trim(), x + w / 2, y + 18 * s + lineCount * 22 * s);
        line = word + " ";
        lineCount++;
      } else {
        line = test;
      }
    });
    if (line) {
      ctx.fillText(line.trim(), x + w / 2, y + 18 * s + lineCount * 22 * s);
      lineCount++;
    }
    return rr(x, y, w, (lineCount * 22 + 10) * s);
  },

  hero_stat(ctx, p, x, y, w, h, pal, s) {
    if (!p.value) return rr(x, y, w, 0);
    ctx.strokeStyle = pal.p + "30";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, y - 10 * s);
    ctx.lineTo(x + w, y - 10 * s);
    ctx.stroke();
    ctx.font = `700 ${120 * s}px ${TK.font.data}`;
    ctx.fillStyle = pal.p;
    ctx.textAlign = "center";
    ctx.fillText(p.value, x + w / 2, y + 100 * s);
    const nw = ctx.measureText(p.value).width;
    ctx.fillStyle = TK.c.acc;
    ctx.fillRect(x + w / 2 - nw / 2, y + 110 * s, nw, 3 * s);
    if (p.label) {
      ctx.font = `400 ${16 * s}px ${TK.font.body}`;
      ctx.fillStyle = TK.c.txtS;
      ctx.textAlign = "center";
      ctx.fillText(p.label, x + w / 2, y + 140 * s);
    }
    return rr(x, y, w, 150 * s);
  },

  delta_badge(ctx, p, x, y, w, h, pal, s) {
    if (!p.value) return rr(x, y, w, 0);
    ctx.font = `700 ${14 * s}px ${TK.font.data}`;
    ctx.fillStyle = p.direction === "negative" ? pal.neg : p.direction === "positive" ? pal.pos : TK.c.txtS;
    ctx.textAlign = "center";
    ctx.fillText(p.value, x + w / 2, y + 16 * s);
    return rr(x, y, w, 24 * s);
  },

  body_annotation(ctx, p, x, y, w, h, pal, s) {
    if (!p.text) return rr(x, y, w, 0);
    ctx.font = `400 ${13 * s}px ${TK.font.body}`;
    ctx.fillStyle = TK.c.txtS;
    ctx.textAlign = "center";
    const mw = w * .8;
    const words = (p.text as string).split(" ");
    let ln = "";
    let lc = 0;
    words.forEach((wd: string) => {
      const t = ln + wd + " ";
      if (ctx.measureText(t).width > mw && ln) {
        ctx.fillText(ln.trim(), x + w / 2, y + 16 * s + lc * 20 * s);
        ln = wd + " ";
        lc++;
      } else {
        ln = t;
      }
    });
    if (ln) {
      ctx.fillText(ln.trim(), x + w / 2, y + 16 * s + lc * 20 * s);
      lc++;
    }

    const warnings: string[] = [];
    let overflow = false;
    const consumedHeight = (lc * 20 + 10) * s;
    if (consumedHeight > h) {
      overflow = true;
      warnings.push(`Annotation needs ~${Math.round(consumedHeight)}px but only ${Math.round(h)}px available`);
    }

    return rr(x, y, w, consumedHeight, overflow, warnings);
  },

  source_footer(ctx, p, x, y, w, h, pal, s) {
    ctx.font = `500 ${10 * s}px ${TK.font.data}`;
    ctx.fillStyle = TK.c.txtM;
    ctx.textAlign = "left";
    if (p.text) ctx.fillText(p.text, x, y + 12 * s);
    if (p.methodology) ctx.fillText(p.methodology, x, y + 26 * s);
    return rr(x, y, w, 30 * s);
  },

  brand_stamp(ctx, p, x, y, w, h, pal, s) {
    const pos = p.position || "bottom-right";
    const bx = pos === "bottom-left" ? x + 8 * s : x + w - 8 * s;
    ctx.textAlign = pos === "bottom-left" ? "left" : "right";
    ctx.font = `700 ${16 * s}px ${TK.font.display}`;
    ctx.fillStyle = TK.c.acc;
    ctx.fillText("SUMMA", bx, y + 16 * s);
    const sw = ctx.measureText("SUMMA").width;
    ctx.font = `400 ${16 * s}px ${TK.font.display}`;
    ctx.fillStyle = TK.c.txtS;
    ctx.fillText("VISION", bx + (pos === "bottom-left" ? sw + 4 * s : -(sw + 4 * s)), y + 16 * s);
    return rr(x, y, w, 20 * s);
  },

  bar_horizontal(ctx, p, x, y, w, h, pal, s) {
    const items = p.items || [];
    if (!items.length) return rr(x, y, w, 0);

    const warnings: string[] = [];
    let overflow = false;

    const unit = p.unit || "";
    const mx = Math.max(...items.map((i: any) => i.value), 0.001);
    const lW = 110 * s;
    const cL = x + lW;
    const cW = w - lW;
    const bH = Math.min((h / items.length) * .65, 30 * s);
    const gap = h / items.length;

    items.forEach((it: any, i: number) => {
      const by = y + i * gap + (gap - bH) / 2;
      const bW = (it.value / mx) * cW * .82;
      ctx.font = `500 ${13 * s}px ${TK.font.body}`;
      ctx.fillStyle = TK.c.txtS;
      ctx.textAlign = "right";
      ctx.fillText(`${it.flag || ""} ${it.label}`, cL - 12 * s, by + bH / 2 + 5 * s);
      ctx.fillStyle = it.highlight ? pal.p : pal.p + "50";
      ctx.beginPath();
      ctx.roundRect(cL, by, bW, bH, [0, 2 * s, 2 * s, 0]);
      ctx.fill();
      ctx.font = `700 ${12 * s}px ${TK.font.data}`;
      ctx.fillStyle = TK.c.txtP;
      ctx.textAlign = "left";
      ctx.fillText(`${it.value}${unit}`, cL + bW + 8 * s, by + bH / 2 + 4 * s);
    });

    const bvRaw = p.benchmarkValue;
    const bvNum = typeof bvRaw === "number" ? bvRaw : typeof bvRaw === "string" ? parseFloat(bvRaw) : NaN;
    if (p.showBenchmark && Number.isFinite(bvNum)) {
      const bx2 = cL + (bvNum / mx) * cW * .82;
      ctx.setLineDash([4 * s, 4 * s]);
      ctx.strokeStyle = TK.c.acc + "80";
      ctx.lineWidth = 1.5 * s;
      ctx.beginPath();
      ctx.moveTo(bx2, y - 8 * s);
      ctx.lineTo(bx2, y + h + 8 * s);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = `500 ${10 * s}px ${TK.font.data}`;
      ctx.fillStyle = TK.c.acc;
      ctx.textAlign = "center";
      ctx.fillText(p.benchmarkLabel || "", bx2, y - 14 * s);
    }

    const neededHeight = items.length * 35 * s;
    if (neededHeight > h) {
      overflow = true;
      warnings.push(`${items.length} bars need ~${Math.round(neededHeight)}px but only ${Math.round(h)}px available`);
    }

    return rr(x, y, w, h, overflow, warnings);
  },

  line_editorial(ctx, p, x, y, w, h, pal, s) {
    const sr = p.series || [];
    const xl = p.xLabels || [];
    const yu = p.yUnit || "%";
    if (!sr.length) return rr(x, y, w, 0);

    const warnings: string[] = [];
    let overflow = false;

    const cL = x;
    const cR = x + w - 70 * s;
    const cB = y + h - 30 * s;
    const cW = cR - cL;
    const cH = cB - y;

    const av = sr.flatMap((l: any) => l.data);
    const yMn = Math.floor(Math.min(...av) - 1);
    const yMx = Math.ceil(Math.max(...av) + 1);
    const yR = Math.max(yMx - yMn, 0.1);

    for (let i = 0; i <= 5; i++) {
      const v = yMn + (yR * i / 5);
      const ly = cB - (i / 5) * cH;
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cL, ly);
      ctx.lineTo(cR, ly);
      ctx.stroke();
      ctx.font = `500 ${10 * s}px ${TK.font.data}`;
      ctx.fillStyle = TK.c.txtM;
      ctx.textAlign = "right";
      ctx.fillText(`${v.toFixed(1)}${yu}`, cL - 6 * s, ly + 4 * s);
    }

    ctx.textAlign = "center";
    xl.forEach((lb: string, i: number) => {
      const xPos = xl.length > 1 ? i / (xl.length - 1) : 0;
      ctx.fillText(lb, cL + xPos * cW, cB + 18 * s);
    });

    sr.forEach((line: any) => {
      const col = line.role === "primary" ? pal.p : line.role === "benchmark" ? TK.c.acc : pal.s;
      ctx.strokeStyle = col;
      ctx.lineWidth = (line.role === "primary" ? 2.5 : 1.5) * s;
      if (line.role === "benchmark") ctx.setLineDash([6 * s, 4 * s]);
      else ctx.setLineDash([]);

      ctx.beginPath();
      line.data.forEach((v: number, i: number) => {
        const xFrac = line.data.length > 1 ? i / (line.data.length - 1) : 0;
        const lx = cL + xFrac * cW;
        const ly = cB - ((v - yMn) / yR) * cH;
        i === 0 ? ctx.moveTo(lx, ly) : ctx.lineTo(lx, ly);
      });
      ctx.stroke();
      ctx.setLineDash([]);

      if (line.role === "primary" && p.showArea) {
        ctx.fillStyle = col + "15";
        ctx.beginPath();
        line.data.forEach((v: number, i: number) => {
          const xFrac = line.data.length > 1 ? i / (line.data.length - 1) : 0;
          const lx = cL + xFrac * cW;
          const ly = cB - ((v - yMn) / yR) * cH;
          i === 0 ? ctx.moveTo(lx, ly) : ctx.lineTo(lx, ly);
        });
        ctx.lineTo(cR, cB);
        ctx.lineTo(cL, cB);
        ctx.closePath();
        ctx.fill();
      }

      const lv = line.data[line.data.length - 1];
      const elx = cR + 8 * s;
      const ely = cB - ((lv - yMn) / yR) * cH;
      ctx.font = `700 ${10 * s}px ${TK.font.data}`;
      ctx.fillStyle = col;
      ctx.textAlign = "left";
      ctx.fillText(`${lv}${yu}`, elx, ely - 2 * s);
      ctx.font = `400 ${9 * s}px ${TK.font.body}`;
      ctx.fillText(line.label, elx, ely + 10 * s);
    });

    const neededHeight = sr.length > 0 ? 250 * s : 0;
    if (neededHeight > h) {
      overflow = true;
      warnings.push(`Line chart needs ~${Math.round(neededHeight)}px but only ${Math.round(h)}px available`);
    }

    return rr(x, y, w, h, overflow, warnings);
  },

  comparison_kpi(ctx, p, x, y, w, h, pal, s) {
    const items = p.items || [];
    if (!items.length) return rr(x, y, w, 0);

    const colW = w / items.length;
    items.forEach((st: any, i: number) => {
      const cx = x + colW * i + colW / 2;
      if (i > 0) {
        ctx.strokeStyle = TK.c.brd;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x + colW * i, y);
        ctx.lineTo(x + colW * i, y + h);
        ctx.stroke();
      }
      ctx.font = `500 ${13 * s}px ${TK.font.body}`;
      ctx.fillStyle = TK.c.txtS;
      ctx.textAlign = "center";
      ctx.fillText(st.label, cx, y + 20 * s);
      ctx.font = `700 ${48 * s}px ${TK.font.data}`;
      ctx.fillStyle = TK.c.txtP;
      ctx.fillText(st.value, cx, y + 78 * s);
      const vw = ctx.measureText(st.value).width;
      ctx.fillStyle = pal.p;
      ctx.fillRect(cx - vw / 2, y + 86 * s, vw, 3 * s);
      ctx.font = `700 ${13 * s}px ${TK.font.data}`;
      ctx.fillStyle = st.direction === "positive" ? pal.pos : pal.neg;
      ctx.fillText(st.delta, cx, y + 112 * s);
    });

    return rr(x, y, w, h);
  },

  table_enriched(ctx, p, x, y, w, h, pal, s) {
    const cols = p.columns || [];
    const rows = p.rows || [];
    if (!rows.length) return rr(x, y, w, 0);

    const warnings: string[] = [];

    const colW = w / (cols.length + 1);
    const rowH = Math.min(36 * s, h / (rows.length + 1));

    ctx.font = `600 ${9 * s}px ${TK.font.data}`;
    ctx.fillStyle = TK.c.txtS;
    ctx.textAlign = "center";
    cols.forEach((c: string, i: number) =>
      ctx.fillText(c, x + colW * (i + 1) + colW / 2, y + 12 * s)
    );

    rows.forEach((row: any, ri: number) => {
      const ry = y + 20 * s + ri * rowH;

      if (ri % 2 === 0) {
        ctx.fillStyle = "rgba(255,255,255,0.02)";
        ctx.fillRect(x, ry, w, rowH);
      }

      ctx.font = `700 ${11 * s}px ${TK.font.data}`;
      ctx.fillStyle = pal.p;
      ctx.textAlign = "right";
      ctx.fillText(`${row.rank}`, x + 18 * s, ry + rowH / 2 + 4 * s);

      ctx.font = `500 ${11 * s}px ${TK.font.body}`;
      ctx.fillStyle = TK.c.txtP;
      ctx.textAlign = "left";
      ctx.fillText(`${row.flag} ${row.country}`, x + 24 * s, ry + rowH / 2 + 4 * s);

      row.vals.forEach((v: any, ci: number) => {
        const ccx = x + colW * (ci + 1) + colW / 2;
        const isScore = ci === row.vals.length - 1;

        if (isScore) {
          const n = v / 100;
          ctx.fillStyle = `rgba(${Math.round(255 * (1 - n))},${Math.round(255 * n * .6)},80,0.15)`;
        } else {
          const n = Math.min((typeof v === "number" ? v : 0) / 38, 1);
          ctx.fillStyle = `rgba(${Math.round(147 + n * 80)},${Math.round(130 - n * 60)},${Math.round(220 - n * 100)},0.12)`;
        }
        ctx.fillRect(ccx - colW / 2 + 2 * s, ry + 1 * s, colW - 4 * s, rowH - 2 * s);

        ctx.font = isScore ? `700 ${11 * s}px ${TK.font.data}` : `500 ${10 * s}px ${TK.font.data}`;
        ctx.fillStyle = isScore ? TK.c.txtP : TK.c.txtS;
        ctx.textAlign = "center";
        ctx.fillText(typeof v === "number" ? v.toFixed(isScore ? 1 : 0) : v, ccx, ry + rowH / 2 + 4 * s);
      });
    });

    const neededHeight = rows.length * rowH + 20 * s;
    const overflow = neededHeight > h;
    if (overflow) {
      warnings.push(`${rows.length} rows overflow section by ~${Math.round(neededHeight - h)}px`);
    }

    return rr(x, y, w, h, overflow, warnings);
  },

  small_multiple(ctx, p, x, y, w, h, pal, s) {
    const items = p.items || [];
    const yU = p.yUnit || "%";
    if (!items.length) return rr(x, y, w, 0);

    const warnings: string[] = [];

    const gc = 3;
    const gr = Math.ceil(items.length / gc);
    const cW = w / gc;
    const cH = h / gr;
    const cp = 14 * s;

    const aV = items.flatMap((i: any) => i.data);
    const yMn = Math.min(...aV) - 1;
    const yMx = Math.max(0, ...aV) + .5;
    const yR = Math.max(yMx - yMn, 0.1);

    items.forEach((it: any, idx: number) => {
      const col = idx % gc;
      const row = Math.floor(idx / gc);
      const cx = x + col * cW;
      const cy = y + row * cH;
      const chL = cx + cp;
      const chR = cx + cW - cp;
      const chB = cy + cH - 10 * s;
      const chW2 = chR - chL;
      const chH2 = chB - (cy + 28 * s);

      ctx.strokeStyle = TK.c.brd;
      ctx.lineWidth = 1;
      ctx.strokeRect(cx + 3 * s, cy + 3 * s, cW - 6 * s, cH - 6 * s);

      ctx.font = `600 ${13 * s}px ${TK.font.body}`;
      ctx.fillStyle = TK.c.txtP;
      ctx.textAlign = "left";
      ctx.fillText(it.label, chL, cy + 20 * s);
      ctx.textAlign = "right";
      ctx.fillText(it.flag, chR, cy + 20 * s);

      const zY = chB - ((0 - yMn) / yR) * chH2;
      ctx.strokeStyle = "rgba(255,255,255,0.1)";
      ctx.beginPath();
      ctx.moveTo(chL, zY);
      ctx.lineTo(chR, zY);
      ctx.stroke();
      ctx.font = `500 ${8 * s}px ${TK.font.data}`;
      ctx.fillStyle = TK.c.txtM;
      ctx.textAlign = "right";
      ctx.fillText("0%", chL - 3 * s, zY + 3 * s);

      ctx.strokeStyle = pal.p;
      ctx.lineWidth = 2 * s;
      ctx.beginPath();
      it.data.forEach((v: number, i: number) => {
        const xFrac = it.data.length > 1 ? i / (it.data.length - 1) : 0;
        const lx = chL + xFrac * chW2;
        const ly = chB - ((v - yMn) / yR) * chH2;
        i === 0 ? ctx.moveTo(lx, ly) : ctx.lineTo(lx, ly);
      });
      ctx.stroke();

      const lv = it.data[it.data.length - 1];
      ctx.font = `700 ${9 * s}px ${TK.font.data}`;
      ctx.fillStyle = pal.neg;
      ctx.textAlign = "right";
      ctx.fillText(`${lv.toFixed(1)}${yU}`, chR, chB - ((lv - yMn) / yR) * chH2 - 6 * s);
    });

    const neededHeight = Math.ceil(items.length / 3) * 160 * s;
    const overflow = neededHeight > h;
    if (overflow) {
      warnings.push(`${items.length} cells need ~${Math.round(neededHeight)}px but only ${Math.round(h)}px available`);
    }

    return rr(x, y, w, h, overflow, warnings);
  },
};
