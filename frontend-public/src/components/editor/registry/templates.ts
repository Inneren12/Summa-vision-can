import type { CanonicalDocument, TemplateEntry, BlockProps } from '../types';
import type { PresetId } from '../config/sizes';
import { BREG } from './blocks';
import { CURRENT_SCHEMA } from './guards';
import { DEFAULT_EXPORT_PRESETS, SIZES } from '../config/sizes';
import { normalizeBlockData } from '../validation/block-data';

export function mkDoc(tid: string, tpl: TemplateEntry, over: Record<string, BlockProps> = {}): CanonicalDocument {
  const blocks: CanonicalDocument['blocks'] = {};
  let seq = 0;
  const now = new Date().toISOString();

  const sections = tpl.sections.map(sec => {
    const blockIds = sec.blockTypes.map(bt => {
      const reg = BREG[bt];
      if (!reg) {
        // Surface template config errors at construction time instead of
        // crashing cryptically later when the renderer tries to read props.
        throw new Error(`Unknown block type "${bt}" referenced in template "${tid}"`);
      }
      const id = `blk_${String(++seq).padStart(3, "0")}`;
      const rawProps = { ...reg.dp, ...(tpl.overrides?.[bt] || {}), ...(over[bt] || {}) };
      const normalized = normalizeBlockData(bt, rawProps, id);
      blocks[id] = {
        id,
        type: bt,
        props: normalized.props,
        visible: true,
      };
      return id;
    });
    return { id: sec.id, type: sec.type, blockIds };
  });

  return {
    schemaVersion: CURRENT_SCHEMA,
    templateId: tid,
    page: {
      // PR#2 fix1 (P1.2): `PageConfig.size` is now `PresetId`. Templates
      // declare `defaultSize` as a free string (legacy registry shape), so
      // narrow it through the SIZES table and fall back to the canonical
      // default when the registry value is missing or unknown.
      size: (tpl.defaultSize && tpl.defaultSize in SIZES
        ? (tpl.defaultSize as PresetId)
        : "instagram_1080"),
      background: tpl.defaultBg || "gradient_warm",
      palette: tpl.defaultPal || "housing",
      exportPresets: [...DEFAULT_EXPORT_PRESETS],
    },
    sections,
    blocks,
    meta: { createdAt: now, updatedAt: now, version: 1, history: [] },
    review: {
      workflow: "draft",
      history: [
        {
          ts: now,
          action: "created",
          summary: "Document created",
          author: "you",
          fromWorkflow: null,
          toWorkflow: "draft",
        },
      ],
      comments: [],
    },
  };
}

export const TPLS: Record<string, TemplateEntry> = {
  single_stat_hero:{fam:"Single Stat Hero",vr:"Number + Delta",variantKey:"number_plus_delta",desc:"Giant number with change",descKey:"giant_number_with_change",defaultPal:"housing",defaultBg:"gradient_warm",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}]},
  single_stat_note:{fam:"Single Stat Hero",vr:"Number + Note",variantKey:"number_plus_note",desc:"Number with annotation",descKey:"number_with_annotation",defaultPal:"housing",defaultBg:"gradient_radial",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"context",type:"context",blockTypes:["body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{body_annotation:{text:"Rates represent posted rates from chartered banks."}}},
  single_stat_minimal:{fam:"Single Stat Hero",vr:"Minimal",variantKey:"minimal",desc:"Clean, centered",descKey:"clean_centered",defaultPal:"neutral",defaultBg:"solid_dark",defaultSize:"twitter_landscape",sections:[{id:"header",type:"header",blockTypes:["headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Bank of Canada\nHolds Rates Steady",align:"center"},hero_stat:{value:"4.50%",label:"Overnight rate"},source_footer:{text:"Source: Bank of Canada"}}},
  stat_comparison:{fam:"Single Stat Hero",vr:"Before / After",variantKey:"before_after",desc:"Two numbers contrasted",descKey:"two_numbers_contrasted",defaultPal:"economy",defaultBg:"gradient_midnight",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor","body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Cost of Living\nOutpaces Wages"},eyebrow_tag:{text:"INSIGHT \u00B7 ECONOMY \u00B7 2026"},hero_stat:{value:"$74K",label:"Median household income"},delta_badge:{value:"+2.1% vs +4.8% CPI",direction:"negative"},subtitle_descriptor:{text:"Income grew 2.1% while cost of living rose 4.8%"},body_annotation:{text:"The gap between wage growth and inflation has widened for 3 consecutive years."},source_footer:{text:"Source: Statistics Canada, Labour Force Survey"}}},
  insight_card:{fam:"Insight Card",vr:"Fact + Context",variantKey:"fact_context",desc:"Key insight with analysis",descKey:"key_insight_with_analysis",defaultPal:"government",defaultBg:"gradient_warm",defaultSize:"instagram_portrait",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat","delta_badge"]},{id:"context",type:"context",blockTypes:["body_annotation"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Federal Deficit\nReaches Record High"},eyebrow_tag:{text:"CHARTED: \u00B7 FISCAL POLICY"},hero_stat:{value:"$61.9B",label:"Projected deficit"},delta_badge:{value:"+$21.8B vs estimate",direction:"negative"},body_annotation:{text:"PBO projects deficit 40% higher than forecast."},source_footer:{text:"Source: Parliamentary Budget Officer, March 2026"}}},
  social_quote:{fam:"Insight Card",vr:"Social Post",variantKey:"social_post",desc:"Shareable stat",descKey:"shareable_stat",defaultPal:"society",defaultBg:"dot_grid",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["headline_editorial"]},{id:"hero",type:"hero",blockTypes:["hero_stat"]},{id:"context",type:"context",blockTypes:["subtitle_descriptor"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Canada Added More People\nThan Any Year in History",align:"center"},hero_stat:{value:"1.27M",label:"Net population growth, 2025"},subtitle_descriptor:{text:"Equivalent to adding Calgary in one year"},source_footer:{text:"Source: Statistics Canada"}}},
  ranked_bar_simple:{fam:"Ranked Bars",vr:"Simple Ranking",variantKey:"simple_ranking",desc:"Horizontal bars by value",descKey:"horizontal_bars_by_value",defaultPal:"housing",defaultBg:"gradient_midnight",defaultSize:"reddit_standard",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["bar_horizontal"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Housing Price-to-Income Ratio\nAcross Major Canadian Cities"},eyebrow_tag:{text:"RANKED: \u00B7 HOUSING AFFORDABILITY \u00B7 Q4 2025"},source_footer:{text:"Source: CMHC, Q4 2025"}}},
  line_area:{fam:"Line Editorial",vr:"Single + Area",variantKey:"single_plus_area",desc:"Time series with area fill",descKey:"time_series_with_area_fill",defaultPal:"government",defaultBg:"gradient_warm",defaultSize:"twitter_landscape",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["line_editorial"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Canada's Inflation Journey:\nFrom Pandemic to New Normal"},eyebrow_tag:{text:"CHARTED: \u00B7 CPI \u00B7 2019\u20132026"},source_footer:{text:"Source: Statistics Canada"}}},
  comparison_3kpi:{fam:"Comparison",vr:"3 KPI Cards",variantKey:"three_kpi_cards",desc:"Three metrics side by side",descKey:"three_metrics_side_by_side",defaultPal:"society",defaultBg:"gradient_radial",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["comparison_kpi"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"Record Immigration Drives\nCanada's Population Surge"},eyebrow_tag:{text:"POPULATION GROWTH \u00B7 2025"},source_footer:{text:"Source: Statistics Canada, CMHC"}}},
  visual_table:{fam:"Visual Table",vr:"Heatmap Rankings",variantKey:"heatmap_rankings",desc:"Table with conditional format",descKey:"table_with_conditional_format",defaultPal:"neutral",defaultBg:"solid_dark",defaultSize:"instagram_portrait",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["table_enriched"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"The Best and Worst\nCountries for Taxes"},eyebrow_tag:{text:"RANKED: \u00B7 TAX COMPETITIVENESS \u00B7 2024"},source_footer:{text:"Source: Tax Foundation"}}},
  small_multiples_grid:{fam:"Small Multiples",vr:"2\u00D73 Grid",variantKey:"2x3_grid",desc:"Same chart repeated",descKey:"same_chart_repeated",defaultPal:"economy",defaultBg:"gradient_midnight",defaultSize:"instagram_1080",sections:[{id:"header",type:"header",blockTypes:["eyebrow_tag","headline_editorial"]},{id:"chart",type:"chart",blockTypes:["small_multiple"]},{id:"footer",type:"footer",blockTypes:["source_footer","brand_stamp"]}],overrides:{headline_editorial:{text:"A Rocky Month\nfor Global Stocks"},eyebrow_tag:{text:"CHARTED: \u00B7 EQUITY INDEXES \u00B7 FEB\u2013MAR 2026"},source_footer:{text:"Source: FactSet, The New York Times"}}},
};
