import { expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RevisionView } from '../RevisionView';
import type { CreativeRevision } from '../engine';

function qualityRevision(body: Record<string, unknown>): CreativeRevision {
  return { revision_id: 'revision-verify', kind: 'quality', input_revision_refs: [], body };
}

it('renders a skipped benchmark and local self-issued evidence as unmeasured, never as certification', () => {
  render(<RevisionView revision={qualityRevision({
    evaluation_scope: 'capability_benchmark_not_performed',
    precision: 'not_measured',
    benchmark_binding: 'embedded_self_issued',
  })} />);

  // New literals must be readable Chinese, never the raw enum.
  expect(screen.getByText('未执行基准/未测量')).toBeInTheDocument();
  expect(screen.getByText('未测量')).toBeInTheDocument();
  expect(screen.getByText('本地自签（非第三方认证）')).toBeInTheDocument();
  expect(screen.queryByText('capability_benchmark_not_performed')).not.toBeInTheDocument();
  expect(screen.queryByText('embedded_self_issued')).not.toBeInTheDocument();
  expect(screen.queryByText('not_measured')).not.toBeInTheDocument();

  // No pass/measured/certified reading is allowed for these states.
  expect(screen.queryByText(/已认证|已测精度|精度通过/)).not.toBeInTheDocument();
  expect(screen.getByText(/本次未执行能力基准，也没有测量精度/)).toBeInTheDocument();
});
