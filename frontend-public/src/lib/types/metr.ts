/** TypeScript types mirroring backend METR API response schemas. */

export interface METRComponents {
  federal_tax: number;
  provincial_tax: number;
  cpp: number;
  cpp2: number;
  ei: number;
  ohp: number;
  ccb: number;
  gst_credit: number;
  cwb: number;
  provincial_benefits: number;
}

export interface METRCalculateResponse {
  gross_income: number;
  net_income: number;
  metr: number;
  zone: string;
  keep_per_dollar: number;
  components: METRComponents;
}

export interface CurvePoint {
  gross: number;
  net: number;
  metr: number;
  zone: string;
}

export interface DeadZone {
  start: number;
  end: number;
  peak_metr: number;
}

export interface Peak {
  gross: number;
  metr: number;
}

export interface Annotation {
  gross: number;
  metr: number;
  label: string;
}

export interface METRCurveResponse {
  province: string;
  family_type: string;
  n_children: number;
  children_under_6: number;
  curve: CurvePoint[];
  dead_zones: DeadZone[];
  peak: Peak;
  annotations: Annotation[];
}

export interface ProvinceCompareItem {
  province: string;
  metr: number;
  zone: string;
}

export interface METRCompareResponse {
  income: number;
  family_type: string;
  provinces: ProvinceCompareItem[];
}

export type Province = 'ON' | 'BC' | 'AB' | 'QC';

export type FamilyType = 'single' | 'single_parent' | 'couple';

export interface METRCalculateParams {
  income: number;
  province?: Province;
  family_type?: FamilyType;
  n_children?: number;
  children_under_6?: number;
}

export interface METRCurveParams {
  province?: Province;
  family_type?: FamilyType;
  n_children?: number;
  children_under_6?: number;
  income_min?: number;
  income_max?: number;
  step?: number;
}
