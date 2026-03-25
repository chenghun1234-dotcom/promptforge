import os
import re
import time
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
