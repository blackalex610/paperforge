import type { Scene } from './components/SceneRenderer';

export interface Question {
  number: number;
  question: string;
  topic: string;
  difficulty: string;
  diagram: boolean;
  diagram_config: Scene | null;
  open_parts: string[] | null;
  options: string[] | null;
  correct_answer?: string | string[];
  solution?: string | null;
  partial_credit?: Record<string, number> | null;
  points: number[];
  kind: 'mc' | 'short' | 'open';
  template: string;
  section: 'part1' | 'part2';
}

export interface Paper {
  exam_id: string;
  questions: Question[];
  difficulty: string;
  difficulty_label: string;
  blueprint: string;
  blueprint_label: string;
  part1_count: number;
  part1_minutes: number;
  part2_minutes: number;
  total_points: number;
  scale_notice_before: number | null;
  scale_notice: string;
  meta: {
    engine: string;
    seed: number;
    generation_ms: number;
    verified: boolean;
    warnings: string[];
    template_count: number;
  };
}
