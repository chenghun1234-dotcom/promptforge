import { execSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const MIN_POST_COUNT = Number(process.env.MIN_POST_COUNT || 70);

function run(command) {
	return execSync(command, {
		stdio: 'pipe',
		encoding: 'utf8',
	}).trim();
}

function checkPostCount() {
	const promptsDir = resolve(process.cwd(), 'src', 'content', 'prompts');
	const mdFiles = readdirSync(promptsDir).filter((name) => name.endsWith('.md'));
	const count = mdFiles.length;

	if (count < MIN_POST_COUNT) {
		throw new Error(`Post count check failed: ${count} < ${MIN_POST_COUNT}`);
	}

	console.log(`✅ Post count check passed: ${count} posts`);
}

function checkAffiliateIntegrity() {
	run('node scripts/validate_affiliate.mjs');
	console.log('✅ Affiliate integrity check passed');
}

function checkBuild() {
	run('npx astro build');
	console.log('✅ Build check passed');
}

function main() {
	console.log('Running PromptForge health check...');
	checkPostCount();
	checkAffiliateIntegrity();
	checkBuild();
	console.log('✅ All health checks passed');
}

main();
