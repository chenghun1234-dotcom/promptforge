import os
import re
import time
import requests
from datetime import datetime, timezone

from groq import Groq


DEFAULT_MODEL = "llama-3.3-70b-versatile"


def get_trending_topics() -> list[str]:
	return ["Cyberpunk Cyberwear for Zepeto", "Isometric 3D Room for Roblox"]


def generate_pro_post(client: Groq, topic: str) -> str:
	prompt = f"""
Create a professional AI prompt guide for: '{topic}'.
The target audience is pro creators selling digital assets.
Write in English. Include:
1. Title (SEO optimized)
2. Pro Prompt (Main prompt + Negative prompt)
3. Technical Settings (Sampler, CFG, Steps)
4. Monetization Tip (How to sell this asset)
Output format: Markdown with a Frontmatter.
Frontmatter fields:
- title (string)
- description (string)
- date (ISO 8601 string)
- tags (array of strings)
- model (string)
- prompt (string)
- negativePrompt (string)
- sampler (string)
- cfg (number)
- steps (number)
- monetizationTip (string)
"""

	model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
	temperature = float(os.environ.get("GROQ_TEMPERATURE", "0.6"))
	max_retries = int(os.environ.get("GROQ_MAX_RETRIES", "3"))
	default_wait = float(os.environ.get("GROQ_RETRY_DEFAULT_SECONDS", "180"))

	def parse_wait_seconds(message: str) -> float:
		m = re.search(r"Please try again in (?:(\d+)m)?([0-9.]+)s", message)
		if m:
			mins = float(m.group(1) or 0)
			secs = float(m.group(2) or 0)
			return mins * 60 + secs
		return default_wait

	for _ in range(max_retries):
		try:
			chat_completion = client.chat.completions.create(
				model=model,
				messages=[{"role": "user", "content": prompt}],
				temperature=temperature,
			)
			return chat_completion.choices[0].message.content
		except Exception as e:
			msg = str(e)
			if "rate_limit" in msg or "Rate limit" in msg or "429" in msg:
				wait = parse_wait_seconds(msg)
				print(f"Rate limited. Waiting {wait:.1f}s before retry.")
				time.sleep(wait)
				continue
			raise
	raise RuntimeError("Failed to generate due to rate limits")


def slugify(value: str) -> str:
	value = value.strip().lower()
	value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
	value = re.sub(r"[\s_-]+", "-", value)
	value = re.sub(r"^-+|-+$", "", value)
	return value or "untitled"


def ensure_frontmatter(content: str, topic: str, model: str) -> str:
	keys = [
		"title",
		"description",
		"date",
		"tags",
		"model",
		"prompt",
		"negativePrompt",
		"sampler",
		"cfg",
		"steps",
		"monetizationTip",
		"image",
	]

	def escape(value: str) -> str:
		return value.replace("\\", "\\\\").replace('"', '\\"')

	def unquote(value: str) -> str:
		value = value.strip()
		if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
			return value[1:-1].strip()
		return value

	def normalize_scalar(value: str) -> str:
		value = unquote(value)
		value = re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()
		return value

	def normalize_frontmatter_text(text: str) -> str:
		for k in keys:
			text = re.sub(rf"(?<!^)(?<!\n)\b{re.escape(k)}\s*:", f"\n{k}:", text)
		return text

	def parse_frontmatter(text: str) -> dict:
		text = normalize_frontmatter_text(text)
		positions: list[tuple[int, str, int]] = []
		for k in keys:
			m = re.search(rf"(?m)^\s*{re.escape(k)}\s*:\s*", text)
			if m:
				positions.append((m.start(), k, m.end()))
		positions.sort(key=lambda x: x[0])
		data: dict = {}
		for idx, (start, k, end) in enumerate(positions):
			next_start = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
			raw = text[end:next_start].strip()
			if k == "tags":
				lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
				tags: list[str] = []
				for ln in lines:
					m_tag = re.match(r"^\s*-\s*(.+?)\s*$", ln)
					if m_tag:
						tags.append(normalize_scalar(m_tag.group(1)))
				if not tags:
					raw_inline = normalize_scalar(raw)
					if raw_inline.startswith("[") and raw_inline.endswith("]"):
						inner = raw_inline[1:-1].strip()
						if inner:
							tags = [normalize_scalar(x) for x in inner.split(",") if x.strip()]
				data[k] = tags
				continue
			data[k] = normalize_scalar(raw)
		return data

	def split_frontmatter_and_body(full: str) -> tuple[str | None, str]:
		if not full.lstrip().startswith("---"):
			return None, full
		lines = full.splitlines()
		if not lines:
			return None, full
		start = None
		for i in range(len(lines)):
			if lines[i].strip() == "---":
				start = i
				break
		if start is None:
			return None, full
		end = None
		for i in range(start + 1, len(lines)):
			if lines[i].strip() == "---":
				end = i
				break
		if end is None:
			return None, full
		fm = "\n".join(lines[start + 1 : end]).strip()
		body = "\n".join(lines[end + 1 :]).lstrip()
		return fm, body

	now = datetime.now(timezone.utc).isoformat()
	title = topic.strip() or "PromptForge"
	existing_fm, body = split_frontmatter_and_body(content)
	parsed = parse_frontmatter(existing_fm) if existing_fm is not None else {}

	tags_value = parsed.get("tags", [])
	if not isinstance(tags_value, list):
		tags_value = []

	def quote(value: str) -> str:
		return f'"{escape(value)}"'

	cfg_value = parsed.get("cfg")
	steps_value = parsed.get("steps")
	try:
		cfg_num = float(cfg_value) if cfg_value is not None and str(cfg_value).strip() != "" else None
	except ValueError:
		cfg_num = None
	try:
		steps_num = int(float(steps_value)) if steps_value is not None and str(steps_value).strip() != "" else None
	except ValueError:
		steps_num = None

	model_value = parsed.get("model") or model
	prompt_value = parsed.get("prompt") or ""
	neg_value = parsed.get("negativePrompt") or ""
	sampler_value = parsed.get("sampler") or ""
	desc_value = parsed.get("description") or f"Forged prompt guide for {title}"
	mon_value = parsed.get("monetizationTip") or ""
	image_value = parsed.get("image") or ""

	fm_lines = [
		"---",
		f"title: {quote(parsed.get('title') or title)}",
		f"description: {quote(desc_value)}",
		f'date: "{now}"',
		"tags:",
	]
	for tag in tags_value:
		if isinstance(tag, str) and tag.strip():
			fm_lines.append(f"  - {tag}")
	fm_lines.extend(
		[
			f"model: {quote(str(model_value))}",
			f"prompt: {quote(str(prompt_value))}",
			f"negativePrompt: {quote(str(neg_value))}",
			f"sampler: {quote(str(sampler_value))}",
		]
	)
	if cfg_num is not None:
		fm_lines.append(f"cfg: {cfg_num}")
	if steps_num is not None:
		fm_lines.append(f"steps: {steps_num}")
	fm_lines.append(f"monetizationTip: {quote(str(mon_value))}")
	if str(image_value).strip():
		fm_lines.append(f"image: {quote(str(image_value))}")
	fm_lines.append("---")
	fm_lines.append("")

	return "\n".join(fm_lines) + (body if body else content.lstrip())


def fetch_top_ai_assets() -> list[dict]:
	url = "https://civitai.com/api/v1/images?limit=10&sort=Most%20Reactions&period=Day"
	headers = {"User-Agent": "PromptForge-Bot/1.0"}
	try:
		resp = requests.get(url, headers=headers, timeout=30)
		if resp.status_code != 200:
			return []
		data = resp.json()
		items = data.get("items", [])
		results: list[dict] = []
		for item in items:
			meta = item.get("meta") or {}
			prompt = meta.get("prompt")
			neg = meta.get("negativePrompt", "")
			sampler = meta.get("sampler", "Euler a")
			cfg = meta.get("cfgScale", 7)
			steps = meta.get("steps", 20)
			image_url = item.get("url")
			if prompt and image_url:
				results.append(
					{
						"image_url": image_url,
						"prompt": str(prompt)[:1000],
						"negative_prompt": str(neg)[:600],
						"sampler": str(sampler),
						"cfg_scale": cfg,
						"steps": steps,
					}
				)
			if len(results) >= 3:
				break
		return results
	except Exception:
		return []


def generate_pro_markdown(client: Groq, asset: dict) -> str:
	now_date = datetime.now(timezone.utc).date().isoformat()
	system_prompt = (
		f"You are an elite AI Prompt Engineer and Digital Asset Monetization Expert.\n"
		f"I will give you raw generation data. Convert it into a highly professional markdown post for 'PromptForge'.\n\n"
		f"Raw Data:\n"
		f"- Image URL: {asset.get('image_url','')}\n"
		f"- Prompt: {asset.get('prompt','')}\n"
		f"- Negative Prompt: {asset.get('negative_prompt','')}\n"
		f"- Settings: Sampler: {asset.get('sampler','')}, CFG: {asset.get('cfg_scale','')}, Steps: {asset.get('steps','')}\n\n"
		f"Output Format (Strictly follow this Markdown structure):\n"
		f"---\n"
		f'title: "[Catchy SEO Title based on the prompt style]"\n'
		f'date: "{now_date}"\n'
		f'image: "{asset.get("image_url","")}"\n'
		f'tags: ["AI Asset", "Prompt", "Monetization"]\n'
		f"---\n\n"
		f"## 🎯 Asset Overview\n"
		f"[Write 2-3 sentences explaining why this style is highly profitable right now (e.g., Zepeto, Stock Photo, Game UI)]\n\n"
		f"## ⚙️ The Forge (Prompt & Settings)\n"
		f"**Core Prompt:** ```text\n{asset.get('prompt','')}\n```\n\n"
		f"**Negative Prompt:**\n```text\n{asset.get('negative_prompt','')}\n```\n\n"
		f"| Setting | Value |\n|---|---|\n"
		f"| Sampler | {asset.get('sampler','')} |\n"
		f"| CFG Scale | {asset.get('cfg_scale','')} |\n"
		f"| Steps | {asset.get('steps','')} |\n\n"
		f"## 💰 Monetization Strategy\n"
		f"[Provide 1 actionable tip on how to sell images generated with this prompt on platforms like Adobe Stock, Unity Asset Store, or Zepeto]\n"
	)

	model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
	temperature = float(os.environ.get("GROQ_TEMPERATURE", "0.7"))
	max_retries = int(os.environ.get("GROQ_MAX_RETRIES", "3"))
	default_wait = float(os.environ.get("GROQ_RETRY_DEFAULT_SECONDS", "150"))

	def parse_wait_seconds(message: str) -> float:
		m = re.search(r"Please try again in (?:(\d+)m)?([0-9.]+)s", message)
		if m:
			mins = float(m.group(1) or 0)
			secs = float(m.group(2) or 0)
			return mins * 60 + secs
		return default_wait

	for _ in range(max_retries):
		try:
			chat_completion = client.chat.completions.create(
				model=model,
				messages=[{"role": "user", "content": system_prompt}],
				temperature=temperature,
			)
			return chat_completion.choices[0].message.content
		except Exception as e:
			msg = str(e)
			if "rate_limit" in msg or "Rate limit" in msg or "429" in msg:
				wait = parse_wait_seconds(msg)
				print(f"Rate limited. Waiting {wait:.1f}s before retry.")
				time.sleep(wait)
				continue
			raise
	raise RuntimeError("Failed to generate due to rate limits")


def filename_from_content(content: str) -> str:
	m = re.search(r'^\s*title\s*:\s*"(.*?)"\s*$', content, re.MULTILINE)
	if m:
		title = m.group(1).strip()
		slug = slugify(title)
		return slug or f"forge-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
	return f"forge-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def save_to_content(content: str, filename: str) -> str:
	project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	path = os.path.join(project_root, "src", "content", "prompts", f"{filename}.md")
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, "w", encoding="utf-8", newline="\n") as f:
		f.write(content)
	return path


def main() -> None:
	api_key = os.environ.get("GROQ_API_KEY")
	if not api_key:
		raise RuntimeError("GROQ_API_KEY is not set")

	sleep_seconds = float(os.environ.get("GROQ_SLEEP_SECONDS", "10"))
	model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
	client = Groq(api_key=api_key)

	assets = fetch_top_ai_assets()
	if assets:
		for index, asset in enumerate(assets):
			post_content = generate_pro_markdown(client, asset)
			post_content = ensure_frontmatter(post_content, "PromptForge", model)
			filename = filename_from_content(post_content)
			output_path = save_to_content(post_content, filename)
			print(f"Successfully forged: {output_path}")
			if index != len(assets) - 1:
				time.sleep(sleep_seconds)
	else:
		topics = get_trending_topics()
		for index, topic in enumerate(topics):
			slug = slugify(topic)
			post_content = generate_pro_post(client, topic)
			post_content = ensure_frontmatter(post_content, topic, model)
			output_path = save_to_content(post_content, slug)
			print(f"Successfully forged: {output_path}")
			if index != len(topics) - 1:
				time.sleep(sleep_seconds)


if __name__ == "__main__":
	main()
