import type { Palette } from '../types';

export const PALETTES: Record<string, Palette> = {
  housing:    { n: "Housing",    p: "#22D3EE", s: "#3B82F6", a: "#FBBF24", pos: "#0D9488", neg: "#F43F5E" },
  government: { n: "Government", p: "#3B82F6", s: "#A78BFA", a: "#FBBF24", pos: "#0D9488", neg: "#F43F5E" },
  energy:     { n: "Energy",     p: "#2DD4BF", s: "#0D9488", a: "#F97316", pos: "#2DD4BF", neg: "#F43F5E" },
  society:    { n: "Society",    p: "#A78BFA", s: "#22D3EE", a: "#FBBF24", pos: "#0D9488", neg: "#F43F5E" },
  economy:    { n: "Markets",    p: "#F97316", s: "#FBBF24", a: "#3B82F6", pos: "#0D9488", neg: "#F43F5E" },
  neutral:    { n: "Neutral",    p: "#94A3B8", s: "#8B949E", a: "#FBBF24", pos: "#0D9488", neg: "#F43F5E" },
};
