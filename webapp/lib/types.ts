// v2 contract — sector -> tech practice -> location -> company -> department -> tools.

export interface Role {
  role_title: string;
  department: string;
  team: string;
  seniority: string;
  tools: string[];
  practices: string[];
  city: string;
  location: string;
  posted_date: string;
  aging_days: number | null;
  source_url: string;
}

export interface Field {
  summary: string;
  sources?: string[];
}

export interface NewsItem {
  category: string;
  title: string;
  url: string;
  date: string;
  source: string;
}

export interface Company {
  slug: string;
  name: string;
  sector: string;
  region: string;
  website: string;
  career_url: string;
  ats: string | null;
  total: number;
  insight: string[];
  partnership_signals: string[];
  vision_shifts: string[];
  practices: [string, number][];   // across tech space (ranked)
  departments: [string, number][];
  tools: [string, number][];
  seniority: [string, number][];
  locations: [string, number][];
  fields: Record<string, Field>;
  news: NewsItem[];
}

export interface SectorRow {
  name: string;
  roles: number;
  companies: { slug: string; name: string; roles: number }[];
}

export interface DemandMatrix {
  sectors: { name: string; total: number }[];
  practices: { name: string; total: number }[];
  cells: [number, number, number][];   // [sectorIdx, practiceIdx, roleCount]
}

export interface Data {
  generated: string;
  month_label: string;
  window: number;
  totals: { companies: number; roles: number; sectors: number; with_roles: number };
  names: Record<string, string>;
  regions: Record<string, string>;
  field_labels: Record<string, string>;
  sectors: SectorRow[];
  practices: { name: string; roles: number }[];
  locations: { city: string; roles: number }[];
  demand_matrix: DemandMatrix;
  tech_radar: { practice: string; value: number }[];
  companies: Company[];
  roles_by_company: Record<string, Role[]>;
}
