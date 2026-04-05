import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const checks = [
  {
    file: 'src/layouts/Layout.astro',
    mustInclude: [
      'impact-site-verification',
      'trackAffiliateClick',
      'https://www.creativefabrica.com/freebies/ref/22296047/',
    ],
  },
  {
    file: 'src/pages/index.astro',
    mustInclude: [
      'data-affiliate-location="copy_button_next"',
      'https://www.creativefabrica.com/studio/ref/22296047/',
    ],
  },
  {
    file: 'src/pages/prompts/index.astro',
    mustInclude: [
      'data-affiliate-location="sidebar"',
      'https://www.creativefabrica.com/subscriptions/graphics/ai-prompts/ref/22296047/',
    ],
  },
  {
    file: 'src/pages/prompts/[...slug].astro',
    mustInclude: [
      'data-affiliate-location="detail_bottom_cta"',
      'Get Premium Prompt Pack',
    ],
  },
  {
    file: 'src/content/prompts/creating-stunning-anime-art-with-ai.md',
    mustInclude: [
      'blog_bottom_cta',
      'https://www.creativefabrica.com/studio/ref/22296047/',
    ],
  },
];

let failed = false;

for (const check of checks) {
  const fullPath = resolve(process.cwd(), check.file);
  const text = readFileSync(fullPath, 'utf8');

  for (const token of check.mustInclude) {
    if (!text.includes(token)) {
      failed = true;
      console.error(`❌ Affiliate guard failed: ${check.file} is missing: ${token}`);
    }
  }
}

if (failed) {
  console.error('\nAffiliate safety check failed. Build stopped to prevent monetization loss.');
  process.exit(1);
}

console.log('✅ Affiliate safety check passed.');
