/** XML 1.0 payload encoding for future test reports; original raw stays separate. */
export function escapeXml10(value) {
  let result = '';
  for (const character of String(value)) {
    const code = character.codePointAt(0);
    const valid = code === 9 || code === 10 || code === 13
      || (code >= 0x20 && code <= 0xd7ff)
      || (code >= 0xe000 && code <= 0xfffd)
      || (code >= 0x10000 && code <= 0x10ffff);
    if (!valid) result += `\\u${code.toString(16).toUpperCase().padStart(4, '0')}`;
    else if (code === 9 || code === 10 || code === 13) result += `&#x${code.toString(16).toUpperCase()};`;
    else result += ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[character] ?? character;
  }
  return result;
}

/** All emitted nodes count; runner/not-executed nodes must be supplied explicitly. */
export function renderJUnit({ name, cases }) {
  if (!Array.isArray(cases)) throw new TypeError('JUnit cases must be an array');
  for (let index = 0; index < cases.length; index++) {
    if (!Object.hasOwn(cases, index)) throw new TypeError(`Sparse JUnit cases at index ${index}`);
  }
  const counts = { tests: cases.length, failures: 0, errors: 0, skipped: 0 };
  const nodes = cases.map(item => {
    if (!['passed', 'failure', 'error', 'skipped'].includes(item.outcome)) throw new TypeError('Unknown JUnit outcome');
    if (!Number.isFinite(item.timeSeconds) || item.timeSeconds < 0) throw new TypeError('Invalid JUnit duration');
    if (item.outcome === 'failure') counts.failures++;
    if (item.outcome === 'error') counts.errors++;
    if (item.outcome === 'skipped') counts.skipped++;
    const payload = item.outcome === 'passed' ? '' : `<${item.outcome}>${escapeXml10(item.message ?? '')}</${item.outcome}>`;
    return `<testcase name="${escapeXml10(item.name)}" time="${item.timeSeconds}">${payload}</testcase>`;
  });
  return `<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="${escapeXml10(name)}" tests="${counts.tests}" failures="${counts.failures}" errors="${counts.errors}" skipped="${counts.skipped}">${nodes.join('')}</testsuite>\n`;
}
